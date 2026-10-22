# IntentProbe: analog research and proposed contribution

Research date: 2026-10-22. This is the discovery record written before implementation and visual selection. Current implementation and test status is tracked in REQUIREMENTS.md and VERIFICATION.md. This research step did not authorize public publication.

## Conclusion

Learning which clarification to ask and when to stop is an established research problem. Cost-aware clarification, noisy or contradictory answers, and solver-checkable constraints also have direct precedents. IntentProbe should claim its own implementation, domain data, controlled evaluation and inspectable interaction design. Algorithmic novelty and improved human satisfaction are not established.

## Primary analogs

| Source | Existing capability | Consequence for IntentProbe |
|---|---|---|
| [Akinator](https://en.akinator.com/) | Interactive guessing through successive questions | A question-by-question interaction is familiar; it is not our contribution. Its internal algorithm was not inspected. |
| [Typeform Logic Jumps](https://www.typeform.com/developers/create/logic-jumps/) | Author-defined conditional routes through forms | Branching forms are a useful rule baseline, not evidence of a learned question policy. This comparison concerns the documented logic feature, not every Typeform capability. |
| [Rao and Daume, 2018](https://users.umiacs.umd.edu/~hal3/docs/daume18clarification.pdf) | Ranking clarification questions by expected usefulness | Expected value of an answer is already a research idea. |
| [Interactive Classification, ACL 2020](https://aclanthology.org/2020.acl-main.237/) | Information-gain selection and learned ASK/STOP; simulated and human evaluation | The core initial proposal is substantially covered by prior work. |
| [ClariQ](https://github.com/aliannejadi/ClariQ) | Whether and which clarification to ask; explicit no-question choice | Useful search benchmark, but not direct evidence about subjective project preferences. |
| [Microsoft MIMICS, 2020](https://github.com/microsoft/MIMICS) | Search clarification panes with candidate answers, interaction signals and manual labels | Click engagement and final decision quality are different outcomes. The repository is archived; historical data is not a supported live service. |
| [CLAMBER, ACL 2024](https://aclanthology.org/2024.acl-long.578/) | Taxonomy and evaluation of ambiguous queries and clarification quality | Ambiguity detection and fluent wording alone do not establish recommendation usefulness. |
| [Herlihy et al., UAI 2024](https://proceedings.mlr.press/v244/herlihy24a.html) | Learned response controls for recommendation under incomplete preferences | A small learned controller has precedent and can be a practical implementation route. |
| [Clarify When Necessary, NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.306/) | Evaluation of when clarification helps and interaction costs; IntentSim | Cost-sensitive clarification is not a new invention here. |
| [PEPPER, EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.1067/) | Evaluation without pre-encoding a single target item into the user simulator | Multiple recommendations can be acceptable; do not turn subjective preference elicitation into target guessing. |
| [ClarifyMT-Bench, December 2025 preprint](https://arxiv.org/abs/2512.21120) | Multi-turn clarification with diverse simulated behavior | Difficult replies and state tracking are product requirements, not novelty claims. |
| [Ask, Relax, or Act?, October 2026 preprint](https://arxiv.org/abs/2610.03102) | Solver-grounded decisions between acting, asking and permitted constraint repair | Even exact constraint-based clarification has a direct recent precedent. Treat the preprint separately from peer-reviewed conference work. |

Sources were inspected through official product documentation, author repositories and primary publication pages. This is a focused survey, not an exhaustive novelty search. No third-party code or dataset was copied; any future reuse requires a separate provenance/license check.

## Proposed product distinction

An inspectable local clarification engine and research workbench for choosing a feasible ML project from a versioned structured catalog. Users supply time, hardware, skills, interests and desired outcomes. Hard constraints remain distinct from preferences. The catalog contains candidate project briefs, not claims that all listed projects have been implemented.

For every question, show the facts already known, the expected reason to ask, the hypothetical effect of each answer, and the observed change after the actual answer. A hypothetical preview must say "If you answer...". It must not be displayed as a confirmed preference or measured result.

Users can answer, skip, say they do not know, revise previous answers, stop and inspect alternatives. Revision invalidates dependent conclusions. Conflicting hard requirements are shown explicitly and never silently relaxed. Valid stopping outcomes include sufficient decision support, exhausted budget, a user stop, and no feasible option.

Research mode replays policies on the same controlled hidden profile. Human-session counterfactual answers remain unknown unless explicitly collected: replay cannot invent what a person would have said.

## ML and evaluation

ML is a required deliverable, not an optional enhancement. IntentProbe is one of the user's ML portfolio projects. A branching questionnaire, prompt-only assistant, or pretrained API wrapper does not satisfy this brief. The application has not been built or trained yet.

The required learned component is a question-value predictor. Its input is the observed session state, a candidate question and the remaining question budget; its output estimates the reduction in recommendation regret from asking that question. STOP is an explicit competing action. Training targets come from controlled rollouts on training profiles, using hidden utility only in the training-label generator and evaluator. Hidden preferences and future answers must never enter inference features. The choice of compact estimator will be established experimentally rather than advertised as a novel algorithm.

Acceptance requires versioned training data and provenance, reproducible training, a saved model artifact, inference through the backend, leakage-safe held-out evaluation, and a report against the strong analytic policy. The interface must expose the model version and distinguish learned estimates, hypothetical previews and measured evaluation results. Real-world usefulness remains unproven until separately evaluated on real users.

Separate the text-to-facts parser from question selection. All main policy comparisons receive the same initial facts and question bank. Begin with a compact CPU-trainable value model; complex reinforcement learning is not a prerequisite. No paid model API is required for the structured core.

Compare no clarification, fixed questionnaire, random admissible question, expected information gain, analytic expected decision-value and a learned policy. Keep candidate data, information access and budget identical.

A claim of superiority to an ordinary AI conversation requires an actual comparison under the same catalog, information and interaction budget. Such a result does not exist now. An external LLM benchmark is separate from the local core and requires selecting an available model, documenting its version and prompt, and agreeing any paid service or private-data transfer before use.

Proposed primary outcome: recommendation regret after a budget of three questions, evaluated against a synthetic hidden preference utility. Several projects may tie. "No feasible project" is a separate valid outcome with its own evaluation; do not hide hard-constraint violations inside a fit score.

Secondary outcomes: quality across zero-to-five-question budgets, constraint violations, unnecessary questions, abstention and sensitivity to skipped, contradictory or changed answers. Artificial question costs are simulation weights, not measured human time or fatigue.

Keep all paraphrases, dialogues and noisy versions of one profile in a single split. Reserve different preference-function families and noise mechanisms for final tests. The evaluator alone sees hidden utility and future answers. Use paired uncertainty estimates grouped by profile. A learned policy losing to the analytic baseline is a reportable result.

A later human pilot is separate from synthetic evaluation and requires explicit agreement on recruitment and data handling. It measures participants' own preference assessments and actual burden; no participants or improvements are claimed now.

## Proposed implementation after visual approval

- Proposed project root: `D:/Projects/intent-probe/`.
- Frontend: React and TypeScript for editable answers, shortlist transitions and replay controls. Standard accessible components, restrained borders, two font families at most; selected mock becomes the visual contract.
- Backend: Python/FastAPI with explicit schemas and documented session, answer, revision, recommendation and explanation endpoints. Exact library versions and APIs will be verified before implementation.
- ML/data: scikit-learn baseline models, versioned catalog and profile generators, frozen split manifests and repeatable evaluation commands.
- Persistence: local SQLite for explicitly saved sessions; no external service or automatic cross-user training in the initial proposal.
- API approach: all ranking and policy decisions come from the backend; the frontend does not fabricate metrics. Input validation and state revision belong to the same session model.
- Limits: a bounded catalog, no universal mind-reading, no guarantee of a single correct subjective recommendation, no permanent hosting assumed.

## Visual brief

Three separate desktop web-app concepts, English content, approximately1440x1024. One primary user action: answer the currently selected useful question. Supporting surfaces: current/hypothetical shortlist and explanation/history. Research comparison is available as a secondary mode, not a wall of metrics on the main screen.

Shared illustrative session: "I want a practical ML project I can finish in four weeks." Time is known. Hardware is not yet known. Ask "What hardware can you use?" with CPU laptop, local GPU, cloud GPU, and not sure. A CPU answer can be selected provisionally; any preview remains labeled hypothetical until applied. No percentages, fake model accuracy, testimonials or invented benchmark results.

Directions: a calm light decision workspace; a dark connected intent map; a restrained research workbench with a simple user mode and an inspectable explanation drawer. All concepts must be feasible with ordinary web components. No application build starts before user selection.

## Review evidence

A separate Trend Researcher checked newer direct analogs and rejected novelty claims for already published mechanisms. A Statistician checked simulator leakage, subjective ground truth, baselines, splits, stopping outcomes and misleading UI metrics. Their recommendations are incorporated above. Neither review proves future implementation or model quality.
