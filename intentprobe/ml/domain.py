"""A finite, explicit preference prior shared by all question policies.

This module ranks project briefs, not implemented portfolio applications. Hidden
evaluation preferences never enter this API. Scores are utilities, not confidence.
"""
from functools import lru_cache
from itertools import product
import math

import numpy as np

QUESTION_COST = 0.006
GENERATOR_VERSION = "project-preferences-1.1"
MODEL_VERSION = "intentprobe-question-value-1.0"
POLICIES = ("learned", "analytic", "information_gain", "fixed", "random", "none")
LABELS = {
    "learned": "Learned question value", "analytic": "Analytic decision value",
    "information_gain": "Information gain", "fixed": "Fixed questionnaire",
    "random": "Random valid question", "none": "No clarification",
}


def question(identifier, title, description, values, indifferent=False):
    options = [{"value": value, "label": label} for value, label in values]
    options.append({"value": "unknown", "label": "I do not know yet"})
    if indifferent:
        options.append({"value": "indifferent", "label": "No preference"})
    return {"id": identifier, "title": title, "description": description, "options": options}


QUESTIONS = [
    question("time", "How much time can you commit?", "A hard limit on the brief's estimated scope, not a delivery guarantee.", [("weekend", "One weekend"), ("week", "About one week"), ("month", "About four weeks"), ("quarter", "About twelve weeks")]),
    question("hardware", "What hardware can you use?", "Exclude briefs requiring hardware you cannot access.", [("cpu", "CPU laptop only"), ("local_gpu", "Local GPU"), ("cloud_gpu", "Cloud GPU")]),
    question("experience", "What is your current ML experience?", "Use your current experience as a hard prerequisite ceiling.", [("beginner", "Beginning ML"), ("intermediate", "Have trained models"), ("advanced", "Comfortable with research experiments")]),
    question("domain", "Which kind of problem interests you?", "A soft preference; alternatives remain visible.", [("tabular", "Structured data"), ("language", "Language"), ("vision", "Images"), ("systems", "ML systems"), ("science", "Scientific ML")], True),
    question("goal", "What should the project demonstrate?", "A soft preference for an applied, research or learning outcome.", [("practical", "A practical application"), ("research", "An experimental finding"), ("learning", "A clear learning exercise")], True),
]
QUESTION_MAP = {q["id"]: q for q in QUESTIONS}
QUESTION_IDS = tuple(QUESTION_MAP)
REAL_VALUES = {q["id"]: tuple(o["value"] for o in q["options"] if o["value"] not in ("unknown", "indifferent")) for q in QUESTIONS}
TIME = {"weekend": 0, "week": 1, "month": 4, "quarter": 12}
HARDWARE = {"cpu": 0, "local_gpu": 1, "cloud_gpu": 2}
EXPERIENCE = {"beginner": 0, "intermediate": 1, "advanced": 2}


def brief(identifier, title, summary, weeks, hardware, experience, domain, goal):
    return {"id": identifier, "title": title, "summary": summary, "weeks": weeks,
            "hardware_level": hardware, "experience_level": experience,
            "domain": domain, "goal": goal, "tags": [domain, goal, "CPU" if hardware == 0 else "GPU"]}


CATALOG = [
    brief("table-quality", "Table quality auditor", "Detect and explain suspicious cells with a small trained anomaly model.", 1, 0, 0, "tabular", "practical"),
    brief("churn-audit", "Churn model audit", "Train a compact churn classifier and study calibration and subgroup errors.", 4, 0, 1, "tabular", "research"),
    brief("price-basics", "Price prediction notebook", "Build a reproducible regression study with leakage-aware evaluation.", 1, 0, 0, "tabular", "learning"),
    brief("causal-shift", "Tabular shift stress test", "Compare predictive models under controlled changes in data collection.", 12, 0, 2, "tabular", "research"),
    brief("ticket-router", "Support ticket router", "Train a local text router with an explicit low-confidence review queue.", 4, 0, 1, "language", "practical"),
    brief("text-basics", "Text feature laboratory", "Compare word and character features on a small labeled corpus.", 1, 0, 0, "language", "learning"),
    brief("intent-shift", "Intent drift study", "Measure how a classifier changes under vocabulary and domain shifts.", 4, 0, 1, "language", "research"),
    brief("small-transformer", "Small language adapter", "Fine-tune a small pretrained encoder and audit transfer to a new domain.", 12, 1, 2, "language", "research"),
    brief("image-inspector", "Image inspection queue", "Fine-tune a small image model and route unfamiliar inputs for review.", 4, 1, 1, "vision", "practical"),
    brief("image-features", "Image feature notebook", "Compare compact image descriptors using small reproducible datasets.", 1, 0, 0, "vision", "learning"),
    brief("vision-corruption", "Vision corruption study", "Evaluate calibration and selective prediction under image corruptions.", 12, 1, 2, "vision", "research"),
    brief("camera-triage", "Camera event triage", "Train a lightweight image-event classifier with error inspection.", 4, 1, 1, "vision", "practical"),
    brief("latency-policy", "Inference routing policy", "Learn when a request should use a cheap model or a stronger local model.", 4, 0, 1, "systems", "practical"),
    brief("cache-study", "Learned cache experiment", "Compare a learned reuse score with conventional cache policies.", 12, 0, 2, "systems", "research"),
    brief("ml-packaging", "Model serving starter", "Train and package a simple predictor with tests and provenance.", 1, 0, 0, "systems", "learning"),
    brief("monitoring-study", "Model drift monitor", "Train a shift detector and evaluate false alarms against a fixed baseline.", 4, 0, 1, "systems", "research"),
    brief("sensor-anomaly", "Sensor anomaly triage", "Learn normal multivariate sensor behavior and inspect unusual windows.", 4, 0, 1, "science", "practical"),
    brief("signal-basics", "Signal classification notebook", "Compare features and small classifiers on labeled sensor windows.", 1, 0, 0, "science", "learning"),
    brief("surrogate-study", "Scientific surrogate study", "Train a compact surrogate and measure failure outside its training range.", 12, 1, 2, "science", "research"),
    brief("uncertainty-lab", "Scientific uncertainty lab", "Compare uncertainty estimates on a controlled physical simulator.", 4, 0, 1, "science", "research"),
]


def validate(facts, excluded, budget, policy=None):
    if not isinstance(budget, int) or isinstance(budget, bool) or not 0 <= budget <= 5:
        raise ValueError("Remaining budget must be an integer from 0 to 5")
    if not isinstance(facts, dict) or not isinstance(excluded, (list, tuple)):
        raise ValueError("Facts must be a mapping and excluded questions a list")
    for key, value in facts.items():
        if key not in QUESTION_MAP or value not in {o["value"] for o in QUESTION_MAP[key]["options"]}:
            raise ValueError(f"Invalid answer for {key}")
    if any(key not in QUESTION_MAP for key in excluded):
        raise ValueError("Invalid excluded question")
    if policy is not None and policy not in POLICIES:
        raise ValueError("Unknown question policy")


def feasible_for(values):
    return np.asarray([
        (values.get("time") not in TIME or p["weeks"] <= TIME[values["time"]])
        and (values.get("hardware") not in HARDWARE or p["hardware_level"] <= HARDWARE[values["hardware"]])
        and (values.get("experience") not in EXPERIENCE or p["experience_level"] <= EXPERIENCE[values["experience"]])
        for p in CATALOG], dtype=bool)


def utility(values, family="balanced"):
    """Synthetic evaluator utility. Used for prior integration and rollout labels."""
    d = np.asarray([0.5 if values.get("domain") == "indifferent" else float(p["domain"] == values["domain"]) for p in CATALOG])
    g = np.asarray([0.5 if values.get("goal") == "indifferent" else float(p["goal"] == values["goal"]) for p in CATALOG])
    level = EXPERIENCE[values["experience"]]
    depth = np.asarray([1 - abs(p["experience_level"] - level) / 2 for p in CATALOG])
    weights = {"balanced": (0.5, 0.3, 0.2), "specialist": (0.7, 0.15, 0.15), "interaction": (0.3, 0.25, 0.15)}[family]
    score = weights[0] * d + weights[1] * g + weights[2] * depth
    if family == "interaction":
        score = score + 0.3 * d * g
    return score * feasible_for(values)


class Prior:
    """Uniform finite prior over complete preferences, not the test population.

    Hard facts filter possibilities. Unknown retains uncertainty. Indifferent
    neutralizes a preference; skip is stored separately and does neither.
    """
    def __init__(self):
        self.profiles = [dict(zip(QUESTION_IDS, values)) for values in product(*(REAL_VALUES[k] for k in QUESTION_IDS))]
        self.arrays = {q: np.asarray([p[q] for p in self.profiles]) for q in QUESTION_IDS}
        self._utilities = {}

    @lru_cache(maxsize=10000)
    def _state(self, facts_tuple):
        facts = dict(facts_tuple)
        mask = np.ones(len(self.profiles), dtype=bool)
        for key, value in facts.items():
            if value in REAL_VALUES[key]:
                mask &= self.arrays[key] == value
        neutral = tuple(k for k, value in facts.items() if value == "indifferent")
        if neutral not in self._utilities:
            self._utilities[neutral] = np.asarray([utility(p | {k: "indifferent" for k in neutral}) for p in self.profiles])
        matrix = self._utilities[neutral]
        means = matrix[mask].mean(axis=0)
        feasible = feasible_for(facts)
        scores = np.clip(means, 0, 1)
        order = np.argsort(-np.where(feasible, scores, -1), kind="stable")
        return scores, feasible, order, mask

    def rank(self, facts):
        scores, feasible, order, _ = self._state(tuple(sorted(facts.items())))
        return scores.copy(), feasible.copy(), order.copy()

    def distribution(self, facts, q):
        _, _, _, mask = self._state(tuple(sorted(facts.items())))
        return [(value, float(np.mean(self.arrays[q][mask] == value))) for value in REAL_VALUES[q]]

    def analytic_gain(self, facts, q):
        before, feasible, order = self.rank(facts)
        if not feasible.any():
            return -QUESTION_COST
        old = before[order[0]]
        expected = 0.0
        for value, probability in self.distribution(facts, q):
            scores, after_feasible, after_order = self.rank(facts | {q: value})
            expected += probability * (float(scores[after_order[0]]) if after_feasible.any() else 0)
        return float(expected - old - QUESTION_COST)

    def information_gain(self, facts, q):
        probabilities = [p for _, p in self.distribution(facts, q) if p > 0]
        return float(-sum(p * math.log2(p) for p in probabilities))


def feature_names():
    names = []
    for q in QUESTIONS:
        names.extend(f"{q['id']}={o['value']}" for o in q["options"])
        names.extend([f"{q['id']}:unobserved", f"{q['id']}:skipped"])
    names += [f"candidate={q}" for q in QUESTION_IDS]
    names += ["remaining_budget", "observed_count", "available_count", "feasible_fraction", "best_utility", "second_utility", "utility_gap", "score_mean", "score_std", "candidate_answer_entropy"]
    return names


def features(prior, facts, excluded, q, budget):
    """Only observable inputs. There is deliberately no hidden-profile argument."""
    result = []
    for question in QUESTIONS:
        key = question["id"]
        result.extend(float(facts.get(key) == o["value"]) for o in question["options"])
        result.extend([float(key not in facts and key not in excluded), float(key in excluded)])
    result.extend(float(q == key) for key in QUESTION_IDS)
    scores, feasible, order = prior.rank(facts)
    best = float(scores[order[0]]) if feasible.any() else 0
    second = float(scores[order[1]]) if feasible.sum() > 1 else 0
    result += [float(budget), float(len(facts)), float(sum(key not in facts and key not in excluded for key in QUESTION_IDS)),
               float(feasible.mean()), best, second, best - second, float(scores.mean()), float(scores.std()), prior.information_gain(facts, q)]
    return result


def explain_infeasible(item, facts):
    reasons = []
    if facts.get("time") in TIME and item["weeks"] > TIME[facts["time"]]:
        reasons.append(f"Needs about {item['weeks']} weeks; exceeds the stated time limit.")
    if facts.get("hardware") in HARDWARE and item["hardware_level"] > HARDWARE[facts["hardware"]]:
        reasons.append("Requires GPU access; the stated hardware does not provide it.")
    if facts.get("experience") in EXPERIENCE and item["experience_level"] > EXPERIENCE[facts["experience"]]:
        reasons.append("Prerequisites exceed the stated experience level.")
    return reasons
