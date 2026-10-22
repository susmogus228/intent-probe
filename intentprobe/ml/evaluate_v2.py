"""Frozen v2 evaluation: raw policy quality is separate from guarded outcomes."""
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import hashlib
import json

import numpy as np

from .constraints import (OBJECTIVE, HARD_CONSTRAINTS, constraint_outcome, constraint_status,
                          action_metrics)
from .domain import CATALOG, POLICIES, LABELS, QUESTION_IDS, REAL_VALUES, feasible_for, Prior
from .evaluate import grouped_values, ci_mean
from .simulator import sha256


def rollout_v2(engine, record, policy, budget, initial_facts=None, response_mode="standard", forced_stop=None):
    facts, excluded = dict(initial_facts or {}), []
    seed = int(hashlib.sha256(f"{record['profile_id']}|{record['variant']}|{budget}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    used = 0
    for remaining in range(budget, 0, -1):
        if forced_stop is not None and used >= forced_stop:
            break
        q, _, _ = engine.choose(facts, excluded, remaining, policy, rng)
        if q is None:
            break
        if response_mode == "skip_all" or (response_mode == "skip_constraints" and q in HARD_CONSTRAINTS):
            excluded.append(q)
        elif response_mode == "unknown_all":
            facts[q] = "unknown"
        elif response_mode == "wrong_time" and q == "time":
            facts[q] = "weekend" if record["hidden"]["time"] != "weekend" else "month"
        else:
            facts[q] = record["answers"][q]
        used += 1
    pair = []
    for guarded in (False, True):
        outcome = constraint_outcome(engine.prior, facts, guarded)
        metrics = action_metrics(record["hidden"], record["family"], outcome)
        pair.append({"profile_id": record["profile_id"], "variant": record["variant"], "condition": record["condition"],
                     "policy": policy, "budget": budget, "guarded": guarded, "outcome": outcome["status"],
                     "questions": used, **metrics, "constraint_violation": metrics["invalid_recommendation"],
                     "total_loss": metrics["regret"] + OBJECTIVE["question_cost"] * used,
                     "objective_with_cost": metrics["objective_loss"] + OBJECTIVE["question_cost"] * used,
                     "all_cases": 1, "hardware": record["hidden"]["hardware"], "experience": record["hidden"]["experience"], "domain": record["hidden"]["domain"]})
    return pair


def ratio_ci(rows, numerator, denominator, replicates=600):
    """Ratio of sums, bootstrapped by profile; abstentions stay in denominators."""
    groups = defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        groups[row["profile_id"]][0] += row[numerator]
        groups[row["profile_id"]][1] += row[denominator]
    values = np.asarray([groups[key] for key in sorted(groups)], dtype=float)
    if not len(values) or values[:, 1].sum() == 0:
        return None, None, None
    value = float(values[:, 0].sum() / values[:, 1].sum())
    rng = np.random.default_rng(997)
    samples = values[rng.integers(0, len(values), size=(replicates, len(values)))].sum(axis=1)
    valid = samples[:, 1] > 0
    boot = samples[valid, 0] / samples[valid, 1]
    low, high = np.quantile(boot, [0.025, 0.975])
    return value, float(min(value, low)), float(max(value, high))


def summarize(rows, policy, label=None):
    feasible = grouped_values(rows, "regret", True)
    mean, low, high = ci_mean(feasible) if feasible else (None, None, None)
    total, total_low, total_high = ci_mean(grouped_values(rows, "total_loss", True)) if feasible else (None, None, None)
    objective, obj_low, obj_high = ci_mean(grouped_values(rows, "objective_with_cost")) if rows else (None, None, None)
    risk, risk_low, risk_high = ratio_ci(rows, "invalid_recommendation", "issued_recommendation")
    coverage, coverage_low, coverage_high = ratio_ci(rows, "valid_feasible_recommendation", "has_feasible")
    detection, detection_low, detection_high = ratio_ci(rows, "correct_no_feasible", "has_no_feasible")
    false_no, false_low, false_high = ratio_ci(rows, "false_no_feasible", "has_feasible")
    recommendation_rate = ratio_ci(rows, "issued_recommendation", "all_cases")[0]
    return {"id": policy, "label": label or LABELS.get(policy, policy), "mean_regret": mean, "ci_low": low, "ci_high": high,
            "mean_total_loss": total, "total_loss_ci_low": total_low, "total_loss_ci_high": total_high,
            "mean_objective_with_cost": objective, "objective_ci_low": obj_low, "objective_ci_high": obj_high,
            "mean_questions": float(np.mean([r["questions"] for r in rows])) if rows else None,
            "mean_questions_feasible": float(np.mean([r["questions"] for r in rows if r["has_feasible"]])) if feasible else None,
            "constraint_violation_rate": ratio_ci(rows, "invalid_recommendation", "all_cases")[0],
            "recommendation_risk": risk, "recommendation_risk_ci_low": risk_low, "recommendation_risk_ci_high": risk_high,
            "feasible_coverage": coverage, "feasible_coverage_ci_low": coverage_low, "feasible_coverage_ci_high": coverage_high,
            "recommendation_rate": recommendation_rate, "false_no_feasible_rate": false_no,
            "false_no_feasible_ci_low": false_low, "false_no_feasible_ci_high": false_high,
            "no_feasible_detection_rate": detection, "no_feasible_detection_ci_low": detection_low, "no_feasible_detection_ci_high": detection_high,
            "optimal_recommendation_rate": ratio_ci(rows, "optimal", "has_feasible")[0],
            "needs_confirmation_rate": ratio_ci(rows, "needs_confirmation", "all_cases")[0],
            "evaluation_cases": len(rows), "base_profiles": len({r["profile_id"] for r in rows}),
            "feasible_cases": sum(r["has_feasible"] for r in rows), "no_feasible_cases": sum(r["has_no_feasible"] for r in rows),
            "issued_recommendations": sum(r["issued_recommendation"] for r in rows), "invalid_recommendations": sum(r["invalid_recommendation"] for r in rows),
            "valid_feasible_recommendations": sum(r["valid_feasible_recommendation"] for r in rows),
            "false_no_feasible_count": sum(r["false_no_feasible"] for r in rows), "correct_no_feasible_count": sum(r["correct_no_feasible"] for r in rows)}


def cohort_rows(engine, records, budget=3, **kwargs):
    rows = {False: {}, True: {}}
    for policy in POLICIES:
        pairs = [rollout_v2(engine, record, policy, budget, **kwargs) for record in records]
        for index, guarded in enumerate((False, True)):
            rows[guarded][policy] = [pair[index] for pair in pairs]
    return rows


def cohort_report(rows, scope):
    return {"scope": scope, "policies": [summarize(rows[False][p], p) for p in POLICIES],
            "guarded_policies": [summarize(rows[True][p], p, LABELS[p] + " + constraint guard") for p in POLICIES]}


def paired_comparisons(rows):
    comparisons = []
    for guarded in (False, True):
        learned = grouped_values(rows[guarded]["learned"], "objective_with_cost")
        for policy in POLICIES:
            if policy == "learned":
                continue
            baseline = grouped_values(rows[guarded][policy], "objective_with_cost")
            differences = {key: learned[key] - baseline[key] for key in sorted(learned.keys() & baseline.keys())}
            value, low, high = ci_mean(differences)
            comparisons.append({"baseline": policy, "guarded": guarded, "learned_minus_baseline": value, "ci_low": low, "ci_high": high,
                                "metric": "regret + invalid + false_no_feasible + 0.006 * questions, all profiles", "profiles": len(differences)})
    return comparisons


def audit_guard_algebra(prior):
    """Exhaustive finite-state correctness checks, not a new independent dataset."""
    failures, cases = [], 0
    for time, hardware, experience in product((None, "unknown", *REAL_VALUES["time"]), (None, "unknown", *REAL_VALUES["hardware"]), (None, "unknown", *REAL_VALUES["experience"])):
        facts = {key: value for key, value in zip(HARD_CONSTRAINTS, (time, hardware, experience)) if value is not None}
        completions = [dict(zip(HARD_CONSTRAINTS, values)) for values in product(*(tuple([facts[key]]) if facts.get(key) in REAL_VALUES[key] else REAL_VALUES[key] for key in HARD_CONSTRAINTS))]
        matrix = np.asarray([feasible_for(values) for values in completions])
        for index, item in enumerate(CATALOG):
            expected = "verified" if matrix[:, index].all() else "conflict" if not matrix[:, index].any() else "unverified"
            actual = constraint_status(item, facts)
            cases += 1
            if actual != expected:
                failures.append({"facts": facts, "project": item["id"], "expected": expected, "actual": actual})
    full_vectors = 0
    for values in product(*(REAL_VALUES[q] for q in QUESTION_IDS)):
        facts = dict(zip(QUESTION_IDS, values))
        outcome = constraint_outcome(prior, facts)
        true_feasible = feasible_for(facts)
        full_vectors += 1
        if (not true_feasible.any() and outcome["status"] != "no_feasible") or (true_feasible.any() and outcome["status"] != "recommendation"):
            failures.append({"facts": facts, "outcome": outcome})
    return {"scope": "Exploratory exhaustive guard algebra, not ML generalization or an independent test.",
            "constraint_project_checks": cases, "complete_vectors": full_vectors, "failures": failures, "passed": not failures}


def evaluate_v2(artifact_dir: Path, v1_dir: Path | None = None):
    from .engine import Engine
    artifact_dir = Path(artifact_dir)
    v1_dir = Path(v1_dir) if v1_dir is not None else artifact_dir.parent
    engine = Engine(artifact_dir)
    metadata = engine._metadata
    audit = json.loads((artifact_dir / "evaluation_profiles.json").read_text(encoding="utf-8"))
    manifest = json.loads((artifact_dir / "data" / "split_manifest.json").read_text(encoding="utf-8"))
    development = json.loads((artifact_dir / "data" / "development_profiles.json").read_text(encoding="utf-8"))
    if sha256(audit) != metadata["dataset"]["test_records_sha256"] or sha256(manifest) != metadata["dataset"]["manifest_sha256"] or sha256(development) != manifest["development"]["records_sha256"]:
        raise ValueError("Frozen v2 evaluation data integrity mismatch")
    main_rows = cohort_rows(engine, audit)
    report = cohort_report(main_rows, "40-vector frozen final synthetic audit, not external validation. Budget three, empty initial facts, paired variants.")
    report["development_benchmark"] = cohort_report(cohort_rows(engine, development), "120 previously inspected v1 test vectors; diagnostic development evidence, not independent test.")
    report["paired_comparisons"] = paired_comparisons(main_rows)
    report["curves"], report["guarded_curves"] = [], []
    for budget in range(6):
        curve_rows = main_rows if budget == 3 else cohort_rows(engine, audit, budget)
        for guarded, key in ((False, "curves"), (True, "guarded_curves")):
            for policy in POLICIES:
                summary = summarize(curve_rows[guarded][policy], policy)
                report[key].append({"policy": policy, "budget": budget, **{k: summary[k] for k in ("mean_regret", "ci_low", "ci_high", "recommendation_risk", "feasible_coverage", "no_feasible_detection_rate", "mean_objective_with_cost")}})
    stress = []
    for condition in ("in_distribution", "preference_shift", "answer_noise"):
        records = [r for r in audit if r["condition"] == condition]
        condition_report = cohort_report(cohort_rows(engine, records), "Small final-audit condition subgroup; different vectors, not a causal effect of shift.")
        stress.append({"name": condition, "description": condition_report["scope"],
                       "results": [{"policy": p["id"], **p} for p in condition_report["policies"]], "guarded_results": condition_report["guarded_policies"]})
    configurations = [("all_unknown", {"response_mode": "unknown_all"}, 3), ("all_skipped", {"response_mode": "skip_all"}, 3),
                      ("constraints_skipped", {"response_mode": "skip_constraints"}, 3), ("incorrect_time", {"response_mode": "wrong_time"}, 3),
                      ("zero_budget", {}, 0), ("forced_stop_after_one", {"forced_stop": 1}, 3), ("five_questions", {}, 5)]
    for name, options, budget in configurations:
        case = cohort_report(cohort_rows(engine, development, budget, **options), "Exploratory stress on the already inspected 120-vector development cohort.")
        stress.append({"name": name, "description": case["scope"], "results": [{"policy": p["id"], **p} for p in case["policies"]], "guarded_results": case["guarded_policies"]})
    for initial in ({"time": "week"}, {"time": "month", "hardware": "cpu"}, {"time": "quarter", "experience": "advanced"}, {"time": "month", "experience": "beginner", "domain": "vision"}):
        matched = [r for r in development if all(r["hidden"][key] == value for key, value in initial.items())]
        case = cohort_report(cohort_rows(engine, matched, 3, initial_facts=initial), "Exploratory truthful preconfirmed facts; the same matched profiles and facts are provided to every policy.")
        stress.append({"name": "confirmed_" + "_".join(initial), "description": case["scope"], "initial_facts": initial,
                       "results": [{"policy": p["id"], **p} for p in case["policies"]], "guarded_results": case["guarded_policies"]})
    report["stress_tests"] = stress
    v1 = Engine(v1_dir)
    report["v1_comparison"] = {"model_artifact_sha256": v1._metadata["model"]["artifact_sha256"],
                               "final_audit": cohort_report(cohort_rows(v1, audit), "Same final audit records and v2 loss, legacy v1 raw question policy."),
                               "development": cohort_report(cohort_rows(v1, development), "Same already inspected development records and v2 loss, legacy v1 raw policy.")}
    report["exhaustive_guard_audit"] = audit_guard_algebra(engine.prior)
    final_learned, final_guarded = report["policies"][0], report["guarded_policies"][0]
    development_raw = report["development_benchmark"]["policies"][0]
    target_specs = [("development_raw_all_case_violation", development_raw["constraint_violation_rate"], 0.05, "max"),
                    ("final_guarded_recommendation_risk", final_guarded["recommendation_risk"], 0.05, "max"),
                    ("final_guarded_feasible_coverage", final_guarded["feasible_coverage"], 0.80, "min"),
                    ("final_no_feasible_detection", final_guarded["no_feasible_detection_rate"], 0.95, "min"),
                    ("final_false_no_feasible", final_guarded["false_no_feasible_rate"], 0.05, "max")]
    report["quality_targets"] = [{"name": name, "value": value, "target": target, "direction": direction,
                                  "met": None if value is None else bool(value <= target if direction == "max" else value >= target)} for name, value, target, direction in target_specs]
    report.update(generated_at=datetime.now(timezone.utc).isoformat(), model_version=metadata["model"]["version"],
                  model_artifact_sha256=metadata["model"]["artifact_sha256"], test_records_sha256=metadata["dataset"]["test_records_sha256"],
                  evaluation_records=len(audit), base_profiles=len({r["profile_id"] for r in audit}),
                  feasible_base_profiles=len(grouped_values(main_rows[False]["learned"], "regret", True)),
                  bootstrap={"unit": "base preference vector, preserving both response variants", "replicates": 600, "seed": 997, "interval": "percentile 95%; ratios use grouped sums"},
                  notes=["The 40 unused vectors were frozen before model fitting. This small final audit comes from the same finite synthetic lattice and is not external validation.",
                         "The old 120-vector test was already inspected and is development evidence. No configuration was selected using it or the final audit.",
                         "Raw learned policy and transparent guarded outcomes are reported separately. The guard changes no question ordering, STOP or top candidate.",
                         "Loss is regret + invalid recommendation + false no-feasible; fixed coefficients one. Cost is 0.006 per question.",
                         "Mean regret and mean_total_loss use feasible profiles; mean_objective_with_cost, mean_questions and all-case violation use every case.",
                         "recommendation_risk=invalid/issued; feasible_coverage=valid issued/feasible; recommendation_rate=issued/all; false_no_feasible_rate=false assertions/feasible.",
                         "Abstention can lower issued risk but loses feasible coverage and incurs forgone-utility regret. Null risk means no issued recommendations, never perfect safety.",
                         "Targets are point-estimate research goals, not certified risk guarantees. Small counts and zero-error bootstrap intervals cannot establish universal safety.",
                         "A guard cannot detect false stated facts. The incorrect-time stress intentionally demonstrates invalid recommendations and false no-feasible assertions.",
                         "Budget curves use final audit; exhaustive guard algebra and special response stresses are exploratory. No full-lattice result is called independent.",
                         "No human participants, private data, demographic fairness claim or ordinary-LLM superiority claim."])
    return report
