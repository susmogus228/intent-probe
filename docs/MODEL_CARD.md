# IntentProbe question-value model

## Purpose and boundary

IntentProbe is an actual trained ML question-selection experiment. It is not a
general language model or a claim to infer a person's true intentions. The saved
`ExtraTreesRegressor` predicts the value of an admissible clarification question
for a fixed catalog of 20 ML-project briefs. These briefs are ideas, not claims
that 20 applications have been implemented.

The ranking engine is an explicit finite-prior utility calculation shared by
all policies. The learned component selects questions and competes with STOP.
There is no silent replacement of the model by rules: missing, mismatched or
corrupted artifacts fail with a clear error.

## Inputs, target and training

Inputs contain only current observed categorical answers, distinct unobserved
and skipped flags, a candidate question ID, remaining budget, and summaries of
the ranking under a uniform finite preference prior. `unknown` retains
uncertainty; `indifferent` neutralizes the domain or goal preference. They are
different from skipping a question. No request free text is parsed by this model.

Training labels are the realized one-answer reduction in regret under the
synthetic profile's hidden utility, minus a question cost of 0.006. Hidden
preferences, future answers, split labels, utility families and profile IDs never
enter inference features. Hidden values are used by the label generator and
evaluator only. STOP has a fixed value of zero. The model is a one-step value
regressor; remaining budget is observed, but it does not learn a multi-step
optimal controller or reinforcement learning policy.

The CPU estimator uses 80 ExtraTrees regression trees, maximum depth 15, minimum
leaf size 8, seed 42 and one worker. No hyperparameters were selected using the
test benchmark. Validation MAE is compared with a constant predictor; this
regression metric is separate from final recommendation performance.

## Measured local artifact, 2026-10-22

The seed-42 artifact fitted 7,927 question-state rows from 300 base profiles.
Validation MAE on 80 disjoint profiles was 0.14538, versus 0.17887 for a constant
training-mean predictor. The held-out test has 120 base profiles, of which 95
have at least one feasible brief. Each profile has two grouped answer variants.

At budget three, feasible-profile mean regret was 0.11697 for learned selection,
0.11776 for analytic decision value, 0.10974 for information gain and 0.54474
without clarification. The paired learned-minus-analytic regret difference was
-0.00079, with 95% interval [-0.00237, 0.00000]. Cost-adjusted difference was
-0.00019, interval [-0.00177, 0.00079]. These results do not establish an
advantage over the analytic policy or information gain.

The learned policy violated hidden constraints in 22.5% of all test cases and
detected only 4% of no-feasible cases. In comparison, information gain used more
questions but had a 0.42% violation rate and 98% no-feasible detection in this
simulator. This is a material limitation, not a production-ready recommendation
claim. Feasibility against stated constraints in the app must never be presented
as assurance about unstated requirements. These measured results are preserved;
the objective was not revised after observing them to manufacture a better test
score. A future objective rewarding infeasibility discovery would require a new
version, training protocol and evaluation.

## Reproduction and artifacts

```powershell
.venv/Scripts/python.exe -m intentprobe.ml.train --output artifacts
.venv/Scripts/python.exe -m pytest tests/test_ml_core.py -q --basetemp=work/pytest-ml
```

The training command writes the actual serialized estimator, feature schema,
environment versions, model SHA-256, split manifests, generated profile records,
training/validation arrays, frozen test records and benchmark report. Exact
current values are in `artifacts/metadata.json` and `artifacts/benchmark.json`.
`evaluate_artifact(Path("artifacts"))` repeats the frozen test without fitting or
changing the model. Training in a different library version is not guaranteed to
produce a byte-identical serialized file; use the recorded environment versions.

Only locally trained, trusted artifacts may be loaded. Joblib uses pickle and
can execute code. A companion SHA-256 detects accidental corruption but cannot
authenticate an untrusted artifact accompanied by a modified metadata file.

## Evaluation and honest claims

Six policies receive the same catalog, observed facts, budgets and ranking:
learned question value, analytic expected decision value, answer information
gain, fixed order, random valid question and no clarification. Random policy
draws and bootstrap resamples use fixed seeds. The primary metric is regret at
budget three on profiles with at least one feasible brief. Several equally
optimal recommendations are accepted. Lower regret is better. Scores and gains
are utilities, not probabilities or prediction accuracy.

No-feasible profiles are excluded from mean regret and reported separately via
no-feasible detection and hard-constraint violations. The one-step target has
zero recommendation utility for such profiles, so it does not separately reward
discovering infeasibility. This limitation is visible in the detection metric.

Report cost-adjusted total loss alongside raw regret and number of questions.
The synthetic interaction cost does not represent measured human effort. All
95% intervals and learned-minus-baseline differences are paired/grouped by base
profile, preserving both response variants; dialogue turns are not independent
samples. Model quality can be worse than a simpler policy, including the exact
analytic baseline; the report preserves those results.

The benchmark separates new in-distribution profiles, a held-out interaction
utility family, and held-out wrong-hardware answer noise. The interaction family
changes weights and adds a domain-goal interaction but often preserves the same
optimum: this is a narrow synthetic shift, not broad generalization evidence.
Unknown replies are simulated; skip, indifference and editing are functional
application tests, not measured robustness to human behavior.

## Privacy, fairness and intended use

No human participants, private datasets, demographic attributes, external
inference APIs or paid services are used. Local saved sessions are not training
data and do not automatically update the model. Performance slices by synthetic
hardware, experience and interest can reveal simulator limitations; they do not
establish demographic fairness. There is no demographic fairness claim because
the simulator contains no such attributes. Do not infer protected attributes
from request text or use this model for admissions, hiring, lending or other
decisions about people. The project is a controlled educational experiment.

## Sources and originality

Question selection and learned ASK/STOP have prior work, including
[Interactive Classification, ACL 2020](https://aclanthology.org/2020.acl-main.237/),
[Clarify When Necessary, NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.306/)
and [PEPPER, EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.1067/).
The contribution is this implementation, explicit data generator, inspectable
interaction and reproducible evaluation. No novel algorithm, superiority to an
ordinary AI chat or real-human benefit has been established.
