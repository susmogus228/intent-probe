from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time

import pytest
from fastapi.testclient import TestClient

from intentprobe.api import create_app


class SmallEngine:
    """Deterministic domain fixture; learned inference is tested in test_ml*.py."""

    questions = [
        {"id": "time", "title": "Time?", "description": "Available time", "options": [{"value": "short", "label": "Short"}, {"value": "long", "label": "Long"}]},
        {"id": "hardware", "title": "Hardware?", "description": "Available hardware", "options": [{"value": "cpu", "label": "CPU"}, {"value": "gpu", "label": "GPU"}, {"value": "unknown", "label": "Not sure"}]},
        {"id": "domain", "title": "Domain?", "description": "Interest", "options": [{"value": "text", "label": "Text"}, {"value": "any", "label": "No preference"}]},
    ]

    def metadata(self):
        return {"questions": self.questions, "catalog": [], "model": {"version": "fixture"}, "dataset": {"kind": "synthetic"}, "benchmark": {"scope": "fixture"}, "protocol": {"limitations": ["Synthetic fixture"]}}

    def inspect(self, facts, excluded, budget, policy):
        available = [q for q in self.questions if q["id"] not in excluded]
        next_q = dict(available[0], reason="Fixture", estimated_gain=0.1) if available and budget and policy != "none" else None
        return {"ranked_projects": [{"id": facts.get("hardware", "unresolved"), "title": "Fixture", "summary": "Fixture", "fit_score": 0.5, "feasible": True, "reasons": [], "tags": []}], "next_question": next_q, "question_values": [], "decision": {"action": "ask" if next_q else "stop", "reason": "Fixture"}, "model_version": "fixture"}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, engine=SmallEngine())) as result:
        yield result


def start(client, **overrides):
    payload = {"initial_request": "A practical project", "budget": 3, "policy": "learned", "facts": {"time": "short"}}
    payload.update(overrides)
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def answer(client, session, q="hardware", value="cpu", skip=False):
    return client.post(f"/api/sessions/{session['id']}/answers", json={"question_id": q, "value": value, "skip": skip, "expected_revision": session["revision"]})


def test_create_restore_export_and_delete(client):
    session = start(client)
    assert session["questions_used"] == 0
    assert session["next_question"]["id"] == "hardware"
    assert client.get("/api/sessions").json()[0]["id"] == session["id"]
    restored = client.get(f"/api/sessions/{session['id']}").json()
    assert restored == session
    export = client.get(f"/api/sessions/{session['id']}/export")
    assert export.status_code == 200
    assert export.json()["session"]["facts"] == {"time": "short"}
    assert "attachment" in export.headers["content-disposition"]
    assert client.delete(f"/api/sessions/{session['id']}").status_code == 204
    assert client.get(f"/api/sessions/{session['id']}").status_code == 404


def test_revised_answer_invalidates_later_answers_and_recomputes(client):
    session = answer(client, start(client)).json()
    session = answer(client, session, "domain", "text").json()
    revised = client.patch(f"/api/sessions/{session['id']}/answers/hardware", json={"value": "gpu", "skip": False, "expected_revision": session["revision"]})
    assert revised.status_code == 200, revised.text
    result = revised.json()
    assert result["invalidated_answers"] == 1
    assert result["questions_used"] == 1
    assert result["facts"] == {"time": "short", "hardware": "gpu"}
    assert result["next_question"]["id"] == "domain"


def test_initial_fact_edit_replays_from_start(client):
    session = answer(client, start(client)).json()
    revised = client.patch(f"/api/sessions/{session['id']}/answers/time", json={"value": "long", "skip": False, "expected_revision": session["revision"]}).json()
    assert revised["facts"] == {"time": "long"}
    assert revised["answers"] == []
    assert revised["invalidated_answers"] == 1


def test_preview_does_not_save_answer_or_advance_revision(client):
    session = start(client)
    preview = client.post(f"/api/sessions/{session['id']}/preview", json={"question_id": "hardware", "value": "gpu", "expected_revision": session["revision"]})
    assert preview.status_code == 200
    assert preview.json()["hypothetical"] is True
    assert preview.json()["ranked_projects"][0]["id"] == "gpu"
    assert client.get(f"/api/sessions/{session['id']}").json() == session


def test_skip_counts_budget_but_unknown_is_a_distinct_answer(client):
    session = start(client, budget=1)
    skipped = answer(client, session, value=None, skip=True).json()
    assert skipped["questions_used"] == 1
    assert "hardware" not in skipped["facts"]
    assert skipped["answers"][0]["skipped"] is True
    assert skipped["status"] == "stopped"
    unknown = answer(client, start(client), value="unknown").json()
    assert unknown["facts"]["hardware"] == "unknown"
    assert unknown["answers"][0]["skipped"] is False


def test_stale_revision_and_stopped_session_are_rejected(client):
    session = start(client)
    assert answer(client, session).status_code == 200
    assert answer(client, session).status_code == 409
    session = start(client)
    stopped = client.post(f"/api/sessions/{session['id']}/stop", json={"expected_revision": session["revision"]}).json()
    assert stopped["status"] == "stopped"
    assert answer(client, stopped).status_code == 409


@pytest.mark.parametrize("overrides", [{"budget": 0}, {"budget": 6}, {"facts": {"hardware": "magic"}}, {"facts": {"secret": "cpu"}}, {"policy": "oracle"}, {"initial_request": "x" * 1001}])
def test_invalid_create_is_not_persisted(client, overrides):
    body = {"budget": 3, "facts": {}, "policy": "learned", "initial_request": "Test"} | overrides
    assert client.post("/api/sessions", json=body).status_code == 422
    assert client.get("/api/sessions").json() == []


def test_invalid_answer_keeps_state(client):
    session = start(client)
    assert answer(client, session, value="magic").status_code == 422
    assert answer(client, session, q="time", value="short").status_code == 409
    assert answer(client, session, value="cpu", skip=True).status_code == 422
    assert client.get(f"/api/sessions/{session['id']}").json() == session


def test_session_survives_app_restart(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, engine=SmallEngine())) as first:
        session = answer(first, start(first)).json()
    with TestClient(create_app(data_dir=tmp_path, engine=SmallEngine())) as second:
        assert second.get(f"/api/sessions/{session['id']}").json() == session


def test_concurrent_answers_use_atomic_revision(client):
    session = start(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: answer(client, session), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    saved = client.get(f"/api/sessions/{session['id']}").json()
    assert saved["questions_used"] == 1


def test_missing_model_is_explicitly_unavailable(tmp_path):
    with TestClient(create_app(data_dir=tmp_path, artifact_dir=tmp_path / "absent")) as unavailable:
        assert unavailable.get("/api/health").status_code == 503
        assert unavailable.get("/api/meta").status_code == 503


def test_benchmark_job_is_real_and_single_flight(tmp_path):
    entered, release = Event(), Event()

    def runner(_):
        entered.set()
        release.wait(5)
        return {"scope": "test-generated", "policies": []}

    with TestClient(create_app(data_dir=tmp_path, engine=SmallEngine(), experiment_runner=runner)) as browser:
        try:
            job = browser.post("/api/experiments").json()
            assert entered.wait(2)
            assert browser.post("/api/experiments").status_code == 409
            assert browser.get(f"/api/experiments/{job['id']}").json()["status"] == "running"
        finally:
            release.set()
    assert job["id"]


def test_browser_host_boundary_and_security_headers(client):
    assert client.get("/api/health", headers={"host": "attacker.invalid"}).status_code == 400
    assert client.get("/api/meta").headers["x-content-type-options"] == "nosniff"


def test_openapi_explains_session_response(client):
    schema = client.get("/openapi.json").json()
    response = schema["paths"]["/api/sessions"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]
    assert response["$ref"].endswith("SessionResponse")
    properties = schema["components"]["schemas"]["SessionResponse"]["properties"]
    assert {"ranked_projects", "next_question", "decision", "remaining_budget", "model_version"}.issubset(properties)


def test_inference_failure_does_not_commit_answer(tmp_path):
    class FailingEngine(SmallEngine):
        def inspect(self, facts, excluded, budget, policy):
            if facts.get("hardware") == "gpu":
                raise RuntimeError("Simulated new-state inference failure")
            return super().inspect(facts, excluded, budget, policy)

    with TestClient(create_app(data_dir=tmp_path, engine=FailingEngine()), raise_server_exceptions=False) as browser:
        session = start(browser)
        assert answer(browser, session, value="gpu").status_code == 500
        assert browser.get(f"/api/sessions/{session['id']}").json() == session


def test_invalid_model_output_does_not_create_saved_session(tmp_path):
    class InvalidEngine(SmallEngine):
        def inspect(self, facts, excluded, budget, policy):
            result = super().inspect(facts, excluded, budget, policy)
            result["ranked_projects"][0]["fit_score"] = 100
            return result

    app = create_app(data_dir=tmp_path, engine=InvalidEngine())
    with TestClient(app, raise_server_exceptions=False) as browser:
        assert browser.post("/api/sessions", json={}).status_code == 500
        assert browser.get("/api/sessions").json() == []


def test_cross_site_forms_cannot_trigger_benchmark_or_mutate_sessions(client):
    response = client.post("/api/experiments", headers={"origin": "https://attacker.invalid", "content-type": "application/x-www-form-urlencoded"}, content="")
    assert response.status_code == 403
    assert client.post("/api/sessions", headers={"origin": "null"}, json={}).status_code == 403
    assert client.post("/api/sessions", headers={"sec-fetch-site": "cross-site"}, json={}).status_code == 403
    assert client.post("/api/sessions", headers={"origin": "http://127.0.0.1:8771"}, json={}).status_code == 201


def test_benchmark_for_a_different_model_is_not_attached(tmp_path):
    class VersionedEngine(SmallEngine):
        def metadata(self):
            metadata = super().metadata()
            metadata["model"]["artifact_sha256"] = "loaded-model-hash"
            return metadata

    with TestClient(create_app(data_dir=tmp_path, engine=VersionedEngine(), experiment_runner=lambda _: {"scope": "wrong bundle", "model_artifact_sha256": "different-model-hash"})) as browser:
        job = browser.post("/api/experiments").json()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            state = browser.get(f"/api/experiments/{job['id']}").json()
            if state["status"] != "running":
                break
            time.sleep(0.01)
        assert state["status"] == "failed"
        assert browser.get("/api/benchmark").json()["scope"] == "fixture"
