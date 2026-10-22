"""Constraint-aware learning and transparent finite-catalog guard regressions."""
from pathlib import Path
import hashlib
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_budget_zero_does_not_claim_unchecked_recommendation():
    from intentprobe.ml.engine import Engine
    result = Engine(ROOT / "artifacts").inspect({}, [], 0, "learned")
    assert "outcome" in result, "A raw top candidate is not a verified recommendation"
    assert result["outcome"]["status"] == "needs_confirmation"
    assert result["outcome"]["project_id"] is None
    assert "time" in result["outcome"]["unchecked_constraints"]
    assert result["decision"]["action"] == "stop"


def test_guard_uses_all_unknown_completions_and_does_not_replace_top():
    from intentprobe.ml.constraints import constraint_outcome, constraint_status
    from intentprobe.ml.domain import Prior, CATALOG
    prior = Prior()
    assert constraint_outcome(prior, {})["status"] == "needs_confirmation"
    assert constraint_outcome(prior, {"time": "unknown"})["status"] == "needs_confirmation"
    assert constraint_outcome(prior, {"time": "weekend"})["status"] == "no_feasible"
    facts = {"time": "week", "experience": "beginner"}
    result = constraint_outcome(prior, facts)
    assert result["status"] == "recommendation"
    assert result["unchecked_constraints"] == []
    _, _, order = prior.rank(facts)
    assert result["project_id"] == CATALOG[int(order[0])]["id"]
    assert constraint_status(CATALOG[0], facts) == "verified"
    assert constraint_status(CATALOG[0], {"time": "weekend"}) == "conflict"
    assert constraint_status(CATALOG[0], {}) == "unverified"


def test_new_loss_rewards_discovering_no_feasible_even_with_zero_utilities():
    from intentprobe.ml.constraints import question_target, raw_loss, ConstraintPrior
    record = {"hidden": {"time": "weekend", "hardware": "cpu", "experience": "beginner", "domain": "tabular", "goal": "practical"}, "family": "balanced"}
    record["answers"] = dict(record["hidden"])
    prior = ConstraintPrior()
    assert raw_loss(prior, {}, record["hidden"], record["family"]) == 1.0
    assert raw_loss(prior, {"time": "weekend"}, record["hidden"], record["family"]) == 0.0
    assert question_target(prior, record, {}, "time") == pytest.approx(0.994)
    assert prior.analytic_gain({}, "time") > 0


def test_false_no_feasible_penalty_and_ordinary_regret_are_separate():
    from intentprobe.ml.constraints import action_metrics
    hidden = {"time": "month", "hardware": "cpu", "experience": "beginner", "domain": "tabular", "goal": "practical"}
    wrong = action_metrics(hidden, "balanced", {"status": "no_feasible", "project_id": None})
    assert wrong["false_no_feasible"] == 1
    assert wrong["invalid_recommendation"] == 0
    assert wrong["objective_loss"] == pytest.approx(wrong["regret"] + 1)
    uncertain = action_metrics(hidden, "balanced", {"status": "needs_confirmation", "project_id": None})
    assert uncertain["false_no_feasible"] == 0
    assert uncertain["issued_recommendation"] == 0
    assert uncertain["regret"] > 0


def test_guard_does_not_change_learned_question_order_or_stop():
    from intentprobe.ml.engine import Engine
    engine = Engine(ROOT / "artifacts")
    for facts, skipped, budget in (({}, [], 3), ({"time": "unknown"}, [], 3), ({}, ["time"], 2), ({"time": "month"}, [], 0)):
        question_id, _, _ = engine.choose(facts, skipped, budget, "learned")
        inspected = engine.inspect(facts, skipped, budget, "learned")
        assert (inspected["next_question"] or {}).get("id") == question_id
        assert inspected["decision"]["action"] == ("ask" if question_id else "stop")
        assert inspected["outcome"]["guard_applied"] is True


def test_lying_about_time_cannot_be_magically_detected():
    from intentprobe.ml.constraints import constraint_outcome, action_metrics
    from intentprobe.ml.domain import Prior
    hidden = {"time": "weekend", "hardware": "cpu", "experience": "beginner", "domain": "tabular", "goal": "practical"}
    result = constraint_outcome(Prior(), {"time": "week", "hardware": "cpu", "experience": "beginner"})
    assert result["status"] == "recommendation"
    assert action_metrics(hidden, "balanced", result)["invalid_recommendation"] == 1


def test_freeze_keeps_v1_membership_and_reserves_only_unused_vectors(tmp_path):
    from intentprobe.ml.train_v2 import freeze_protocol
    protocol = freeze_protocol(ROOT / "artifacts", tmp_path)
    assert protocol["counts"] == {"train": 300, "validation": 80, "development": 120, "final_audit": 40}
    memberships = json.loads((tmp_path / "data" / "split_manifest.json").read_text())
    sets = [set(memberships[name]["profile_ids"]) for name in ("train", "validation", "development", "final_audit")]
    assert sum(map(len, sets)) == len(set.union(*sets)) == 540
    assert protocol["objective"] == {"invalid_recommendation": 1.0, "false_no_feasible": 1.0, "question_cost": 0.006}
    assert protocol["frozen_before_fit"] is True


def test_v2_artifact_is_constraint_aware_and_replays_raw_and_guarded_metrics():
    from intentprobe.ml.engine import Engine
    from intentprobe.ml.evaluate_v2 import rollout_v2, summarize
    folder = ROOT / "artifacts" / "v2"
    engine = Engine(folder)
    metadata = engine.metadata()
    assert metadata["model"]["objective"] == "constraint_aware"
    assert len(metadata["model"]["feature_names"]) == 58
    # Learning constraint value does not require a manually forced first slot.
    # Verify that the learned policy asks time in a truthful infeasible session.
    facts, asked = {}, []
    truthful = {"time": "weekend", "hardware": "cpu", "experience": "beginner", "domain": "tabular", "goal": "practical"}
    for budget in (3, 2, 1):
        result = engine.inspect(facts, [], budget, "learned")
        if result["next_question"] is None:
            break
        question = result["next_question"]["id"]
        asked.append(question)
        facts[question] = truthful[question]
    assert "time" in asked
    assert engine.inspect(facts, [], 0, "learned")["outcome"]["status"] == "no_feasible"
    records = json.loads((folder / "evaluation_profiles.json").read_text())
    pairs = [rollout_v2(engine, record, "learned", 3) for record in records]
    for index, key in ((0, "policies"), (1, "guarded_policies")):
        summary = summarize([pair[index] for pair in pairs], "learned")
        frozen = metadata["benchmark"][key][0]
        for field in ("mean_regret", "mean_objective_with_cost", "recommendation_risk", "feasible_coverage", "no_feasible_detection_rate"):
            assert summary[field] == pytest.approx(frozen[field])


def test_v1_artifact_bytes_are_preserved():
    from intentprobe.ml.train_v2 import frozen_v1_hashes
    manifest = json.loads((ROOT / "artifacts" / "v2" / "v1-preservation-manifest.json").read_text())
    assert frozen_v1_hashes(ROOT / "artifacts") == manifest


def test_full_guard_algebra_matches_all_completion_oracle():
    from intentprobe.ml.evaluate_v2 import audit_guard_algebra
    from intentprobe.ml.domain import Prior
    audit = audit_guard_algebra(Prior())
    assert audit["complete_vectors"] == 540
    assert audit["constraint_project_checks"] == 3000
    assert audit["failures"] == []


def test_abstaining_everywhere_is_not_scored_as_safe_full_coverage():
    from intentprobe.ml.engine import Engine
    from intentprobe.ml.evaluate_v2 import rollout_v2, summarize
    folder = ROOT / "artifacts" / "v2"
    record = json.loads((folder / "evaluation_profiles.json").read_text())[0]
    record["hidden"]["time"] = "month"
    record["answers"] = dict(record["hidden"])
    row = rollout_v2(Engine(folder), record, "none", 0)[1]
    summary = summarize([row], "none")
    assert summary["recommendation_risk"] is None
    assert summary["feasible_coverage"] == 0.0
    assert summary["mean_regret"] > 0
