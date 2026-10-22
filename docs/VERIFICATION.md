# Local verification record

## Current v2 result, 2026-10-22

Scope: the approved constraint-aware model, explicit outcomes and synthetic audit. The user excluded human participants. No human study, external inference service or public application deployment was performed. The later source publication and hosted checks are documented in [PUBLICATION_REPORT.md](PUBLICATION_REPORT.md).

| Check | Actual result |
|---|---|
| Python suite | **63 passed**, no failures/errors/skips; outputs/pytest-v2.xml, 18.26 seconds |
| ML subset | 22 tests included in the full suite; v1 compatibility, loss, guard, data roles, noise and model integrity |
| Frontend | TypeScript/Vite production build passed; final JS 313.37kB, gzip 93.35kB |
| API | Actual v2 artifact and explicit v1 load passed integration; OpenAPI describes Outcome; preview/export validate the complete session |
| Live server | Loopback port 8771 serves question-value-2.0; no missing-model fallback |
| Evaluation job | Run experiment visibly changed running to completed; no training; report stays tied to loaded model/test hashes |
| Independent code review | Pass for API/schema and corrected frontend loss mapping |
| Independent statistical review | Warn, no blocking calculation/leakage defect; target miss and simulator limits remain |
| Preservation | Independent review confirmed all ten v1 artifact files byte-identical |

The existing Starlette TestClient deprecation warning remains visible. No dependency was added to suppress it. The full suite predates the final copy-only frontend edits; the final frontend build and browser checks cover those edits. Python behavior did not change afterward.

### Browser and numeric reconciliation

The in-app browser used the production build. Checked desktop 1487x1058, mobile 390x844 and compact 320x740. At the narrow sizes, document client/scroll widths matched 375/375 and 305/305; tables scrolled internally. Device metrics were cleared afterward. No physical-phone or Safari test is claimed.

Verified actual creation with explicit initial limits, hypothetical unknown-answer preview, apply, budget exhaustion retaining needs-confirmation, no-feasible weekend, editing time to restore a feasible recommendation, manual STOP, saved-session reopening and reload. New/opened sessions return to the page top; answer revisions retain position. The raw model still chooses the question; the guard does not manufacture a missing answer.

Found and fixed a v2 presentation mismatch: the UI formula described constraint-aware loss while the table used feasible-only regret plus cost. A browser check first observed 0.1725 where the saved all-case objective was 0.2081. The final UI uses `mean_objective_with_cost` and its matching intervals for v2, and displays **0.2081 raw / 0.1493 guarded**, with the all-case denominator. Legacy v1 retains its own field and feasible-only label. The independent code reviewer confirmed all twelve row mappings.

Normal browser console errors: none observed. Three current captures live in docs/images/v2/. Earlier screenshots below refer to v1.

### Quality boundaries

The final 40-vector audit contains 80 related response variants. Matched v1/v2 raw violations are26/80 versus 7/80. Guarded learned issues48 recommendations with 0 observed violations and valid coverage 48/54. No-feasible detection 22/26 (84.62%) misses the 95% target. Four relevant replies leave time unknown, so neither budget nor the guard can invent confirmation.

The old 120-vector diagnostic cohort improves from 22.5% to 2.5% violations. Its outcomes informed v2 design and are not an independent test. Forty audit vectors and 26 distinct profiles receiving guarded recommendations cannot certify population risk below 5%. Regret increased while the new objective improved; several modeling choices changed together, and learned has not established an advantage over the analytic baseline. See MODEL_CARD_V2.md and the independent review.

## Historical v1 verification

Date: 2026-10-22. Scope: approved local application, trained model and synthetic evaluation. Public release and user acceptance are separate.

## Automated evidence

| Check | Result | Evidence |
|---|---|---|
| Python regression suite | 40 passed; zero errors, failures or skips | outputs/pytest.xml; `python -m pytest -q --basetemp=work/pytest-final --junitxml=outputs/pytest.xml` |
| Frontend TypeScript and production build | Passed | `npm --prefix frontend run build` runs tsc-b and Vite; JS307.95kB, gzip91.94kB |
| Real model/API boundary | Passed | tests/test_model_api.py; actual inference, infeasible outcome and executable Swagger example |
| Live HTTP smoke | Passed | outputs/smoke.json; health, matching model/test hashes, create201, export200 and disposable-session delete204 |
| Artifact and split integrity | Passed | ML tests and independent statistical review |

One visible dependency warning remains: Starlette1.9.0 deprecates its httpx-based TestClient. Assertions pass; the warning is not suppressed. Pytest uses project-local work/ temporary directories.

## Browser evidence

The in-app browser rendered the production build served by Python. Checked desktop 1487x1058, mobile 390x844 and compact 320x740 CSS viewports. Document scroll width equalled client width; wide tables scrolled inside their containers.

Verified creation, keyboard radio selection, hypothetical preview without saving, applied answers and changed recommendations. Revised an earlier answer after STOP: the app removed the later dependent answer, showed a notice and recalculated. Skip and explicit unknown remained distinct, and the budget stopped further questions.

Reopened saved sessions after a server restart and switched sessions with an unsaved editor. Opened deletion confirmation and cancelled; automated tests and a disposable live HTTP record verified actual deletion. Browser automation did not delete a user-created session.

Preserved an infeasible weekend limit and displayed the explicit no-feasible result. Ran a real frozen benchmark from the UI and observed running/completed states. Opened Dataset, Train, Evaluate, Inspect and interactive API schemas. Simulated an offline request, observed a useful error, restored networking and created a session successfully. Normal browser flows had no captured console errors.

See QA-INVENTORY.md and project-root design-qa.md. These are Chromium viewport checks, not physical-phone or Safari tests.

## Independent reviews

Statistical review: **warn**, no remaining blocking protocol issue. The reviewer reproduced all six budget-three policies to1e-12 and checked zero vector overlap. The warning concerns model quality and synthetic scope.

Code review: **pass** on corrected API/store/state boundaries. The selected implementation-reviewer could not run because its configured model was unsupported; an available Code Reviewer supplied the actual review. Root also verified subsequent frontend state-reset changes in the browser. Review details are in reviews/.

Initial findings included grouping overlap, omitted cost metrics, cross-site benchmark triggering, post-commit inference failure and a cross-session editor. The implementation closes these with regression and browser evidence.

## Quality and limits

Training used7,927 rows from300 profiles; validation/test contain80/120 distinct preference vectors. The test has95 feasible profiles.

Budget-three regret: learned0.11697, analytic0.11776, information gain0.10974, no clarification0.54474. The cost-adjusted paired interval crosses zero. No advantage over strong baselines is established.

Learned hidden-constraint violations are22.5%; no-feasible detection is4%. The objective does not reward infeasibility discovery separately. The UI exposes these limits and checks fit only against stated constraints.

Not verified: human usefulness, LLM comparison, arbitrary free-text understanding, physical handset/Safari, Linux/macOS execution, public hosting or GitHub publication. Session answers do not retrain the model. Only trusted local joblib bundles may load.
