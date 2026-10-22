"""Integration at the real trained model / public schema boundary."""

from pathlib import Path
import math

from fastapi.testclient import TestClient

from intentprobe.api import create_app
from intentprobe.ml.engine import Engine


ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def test_public_session_uses_actual_trained_policy(tmp_path):
    engine = Engine(ARTIFACTS)
    with TestClient(create_app(data_dir=tmp_path, engine=engine)) as client:
        meta = client.get("/api/meta").json()
        assert meta["model"]["training_rows"] > 0
        assert meta["dataset"]["kind"] == "synthetic"
        assert meta["benchmark"]["policies"]
        created = client.post("/api/sessions", json={"initial_request": "API integration check", "facts": {"time": "month"}, "policy": "learned", "budget": 3})
        assert created.status_code == 201, created.text
        session = created.json()
        direct = engine.inspect({"time": "month"}, ["time"], 3, "learned")
        assert session["model_version"] == meta["model"]["version"]
        assert session["ranked_projects"] == direct["ranked_projects"]
        assert session["next_question"] == direct["next_question"]
        for _ in range(3):
            question = session["next_question"]
            if question is None:
                break
            choice = next(option["value"] for option in question["options"] if option["value"] != "unknown")
            response = client.post(f"/api/sessions/{session['id']}/answers", json={"question_id": question["id"], "value": choice, "skip": False, "expected_revision": session["revision"]})
            assert response.status_code == 200, response.text
            session = response.json()
            assert all(math.isfinite(project["fit_score"]) for project in session["ranked_projects"])
        assert session["questions_used"] <= 3
        assert session["status"] == "stopped"


def test_actual_empty_feasible_set_is_an_explicit_outcome(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, artifact_dir=ARTIFACTS)) as client:
        response = client.post("/api/sessions", json={"facts": {"time": "weekend"}})
        assert response.status_code == 201, response.text
        session = response.json()
        assert session["status"] == "stopped"
        assert session["next_question"] is None
        assert not any(project["feasible"] for project in session["ranked_projects"])
        assert session["facts"]["time"] == "weekend"
        assert "No feasible" in session["decision"]["reason"]


def test_swagger_request_example_can_be_executed(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, artifact_dir=ARTIFACTS)) as client:
        schema = client.get("/openapi.json").json()
        example = schema["components"]["schemas"]["CreateSession"]["examples"][0]
        response = client.post("/api/sessions", json=example)
        assert response.status_code == 201, response.text
        assert response.json()["facts"] == {"time": "month"}
