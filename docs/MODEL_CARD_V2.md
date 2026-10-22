# IntentProbe v2: constraint-aware question value

## What is trained

The version `intentprobe-question-value-2.0` is a locally fitted
`ExtraTreesRegressor`, not an LLM wrapper or a rule-only questionnaire. Its
learned role is choosing a clarification question or STOP. A separate finite
prior ranks the 20 authored project briefs, identically for all policies. The
briefs are ideas, not claims that 20 applications have been implemented.

Version one remains available, with its model, data, metadata and benchmark
unchanged byte for byte. `artifacts/v2/v1-preservation-manifest.json` records the
ten source-file hashes. Loading v1 still uses its original feature schema,
prior and question-selection objective. Its response can additionally expose
the transparent guard; its historical benchmark remains a raw v1 benchmark.

## Objective fixed before fitting

For a terminal **raw** action, define:

```text
L = recommendation_regret
    + 1.0 * invalid_recommendation
    + 1.0 * false_no_feasible
question_target = L(before) - L(after the observed answer) - 0.006
STOP value = 0
```

Regret is the best hidden synthetic utility minus delivered utility. Several
equally optimal projects are accepted. An invalid recommendation violates the
hidden profile's hard constraints. A false `no_feasible` assertion rejects a
profile with an available project. Correct `no_feasible` has loss zero. When
the catalog is truly infeasible, utilities are all zero but an invalid issued
recommendation now costs one; learning to ask time therefore has value.

The guard is **excluded** from both before/after labels and raw validation
selection. It cannot remove this training signal by abstaining. The coefficients,
two candidate configurations and validation selection rule were written to
`training_protocol.json` before fitting. Neither the old inspected test nor the
final audit selected a configuration. No model was refitted after audit results.

## Separate output guard

The guard checks the raw top candidate against every allowed completion of
unstated time, hardware and experience. These constraints are monotone thresholds
on a finite Cartesian product, so checking each allowed minimum is equivalent
to enumerating all combinations. An independent exhaustive oracle checked
3,000 project/constraint states and all 540 complete preference vectors, with
no disagreement. This establishes finite-catalog guard correctness, not learned
model generalization.

The guard does not reorder questions, override STOP, relax constraints or
substitute an easier candidate. Its public outcomes are:

- `recommendation`: the raw top candidate is verified for every allowed
  completion; `project_id` identifies that candidate.
- `no_feasible`: stated hard facts already rule out the entire catalog;
  `project_id` is null.
- `needs_confirmation`: a possible completion can invalidate the raw top
  candidate; `project_id` is null and the relevant unchecked constraints are
  listed. The state does not assert that the catalog is infeasible.

Each ranked brief has `constraint_status`: `verified`, `unverified` or `conflict`.
Verification depends on accurate answers. A false stated time or hardware answer
cannot be magically detected by this structured-input model. Incorrect-time
stress deliberately demonstrates both invalid recommendations and false
no-feasible assertions. Unknown, skip, indifference, exhausted budget and forced
stop never fabricate a constraint confirmation.

## Data and model selection

The original 300 training and 80 validation vector memberships are preserved.
Their response variants and derived states stay grouped. The old 120 test vectors
were already inspected, so v2 calls them **development diagnostics**. The remaining
40 unused vectors were frozen, with hash
`90a8cc41cf93fa1d4e24a5a3822aded582aaf73fadaf3b37c95c38c50f384833`,
before model fitting. This is a small final audit within the same known finite
synthetic lattice, not a new external dataset or real-human evaluation.

The selected model fitted 19,439 state/question rows with 58 observed-state
features. Validation has 5,341 rows. Inputs contain current answers/skips,
candidate question, remaining budget, ranking summaries, top requirements and
finite-prior constraint uncertainty. Hidden utility, profile IDs, future answers,
split and utility-family labels are not inference features.

Two fixed ExtraTrees configurations were compared using raw constraint-aware
validation loss plus question cost at budget three. The selected configuration
has 120 trees, depth 22, minimum leaf size 2 and seed 42. Validation objective
with cost was 0.18921, versus 0.19426 for the other configuration. Validation MAE
was 0.24249, versus 0.25433 for a constant predictor. The other candidate had
slightly lower MAE, but MAE was explicitly secondary to the terminal objective.
No group cross-validation was run; no pseudo-CV result is claimed.

This release changes more than the loss: observed features increase from 50 to
58, sampled partial states per response variant from 5 to 12, and the selected
forest from 80 to 120 trees with different depth/leaf settings. The matched v1/v2
comparison evaluates the combined release. It is not a controlled ablation and
cannot attribute the improvement causally to the new loss alone.

## Measured frozen audit, 2026-10-22

Budget three, identical empty initial facts, 40 base profiles with two grouped
response variants each. There are 54 feasible cases and 26 infeasible cases.

| Metric | Legacy v1 raw | v2 raw | v2 plus guard |
|---|---:|---:|---:|
| Invalid issued recommendations / all cases | 26/80 (32.50%) | 7/80 (8.75%) | 0/80 |
| Invalid / issued recommendations | 26/78 | 7/58 (12.07%) | 0/48 |
| Valid issued / feasible cases | 52/54 | 51/54 | 48/54 (88.89%) |
| Correct no-feasible / infeasible cases | 2/26 | 22/26 | 22/26 (84.62%) |
| False no-feasible / feasible cases | 0/54 | 0/54 | 0/54 |
| Mean feasible-case regret | 0.10370 | 0.15741 | 0.20000 |
| Mean all-case objective with question cost | 0.40430 | 0.20808 | 0.14933 |

V2 reduces constraint errors while sacrificing some preference utility. The
guard reduces issuance further; coverage and regret expose that cost. The
analytic v2 baseline's raw objective with cost is 0.14939, better than the learned
model's 0.20808 on this small audit. No superiority to the strong baseline is
claimed.

The **95% no-feasible detection target was missed**: observed detection is 84.62%.
Four infeasible response variants answer `unknown` to time. Even all their
available replies do not establish infeasibility, so a factual guard must retain
`needs_confirmation`; it cannot invent that answer to reach the target. The
raw audit all-case violation rate is 8.75%, despite 2.50% on the already inspected
development cohort. Development no-feasible detection is 98%, guarded feasible
coverage 85.26%, and guarded observed recommendation risk zero. Development
numbers are diagnostic and are not an independent validation claim.

The preregistered goals are point-estimate research targets, not promised or
certified safety levels. Zero observed errors in 48 issued responses does not
mean zero population risk: response variants share base profiles. Even zero
errors in 40 independent Bernoulli profiles would have a one-sided 95% upper
bound of about 7.22%, above 5%. In fact fewer than 40 profiles receive an issued
recommendation, so the relevant bound would be weaker. A zero-width bootstrap
interval for an all-zero finite sample does not remove this uncertainty.

## Evaluation, reproduction and limits

Raw and guarded versions of all six policies use the same budgets, initial
facts, catalog and available replies. Conditional risk, all-case violation,
valid feasible coverage, recommendation rate, detection, false no-feasible,
regret and cost-adjusted objective are all reported with counts. A policy
abstaining everywhere has null issued risk, zero feasible coverage and positive
forgone-utility regret, rather than perfect performance.

Intervals use 600 seeded paired/grouped profile resamples. Ratios bootstrap
grouped numerator/denominator sums, not independent turns. Curves cover budgets
zero through five on the final audit. Unknown/skipped constraints, incorrect
time, forced stop, budget zero, five questions and multiple truthful initial-fact
sets have exploratory development-cohort evaluations. The exhaustive guard
audit is separate from these policy evaluations. A new seed over the same 540
vectors would not create independent data.

```powershell
python -m intentprobe.ml.train_v2 --output artifacts/v2
python -m pytest tests/test_ml_core.py tests/test_ml_v2.py -q --basetemp=work/pytest-v2
```

`evaluate_artifact(Path("artifacts/v2"))` repeats frozen evaluation without
training. The selected model SHA-256 is
`9b9d3e22ae16265841e95c59066753bbca13d954cc07e15f5e8483943a5aba1e`.
Runtime versions are recorded in metadata; incompatible sklearn versions and
corrupted models are rejected. Joblib uses pickle: use only trusted local
artifacts. A matching companion hash is integrity evidence, not authentication.

No humans, private data, demographic attributes, external inference services or
automatic training from saved sessions were used. No demographic fairness,
ordinary-LLM superiority or universal intent-understanding claim is made.
The shifted utility family is narrow and often preserves the same optimum.
The incorrect-time stress is deliberately adversarial: in the development
cohort its 50 issued recommendations violate the true time limit and its 190
no-feasible assertions are false. These constructed failures demonstrate the
truthful-input boundary; they are not an estimate of population error rates.
Research precedents and authorship boundaries remain in `RESEARCH.md`.
