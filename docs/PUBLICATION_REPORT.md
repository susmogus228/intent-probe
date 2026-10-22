# GitHub source publication

Date: 2026-10-22. The user approved publishing this project and asked for the 84.6% limitation to remain visible.

Repository: [susmogus228/intent-probe](https://github.com/susmogus228/intent-probe), public, default branch `main`.

## Published content and disclosure

The source package includes the frontend, API, tests, trusted v1/v2 model bundles, synthetic data, frozen evaluation, research, model/data cards and interface captures. The README introduction states **84.6% (22/26) no-feasible detection**, below the95% target, at budget three on40 synthetic profiles with two related response variants. It explicitly distinguishes this measure from overall accuracy.

Working directories, local session databases, environment files, dependencies, build outputs, caches and local agent-execution plans are excluded. A bounded independent privacy review passed before publication. No personal contact email was used for the Git author; commits use the account's GitHub noreply identity.

Git attributes preserve artifact bytes. Before push, all25 staged artifact files matched local bytes and the ten original v1 files matched their preserved SHA-256 manifest. The largest file is the10.55MB v2 model, below the ordinary GitHub file-size limit; no Git LFS setup is required for this package.

## Remote verification

Verified source commit: `bef6f9cbd79c04ff559a94c9ac5d0be556aa3eed`.

- The GitHub repository is public and the remote branch matches the pushed source commit.
- An unauthenticated README request returned HTTP200 and matched the committed README bytes.
- The rendered GitHub page contains the84.6% limitation notice.
- All three current v2 screenshots returned HTTP200 with the expected PNG dimensions: two2974x2116 desktop captures and one750x1688 mobile capture.
- [Hosted run39781868153](https://github.com/susmogus228/intent-probe/actions/runs/39781868153) completed successfully for **Backend and frozen models** and **Frontend production build**. Backend runs the63-test suite with Python3.11 and the locked dependencies; frontend builds with Node22.

The first hosted run exposed a workflow setup error: pytest's nested temporary directory had no `work/` parent in a clean checkout. The corrected workflow creates that ignored directory before testing. Model files and evaluation results were not changed to resolve it.

This report and the status badge are documentation changes. [Current main-branch checks](https://github.com/susmogus228/intent-probe/actions/workflows/ci.yml) provide the status for later commits.

## Distribution boundary

Publishing source does not deploy the application. Users start the Python API and built frontend as described in README.md. GitHub Pages was not enabled. The84.6% result remains a small synthetic-audit measurement, not evidence of real-user usefulness or a risk guarantee. Model-quality limitations remain in MODEL_CARD_V2.md.
