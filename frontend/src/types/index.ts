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
