# Resource provenance

| Resource | Source | Use | Conditions / verification |
|---|---|---|---|
| Approved UI reference | User-approved generated option 3, docs/design/approved-workbench.png | Layout reference only | Generated in this chat; editable application uses HTML and React components |
| Clarification literature | Primary links in RESEARCH.md | Method and evaluation design | No paper text, third-party training dataset or implementation copied |
| scikit-learn | https://scikit-learn.org/stable/ | Local regression model | BSD-3-Clause; exact installed version in requirements.lock and model metadata |
| FastAPI | https://fastapi.tiangolo.com/ | API and OpenAPI schemas | MIT; exact version in requirements.lock |
| React | https://react.dev/ | Frontend components | MIT; exact version in frontend/package-lock.json |
| Vite | https://vite.dev/ | Frontend build/dev tooling | MIT; exact version in frontend/package-lock.json |
| Phosphor icons | https://github.com/phosphor-icons/react | Consistent UI icons | MIT; @phosphor-icons/react version in lockfile; source assets are library icons |
| Selective-risk literature | https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html | Distinguish empirical risk/coverage reporting from formal risk control | Primary paper consulted; no implementation or guarantee copied |
| ML evaluation guidance | https://scikit-learn.org/stable/modules/cross_validation.html | Separate validation, diagnostic replay and final audit; group related observations | Official documentation consulted for v2; no new dependency |
| GitHub Actions | https://github.com/actions/checkout/releases/tag/v7.0.1; https://github.com/actions/setup-python/releases/tag/v7.1.0; https://github.com/actions/setup-node/releases/tag/v7.1.0 | Hosted backend tests and frontend build | Official release tags and commit SHAs checked before publishing; actions pinned to those commits with read-only contents permission |

The synthetic profile generator and project catalog are authored in this project. Model and data cards document their assumptions, version and hashes. No participant data, external inference API, real search history or private chat export enters training.
