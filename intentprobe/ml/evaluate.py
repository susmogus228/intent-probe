"""Frozen-model, profile-grouped paired benchmark; never retrains a model."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

import numpy as np

from .domain import POLICIES, LABELS, QUESTION_COST, REAL_VALUES, utility, feasible_for
from .simulator import sha256


def rollout(engine, record, policy, budget):
    facts, excluded = {}, []
    seed = int(hashlib.sha256(f"{record['profile_id']}|{record['variant']}|{budget}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    used = 0
    for remaining in range(budget, 0, -1):
        q, _, _ = engine.choose(facts, excluded, remaining, policy, rng)
        if q is None:
            break
        facts[q] = record["answers"][q]
        used += 1
    _, observed_feasible, order = engine.prior.rank(facts)
    true_feasible = feasible_for(record["hidden"])
    utilities = utility(record["hidden"], record["family"])
    optimum = float(utilities.max()) if true_feasible.any() else 0
    recommendation = int(order[0]) if observed_feasible.any() else None
    delivered = float(utilities[recommendation]) if recommendation is not None else 0
    # No-feasible profiles are evaluated as valid abstention, not as zero-regret
    # successes in the primary mean. Report both separately.
    violation = float(recommendation is not None and not true_feasible[recommendation])
    return {"profile_id": record["profile_id"], "variant": record["variant"], "condition": record["condition"],
            "policy": policy, "budget": budget, "regret": max(0.0, optimum - delivered),
            "total_loss": max(0.0, optimum - delivered) + QUESTION_COST * used,
            "questions": used, "constraint_violation": violation, "has_feasible": bool(true_feasible.any()),
            "correct_no_feasible": bool(not true_feasible.any() and recommendation is None),
            "abstained": recommendation is None, "optimal": bool(true_feasible.any() and abs(optimum - delivered) < 1e-9),
            "hardware": record["hidden"]["hardware"], "experience": record["hidden"]["experience"], "domain": record["hidden"]["domain"]}


def grouped_values(rows, field, feasible_only=False):
    grouped = defaultdict(list)
    for row in rows:
        if feasible_only and not row["has_feasible"]:
            continue
        grouped[row["profile_id"]].append(float(row[field]))
    return {key: float(np.mean(values)) for key, values in sorted(grouped.items())}


def ci_mean(grouped, seed=997, replicates=600):
    values = np.asarray(list(grouped.values()), dtype=float)
    if len(values) == 0:
        raise ValueError("Insufficient bootstrap data: empty profile group")
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    mean = float(values.mean())
    low, high = np.quantile(means, [0.025, 0.975])
    return mean, float(min(low, mean)), float(max(high, mean))


def evaluate_artifact(artifact_dir: Path) -> dict:
    from .engine import Engine
    engine = Engine(artifact_dir)
    if engine.constraint_aware:
        from .evaluate_v2 import evaluate_v2
        return evaluate_v2(artifact_dir)
    records = json.loads((Path(artifact_dir) / "evaluation_profiles.json").read_text(encoding="utf-8"))
    expected = engine.metadata()["dataset"]["test_records_sha256"]
    if sha256(records) != expected:
        raise ValueError("Frozen evaluation dataset integrity hash mismatch")
    all_rows = []
    for policy in POLICIES:
        for budget in range(6):
            for record in records:
                all_rows.append(rollout(engine, record, policy, budget))
    summaries, curves = [], []
    primary = {policy: [r for r in all_rows if r["policy"] == policy and r["budget"] == 3] for policy in POLICIES}
    for policy in POLICIES:
        rows = primary[policy]
        mean, low, high = ci_mean(grouped_values(rows, "regret", True))
        loss_mean, loss_low, loss_high = ci_mean(grouped_values(rows, "total_loss", True))
        no_feasible = [r for r in rows if not r["has_feasible"]]
        summaries.append({"id": policy, "label": LABELS[policy], "mean_regret": mean,
                          "ci_low": low, "ci_high": high,
                          "mean_total_loss": loss_mean, "total_loss_ci_low": loss_low, "total_loss_ci_high": loss_high,
                          "mean_questions": ci_mean(grouped_values(rows, "questions"))[0],
                          "mean_questions_feasible": ci_mean(grouped_values(rows, "questions", True))[0],
                          "constraint_violation_rate": ci_mean(grouped_values(rows, "constraint_violation"))[0],
                          "optimal_recommendation_rate": ci_mean(grouped_values(rows, "optimal", True))[0],
                          "no_feasible_detection_rate": float(np.mean([r["correct_no_feasible"] for r in no_feasible])) if no_feasible else None})
        for budget in range(6):
            curve_rows = [r for r in all_rows if r["policy"] == policy and r["budget"] == budget]
            curve_mean, curve_low, curve_high = ci_mean(grouped_values(curve_rows, "regret", True))
            curves.append({"policy": policy, "budget": budget, "mean_regret": curve_mean, "ci_low": curve_low, "ci_high": curve_high})
    stress_tests = []
    descriptions = {"in_distribution": "New profiles from training utility families; one unknown-answer variant per profile.",
                    "preference_shift": "Held-out interaction utility family, absent from model fitting and validation.",
                    "answer_noise": "Held-out wrong-hardware response mechanism plus unknown goal; truthful and noisy variants share a group."}
    for condition, description in descriptions.items():
        results = []
        for policy in POLICIES:
            rows = [r for r in primary[policy] if r["condition"] == condition]
            grouped = grouped_values(rows, "regret", True)
            mean, low, high = ci_mean(grouped) if grouped else (None, None, None)
            results.append({"policy": policy, "mean_regret": mean, "ci_low": low, "ci_high": high,
                            "profiles": len(grouped), "available": bool(grouped)})
        stress_tests.append({"name": condition, "description": description, "results": results})
    paired, paired_loss = [], []
    learned = grouped_values(primary["learned"], "regret", True)
    if not learned:
        raise ValueError("Frozen benchmark has no feasible base profiles; regret cannot be evaluated")
    for policy in POLICIES:
        if policy == "learned":
            continue
        baseline = grouped_values(primary[policy], "regret", True)
        difference = {key: learned[key] - baseline[key] for key in learned.keys() & baseline.keys()}
        mean, low, high = ci_mean(dict(sorted(difference.items())))
        paired.append({"baseline": policy, "learned_minus_baseline": mean, "ci_low": low, "ci_high": high,
                       "interpretation": "Negative favors learned; paired by base profile, not dialogue turn."})
        learned_loss = grouped_values(primary["learned"], "total_loss", True)
        baseline_loss = grouped_values(primary[policy], "total_loss", True)
        difference_loss = {key: learned_loss[key] - baseline_loss[key] for key in learned_loss.keys() & baseline_loss.keys()}
        mean_loss, low_loss, high_loss = ci_mean(dict(sorted(difference_loss.items())))
        paired_loss.append({"baseline": policy, "learned_minus_baseline": mean_loss, "ci_low": low_loss, "ci_high": high_loss,
                            "interpretation": "Regret plus 0.006 per question, feasible profiles only; negative favors learned."})
    slices = []
    for attribute in ("hardware", "experience", "domain"):
        for value in REAL_VALUES[attribute]:
            results = []
            for policy in POLICIES:
                group = grouped_values([r for r in primary[policy] if r[attribute] == value], "regret", True)
                mean, low, high = ci_mean(group) if group else (None, None, None)
                results.append({"policy": policy, "profiles": len(group), "mean_regret": mean, "ci_low": low, "ci_high": high, "available": bool(group)})
            slices.append({"attribute": attribute, "value": value, "results": results})
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "model_version": engine.metadata()["model"]["version"],
            "model_artifact_sha256": engine.metadata()["model"]["artifact_sha256"], "test_records_sha256": expected,
            "scope": "Controlled synthetic profiles only. Primary regret at budget 3 on profiles with at least one feasible brief; lower is better.",
            "policies": summaries, "curves": curves, "stress_tests": stress_tests, "paired_comparisons": paired,
            "paired_total_loss_comparisons": paired_loss, "performance_slices": slices,
            "evaluation_records": len(records), "base_profiles": len({p["profile_id"] for p in records}),
            "feasible_base_profiles": len(learned), "bootstrap": {"unit": "base profile", "replicates": 600, "seed": 997, "interval": "percentile 95%"},
            "notes": ["All numbers are computed from actual frozen-model runs, not illustrations.",
                      "Training labels use one-step realized utility changes; this is not a learned multi-step optimal controller.",
                      "Ranking and the analytic baseline use a uniform finite prior that can be misspecified under shift.",
                      "A 0.006 synthetic cost governs ASK/STOP; it is not measured human time or fatigue.",
                      "Total loss is regret plus question cost on feasible profiles. mean_questions uses all profiles; mean_questions_feasible uses the regret denominator.",
                      "No-feasible profiles are excluded from mean regret and reported separately by detection and constraint-violation rates.",
                      "The utility target does not independently reward discovering no-feasible outcomes; their utilities are all zero.",
                      "The held-out interaction family is a narrow synthetic shift that often preserves the same optimal briefs.",
                      "Paired intervals group both answer variants of a person-like synthetic profile; no real participants were recruited.",
                      "No external LLM was benchmarked, so superiority to an AI chat is unproven.",
                      "Unknown and incorrect hardware replies are simulated. Skip, indifferent and revision behavior are functional tests, not efficacy benchmarks.",
                      "Slices use synthetic hardware, experience and domain, not protected attributes. No demographic data or demographic fairness claim is made."]}
