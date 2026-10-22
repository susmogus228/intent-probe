export interface Option { value: string; label: string }
export interface Question { id: string; title: string; description: string; options: Option[]; reason?: string; estimated_gain?: number }
export interface RankedProject { id: string; title: string; summary: string; fit_score: number; feasible: boolean; reasons: string[]; tags: string[]; constraint_status?: 'verified' | 'unverified' | 'conflict' }
export interface Outcome { status: 'recommendation' | 'no_feasible' | 'needs_confirmation'; reason: string; project_id: string | null; unchecked_constraints: string[]; guard_applied: boolean }
export interface Decision { action: 'ask' | 'stop'; reason: string }
export interface Answer { question_id: string; value: string | null; skipped: boolean }
export interface Session {
  id: string; revision: number; status: 'active' | 'stopped'; initial_request: string; budget: number; policy: string;
  initial_facts: Record<string, string>; answers: Answer[]; facts: Record<string, string>; ranked_projects: RankedProject[];
  next_question: Question | null; question_values: {question_id: string; title: string; estimated_gain: number}[];
  decision: Decision; outcome?: Outcome; model_version: string; questions_used: number; remaining_budget: number;
  created_at: string; updated_at: string; invalidated_answers: number;
}
export interface SessionSummary { id: string; initial_request: string; updated_at: string; status: string }
export interface Model { version: string; estimator: string; trained_at: string; training_rows: number; feature_names: string[]; artifact_sha256: string; validation_mae: number; objective?: string; training_command?: string }
export interface Dataset { kind: string; train_profiles: number; validation_profiles: number; test_profiles: number; development_profiles?: number; split_seed: number; generator_version: string; limitations: string[]; splits_disjoint: boolean }
export interface PolicyResult { id: string; label: string; mean_regret: number; ci_low: number; ci_high: number; mean_questions: number; constraint_violation_rate: number; no_feasible_detection_rate?: number | null; mean_total_loss?: number; total_loss_ci_low?: number; total_loss_ci_high?: number; mean_objective_with_cost?: number; objective_ci_low?: number; objective_ci_high?: number; recommendation_risk?: number | null; feasible_coverage?: number; false_no_feasible_rate?: number; recommendation_rate?: number }
export interface Benchmark { generated_at: string; model_version: string; scope: string; objective?: string; policies: PolicyResult[]; guarded_policies?: PolicyResult[]; curves: {policy: string; budget: number; mean_regret: number}[]; stress_tests: {name: string; description: string; results: {policy: string; mean_regret: number | null}[]}[]; notes: string[] }
export interface Metadata { questions: Question[]; catalog: RankedProject[]; model: Model; dataset: Dataset; benchmark: Benchmark; protocol: Record<string, unknown> | string }
export interface Preview { hypothetical: true; ranked_projects: RankedProject[]; decision: Decision; outcome?: Outcome }
export interface Experiment { id: string; status: 'running' | 'completed' | 'failed'; error?: string }
