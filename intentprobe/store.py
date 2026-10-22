"""Transactional, revision-aware local session storage."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Callable
from uuid import uuid4


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL, payload TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, initial_request: str, budget: int, policy: str, facts: dict, validate: Callable[[dict], None] | None = None) -> dict:
        now = utc_now()
        record = {"id": str(uuid4()), "revision": 0, "status": "active", "initial_request": initial_request, "budget": budget, "policy": policy, "initial_facts": facts.copy(), "answers": [], "created_at": now, "updated_at": now, "invalidated_answers": 0}
        if validate is not None:
            validate(record)
        with self.connect() as connection:
            connection.execute("INSERT INTO sessions VALUES (?,?,?)", (record["id"], now, json.dumps(record)))
        return record

    def get(self, session_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise NotFound("Session not found.")
        return json.loads(row[0])

    def list(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM sessions ORDER BY updated_at DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, session_id: str) -> None:
        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            if cursor.rowcount != 1:
                raise NotFound("Session not found.")

    def mutate(self, session_id: str, expected_revision: int, change: Callable[[dict], None], validate: Callable[[dict], None] | None = None) -> dict:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise NotFound("Session not found.")
            record = json.loads(row[0])
            if record["revision"] != expected_revision:
                raise Conflict("Session changed. Reload the latest session before trying again.")
            change(record)
            record["revision"] += 1
            record["updated_at"] = utc_now()
            if validate is not None:
                validate(record)
            connection.execute("UPDATE sessions SET updated_at=?, payload=? WHERE id=?", (record["updated_at"], json.dumps(record), session_id))
        return record
