"""Behavioral tests written before the ML implementation."""
from pathlib import Path
import importlib.util
import hashlib
import json

import pytest


def test_ml_core_exists_and_does_not_replace_missing_model_with_rules(tmp_path):
    assert importlib.util.find_spec("intentprobe.ml.engine") is not None, "A trained-model engine is required"
    from intentprobe.ml.engine import Engine
    with pytest.raises((FileNotFoundError, ValueError), match="(?i)(model|artifact|train)"):
        Engine(tmp_path)


def test_profile_families_have_disjoint_groups_and_frozen_shift():
    from intentprobe.ml.simulator import generate_profiles
    records = generate_profiles(seed=42, train_count=40, validation_count=12, test_count=16)
    groups = {name: {p["profile_id"] for p in records if p["split"] == name} for name in ("train", "validation", "test")}
    assert not (groups["train"] & groups["validation"] | groups["train"] & groups["test"] | groups["test"] & groups["validation"])
    for group in {p["profile_id"] for p in records}:
        assert len({p["split"] for p in records if p["profile_id"] == group}) == 1
    assert {p["condition"] for p in records if p["split"] == "test"} == {"in_distribution", "preference_shift", "answer_noise"}


def test_semantically_identical_preferences_do_not_cross_splits():
    from intentprobe.ml.simulator import generate_profiles
    records = generate_profiles(seed=42, train_count=200, validation_count=50, test_count=60)
    seen = {}
    for record in records:
        signature = json.dumps(record["hidden"], sort_keys=True)
        if signature in seen:
            assert seen[signature] == record["split"], "Identical preference vectors must not cross splits regardless of utility family"
        seen[signature] = record["split"]


def test_observation_features_do_not_accept_hidden_preferences():
    from intentprobe.ml.domain import Prior, features, feature_names
    prior = Prior()
    observed = {"time": "month", "hardware": "cpu"}
    vector = features(prior, observed, [], "domain", 3)
    assert len(vector) == len(feature_names())
    assert all(isinstance(float(x), float) for x in vector)
    assert not any("hidden" in name or "profile_id" in name or "family" in name for name in feature_names())
    assert features(prior, {"domain": "unknown"}, [], "goal", 2) != features(prior, {"domain": "indifferent"}, [], "goal", 2)
    assert features(prior, {}, ["domain"], "goal", 2) != features(prior, {"domain": "unknown"}, [], "goal", 2)


def test_catalog_constraints_and_no_feasible_outcome():
    from intentprobe.ml.domain import CATALOG, Prior
    assert len(CATALOG) >= 16
    prior = Prior()
    scores, feasible, _ = prior.rank({"time": "weekend", "hardware": "cpu", "experience": "beginner"})
    assert not any(feasible)
    scores, feasible, _ = prior.rank({"time": "month", "hardware": "cpu", "experience": "beginner"})
    assert any(feasible)
    assert all(0 <= value <= 1 for value in scores)
    assert not any(feasible[i] for i, item in enumerate(CATALOG) if item["hardware_level"] > 0)


def test_empty_bootstrap_group_is_not_presented_as_perfect_zero():
    from intentprobe.ml.evaluate import ci_mean
    with pytest.raises(ValueError, match="(?i)(empty|insufficient|no profiles)"):
        ci_mean({})


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    from intentprobe.ml.train import train
    folder = tmp_path_factory.mktemp("trained")
    train(folder, seed=12, train_count=80, validation_count=20, test_count=24, states_per_profile=3, trees=16)
    return folder


def test_actual_training_and_frozen_replay_are_reproducible(trained):
    from intentprobe.ml.engine import Engine
    from intentprobe.ml.evaluate import evaluate_artifact
    engine = Engine(trained)
    metadata = engine.metadata()
    assert metadata["model"]["training_rows"] > 0
    assert metadata["model"]["estimator"] == "ExtraTreesRegressor"
    assert metadata["model"]["artifact_sha256"] == hashlib.sha256((trained / "question_value.joblib").read_bytes()).hexdigest()
    assert metadata["dataset"]["splits_disjoint"] is True
    report = evaluate_artifact(trained)
    assert report["policies"] == metadata["benchmark"]["policies"]
    assert report["curves"] == metadata["benchmark"]["curves"]
    assert {p["id"] for p in report["policies"]} == {"learned", "analytic", "information_gain", "fixed", "random", "none"}
    assert len(report["stress_tests"]) >= 2
    for policy in report["policies"]:
        assert policy["ci_low"] <= policy["mean_regret"] <= policy["ci_high"]
        assert 0 <= policy["constraint_violation_rate"] <= 1
        assert policy["mean_total_loss"] >= policy["mean_regret"]
        assert policy["total_loss_ci_low"] <= policy["mean_total_loss"] <= policy["total_loss_ci_high"]
    assert len(report["paired_total_loss_comparisons"]) == 5


def test_engine_uses_real_estimator_and_validates_state(trained):
    from intentprobe.ml.engine import Engine
    engine = Engine(trained)
    result = engine.inspect({}, [], 3, "learned")
    assert result["decision"]["action"] in {"ask", "stop"}
    assert len(result["ranked_projects"]) >= 16
    assert len(result["question_values"]) == 5
    exhausted = engine.inspect({}, [], 0, "learned")
    assert exhausted["next_question"] is None
    assert exhausted["decision"]["action"] == "stop"
    impossible = engine.inspect({"time": "weekend"}, [], 3, "learned")
    assert impossible["next_question"] is None
    assert "feasible" in impossible["decision"]["reason"].lower()
    revised = engine.inspect({"domain": "vision"}, [], 3, "analytic")
    assert all(x["question_id"] != "domain" for x in revised["question_values"])
    skipped = engine.inspect({}, ["hardware"], 3, "learned")
    assert all(x["question_id"] != "hardware" for x in skipped["question_values"])
    with pytest.raises(ValueError):
        engine.inspect({"hardware": "quantum"}, [], 3, "learned")
    with pytest.raises(ValueError):
        engine.inspect({}, [], 3, "chatgpt")


def test_corrupted_artifact_is_rejected_before_loading(trained, tmp_path):
    import shutil
    from intentprobe.ml.engine import Engine
    shutil.copytree(trained, tmp_path / "copy")
    path = tmp_path / "copy" / "question_value.joblib"
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="(?i)(hash|integrity)"):
        Engine(tmp_path / "copy")


def test_incompatible_sklearn_is_rejected_before_pickle_loading(trained, tmp_path):
    import shutil
    from intentprobe.ml.engine import Engine
    shutil.copytree(trained, tmp_path / "copy")
    path = tmp_path / "copy" / "metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["model"]["environment"]["scikit_learn"] = "0.0.0"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="(?i)(version|incompatible)"):
        Engine(tmp_path / "copy")


def test_stale_benchmark_is_omitted_instead_of_mixing_model_bundles(trained, tmp_path):
    import shutil
    from intentprobe.ml.engine import Engine
    shutil.copytree(trained, tmp_path / "copy")
    path = tmp_path / "copy" / "benchmark.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["model_artifact_sha256"] = "0" * 64
    path.write_text(json.dumps(report), encoding="utf-8")
    assert Engine(tmp_path / "copy").metadata()["benchmark"] == {}
