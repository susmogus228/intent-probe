# Statistical review: constraint-aware v2

Reviewer: independent Statistician, read-only. Verdict: **warn, no blocking statistical implementation defect**. The no-feasible detection goal remains unmet.

## Independent checks

Verified disjoint 300/80/120/40 base-vector memberships, the complete 540-vector union, stable content IDs, grouped response variants, data/model hashes and preservation of ten v1 files. The protocol timestamp 12:21:22 UTC precedes model 12:24:31 and report 12:24:43. Selection uses only the 80 validation profiles and the two predefined configurations.

The actual forest has 120 trees and fitted 19,439 rows with 58 observed features. The training target uses raw terminal actions before the guard. Hidden labels stay outside inference features. One guard function checks the original candidate after an unchanged shared question path for each baseline.

Replayed learned raw and guarded rollouts at budget three. Reported numbers and intervals matched within 1e-12:

| Final40-vector audit | Result |
|---|---:|
| Matched v1 raw violations |26/80 (32.5%)|
| V2 raw violations |7/80 (8.75%)|
| Guarded violations / issued |0/48|
| Guarded valid coverage |48/54 (88.89%)|
| Correct no-feasible detection |22/26 (84.62%)|
| False no-feasible |0/54|
| Guarded needs-confirmation |10/80|

## Remaining limits

The95% detection target is missed. Report final 8.75% raw violations separately from development 2.5%. The 48 guarded recommendations belong to 26 base profiles; two variants do not create independent observations. The all-zero bootstrap risk interval cannot certify a risk below 5%. Even zero errors among 40 independent Bernoulli profiles would have an illustrative one-sided95% upper bound around 7.22%; the actual conditional estimand differs and uses fewer groups.

On matched final cases, raw preference regret increases from v1 0.10370 to v2 0.15741, and guarded regret is0.20000. The new all-case objective plus cost improves from 0.40430 to 0.20808 raw and 0.14933 guarded. This is a trade-off. Changes in the target, feature count, state sampling and forest settings prevent causal attribution to the loss alone. The analytic baseline has better point estimates on the final objective; superiority is unestablished.

The incorrect-time stress demonstrates the truthful-input boundary rather than a population error rate. Unknown/skipped/zero-budget cases can correctly decline all recommendations; null risk and zero coverage do not constitute a safety win.

The final 40 vectors are now disclosed. Further changes selected from their results would make subsequent evaluation exploratory. No humans or external validation were inspected or required by this scope.
