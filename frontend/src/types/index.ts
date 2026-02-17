export interface Plan {
  session_id: string;
  status: string;
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
  status: string;
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
