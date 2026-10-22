# IntentProbe API contract v2

Owner: root integrator. All public text is English. Local-first, no external inference service.

## Core interface (Python)

`from intentprobe.ml.engine import Engine`

- `Engine(artifact_dir: Path)` loads only locally trained trusted artifacts. Missing model raises a clear error; never silently use rules as the learned model.
- `engine.metadata() -> dict` returns `questions`, `catalog`, `model`, `dataset`, `benchmark`, `protocol`.
- `engine.inspect(facts: dict[str,str], excluded: list[str], budget: int, policy: str) -> dict` returns `ranked_projects`, `next_question`, `question_values`, `decision`, `outcome`, `model_version`.
- Policy IDs: `learned`, `fixed`, `random`, `information_gain`, `analytic`, `none`.
- Questions: `{id,title,description,options:[{value,label}]}`. Options include only real answers. Skip is a separate action. Unknown and indifferent can be explicit distinct options when meaningful.
- Ranked project: `{id,title,summary,fit_score,feasible,constraint_status,reasons:[str],tags:[str]}`. `constraint_status` is `verified | unverified | conflict`. Score is a synthetic-model utility estimate on [0,1], not a probability. `feasible` concerns stated constraints; verification also checks admissible completions of unknown supported hard limits.
- Outcome: `{status:"recommendation"|"no_feasible"|"needs_confirmation",reason,project_id:string|null,unchecked_constraints:[str],guard_applied:boolean}`. Only a recommendation identifies a project; the response validator requires that project to exist, be feasible and have verified constraints. No-feasible cannot coexist with a feasible catalog item. Insufficient information is not no-feasible. The guard does not secretly change the learned ASK/STOP policy.
- Next question: question object plus `{reason,estimated_gain}`; null when stopped. The estimate can be negative, never format as a correctness probability.
- Question values: `[{question_id,title,estimated_gain}]`.
- Decision: `{action: "ask"|"stop",reason}`. An infeasible catalog is an explicit stop reason, never a recommendation.
- `model`: `{version,objective,estimator,trained_at,training_rows,feature_names:[str],artifact_sha256,validation_mae}`. V2 objective is `constraint_aware`; v1 artifacts retain their original recorded objective.
- `dataset`: `{kind:"synthetic",train_profiles,validation_profiles,test_profiles,split_seed,generator_version,limitations:[str],splits_disjoint:true}`.
- `benchmark`: `{generated_at,model_version,scope,policies:[{id,label,mean_regret,ci_low,ci_high,mean_questions,constraint_violation_rate}],curves:[{policy,budget,mean_regret}],stress_tests:[{name,description,results:[{policy,mean_regret}]}],notes:[str]}`. All values computed from actual runs; stress_tests can be an empty list only if limitations explicitly explain missing conditions.
- `protocol`: English prose, source links, metric and simulator limitations.

## HTTP

- `GET /api/health` -> `{status:"ok",model_version}`.
- `GET /api/meta` -> metadata object above.
- `GET /api/benchmark` -> benchmark above.
- `POST /api/experiments` -> `{id,status:"running"|"completed"|"failed",error?:str}`. Re-run frozen benchmark on current artifact; one concurrent job, 409 while busy. `GET /api/experiments/{id}` polls job. Does not retrain or tune on test data.
- `POST /api/sessions` body `{initial_request:str,budget:int,policy:str,facts:Record<string,string>}`. Budget 1..5. All request facts validated against question options. Request text is a context note, not silently parsed or used as model features.
- `GET /api/sessions` -> `[{id,initial_request,updated_at,status}]`.
- `GET /api/sessions/{id}` -> Session.
- `POST /api/sessions/{id}/answers` body `{question_id,value:string|null,skip:boolean,expected_revision:int}`. Only available question IDs. Applies answer or skip, recalculates from stored facts. New answer consumes a question; revision to an existing answer does not consume another. Reject beyond budget or stopped session; use revision endpoint to edit existing answers.
- `PATCH /api/sessions/{id}/answers/{question_id}` body `{value:string|null,skip:boolean,expected_revision:int}`. Edit an existing answer or initial fact. Editing earlier answers removes subsequent answers, marks dependent conclusions invalidated, recomputes ranking. Retains context note and budget. This is intentional replay, never fabricate counterfactual human answers.
- `POST /api/sessions/{id}/stop` body `{expected_revision:int}`.
- `DELETE /api/sessions/{id}` -> 204, removes local session data.
- `GET /api/sessions/{id}/export` -> JSON with session, provenance, limitations. No unseen profile values.
- `POST /api/sessions/{id}/preview` body `{question_id,value,expected_revision}` -> `{hypothetical:true,ranked_projects,decision,outcome}`. Read only, allowed question or edited answer; no mutation/revision increment. The server validates the full hypothetical session before returning its subset.

Session:
`{id,revision,status:"active"|"stopped",initial_request,budget,policy,initial_facts,answers:[{question_id,value:string|null,skipped:boolean}],facts,ranked_projects,next_question,question_values,decision,outcome,model_version,questions_used,remaining_budget,created_at,updated_at,invalidated_answers:int}`.

The default artifact path is `artifacts/v2`. Missing or incompatible artifacts fail explicitly; the server does not fall back to v1. Set `INTENTPROBE_ARTIFACT_DIR` to a trusted v1 bundle only when deliberately choosing it. Stored answers are recomputed using the currently loaded model. Export schema version 2 records this provenance. Manual STOP preserves the constraint outcome and does not imply a successful recommendation.

V2 benchmark adds a separate `guarded_policies` table. Rates include `recommendation_risk` (nullable when no recommendation is issued), `recommendation_rate`, `feasible_coverage` and `false_no_feasible_rate`, as well as the original metrics. `scope` identifies the small final audit; historical diagnostics must retain their separate label. See SIMULATION-PROTOCOL-V2.md for denominators and limitations.

Errors use standard FastAPI `{detail: string|array}`; 422 invalid input, 404 absent record, 409 stale revision or invalid state, 503 missing model. All mutations use expected revision and SQLite transaction. Session IDs random UUIDs. SQLite/runtime/exports ignored by Git. Service binds localhost by default; no public multi-user/auth claim.

## UI

Default Try the model: explicit initial constraint controls and context note, ask/skip/stop, ranked feasible projects and why, clear hypothetical preview before applying, edit answer/history, local saved sessions and delete/export. Distinguish unknown, skipped and indifferent. No fake percentages.

ML workbench: chosen light cobalt reference. Dataset/training/evaluation/inspect navigation with real data, pipeline, model version, provenance/splits, comparison table, regret-by-budget visualization, run benchmark and actual job states, API docs link. No dead training button: show exact reproducible CLI command rather than imply browser training. Test numbers mean synthetic evaluation only.
