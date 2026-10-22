"""Version-two objective and a separate, transparent finite-catalog guard.

The guard never selects a different project or question. It verifies the raw
top candidate against every allowed completion of unstated hard constraints.
"""
from functools import lru_cache

import numpy as np

from .domain import (CATALOG, QUESTION_COST, TIME, HARDWARE, EXPERIENCE, Prior,
                     feasible_for, utility, features, feature_names)

V2_MODEL_VERSION = "intentprobe-question-value-2.0"
V2_GENERATOR_VERSION = "project-preferences-2.0"
OBJECTIVE = {"invalid_recommendation": 1.0, "false_no_feasible": 1.0, "question_cost": QUESTION_COST}
HARD_CONSTRAINTS = {"time": TIME, "hardware": HARDWARE, "experience": EXPERIENCE}
CATALOG_INDEX = {item["id"]: i for i, item in enumerate(CATALOG)}


def unchecked_for(item, facts):
    requirements = {"time": item["weeks"], "hardware": item["hardware_level"], "experience": item["experience_level"]}
    # Requirements are monotone thresholds on a finite Cartesian product.
    # The minimum of each allowed coordinate is an exact all-completions check.
    return [key for key, mapping in HARD_CONSTRAINTS.items()
            if facts.get(key) not in mapping and requirements[key] > min(mapping.values())]


def constraint_status(item, facts):
    requirements = {"time": item["weeks"], "hardware": item["hardware_level"], "experience": item["experience_level"]}
    if any(facts.get(key) in mapping and requirements[key] > mapping[facts[key]] for key, mapping in HARD_CONSTRAINTS.items()):
        return "conflict"
    return "unverified" if unchecked_for(item, facts) else "verified"


def constraint_outcome(prior, facts, guarded=True):
    _, feasible, order = prior.rank(facts)
    if not feasible.any():
        return {"status": "no_feasible", "reason": "The stated hard constraints rule out every brief in this catalog. This conclusion assumes the answers are accurate.",
                "project_id": None, "unchecked_constraints": [], "guard_applied": bool(guarded)}
    item = CATALOG[int(order[0])]
    unchecked = unchecked_for(item, facts)
    if guarded and unchecked:
        return {"status": "needs_confirmation", "reason": "The raw top candidate is not feasible for every allowed completion of: " + ", ".join(unchecked) + ". Confirm or revise these constraints; no substitute was selected.",
                "project_id": None, "unchecked_constraints": unchecked, "guard_applied": True}
    return {"status": "recommendation", "reason": ("The raw top candidate is feasible for every allowed completion of the hard constraints. Verification depends on accurate answers; fit is still a synthetic utility estimate." if guarded else "Raw model recommendation before the separate constraint guard."),
            "project_id": item["id"], "unchecked_constraints": unchecked, "guard_applied": bool(guarded)}


def action_metrics(hidden, family, outcome):
    true_feasible = feasible_for(hidden)
    utilities = utility(hidden, family)
    has_feasible = bool(true_feasible.any())
    optimum = float(utilities.max()) if has_feasible else 0.0
    issued = outcome["status"] == "recommendation"
    index = CATALOG_INDEX.get(outcome.get("project_id")) if issued else None
    if issued and index is None:
        raise ValueError("A recommendation must identify a catalog project")
    invalid = int(issued and not true_feasible[index])
    false_no = int(outcome["status"] == "no_feasible" and has_feasible)
    delivered = float(utilities[index]) if issued else 0.0
    regret = max(0.0, optimum - delivered)
    return {"regret": regret, "invalid_recommendation": invalid, "false_no_feasible": false_no,
            "objective_loss": regret + OBJECTIVE["invalid_recommendation"] * invalid + OBJECTIVE["false_no_feasible"] * false_no,
            "issued_recommendation": int(issued), "valid_feasible_recommendation": int(issued and has_feasible and not invalid),
            "has_feasible": int(has_feasible), "has_no_feasible": int(not has_feasible),
            "correct_no_feasible": int(outcome["status"] == "no_feasible" and not has_feasible),
            "needs_confirmation": int(outcome["status"] == "needs_confirmation"),
            "optimal": int(issued and has_feasible and abs(optimum - delivered) < 1e-9)}


def raw_loss(prior, facts, hidden, family):
    return action_metrics(hidden, family, constraint_outcome(prior, facts, guarded=False))["objective_loss"]


def question_target(prior, record, facts, q):
    before = raw_loss(prior, facts, record["hidden"], record["family"])
    after = raw_loss(prior, facts | {q: record["answers"][q]}, record["hidden"], record["family"])
    return float(before - after - QUESTION_COST)


class ConstraintPrior(Prior):
    def __init__(self):
        super().__init__()
        self.latent_feasibility = np.asarray([feasible_for(p) for p in self.profiles])

    @lru_cache(maxsize=16000)
    def expected_components(self, facts_tuple):
        facts = dict(facts_tuple)
        _, feasible, order, mask = self._state(facts_tuple)
        neutral = tuple(key for key, value in facts_tuple if value == "indifferent")
        matrix = self._utilities[neutral][mask]
        actual_feasible = self.latent_feasibility[mask]
        has_feasible = actual_feasible.any(axis=1)
        optimum = matrix.max(axis=1)
        if feasible.any():
            index = int(order[0])
            invalid = ~actual_feasible[:, index]
            losses = optimum - matrix[:, index] + invalid.astype(float)
        else:
            invalid = np.zeros(len(matrix), dtype=bool)
            losses = optimum + has_feasible.astype(float)
        return float(losses.mean()), float(invalid.mean()), float((~has_feasible).mean())

    @lru_cache(maxsize=16000)
    def _gain(self, facts_tuple, q):
        facts = dict(facts_tuple)
        before = self.expected_components(facts_tuple)[0]
        after = sum(probability * self.expected_components(tuple(sorted((facts | {q: answer}).items())))[0]
                    for answer, probability in self.distribution(facts, q))
        return float(before - after - QUESTION_COST)

    def analytic_gain(self, facts, q):
        return self._gain(tuple(sorted(facts.items())), q)


def feature_names_v2():
    return feature_names() + ["top_required_weeks", "top_required_hardware", "top_required_experience",
                              "unchecked_time", "unchecked_hardware", "unchecked_experience",
                              "prior_invalid_fraction", "prior_no_feasible_fraction"]


def features_v2(prior, facts, excluded, q, budget):
    result = features(prior, facts, excluded, q, budget)
    _, feasible, order = prior.rank(facts)
    item = CATALOG[int(order[0])]
    unchecked = unchecked_for(item, facts) if feasible.any() else []
    _, invalid, no_feasible = prior.expected_components(tuple(sorted(facts.items())))
    return result + [item["weeks"] / 12, item["hardware_level"] / 2, item["experience_level"] / 2,
                     float("time" in unchecked), float("hardware" in unchecked), float("experience" in unchecked), invalid, no_feasible]
