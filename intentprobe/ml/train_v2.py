"""Constraint-aware CPU training; preserves v1 and freezes the unused audit first."""
import argparse
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import hashlib
import json
import platform

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error
from threadpoolctl import threadpool_limits

from .domain import CATALOG, QUESTIONS, QUESTION_IDS, REAL_VALUES
from .constraints import (ConstraintPrior, OBJECTIVE, V2_MODEL_VERSION, V2_GENERATOR_VERSION,
                          feature_names_v2, features_v2, question_target)
from .simulator import canonical_bytes, sha256, observed_states
from .train import write_json


CONFIGS = [
    {"n_estimators": 80, "max_depth": 18, "min_samples_leaf": 3},
    {"n_estimators": 120, "max_depth": 22, "min_samples_leaf": 2},
]


def frozen_v1_hashes(v1_dir):
    v1_dir = Path(v1_dir)
    return {path.relative_to(v1_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(v1_dir.rglob("*")) if path.is_file() and "v2" not in path.relative_to(v1_dir).parts}


def freeze_protocol(v1_dir: Path, output: Path):
    """Write protocol and untouched audit records BEFORE computing any outcome."""
    v1_dir, output = Path(v1_dir), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = output / "data"
    data.mkdir(exist_ok=True)
    protocol_path = output / "training_protocol.json"
    source_records = [json.loads(line) for line in (v1_dir / "data" / "profiles.jsonl").read_text(encoding="utf-8").splitlines() if line]
    source_hash = sha256(source_records)
    if protocol_path.exists():
        existing = json.loads(protocol_path.read_text(encoding="utf-8"))
        if existing["source_records_sha256"] != source_hash or existing["objective"] != OBJECTIVE or existing["candidate_configs"] != CONFIGS:
            raise ValueError("Frozen protocol does not match source or fixed configuration; use a new version directory")
        audit = json.loads((output / "evaluation_profiles.json").read_text(encoding="utf-8"))
        if sha256(audit) != existing["final_audit_records_sha256"]:
            raise ValueError("Frozen final audit integrity mismatch")
        return existing
    splits = {"train": [p for p in source_records if p["split"] == "train"],
              "validation": [p for p in source_records if p["split"] == "validation"],
              "development": [p for p in source_records if p["split"] == "test"]}
    seen = {canonical_bytes(p["hidden"]) for p in source_records}
    complete = [dict(zip(QUESTION_IDS, values)) for values in product(*(REAL_VALUES[q] for q in QUESTION_IDS))]
    unused = [p for p in complete if canonical_bytes(p) not in seen]
    counts = {name: len({p["profile_id"] for p in records}) for name, records in splits.items()}
    counts["final_audit"] = len(unused)
    if counts != {"train": 300, "validation": 80, "development": 120, "final_audit": 40}:
        raise ValueError("v2 requires the frozen v1 300/80/120 partition and exactly 40 unused vectors")
    rng = np.random.default_rng(20261022)
    audit = []
    for index, hidden in enumerate(unused):
        condition = ("in_distribution", "preference_shift", "answer_noise")[index % 3]
        family = "interaction" if condition == "preference_shift" else str(rng.choice(["balanced", "specialist"]))
        for variant in ("clean", "uncertain"):
            answers = dict(hidden)
            if variant == "uncertain":
                if condition == "answer_noise":
                    answers["hardware"] = "local_gpu" if hidden["hardware"] == "cpu" else "cpu"
                    answers["goal"] = "unknown"
                else:
                    answers[str(rng.choice(QUESTION_IDS))] = "unknown"
            audit.append({"profile_id": "profile-" + sha256(hidden)[:16], "variant": variant, "split": "final_audit",
                          "condition": condition, "family": family, "hidden": hidden, "answers": answers})
    splits["final_audit"] = audit
    manifest = {name: {"profile_ids": sorted({p["profile_id"] for p in rows}), "base_profiles": len({p["profile_id"] for p in rows}),
                       "records": len(rows), "records_sha256": sha256(rows)} for name, rows in splits.items()}
    protocol = {"frozen_at": datetime.now(timezone.utc).isoformat(), "frozen_before_fit": True,
                "objective": OBJECTIVE, "candidate_configs": CONFIGS, "states_per_profile": 12, "fit_seed": 42,
                "selection": "Choose the lowest validation raw constraint-aware loss plus question cost at budget three; MAE is secondary. Never select using development or final audit.",
                "counts": counts, "source_records_sha256": source_hash, "final_audit_records_sha256": sha256(audit),
                "split_manifest_sha256": sha256(manifest), "audit_scope": "The last 40 unused vectors from the same finite synthetic lattice; small final audit, not external validation.",
                "targets": {"development_raw_all_case_violation_max": 0.05, "guarded_recommendation_risk_max": 0.05,
                            "guarded_feasible_coverage_min": 0.8, "no_feasible_detection_min": 0.95, "false_no_feasible_rate_max": 0.05}}
    write_json(output / "evaluation_profiles.json", audit)
    write_json(data / "development_profiles.json", splits["development"])
    for name in ("train", "validation"):
        write_json(data / (name + "_profiles.json"), splits[name])
    write_json(data / "split_manifest.json", manifest)
    write_json(data / "catalog.json", CATALOG)
    write_json(data / "questions.json", QUESTIONS)
    write_json(output / "v1-preservation-manifest.json", frozen_v1_hashes(v1_dir))
    write_json(protocol_path, protocol)
    return protocol


def examples_v2(records, prior, seed, count=12):
    rows, labels, groups = [], [], []
    rng = np.random.default_rng(seed)
    for record in records:
        for facts, excluded, budget in observed_states(record, rng, count):
            _, feasible, _ = prior.rank(facts)
            if not feasible.any():
                continue
            for q in QUESTION_IDS:
                if q in facts or q in excluded:
                    continue
                rows.append(features_v2(prior, facts, excluded, q, budget))
                labels.append(question_target(prior, record, facts, q))
                groups.append(record["profile_id"])
    return np.asarray(rows, dtype=float), np.asarray(labels), np.asarray(groups)


def train_v2(output: Path, v1_dir: Path = Path("artifacts")):
    output, v1_dir = Path(output), Path(v1_dir)
    if output.resolve() == v1_dir.resolve():
        raise ValueError("v2 output must be a separate directory; v1 cannot be overwritten")
    protocol = freeze_protocol(v1_dir, output)
    data = output / "data"
    train_records = json.loads((data / "train_profiles.json").read_text(encoding="utf-8"))
    validation_records = json.loads((data / "validation_profiles.json").read_text(encoding="utf-8"))
    prior = ConstraintPrior()
    x, y, groups = examples_v2(train_records, prior, 43, protocol["states_per_profile"])
    xv, yv, validation_groups = examples_v2(validation_records, prior, 44, protocol["states_per_profile"])
    np.savez_compressed(data / "training_rows.npz", X=x, y=y, profile_id=groups)
    np.savez_compressed(data / "validation_rows.npz", X=xv, y=yv, profile_id=validation_groups)
    candidates, fitted = [], []
    from .engine import Engine
    from .evaluate_v2 import rollout_v2, summarize
    for index, config in enumerate(CONFIGS):
        estimator = ExtraTreesRegressor(**config, random_state=42, n_jobs=1)
        with threadpool_limits(limits=1):
            estimator.fit(x, y)
            predictions = estimator.predict(xv)
        # Validation adapter uses the exact inference path and frozen estimator;
        # no audit/development records are loaded here.
        adapter = Engine.__new__(Engine)
        adapter.constraint_aware, adapter.prior, adapter.estimator = True, prior, estimator
        adapter._metadata = {"model": {"version": V2_MODEL_VERSION}}
        rows = [rollout_v2(adapter, record, "learned", 3)[0] for record in validation_records]
        validation = summarize(rows, "learned", "Validation learned")
        result = {"id": index, "config": config, "validation_mae": float(mean_absolute_error(yv, predictions)),
                  "validation_objective_with_cost": validation["mean_objective_with_cost"],
                  "validation_violation_rate": validation["constraint_violation_rate"],
                  "validation_regret": validation["mean_regret"]}
        candidates.append(result)
        fitted.append(estimator)
    selected = min(range(len(candidates)), key=lambda i: (candidates[i]["validation_objective_with_cost"], candidates[i]["validation_mae"]))
    estimator = fitted[selected]
    write_json(output / "validation_selection.json", {"candidates": candidates, "selected_id": selected,
                                                     "test_used_for_selection": False, "group_cv": "Not run; one fixed vector-disjoint validation split and two preregistered configurations."})
    model_path = output / "question_value.joblib"
    joblib.dump(estimator, model_path, compress=3)
    source_meta = json.loads((v1_dir / "metadata.json").read_text(encoding="utf-8"))
    dataset = {"kind": "synthetic", "train_profiles": 300, "validation_profiles": 80, "test_profiles": 40,
               "development_profiles": 120, "final_audit_profiles": 40, "splits_disjoint": True, "split_seed": 42,
               "generator_version": V2_GENERATOR_VERSION, "catalog_sha256": sha256(CATALOG),
               "test_records_sha256": protocol["final_audit_records_sha256"], "manifest_sha256": protocol["split_manifest_sha256"],
               "source_v1_records_sha256": protocol["source_records_sha256"], "development_role": "Already inspected v1 test, diagnostic only.",
               "limitations": ["Synthetic finite lattice; 40-vector final audit is small and not real-world or external validation.",
                               "The same predefined finite prior is available to all policies; no unseen synthetic seed is an independent dataset.",
                               "Utility shift is narrow. Incorrect user answers can defeat fact-based verification.",
                               "No human or demographic data, no demographic fairness claim."]}
    metadata = {"model": {"version": V2_MODEL_VERSION, "objective": "constraint_aware", "objective_coefficients": OBJECTIVE,
                           "estimator": "ExtraTreesRegressor", "trained_at": datetime.now(timezone.utc).isoformat(), "training_rows": len(x),
                           "feature_names": feature_names_v2(), "artifact_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                           "validation_mae": candidates[selected]["validation_mae"],
                           "constant_baseline_validation_mae": float(mean_absolute_error(yv, np.full(len(yv), float(y.mean())))),
                           "validation_rows": len(xv), "hyperparameters": estimator.get_params(),
                           "training_command": "python -m intentprobe.ml.train_v2 --output artifacts/v2",
                           "selection": candidates[selected], "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "numpy": np.__version__, "joblib": joblib.__version__}},
                "dataset": dataset, "protocol": {"summary": "Constraint-aware one-step learned question value with a separate robust output guard.",
                "target": "Loss(before) - loss(after) - 0.006. Loss=regret+1*invalid_recommendation+1*false_no_feasible. Coefficients fixed before fit.",
                "guard": "A transparent finite-catalog check of the raw top candidate over all allowed unknown hard-constraint completions. It never changes question order, STOP, or substitutes a candidate.",
                "score_definition": "Expected synthetic utility on [0,1], not a correctness probability.",
                "feature_boundary": "Observed answers/skips, candidate question, budget, raw top requirements and finite-prior state summaries only; no hidden test preferences or future replies.",
                "sources": source_meta["protocol"]["sources"], "limitations": "No human validation. Incorrect answers cannot be inferred from these structured inputs. Targets are research goals, not guarantees."}}
    write_json(output / "metadata.json", metadata)
    print(json.dumps({"stage": "model_ready", "version": V2_MODEL_VERSION, "rows": len(x), "selected_config": selected,
                      "model_sha256": metadata["model"]["artifact_sha256"]}), flush=True)
    from .evaluate_v2 import evaluate_v2
    report = evaluate_v2(output, v1_dir)
    write_json(output / "benchmark.json", report)
    before = json.loads((output / "v1-preservation-manifest.json").read_text(encoding="utf-8"))
    if frozen_v1_hashes(v1_dir) != before:
        raise ValueError("v1 artifact preservation check failed")
    print(json.dumps({"stage": "complete", "v1_byte_identical": True, "policies": report["policies"], "guarded_policies": report["guarded_policies"]}, indent=2), flush=True)
    return metadata | {"benchmark": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/v2"))
    parser.add_argument("--v1-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    train_v2(args.output, args.v1_dir)


if __name__ == "__main__":
    main()
