"""The HTTP boundary must preserve and validate constraint outcomes."""

from fastapi.testclient import TestClient

from intentprobe.api import create_app
from test_api import SmallEngine, answer, start


class OutcomeEngine(SmallEngine):
    def inspect(self, facts, excluded, budget, policy):
        result = super().inspect(facts, excluded, budget, policy)
        confirmed = facts.get("hardware") in {"cpu", "gpu"}
        result["ranked_projects"][0]["constraint_status"] = "verified" if confirmed else "unverified"
        result["outcome"] = {
            "status": "recommendation" if confirmed else "needs_confirmation",
            "reason": "Confirmed fixture constraints" if confirmed else "Hardware still needs confirmation",
            "project_id": result["ranked_projects"][0]["id"] if confirmed else None,
            "unchecked_constraints": [] if confirmed else ["hardware"],
            "guard_applied": True,
        }
        return result


def test_openapi_documents_three_distinct_outcomes(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, engine=OutcomeEngine())) as client:
        components = client.get("/openapi.json").json()["components"]["schemas"]
        assert "outcome" in components["SessionResponse"]["properties"]
        assert set(components["Outcome"]["properties"]["status"]["enum"]) == {
            "recommendation", "no_feasible", "needs_confirmation"
        }


def test_preview_preserves_hypothetical_outcome_without_committing(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, engine=OutcomeEngine())) as client:
        session = start(client)
        assert session["outcome"]["status"] == "needs_confirmation"
        preview = client.post(f"/api/sessions/{session['id']}/preview", json={
            "question_id": "hardware", "value": "cpu", "expected_revision": session["revision"],
        }).json()
        assert preview["hypothetical"] is True
        assert preview["outcome"]["status"] == "recommendation"
        assert client.get(f"/api/sessions/{session['id']}").json() == session


def test_manual_stop_does_not_turn_uncertainty_into_success(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, engine=OutcomeEngine())) as client:
        session = start(client)
        stopped = client.post(f"/api/sessions/{session['id']}/stop", json={"expected_revision": session["revision"]}).json()
        assert stopped["status"] == "stopped"
        assert stopped["outcome"] == session["outcome"]
        assert stopped["next_question"] is None


def test_invalid_confirmed_outcome_does_not_commit(tmp_path):
    class InvalidOutcome(OutcomeEngine):
        def inspect(self, facts, excluded, budget, policy):
            result = super().inspect(facts, excluded, budget, policy)
            result["outcome"].update(status="recommendation", project_id=None)
            return result

    with TestClient(create_app(data_dir=tmp_path, engine=InvalidOutcome()), raise_server_exceptions=False) as client:
        assert client.post("/api/sessions", json={}).status_code == 500
        assert client.get("/api/sessions").json() == []


def test_outcome_cannot_claim_a_conflicting_project_is_confirmed(tmp_path):
    class ConflictOutcome(OutcomeEngine):
        def inspect(self, facts, excluded, budget, policy):
            result = super().inspect(facts, excluded, budget, policy)
            result["ranked_projects"][0].update(feasible=False, constraint_status="conflict")
            return result

    with TestClient(create_app(data_dir=tmp_path, engine=ConflictOutcome()), raise_server_exceptions=False) as client:
        assert client.post("/api/sessions", json={"facts": {"hardware": "cpu"}}).status_code == 500
        assert client.get("/api/sessions").json() == []


def test_invalid_recomputed_outcome_is_rejected_in_preview_and_export(tmp_path):
    class ChangedEngine(OutcomeEngine):
        broken = False

        def inspect(self, facts, excluded, budget, policy):
            result = super().inspect(facts, excluded, budget, policy)
            if self.broken:
                result["outcome"].update(status="recommendation", project_id=result["ranked_projects"][0]["id"])
                result["ranked_projects"][0].update(feasible=False, constraint_status="conflict")
            return result

    engine = ChangedEngine()
    with TestClient(create_app(data_dir=tmp_path, engine=engine), raise_server_exceptions=False) as client:
        session = start(client)
        engine.broken = True
        assert client.post(f"/api/sessions/{session['id']}/preview", json={
            "question_id": "hardware", "value": "cpu", "expected_revision": session["revision"],
        }).status_code == 500
        assert client.get(f"/api/sessions/{session['id']}/export").status_code == 500
        engine.broken = False
        assert client.get(f"/api/sessions/{session['id']}").json() == session
