# Data provenance

The authored catalog, questions and controlled synthetic profiles are generated
by `intentprobe.ml` and frozen under `artifacts/data/` when training runs. See
`docs/DATA_CARD.md` for population assumptions, split integrity and limitations.
No external dataset or personal data is required.

Reproduce the default 300/80/120 vector-disjoint profile split with:

```powershell
python -m intentprobe.ml.train --output artifacts
```
