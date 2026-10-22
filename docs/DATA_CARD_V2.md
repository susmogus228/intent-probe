# IntentProbe v2 data and frozen protocol

Generator version: `project-preferences-2.0`. This is authored synthetic data for
a controlled experiment, not observations from people. No external corpus,
scraped private data or third-party implementation was copied. The catalog and
question wording remain the authored v1 domain; see `DATA_CARD.md` for those
field definitions and scope estimates.

## Membership, grouping and audit status

The finite domain contains 540 complete five-answer preference vectors. V2
preserves the original 300 training and 80 validation memberships and response
variants. The original 120 test vectors had already been examined, so their role
is development diagnostics. They never become training examples.

The 40 vectors absent from all three original splits were frozen before fit.
There is no new seed pretending to create independent data. All 540 base-vector
IDs are content-derived and disjoint across train, validation, development and
final audit. Both response variants and all partial states for a vector remain
in its group. Partially observed feature rows can legitimately coincide across
different complete vectors.

The final-audit record hash is
`90a8cc41cf93fa1d4e24a5a3822aded582aaf73fadaf3b37c95c38c50f384833`.
The frozen protocol records its timestamp, fixed coefficients, configuration
choices and counts before model fitting. Its 80 records are **40 base profiles**,
not 80 independent respondents. The known finite prior uses domain structure;
the audit does not establish external generalization.

## Profiles and labels

Time, hardware and current experience are hard constraints. Domain, goal and
matching complexity define synthetic utility. A weekend is shorter than every
catalog brief and therefore genuinely has no feasible project. Utilities may
have several tied optima; tied recommendations receive no artificial penalty.

Training/validation retain additive balanced/specialist utility families and
truthful/uncertain response variants. Final audit cycles through new additive
profiles, held-out interaction utilities and wrong-hardware noise. Unknown
answers retain uncertainty; indifference neutralizes a soft preference; skip is
an excluded question rather than an answer. The interaction shift is narrow.

The v2 label is the decrease in **raw** terminal loss after an available answer,
minus 0.006. Loss is regret plus one for an invalid recommendation plus one for
a false no-feasible assertion. Correct no-feasible costs zero. The raw terminal
action uses only the current observations. Hidden utility appears in labels and
evaluation, never in inference features. The separate output guard is excluded
from training labels and validation model selection.

There are 19,439 fitted rows and 5,341 validation rows, each with 58 observed-state
features. Rows, labels and profile IDs are persisted in NPZ files. The complete
profile records separately preserve hidden labels so that the simulator can be
audited. No natural-language request parser or demographic feature is involved.

V2 also increases sampled states per response variant from 5 to 12 and observed
features from 50 to 58. Forest settings change along with the loss. Matched v1/v2
results therefore compare combined releases; they do not causally isolate the
effect of the objective. A dedicated ablation was not run.

## Protocol and files

All new outputs are under `artifacts/v2/`:

- `training_protocol.json`: before-fit freeze, 300/80/120/40 counts, fixed
  objective, two candidate configurations and validation selection rule.
- `data/split_manifest.json`: vector IDs, record counts and canonical hashes.
- `data/train_profiles.json`, `data/validation_profiles.json`: unchanged v1
  training/validation memberships and responses.
- `data/development_profiles.json`: previously inspected old test records,
  diagnostic only.
- `evaluation_profiles.json`: the frozen final-audit records.
- `data/training_rows.npz`, `data/validation_rows.npz`: observed inputs, targets
  and base-vector ownership.
- `validation_selection.json`: both configurations' validation metrics and the
  chosen configuration; no audit/development selection.
- `question_value.joblib`, `metadata.json`, `benchmark.json`: fitted model,
  provenance and actual raw/guarded results.
- `v1-preservation-manifest.json`: byte hashes proving old source artifacts
  remain unchanged.

Canonical hashes use sorted compact UTF-8 JSON. The model hash uses actual file
bytes. Every new model/data/config output lives in v2; v1 remains available.

## Reported populations and denominators

Primary v2 results use 40 frozen audit profiles: 54 feasible and 26 infeasible
response cases. Feasible-case mean regret excludes the latter, while the new
penalized objective includes every case. Invalid/issued recommendation risk is
distinct from invalid/all-case violation. Valid-feasible coverage divides valid
issued recommendations by feasible cases. Recommendation rate uses all cases.
False no-feasible rate divides false assertions by feasible cases; no-feasible
detection divides correct assertions by infeasible cases. Counts accompany
these rates. Null conditional risk means no recommendation was issued.

Four infeasible audit cases have an unknown time reply. Even collecting all
their available answers cannot verify the weekend limitation. The resulting
22/26 detection (84.62%) misses the 95% target; the report does not guess time or
relabel ambiguity as successful no-feasible detection. Incorrect supplied facts
can instead cause confidently wrong constraint conclusions; this is explicitly
tested and disclosed.

Confidence intervals resample base-vector groups, preserving response pairs.
Zero-error bootstrap intervals do not certify zero population risk or a 5% risk
bound. Forty independent zero-error profiles would still imply an idealized
one-sided 95% upper bound of about 7.22%; paired variants do not double that
sample size.

## Exploratory stress and limits

The already inspected 120-vector development cohort supports unknown, skip,
constraint skip, wrong-time, budget-zero, forced-stop, five-question and several
truthful initial-fact stress comparisons. Every policy receives the same facts,
answers and budget within a comparison. A separate exhaustive guard oracle
checks 3,000 project/constraint states and all 540 complete vectors. These are
finite-domain correctness and exploratory diagnostics, not new independent
tests or demographic fairness results.

No human-study protocol, participant recruitment, personal data or demographic
performance claims are needed or included. The model is polished and evaluated
within the stated synthetic experiment; real-user benefit and broad
generalization remain unmeasured. Local session corrections do not retrain it.
