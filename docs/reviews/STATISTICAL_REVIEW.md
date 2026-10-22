# Independent statistical review

Profile: Statistician. Read-only review and corrected-state check,2026-10-22.

Final verdict: **warn**. Both initial blocking findings were fixed; no blocking statistical implementation issue remained.

The first generator split preference/family combinations, allowing repeated answer vectors across splits. It now partitions the full five-answer vector, uses stable content-derived IDs and groups both response variants. Actual train/validation/test counts are300/80/120, with all pairwise intersections zero.

The benchmark now includes the target's synthetic cost term, `regret +0.006*questions`, grouped intervals and paired comparisons on the feasible-profile denominator. Empty groups explicitly report missing data or reject invalid estimation.

The reviewer independently checked training(7927,50) and validation(2152,50) group membership, hashes and manifests. Hidden preferences/future answers enter labels and evaluation only. All six budget-three policies replayed to1e-12 agreement; cost identities match to1e-12. Four analytic expected-value/label checks agreed to2.3e-16.

Model SHA-256: d1f76dcadd0b20c5f60406c50afd950c5ae1638a3c52cf7bce98b78d3275afa3. Benchmark/model/test hashes agree.

Residual limits: learned violations22.5%, no-feasible detection4%; cost-adjusted difference vs analytic-0.00019 with95% interval[-0.00177,0.00079]. The utility shift is narrow;120 synthetic profiles do not establish human usefulness. This review does not endorse a reliable real-world assistant.
