# Constraint-aware simulation protocol v2

Date: 2026-10-22. Scope: a trained clarification policy over the authored finite project catalog. The user excludes human participants. This protocol does not authorize recruitment, participant data, external inference or public publication.

## Decision and objective

The learned predictor estimates the value of asking one admissible question. It sees observed answers, skipped flags, remaining budget and public prior summaries. Hidden profile values, future answers and synthetic utility-family labels belong to the label generator and evaluator only.

Use the fixed coefficients in the approved plan: recommendation regret plus 1.0 for an invalid recommendation and 1.0 for a false assertion that no item is feasible. Compute training losses from the raw terminal action (top recommendation, or no-feasible established by observed constraints), before applying the guard. Using guarded abstention here could again remove the incentive to discover no-feasible cases. Subtract 0.006 per question when generating question-value targets. Correct no-feasible decisions have zero terminal loss. These constants describe the simulator; they do not estimate human satisfaction or burden.

Keep the constraint guard separate. It checks the raw top candidate and preserves the learned question order and stopping choice. `needs_confirmation` means insufficient evidence and must not count as correct no-feasible detection. Verification covers this catalog's supported constraints and supplied values. Wrong answers and incorrect catalog estimates remain possible.

## Data roles fixed before fitting

| Population | Role |
|---|---|
| Original 300 training vectors | Fit model parameters |
| Original 80 validation vectors | Select settings and diagnose validation behavior |
| Original 120 test vectors | Historical diagnostic cohort that motivated v2; no longer independent |
| Original 40 unused vectors | Freeze before fit; small final audit within the same 540-vector space |
| Exhaustive finite space and constructed stress cases | Technical coverage and exploratory stress checks; not additional independent users |

Keep every answer variant and observed prefix in its base profile's group. Never split dialogue turns randomly. A seed change over the same finite support does not create a new independent population. Preserve manifests, group IDs, actual fitted rows, frozen records, configuration and hashes. If a final-audit result motivates a code or objective change, label the subsequent audit exploratory and disclose the change.

The prior enumerates the declared finite domain as prior knowledge. It must not fit its probabilities or utility families to validation/audit outcomes. This experiment does not establish generalization to a new catalog or arbitrary free-form requests.

## Comparisons

Compare learned, analytic decision value, information gain, fixed questionnaire, random admissible questions and no clarification. Use the same catalog, initial facts, answer variants, maximum follow-up budget and question cost. Apply the same constraint guard to each policy in a second table. Preserve a v1 comparison on matched diagnostic/audit profiles. Label the loss version rather than comparing differently defined losses as if they were identical.

Default primary budget: three follow-up questions. Report available budget curves, including zero budget where no new evidence is available. A policy must not spend extra guard questions outside the shared budget.

## Required outcomes and denominators

- All-case violation rate: invalid issued recommendations / all rollouts.
- Recommendation risk: invalid issued recommendations / issued recommendations. Zero issued recommendations means unavailable risk, not 0% risk.
- Recommendation rate: issued recommendations / all rollouts.
- Feasible coverage: valid issued recommendations / feasible-profile rollouts. A recommendation that violates a hidden constraint does not count as coverage. Report issuance separately through recommendation rate.
- No-feasible detection: correct `no_feasible` outcomes / no-feasible-profile rollouts.
- False no-feasible rate: erroneous `no_feasible` outcomes / feasible-profile rollouts.
- Preference regret: oracle feasible utility minus delivered utility on feasible profiles. Abstention receives zero delivered utility and therefore retains its opportunity cost.
- Terminal constraint-aware loss and question cost: report together and separately, with the objective version.

Include numerators and denominators. Group uncertainty calculations by base profile. For ratios with a policy-dependent denominator, resample profile clusters and recompute the ratio within each bootstrap sample; do not treat two variants as two independent people. Mark unavailable quantities and empty strata explicitly.

Show risk and coverage together. A policy that declines everything cannot pass by showing zero violations. Compare paired profile outcomes and intervals, not isolated rounded percentages. Report the small audit's sample size next to its estimates. Even zero failures in 40 independent vectors would give a one-sided 95% binomial upper error bound of about 7.22%, before accounting for conditional issuance. The two answer variants do not create 80 independent vectors. This audit cannot certify a population error rate below 5% merely because a point estimate is small.

## Engineering targets and failure handling

The approved targets describe desired point estimates, not statistical guarantees: raw diagnostic violations <=5%; guarded recommendation risk <=5%; feasible coverage >=80%; no-feasible detection >=95%; false no-feasible <=5%. Report results against each target, including misses. Do not change the target, hide unknown cases or increase the question budget after examining the audit.

Check clean and uncertain variants, deliberately wrong answers, unobserved hard limits, skipped constraints, exhausted budget, early STOP and revised answers. Report sensitivity to bad supplied facts rather than pretending that the guard knows the hidden truth. An exhausted question budget can end in `needs_confirmation`.

## Evidence boundaries

Unit tests establish implementation behavior. Frozen replay establishes reproducibility on the stated data. A finite-domain audit establishes behavior within that simulator. None establishes human usefulness, realistic project completion time, broad language understanding or superiority to a chat assistant. No study on real people is required for this approved scope.

Sources: [scikit-learn on evaluation and grouped observations](https://scikit-learn.org/stable/modules/cross_validation.html), [data-leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html), [PEPPER evaluation protocol](https://aclanthology.org/2025.findings-emnlp.1067/). [Conformal Risk Control](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html) requires explicit assumptions for formal risk control; IntentProbe v2 reports empirical risk and makes no conformal guarantee.
