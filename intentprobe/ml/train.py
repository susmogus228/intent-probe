"""Reproducible local CPU training. Example: python -m intentprobe.ml.train --output artifacts"""
import argparse
from datetime import datetime, timezone
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

from .domain import CATALOG, QUESTIONS, Prior, feature_names, GENERATOR_VERSION, MODEL_VERSION
from .simulator import generate_profiles, training_examples, sha256, canonical_bytes


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def train(output: Path, seed=42, train_count=300, validation_count=80, test_count=120, states_per_profile=5, trees=80):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data_dir = output / "data"
    data_dir.mkdir(exist_ok=True)
    records = generate_profiles(seed, train_count, validation_count, test_count)
    splits = {split: [p for p in records if p["split"] == split] for split in ("train", "validation", "test")}
    group_sets = {split: {p["profile_id"] for p in rows} for split, rows in splits.items()}
    assert not (group_sets["train"] & group_sets["test"] | group_sets["train"] & group_sets["validation"] | group_sets["validation"] & group_sets["test"])
    prior = Prior()
    x_train, y_train, train_groups = training_examples(splits["train"], prior, seed + 1, states_per_profile)
    x_validation, y_validation, validation_groups = training_examples(splits["validation"], prior, seed + 2, states_per_profile)
    if not len(x_train) or not len(x_validation):
        raise ValueError("Not enough profile examples to train and validate")
    estimator = ExtraTreesRegressor(n_estimators=trees, max_depth=15, min_samples_leaf=8, random_state=seed, n_jobs=1)
    with threadpool_limits(limits=1):
        estimator.fit(x_train, y_train)
        predicted = estimator.predict(x_validation)
    mae = float(mean_absolute_error(y_validation, predicted))
    baseline_mae = float(mean_absolute_error(y_validation, np.full(len(y_validation), float(y_train.mean()))))
    model_path = output / "question_value.joblib"
    joblib.dump(estimator, model_path, compress=3)
    write_json(output / "evaluation_profiles.json", splits["test"])
    write_json(data_dir / "catalog.json", CATALOG)
    write_json(data_dir / "questions.json", QUESTIONS)
    (data_dir / "profiles.jsonl").write_bytes(b"\n".join(canonical_bytes(p) for p in records) + b"\n")
    manifest = {split: {"profile_ids": sorted(group_sets[split]), "base_profiles": len(group_sets[split]),
                        "records": len(rows), "records_sha256": sha256(rows)} for split, rows in splits.items()}
    write_json(data_dir / "split_manifest.json", manifest)
    np.savez_compressed(data_dir / "training_rows.npz", X=x_train, y=y_train, profile_id=np.asarray(train_groups))
    np.savez_compressed(data_dir / "validation_rows.npz", X=x_validation, y=y_validation, profile_id=np.asarray(validation_groups))
    importance = sorted(zip(feature_names(), map(float, estimator.feature_importances_)), key=lambda pair: -pair[1])
    metadata = {"model": {"version": MODEL_VERSION, "estimator": "ExtraTreesRegressor", "trained_at": datetime.now(timezone.utc).isoformat(),
                           "training_rows": len(x_train), "feature_names": feature_names(),
                           "artifact_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(), "validation_mae": mae,
                           "constant_baseline_validation_mae": baseline_mae, "validation_rows": len(x_validation),
                           "training_command": "python -m intentprobe.ml.train --output artifacts",
                           "hyperparameters": estimator.get_params(), "top_features": [{"name": name, "importance": value} for name, value in importance[:15]],
                           "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "numpy": np.__version__, "joblib": joblib.__version__}},
                "dataset": {"kind": "synthetic", "train_profiles": train_count, "validation_profiles": validation_count, "test_profiles": test_count,
                            "split_seed": seed, "generator_version": GENERATOR_VERSION, "splits_disjoint": True,
                            "catalog_sha256": sha256(CATALOG), "records_sha256": sha256(records), "test_records_sha256": sha256(splits["test"]),
                            "manifest_sha256": sha256(manifest), "conditions": ["in_distribution", "preference_shift", "answer_noise"],
                            "limitations": ["Controlled synthetic utilities and replies, not human preference data.", "Fixed English questions and a hand-authored catalog of 20 project briefs.",
                                            "Complete five-answer preference vectors are disjoint regardless of utility family; all response variants stay grouped. Partially observed feature states can recur.",
                                            "Held-out interaction utilities and wrong-hardware replies test limited shifts, not unrestricted real-world generalization.",
                                            "No protected attributes or demographic fairness evaluation; domain, hardware and experience slices are available."]},
                "protocol": {"summary": "Learn a regression surrogate for one-step question value. Compare frozen policies with identical ranking, facts, catalog and budgets.",
                             "target": "Realized reduction in hidden synthetic recommendation regret after one answer, minus a 0.006 question cost. STOP has value zero.",
                             "feature_boundary": "Only observed categorical answers, skipped flags, candidate question, remaining budget and observed-state prior summaries. Hidden utilities are evaluator/label inputs only.",
                             "score_definition": "Expected synthetic utility on [0,1] under a uniform finite preference prior; never a correctness probability.",
                             "sources": [{"title": "Interactive Classification by Asking Informative Questions, ACL 2020", "url": "https://aclanthology.org/2020.acl-main.237/"},
                                         {"title": "PEPPER, EMNLP Findings 2025", "url": "https://aclanthology.org/2025.findings-emnlp.1067/"},
                                         {"title": "Clarify When Necessary, NAACL Findings 2025", "url": "https://aclanthology.org/2025.findings-naacl.306/"}],
                             "limitations": "A learned one-step approximation, not novel RL, human validation, or a universal intent detector. A matching file hash does not authenticate an untrusted pickle artifact."}}
    write_json(output / "metadata.json", metadata)
    from .evaluate import evaluate_artifact
    report = evaluate_artifact(output)
    write_json(output / "benchmark.json", report)
    return metadata | {"benchmark": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-profiles", type=int, default=300)
    parser.add_argument("--validation-profiles", type=int, default=80)
    parser.add_argument("--test-profiles", type=int, default=120)
    parser.add_argument("--states-per-profile", type=int, default=5)
    parser.add_argument("--trees", type=int, default=80)
    args = parser.parse_args()
    if min(args.train_profiles, args.validation_profiles, args.test_profiles) < 6:
        parser.error("Each split needs at least six base profiles")
    result = train(args.output, args.seed, args.train_profiles, args.validation_profiles, args.test_profiles, args.states_per_profile, args.trees)
    print(json.dumps({"model": result["model"]["version"], "training_rows": result["model"]["training_rows"],
                      "validation_mae": result["model"]["validation_mae"], "policies": result["benchmark"]["policies"]}, indent=2))


if __name__ == "__main__":
    main()
