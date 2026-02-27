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
  | 'FAILED';

export interface Plan {
  session_id: string;
  status: PlanStatus;
  user_intent: string;
  locked_constraints: Record<string, unknown>;
  open_questions: OpenQuestion[];
  strawman_proposals: StrawmanProposal[];
  execution_graph: ExecutionStep[];
  final_output: Record<string, unknown> | null;
}

export interface OpenQuestion {
  id: string;
  question: string;
  answered: boolean;
  answer: string | null;
}

export interface StrawmanProposal {
  id: string;
  title: string;
  description: string;
  pros: string[];
  cons: string[];
  selected: boolean;
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

export interface ProposalWithAnalysis {
  proposal_id: string;
  title: string;
  description: string;
  pros: string[];
  cons: string[];
  selected: boolean;
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

export type OptimizationStatus = 'idle' | 'generating_variants' | 'rating' | 'completed' | 'error';

export interface OptimizedVariant {
  id: string;
  proposal_id: string;
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
  selected_proposal_id: string;
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

export interface OptimizerStageData {
  sessionId: string;
  selectedProposalId: string;
  variants: OptimizedVariant[];
  ratings: Record<string, RatedPlan>;
  selectedPlanId: string | null;
  status: OptimizationStatus;
}
