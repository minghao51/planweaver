export type PlanStatus =
  | 'BRAINSTORMING'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'EXECUTING'
  | 'COMPLETED'
  | 'FAILED';

export type ExecutionStepStatus =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'FAILED'
  | 'SKIPPED';

export type CandidatePlanStatus =
  | 'draft'
  | 'selected'
  | 'approved'
  | 'superseded';

export interface Plan {
  session_id: string;
  status: PlanStatus;
  user_intent: string;
  locked_constraints: Record<string, unknown>;
  open_questions: OpenQuestion[];
  strawman_proposals: StrawmanProposal[];
  execution_graph: ExecutionStep[];
  external_contexts: ExternalContext[];
  context_suggestions: ContextSuggestion[];
  candidate_plans: CandidatePlan[];
  candidate_revisions: CandidatePlanRevision[];
  planning_outcomes: PlanningOutcome[];
  selected_candidate_id: string | null;
  approved_candidate_id: string | null;
  final_output: Record<string, unknown> | null;
}

export interface OpenQuestion {
  id: string;
  question: string;
  answered: boolean;
  answer: string | null;
  rationale?: string | null;
  context_references: string[];
  confidence?: number | null;
}

export interface StrawmanProposal {
  id: string;
  title: string;
  description: string;
  pros: string[];
  cons: string[];
  selected: boolean;
  why_suggested?: string | null;
  context_references: string[];
  confidence?: number | null;
  planning_style: string;
  parent_candidate_id?: string | null;
}

export interface ExecutionStep {
  step_id: number;
  task: string;
  prompt_template_id: string;
  assigned_model: string;
  status: ExecutionStepStatus;
  dependencies: number[];
  output: string | null;
  error: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ExternalContext {
  id: string;
  source_type: 'github' | 'web_search' | 'file_upload';
  source_url?: string | null;
  content_summary: string;
  metadata: Record<string, unknown>;
  created_at?: string | null;
}

export interface ContextSuggestion {
  id: string;
  suggestion_type: 'github' | 'web_search' | 'file_upload';
  title: string;
  description: string;
  reason: string;
  suggested_query?: string | null;
  confidence: number;
}

export interface CandidatePlan {
  candidate_id: string;
  session_id?: string | null;
  title: string;
  summary: string;
  source_type: PlanSourceType;
  source_model: string;
  planning_style: string;
  parent_candidate_id?: string | null;
  proposal_id?: string | null;
  status: CandidatePlanStatus;
  normalized_plan_id?: string | null;
  normalized_plan?: Record<string, unknown> | null;
  execution_graph: ExecutionStep[];
  context_references: string[];
  confidence?: number | null;
  why_suggested?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CandidatePlanRevision {
  revision_id: string;
  candidate_id: string;
  session_id?: string | null;
  revision_type: string;
  title: string;
  summary: string;
  execution_graph: ExecutionStep[];
  note?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
}

export interface PlanningOutcome {
  outcome_id: string;
  session_id: string;
  candidate_id?: string | null;
  event_type: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at?: string | null;
}

export interface Scenario {
  name: string;
  description: string;
}

export interface Model {
  id: string;
  name: string;
  type: string;
  provider?: string;
  is_free?: boolean;
  pricing_info?: Record<string, unknown> | null;
  context_length?: number | null;
}

export interface CreateSessionResponse {
  session_id: string;
}

export interface ProposalsResponse {
  proposals: StrawmanProposal[];
}

export interface ScenariosResponse {
  scenarios: string[];
}

export interface ModelsResponse {
  models: Model[];
}

export interface SessionHistoryItem {
  session_id: string;
  status: PlanStatus;
  user_intent: string;
  scenario_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SessionHistoryQuery {
  limit?: number;
  offset?: number;
  status?: PlanStatus | '';
  q?: string;
}

export interface SessionsListResponse {
  sessions: SessionHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

// Comparison types
export type ComplexityScore = 'Low' | 'Medium' | 'High';
export type PlanSourceType = 'llm_generated' | 'manual' | 'optimized_variant';
export type EvaluationVerdict = 'strong' | 'acceptable' | 'weak' | 'reject';
export type DisagreementLevel = 'low' | 'medium' | 'high';
export type ComparisonMargin = 'narrow' | 'moderate' | 'clear';

export interface ProposalWithAnalysis {
  proposal_id: string;
  title: string;
  description: string;
  pros: string[];
  cons: string[];
  selected: boolean;
  why_suggested?: string | null;
  context_references: string[];
  confidence?: number | null;
  planning_style?: string;
  parent_candidate_id?: string | null;
  estimated_step_count: number;
  complexity_score: ComplexityScore;
  estimated_time_minutes: number;
  estimated_cost_usd: number;
  risk_factors: string[];
}

export interface StepSummary {
  task: string;
  complexity: ComplexityScore;
  estimated_time_minutes: number;
}

export interface ProposalDetail {
  proposal_id: string;
  full_execution_graph: ExecutionStep[];
  accurate_time_estimate: number;
  accurate_cost_estimate: number;
  all_risk_factors: string[];
  generation_error?: string;
}

export interface ProposalComparison {
  session_id: string;
  proposals: ProposalDetail[];
  common_steps: StepSummary[];
  unique_steps_by_proposal: Record<string, StepSummary[]>;
  time_comparison: Record<string, number>;
  cost_comparison: Record<string, number>;
  complexity_comparison: Record<string, ComplexityScore>;
}

export interface ComparisonRequest {
  proposal_ids: string[];
}

// ==================== Optimizer Types ====================

export type VariantType = 'simplified' | 'enhanced' | 'cost-optimized';

export type OptimizationStatus =
  | 'idle'
  | 'generating_variants'
  | 'rating'
  | 'completed'
  | 'error';

export interface OptimizedVariant {
  id: string;
  parent_candidate_id?: string;
  variant_type: VariantType;
  execution_graph: ExecutionStep[];
  metadata: VariantMetadata;
  created_at?: string | null;
}

export interface VariantMetadata {
  step_count: number;
  complexity_score: ComplexityScore;
  optimization_notes: string;
  estimated_time_minutes: number;
  estimated_cost_usd: number;
}

export interface ModelRating {
  model_name: string;
  ratings: PlanRatings;
  overall_score: number;
  reasoning: string;
}

export interface PlanRatings {
  feasibility: number;
  cost_efficiency: number;
  time_efficiency: number;
  complexity: number;
  risk_level?: number;
}

export interface PlanRatingsByModel {
  [modelName: string]: ModelRating;
}

export interface RatedPlan {
  plan_id: string;
  ratings: PlanRatingsByModel;
  average_score: number;
}

export interface OptimizerRequest {
  session_id: string;
  candidate_id: string;
  optimization_types: VariantType[];
  user_context?: string;
}

export interface OptimizerResponse {
  optimization_id: string;
  status: string;
  variants: OptimizedVariant[];
  ratings: Record<string, RatedPlan>;
  session_id: string;
}

export interface RatePlansRequest {
  plan_ids: string[];
  models?: string[];
  criteria?: string[];
}

export interface RatePlansResponse {
  rating_id: string;
  status: string;
  ratings: Record<string, RatedPlan>;
}

export interface CandidateListResponse {
  session_id: string;
  selected_candidate_id: string | null;
  approved_candidate_id: string | null;
  candidates: CandidatePlan[];
}

export interface CandidateOperationResponse {
  session_id: string;
  selected_candidate_id: string | null;
  approved_candidate_id: string | null;
  candidate: CandidatePlan;
  execution_graph: ExecutionStep[];
  status: PlanStatus;
}

export interface CandidateOutcomesResponse {
  session_id: string;
  outcomes: PlanningOutcome[];
}

export interface RefineCandidateRequest {
  operation: 'edit_step' | 'delete_step' | 'add_step' | 'regenerate_from_step';
  step_id?: number;
  task?: string;
  insert_after_step_id?: number;
  note?: string;
}

export interface BranchCandidateRequest {
  title?: string;
  note?: string;
}

export interface UserRatingRequest {
  plan_id: string;
  rating: number;
  comment?: string;
  rationale?: string;
}

export interface UserRatingResponse {
  saved: boolean;
  rating_id: string;
}

export interface OptimizationState {
  status: OptimizationStatus;
  progress: number;
  message?: string;
}

export interface NormalizedStep {
  step_id: string;
  description: string;
  dependencies: string[];
  validation: string[];
  tools: string[];
  owner_model?: string | null;
  estimated_time_minutes?: number | null;
}

export interface NormalizedPlan {
  id: string;
  session_id?: string | null;
  source_type: PlanSourceType;
  source_model: string;
  planning_style: string;
  title: string;
  summary: string;
  assumptions: string[];
  constraints: string[];
  success_criteria: string[];
  risks: string[];
  fallbacks: string[];
  estimated_time_minutes?: number | null;
  estimated_cost_usd?: number | string | null;
  steps: NormalizedStep[];
  metadata: Record<string, unknown>;
  normalization_warnings: string[];
}

export interface RubricPlanEvaluation {
  plan_id: string;
  judge_model: string;
  rubric_scores: Record<string, number>;
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  blocking_issues: string[];
  confidence: number;
  verdict: EvaluationVerdict;
}

export interface RankedPlan {
  plan_id: string;
  final_score: number;
  rank: number;
  confidence: number;
  disagreement_level: DisagreementLevel;
  recommendation_reason: string;
}

export interface PairwisePlanComparison {
  left_plan_id: string;
  right_plan_id: string;
  judge_model: string;
  winner_plan_id: string;
  margin: ComparisonMargin;
  rationale: string;
  preference_factors: string[];
}

export interface ManualPlanRequest {
  session_id?: string;
  title: string;
  summary?: string;
  plan_text?: string;
  assumptions?: string[];
  constraints?: string[];
  success_criteria?: string[];
  risks?: string[];
  fallbacks?: string[];
  steps?: NormalizedStep[];
  estimated_time_minutes?: number;
  estimated_cost_usd?: number;
  metadata?: Record<string, unknown>;
  judge_models?: string[];
}

export interface ManualPlanResponse {
  normalized_plan: NormalizedPlan;
  evaluations: Record<string, RubricPlanEvaluation>;
  ranking: RankedPlan[];
}

export interface NormalizePlanRequest {
  session_id?: string;
  plan: Record<string, unknown>;
  source_type?: PlanSourceType;
  source_model?: string;
  planning_style?: string;
  persist?: boolean;
}

export interface NormalizePlanResponse {
  normalized_plan: NormalizedPlan;
}

export interface PlanEvaluationResponse {
  normalized_plans: NormalizedPlan[];
  evaluations: Record<string, Record<string, RubricPlanEvaluation>>;
  ranking: RankedPlan[];
}

export interface PairwiseComparisonResponse {
  normalized_plans: NormalizedPlan[];
  evaluations: Record<string, Record<string, RubricPlanEvaluation>>;
  comparisons: PairwisePlanComparison[];
  ranking: RankedPlan[];
}

export interface OptimizerStageData {
  sessionId: string;
  selectedProposalId: string;
  variants: OptimizedVariant[];
  ratings: Record<string, RatedPlan>;
  selectedPlanId: string | null;
  status: OptimizationStatus;
}
