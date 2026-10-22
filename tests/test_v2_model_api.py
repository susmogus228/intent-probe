"""Real v2 artifact integration, beyond the small HTTP fixture."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from intentprobe.api import create_app


ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "v2"


@pytest.mark.parametrize("facts, expected", [
    ({}, "needs_confirmation"),
    ({"time": "unknown", "hardware": "cpu", "experience": "beginner"}, "needs_confirmation"),
    ({"time": "weekend"}, "no_feasible"),
    ({"time": "week", "hardware": "cpu", "experience": "beginner"}, "recommendation"),
])
def test_real_artifact_has_distinct_constraint_outcomes(tmp_path, facts, expected):
    with TestClient(create_app(data_dir=tmp_path, artifact_dir=ARTIFACTS)) as client:
        response = client.post("/api/sessions", json={"facts": facts, "budget": 1})
        assert response.status_code == 201, response.text
        session = response.json()
        assert session["outcome"]["status"] == expected
        assert session["outcome"]["guard_applied"] is True
        assert "2.0" in session["model_version"]
        if expected == "recommendation":
            selected = next(p for p in session["ranked_projects"] if p["id"] == session["outcome"]["project_id"])
            assert selected["constraint_status"] == "verified"
        else:
            assert session["outcome"]["project_id"] is None


def test_unknown_at_budget_limit_is_not_a_no_feasible_claim(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, artifact_dir=ARTIFACTS)) as client:
        facts = {"hardware": "cpu", "experience": "beginner", "domain": "language", "goal": "learning"}
        session = client.post("/api/sessions", json={"facts": facts, "budget": 1}).json()
        assert session["next_question"]["id"] == "time"
        preview = client.post(f"/api/sessions/{session['id']}/preview", json={
            "question_id": "time", "value": "week", "expected_revision": session["revision"],
        }).json()
        assert preview["hypothetical"] is True
        assert preview["outcome"]["status"] == "recommendation"
        assert client.get(f"/api/sessions/{session['id']}").json() == session
        updated = client.post(f"/api/sessions/{session['id']}/answers", json={
            "question_id": "time", "value": "unknown", "skip": False, "expected_revision": session["revision"],
        })
        assert updated.status_code == 200, updated.text
        result = updated.json()
        assert result["status"] == "stopped"
        assert result["outcome"]["status"] == "needs_confirmation"
        exported = client.get(f"/api/sessions/{session['id']}/export").json()
        assert exported["schema_version"] == "2"
        assert exported["session"]["outcome"] == result["outcome"]


def test_default_application_loads_v2_not_legacy_artifact(tmp_path):
    with TestClient(create_app(data_dir=tmp_path)) as client:
        response = client.get("/api/meta")
        assert response.status_code == 200, response.text
        assert response.json()["model"]["objective"] == "constraint_aware"
