"""Same-origin API for local IntentProbe sessions and frozen-model evaluation."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
from threading import Lock
from typing import Callable, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from intentprobe.store import Conflict, NotFound, Store
from intentprobe.schemas import SessionResponse


ROOT = Path(__file__).resolve().parents[1]
Policy = Literal["learned", "fixed", "random", "information_gain", "analytic", "none"]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreateSession(StrictBody):
    model_config = ConfigDict(json_schema_extra={"examples": [{"initial_request": "A practical ML project in four weeks", "budget": 3, "policy": "learned", "facts": {"time": "month"}}]})
    initial_request: str = Field(default="", max_length=1000)
    budget: int = Field(default=3, ge=1, le=5)
    policy: Policy = "learned"
    facts: dict[str, str] = Field(default_factory=dict, max_length=10)


class Revision(StrictBody):
    expected_revision: int = Field(ge=0)


class EditAnswer(Revision):
    value: str | None = Field(default=None, max_length=80)
    skip: bool = False

    @model_validator(mode="after")
    def consistent_answer(self):
        if (self.skip and self.value is not None) or (not self.skip and self.value is None):
            raise ValueError("Provide an answer value or skip=true with value=null.")
        return self


class Answer(EditAnswer):
    question_id: str = Field(min_length=1, max_length=80)


class Preview(Revision):
    question_id: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=80)


def create_app(data_dir: Path | None = None, artifact_dir: Path | None = None, engine=None, experiment_runner: Callable | None = None) -> FastAPI:
    data_dir = Path(data_dir or os.environ.get("INTENTPROBE_DATA_DIR", ROOT / "runtime"))
    artifact_dir = Path(artifact_dir or os.environ.get("INTENTPROBE_ARTIFACT_DIR", ROOT / "artifacts" / "v2"))
    store = Store(data_dir / "sessions.sqlite3")
    job_lock = Lock()
    jobs: dict[str, dict] = {}
    current_job: list[str | None] = [None]
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="intentprobe-evaluation")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.engine = engine
        application.state.model_error = None
        application.state.benchmark = None
        if engine is None:
            try:
                from intentprobe.ml.engine import Engine
                application.state.engine = Engine(artifact_dir)
            except (FileNotFoundError, ValueError, ImportError, RuntimeError, OSError) as error:
                application.state.model_error = type(error).__name__
        yield
        executor.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(title="IntentProbe local API", version="0.2.0", description="Constraint-aware learned clarification on a controlled synthetic benchmark. Explicit recommendation, no-feasible and needs-confirmation outcomes. Local-only sessions; no human study or external inference API.", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver", "[::1]"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        allowed_origins = {str(request.base_url).rstrip("/"), "http://127.0.0.1:8771", "http://localhost:8771", "http://127.0.0.1:5173", "http://localhost:5173"}
        unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
        origin = request.headers.get("origin")
        if unsafe and (request.headers.get("sec-fetch-site") == "cross-site" or (origin is not None and origin not in allowed_origins)):
            response = JSONResponse(status_code=403, content={"detail": "Cross-origin changes are not allowed. Use the local IntentProbe application."})
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(NotFound)
    async def not_found_handler(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(Conflict)
    async def conflict_handler(request, error):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    def get_engine():
        loaded = getattr(app.state, "engine", None)
        if loaded is None:
            raise HTTPException(503, "Trained model unavailable. From the project root, run: python -m intentprobe.ml.train_v2 --output artifacts/v2, then restart the server. Set INTENTPROBE_ARTIFACT_DIR only to an explicitly chosen trusted artifact directory.")
        return loaded

    def metadata():
        return get_engine().metadata()

    def check_answer(question_id: str, value: str | None, skip=False):
        question = next((question for question in metadata()["questions"] if question["id"] == question_id), None)
        if question is None:
            raise HTTPException(422, "Unknown question ID.")
        if not skip and value not in {option["value"] for option in question["options"]}:
            raise HTTPException(422, "Invalid answer option for this question.")

    def present(record: dict) -> dict:
        facts = dict(record["initial_facts"])
        excluded = list(facts)
        for answer in record["answers"]:
            excluded.append(answer["question_id"])
            if not answer["skipped"]:
                facts[answer["question_id"]] = answer["value"]
        remaining = max(0, record["budget"] - len(record["answers"]))
        inspection = get_engine().inspect(facts=facts, excluded=excluded, budget=remaining, policy=record["policy"])
        if record["status"] == "stopped":
            inspection = inspection | {"next_question": None, "decision": {"action": "stop", "reason": "You ended this session. You can still inspect recommendations or edit an earlier answer."}}
        stopped = record["status"] == "stopped" or inspection["decision"]["action"] == "stop"
        return record | inspection | {"facts": facts, "questions_used": len(record["answers"]), "remaining_budget": remaining, "status": "stopped" if stopped else "active"}

    def revise(record: dict, question_id: str, value: str | None, skip: bool):
        check_answer(question_id, value, skip)
        if question_id in record["initial_facts"]:
            record["invalidated_answers"] = len(record["answers"])
            record["answers"] = []
            if skip:
                record["initial_facts"].pop(question_id)
            else:
                record["initial_facts"][question_id] = value
        else:
            index = next((index for index, answer in enumerate(record["answers"]) if answer["question_id"] == question_id), None)
            if index is None:
                raise Conflict("Only a recorded answer or initial fact can be revised.")
            record["invalidated_answers"] = len(record["answers"]) - index - 1
            record["answers"] = record["answers"][:index] + [{"question_id": question_id, "value": value, "skipped": skip}]
        record["status"] = "active"

    def transaction_response(session_id: str, expected_revision: int, change: Callable) -> dict:
        result = {}

        def validate(record):
            result.update(SessionResponse.model_validate(present(record)).model_dump())

        store.mutate(session_id, expected_revision, change, validate=validate)
        return result

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model_version": metadata()["model"]["version"]}

    @app.get("/api/meta")
    def meta():
        value = metadata()
        if app.state.benchmark is not None:
            value = value | {"benchmark": app.state.benchmark}
        return value

    @app.get("/api/benchmark")
    def benchmark():
        return app.state.benchmark if app.state.benchmark is not None else metadata()["benchmark"]

    @app.post("/api/sessions", status_code=201, response_model=SessionResponse)
    def create_session(body: CreateSession):
        for key, value in body.facts.items():
            check_answer(key, value)
        get_engine()
        result = {}

        def validate(record):
            result.update(SessionResponse.model_validate(present(record)).model_dump())

        store.create(body.initial_request.strip(), body.budget, body.policy, body.facts, validate=validate)
        return result

    @app.get("/api/sessions")
    def list_sessions():
        result = []
        for record in store.list():
            session = present(record)
            result.append({key: session[key] for key in ("id", "initial_request", "updated_at", "status")})
        return result

    @app.get("/api/sessions/{session_id}", response_model=SessionResponse)
    def read_session(session_id: str):
        return present(store.get(session_id))

    @app.post("/api/sessions/{session_id}/answers", response_model=SessionResponse)
    def add_answer(session_id: str, body: Answer):
        check_answer(body.question_id, body.value, body.skip)

        def change(record):
            current = present(record)
            if current["status"] != "active" or current["remaining_budget"] == 0:
                raise Conflict("Session has stopped. Edit an earlier answer or start a new session.")
            if body.question_id in record["initial_facts"] or any(answer["question_id"] == body.question_id for answer in record["answers"]):
                raise Conflict("This question already has a recorded value; use the revision endpoint.")
            if not current["next_question"] or body.question_id != current["next_question"]["id"]:
                raise Conflict("Answer the currently proposed question or reload the session.")
            record["answers"].append({"question_id": body.question_id, "value": body.value, "skipped": body.skip})
            record["invalidated_answers"] = 0

        return transaction_response(session_id, body.expected_revision, change)

    @app.patch("/api/sessions/{session_id}/answers/{question_id}", response_model=SessionResponse)
    def edit_answer(session_id: str, question_id: str, body: EditAnswer):
        return transaction_response(session_id, body.expected_revision, lambda record: revise(record, question_id, body.value, body.skip))

    @app.post("/api/sessions/{session_id}/preview")
    def preview(session_id: str, body: Preview):
        check_answer(body.question_id, body.value)
        record = deepcopy(store.get(session_id))
        if record["revision"] != body.expected_revision:
            raise Conflict("Session changed. Reload before previewing an answer.")
        existing = body.question_id in record["initial_facts"] or any(answer["question_id"] == body.question_id for answer in record["answers"])
        if existing:
            revise(record, body.question_id, body.value, False)
        else:
            current = present(record)
            if current["status"] != "active" or not current["next_question"] or body.question_id != current["next_question"]["id"]:
                raise Conflict("Only the next proposed answer can be previewed.")
            record["answers"].append({"question_id": body.question_id, "value": body.value, "skipped": False})
        inspected = SessionResponse.model_validate(present(record)).model_dump()
        return {"hypothetical": True, "ranked_projects": inspected["ranked_projects"], "decision": inspected["decision"], "outcome": inspected.get("outcome")}

    @app.post("/api/sessions/{session_id}/stop", response_model=SessionResponse)
    def stop(session_id: str, body: Revision):
        return transaction_response(session_id, body.expected_revision, lambda record: record.update(status="stopped"))

    @app.delete("/api/sessions/{session_id}", status_code=204)
    def delete(session_id: str):
        store.delete(session_id)
        return Response(status_code=204)

    @app.get("/api/sessions/{session_id}/export")
    def export(session_id: str):
        session = SessionResponse.model_validate(present(store.get(session_id))).model_dump()
        value = {"schema_version": "2", "session": session, "provenance": {"model_version": session["model_version"], "scope": "Synthetic preference model; not a calibrated probability of human satisfaction. Stored answers are recomputed using the currently loaded model."}, "limitations": metadata().get("dataset", {}).get("limitations", [])}
        return Response(content=json.dumps(value, indent=2, allow_nan=False), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="intentprobe-{session["id"]}.json"'})

    def run_experiment(job_id: str):
        try:
            if experiment_runner is None:
                from intentprobe.ml.evaluate import evaluate_artifact
                result = evaluate_artifact(artifact_dir)
            else:
                result = experiment_runner(artifact_dir)
            loaded_metadata = metadata()
            expected_model = loaded_metadata["model"].get("artifact_sha256")
            expected_test = loaded_metadata.get("dataset", {}).get("test_records_sha256")
            if (expected_model and result.get("model_artifact_sha256") != expected_model) or (expected_test and result.get("test_records_sha256") != expected_test):
                raise ValueError("Evaluation bundle differs from the loaded model. Restart after replacing artifacts.")
            with job_lock:
                app.state.benchmark = result
                jobs[job_id]["status"] = "completed"
        except Exception as error:
            with job_lock:
                jobs[job_id].update(status="failed", error=f"Evaluation failed ({type(error).__name__}). Check the local server log.")
            import logging
            logging.getLogger(__name__).exception("Frozen benchmark evaluation failed")
        finally:
            with job_lock:
                current_job[0] = None

    @app.post("/api/experiments", status_code=202)
    def experiment():
        get_engine()
        with job_lock:
            if current_job[0] is not None:
                raise Conflict("An evaluation is already running. Wait for it to finish.")
            job_id = str(uuid4())
            if len(jobs) >= 20:
                jobs.pop(next(iter(jobs)))
            jobs[job_id] = {"id": job_id, "status": "running"}
            current_job[0] = job_id
            executor.submit(run_experiment, job_id)
            return dict(jobs[job_id])

    @app.get("/api/experiments/{job_id}")
    def experiment_status(job_id: str):
        with job_lock:
            if job_id not in jobs:
                raise NotFound("Evaluation job not found. Jobs are local to this server process.")
            return dict(jobs[job_id])

    distribution = ROOT / "frontend" / "dist"
    if distribution.is_dir():
        app.mount("/assets", StaticFiles(directory=distribution / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend():
        if not (distribution / "index.html").is_file():
            return JSONResponse(status_code=503, content={"detail": "Frontend build missing. Run npm ci and npm run build in frontend/. API docs are at /docs."})
        return FileResponse(distribution / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    return app


app = create_app()
