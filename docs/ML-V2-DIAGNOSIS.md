# Diagnosis before changing the ML objective

Date: 2026-10-22. An independent Statistician replayed the saved v1 policy at budget three without changing the model or data. These observations motivated v2. They are diagnostic evidence, not an independent final test for v2.

## The 22.5% denominator

The 120 hidden preference vectors have two response variants each, giving 240 rollouts. V1 issued 54 recommendations that violated hidden hard constraints: 54/240 = 22.5%. Variants of the same profile are dependent; uncertainty estimates must group them by base profile.

| Breakdown | Result |
|---|---:|
| Violations concerning time | 54/54 |
| Violations where time was never asked | 54/54 |
| Violations among no-feasible cases | 48/50 |
| Violations among feasible cases | 6/190 |
| Clean response variants | 27/120 |
| Uncertain response variants | 27/120 |
| Violations after early STOP | 40/54 |
| Violations after spending the budget | 14/54 |
| Sessions that asked time | 12/240 |

All rollouts initially asked domain. Time receives little value under the existing utility objective; adding trees alone does not repair that objective.

## Source mechanism

`domain.py::utility` multiplies utility by feasibility. For a profile with no feasible project, all item utilities are zero. `simulator.py::training_examples` rewards only the realized utility improvement after one answer, minus 0.006. Discovering that no project is possible therefore fails to improve this label. `Engine.choose` stops when the largest predicted gain is nonpositive. The current fixed catalog treats one weekend as insufficient for any brief by construction.

V2 will explicitly penalize invalid recommendations and false no-feasible statements. A separate outcome distinguishes insufficient evidence from an actual catalog conflict. The guard will use observed facts and admissible completions, without reading the hidden evaluation profile.

## Preservation record

The following SHA-256 values describe the v1 files before implementation. The v2 worker also records a complete v1 artifact manifest.

| File | SHA-256 |
|---|---|
| artifacts/question_value.joblib | d1f76dcadd0b20c5f60406c50afd950c5ae1638a3c52cf7bce98b78d3275afa3 |
| artifacts/evaluation_profiles.json | 930cfc6a18db5d7b575f6ff714a85f8cea11002af4cb68eb4a6dbe50c953b1b9 |
| artifacts/metadata.json | b98268c9a9ac330a326b8d7142b7cf61cee1a20f901793c9c19a6286d7996f64 |
| artifacts/benchmark.json | 00090f15e102351e31c2b5105943b22552316e9b7547592d95d67ef48113ac33 |

## Scope limits

The user approved synthetic ML improvement and then excluded human participants. No participant data or substitute LLM-generated 'human' judgments will be collected. The authored project durations and skill requirements remain estimates. A lower synthetic error rate does not establish that a person can complete the recommended project or will prefer it.

The current finite space has only 540 full vectors. Forty unused vectors can support a small audit inside that space. They cannot establish performance outside it. A new seed over the same vectors does not solve this limitation.

See the [simulation protocol](SIMULATION-PROTOCOL-V2.md) for the fixed objective, targets and evaluation process. Local agent-execution plans are excluded from the published source package.
