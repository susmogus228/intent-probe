# Requirements and evidence register

Human source: this chat, 2026-10-22. Scope: one actual ML portfolio project, IntentProbe. Option 3 approved with default Try the model and separate ML workbench. Status is updated during verification.

| ID | Requirement | Approval | Status | Evidence |
|---|---|---|---|---|
| R1 | Learned model, real training, held-out evaluation | Explicit | Locally verified, synthetic scope | MODEL_CARD_V2.md; artifacts/v2;22 ML tests; independent statistical replay |
| R2 | Research analogs first and explain distinction honestly | Explicit | Done | RESEARCH.md, primary sources |
| R3 | UI option 3, English, Try the model first | Explicit | Locally verified | design-qa.md; actual browser and screenshots |
| R4 | Working frontend and backend/API | Explicit current implementation | Locally verified | 63 tests; frontend TypeScript/build; live v2 API and browser experiment |
| R5 | Reproducible training, model/data provenance and strong baselines | Agreed ML specification | Verified with quality limits | V2 model/data cards; 300/80/120/40 manifests; matched raw/guarded baselines; hashes |
| R6 | Ask/skip/unknown/revise/stop, no silent constraint relaxation | Agreed specification | Locally verified | API/model tests and browser answer/revision/skip/stop flows |
| R7 | Local sessions, export and delete, no automatic cross-user learning | Agreed specification | Locally verified | SQLite restart/revision tests; live export/delete; browser restore |
| R8 | Real benchmark values, uncertainty, no synthetic-to-human claims | Agreed specification | Verified with warnings | Statistical v2 review warn; target miss and regret trade-off; browser loss fields reconciled to API |
| R9 | Actual desktop/mobile UI checks and useful error states | User testing expectations | Browser verified | 1487x1058,390x844,320x740; offline error/recovery; no physical-phone claim |
| R10 | Public documentation and run instructions | Portfolio requirement | Prepared locally | README; lockfiles; cards; API schemas;3 annotated screenshots |
| R11 | Publish source on GitHub, with the 84.6% limitation visible | Explicit publication approval, 2026-10-22 | Public source and hosted checks verified; app hosting remains local | PUBLICATION_REPORT.md; anonymous README/screenshots HTTP200; limitation notice at the top |
| R12 | Constraint-aware v2 objective, explicit outcomes and independent constraint guard | Explicit follow-up approval, 2026-10-22 | Implemented and locally verified; quality goals partly met | MODEL_CARD_V2.md; 63 tests; three outcome browser flows; detection 84.62% below 95% target |
| R13 | Preserve v1; report raw and guarded performance with coverage and matched baselines | Approved v2 plan | Verified | Separate v2 bundle; ten preserved v1 hashes; independent paired replay; UI and cards |
| R14 | Improve ML without human participants or external simulated-human claims | Latest explicit instruction | Active constraint | No participant recruitment, collection or study UI |

Model quality, code correctness, local usability, public release and user acceptance are separate. A running server does not establish real-human usefulness or overall user acceptance.
