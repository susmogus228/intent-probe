# Code review: constraint-aware v2 integration

Reviewer: independent Code Reviewer, read-only. Final verdict: **pass for the reviewed API/schema and frontend delta**. This verdict does not certify real-user model quality.

Initial finding: preview could return a contradictory confirmed recommendation because it bypassed `SessionResponse` validation. Export also returned raw recomputed data. Root reproduced the failure in a regression test, then validated the full session in both paths. The reviewer reran the new regression: one passed, persisted state unchanged. Manual STOP retains the actual constraint outcome. Mutations validate before commit; missing v2 artifacts do not silently select v1.

The final delta review checked all six raw and six guarded loss rows against the actual saved benchmark. V2 selects `mean_objective_with_cost` with `objective_ci_low/high`; v1 selects its existing feasible-only loss fields. Learned raw 0.2081 and guarded 0.1493 match the browser and API. STOP copy distinguishes the three outcomes. Scroll reset depends on view, section and session ID, not answer revision.

Root verification: 63 Python tests, final TypeScript/Vite build, browser outcomes at desktop/mobile, hypothetical preview, actual evaluation job and console checks. The reviewer did not claim a separate full browser or complete-model code audit.
