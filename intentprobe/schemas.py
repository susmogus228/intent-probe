"""Public response shapes used by OpenAPI and response validation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)


class Option(PublicModel):
    value: str
    label: str


class Question(PublicModel):
    id: str
    title: str
    description: str = ""
    options: list[Option]
    reason: str
    estimated_gain: float = Field(description="Predicted reduction in the recorded synthetic objective after question cost, not a probability. See the model version's objective.")


class Project(PublicModel):
    id: str
    title: str
    summary: str
    fit_score: float = Field(ge=0, le=1, description="Synthetic utility estimate on [0,1]. Not real-world correctness or satisfaction probability.")
    feasible: bool
    reasons: list[str]
    tags: list[str]
    constraint_status: Literal["verified", "unverified", "conflict"] | None = None


class Outcome(PublicModel):
    status: Literal["recommendation", "no_feasible", "needs_confirmation"]
    reason: str
    project_id: str | None = None
    unchecked_constraints: list[str]
    guard_applied: bool

    @model_validator(mode="after")
    def consistent_project(self):
        if (self.status == "recommendation") != bool(self.project_id):
            raise ValueError("Only a recommendation outcome must identify a project.")
        return self


class Decision(PublicModel):
    action: Literal["ask", "stop"]
    reason: str


class QuestionValue(PublicModel):
    question_id: str
    title: str
    estimated_gain: float


class RecordedAnswer(PublicModel):
    question_id: str
    value: str | None
    skipped: bool


class SessionResponse(PublicModel):
    id: str
    revision: int
    status: Literal["active", "stopped"]
    initial_request: str = Field(description="User context note. It is not parsed into model features.")
    budget: int
    policy: str
    initial_facts: dict[str, str]
    answers: list[RecordedAnswer]
    facts: dict[str, str]
    ranked_projects: list[Project]
    next_question: Question | None
    question_values: list[QuestionValue]
    decision: Decision
    outcome: Outcome | None = Field(default=None, description="Constraint check, separate from learned ASK/STOP. Null only for legacy/custom engines. No-feasible means a conflict in this catalog; needs-confirmation means missing evidence.")
    model_version: str
    questions_used: int
    remaining_budget: int
    created_at: str
    updated_at: str
    invalidated_answers: int

    @model_validator(mode="after")
    def consistent_outcome(self):
        if self.outcome and self.outcome.status == "recommendation":
            selected = next((p for p in self.ranked_projects if p.id == self.outcome.project_id), None)
            if selected is None or not selected.feasible or selected.constraint_status != "verified":
                raise ValueError("A confirmed recommendation must identify a verified feasible project.")
        if self.outcome and self.outcome.status == "no_feasible" and any(p.feasible for p in self.ranked_projects):
            raise ValueError("No-feasible outcome contradicts the stated constraint checks.")
        return self
