import { fetchJson } from './client';
import type {
  BranchCandidateRequest,
  CandidateListResponse,
  CandidateOperationResponse,
  CandidateOutcomesResponse,
  CreateSessionResponse,
  ModelsResponse,
  Plan,
  ProposalComparison,
  ProposalsResponse,
  ScenariosResponse,
  SessionHistoryQuery,
  SessionsListResponse,
  OptimizerResponse,
  RatePlansResponse,
  UserRatingResponse,
  OptimizationState,
  ManualPlanRequest,
  ManualPlanResponse,
  NormalizePlanRequest,
  NormalizePlanResponse,
  PlanEvaluationResponse,
  PairwiseComparisonResponse,
  RefineCandidateRequest,
} from '../types';

export const planApi = {
  createSession(
    userIntent: string,
    scenarioName?: string,
    plannerModel?: string,
    executorModel?: string
  ) {
    return fetchJson<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        user_intent: userIntent,
        scenario_name: scenarioName,
        planner_model: plannerModel,
        executor_model: executorModel,
      }),
    });
  },

  getSession(sessionId: string) {
    return fetchJson<Plan>(`/sessions/${sessionId}`);
  },

  answerQuestions(sessionId: string, answers: Record<string, string>) {
    return fetchJson<Record<string, unknown>>(
      `/sessions/${sessionId}/questions`,
      {
        method: 'POST',
        body: JSON.stringify({ answers }),
      }
    );
  },

  async getProposals(sessionId: string) {
    const result = await fetchJson<ProposalsResponse>(
      `/sessions/${sessionId}/proposals`
    );
    return result.proposals;
  },

  selectProposal(sessionId: string, proposalId: string) {
    return fetchJson<Record<string, unknown>>(
      `/sessions/${sessionId}/proposals/${proposalId}/select`,
      { method: 'POST' }
    );
  },

  approvePlan(sessionId: string) {
    return fetchJson<Record<string, unknown>>(
      `/sessions/${sessionId}/approve`,
      {
        method: 'POST',
      }
    );
  },

  executePlan(sessionId: string, context?: Record<string, unknown>) {
    return fetchJson<Record<string, unknown>>(
      `/sessions/${sessionId}/execute`,
      {
        method: 'POST',
        body: JSON.stringify({ context: context ?? {} }),
      }
    );
  },

  async listScenarios() {
    const result = await fetchJson<ScenariosResponse>('/scenarios');
    return result.scenarios;
  },

  async listModels() {
    const result = await fetchJson<ModelsResponse>('/models');
    return result.models;
  },

  listSessions(query: SessionHistoryQuery = {}) {
    const params = new URLSearchParams();
    if (query.limit) params.set('limit', String(query.limit));
    if (query.offset) params.set('offset', String(query.offset));
    if (query.status) params.set('status', query.status);
    if (query.q?.trim()) params.set('q', query.q.trim());

    const suffix = params.toString();
    return fetchJson<SessionsListResponse>(
      `/sessions${suffix ? `?${suffix}` : ''}`
    );
  },

  compareProposals(sessionId: string, proposalIds: string[]) {
    return fetchJson<ProposalComparison>(
      `/sessions/${sessionId}/compare-proposals`,
      {
        method: 'POST',
        body: JSON.stringify({ proposal_ids: proposalIds }),
      }
    );
  },

  listCandidates(sessionId: string) {
    return fetchJson<CandidateListResponse>(
      `/sessions/${sessionId}/candidates`
    );
  },

  refineCandidate(
    sessionId: string,
    candidateId: string,
    payload: RefineCandidateRequest
  ) {
    return fetchJson<CandidateOperationResponse>(
      `/sessions/${sessionId}/candidates/${candidateId}/refine`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  branchCandidate(
    sessionId: string,
    candidateId: string,
    payload: BranchCandidateRequest = {}
  ) {
    return fetchJson<CandidateOperationResponse>(
      `/sessions/${sessionId}/candidates/${candidateId}/branch`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  approveCandidate(sessionId: string, candidateId: string) {
    return fetchJson<CandidateOperationResponse>(
      `/sessions/${sessionId}/candidates/${candidateId}/approve`,
      {
        method: 'POST',
      }
    );
  },

  getOutcomes(sessionId: string) {
    return fetchJson<CandidateOutcomesResponse>(
      `/sessions/${sessionId}/outcomes`
    );
  },

  // ==================== Optimizer APIs ====================

  optimizePlan(
    sessionId: string,
    candidateId: string,
    optimizationTypes: string[] = ['simplified', 'enhanced'],
    userContext?: string
  ) {
    return fetchJson<OptimizerResponse>('/optimizer/optimize', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        candidate_id: candidateId,
        optimization_types: optimizationTypes,
        user_context: userContext,
      }),
    });
  },

  getOptimizationResults(sessionId: string) {
    return fetchJson<Record<string, unknown>>(
      `/optimizer/results/${sessionId}`
    );
  },

  ratePlans(planIds: string[], models?: string[], criteria?: string[]) {
    return fetchJson<RatePlansResponse>('/optimizer/rate', {
      method: 'POST',
      body: JSON.stringify({
        plan_ids: planIds,
        models: models || ['claude-3.5-sonnet', 'gpt-4o', 'deepseek-chat'],
        criteria: criteria || [
          'feasibility',
          'cost_efficiency',
          'time_efficiency',
          'complexity',
        ],
      }),
    });
  },

  saveUserRating(
    planId: string,
    rating: number,
    comment?: string,
    rationale?: string
  ) {
    return fetchJson<UserRatingResponse>('/optimizer/user-rating', {
      method: 'POST',
      body: JSON.stringify({
        plan_id: planId,
        rating,
        comment,
        rationale,
      }),
    });
  },

  getOptimizationState(sessionId: string) {
    return fetchJson<OptimizationState>(`/optimizer/state/${sessionId}`);
  },

  submitManualPlan(payload: ManualPlanRequest) {
    return fetchJson<ManualPlanResponse>('/optimizer/manual', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  normalizePlan(payload: NormalizePlanRequest) {
    return fetchJson<NormalizePlanResponse>('/optimizer/normalize', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  evaluatePlans(
    plans: Record<string, unknown>[],
    sessionId?: string,
    judgeModels?: string[]
  ) {
    return fetchJson<PlanEvaluationResponse>('/optimizer/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        plans,
        judge_models: judgeModels || [],
      }),
    });
  },

  comparePlans(
    plans: Record<string, unknown>[],
    sessionId?: string,
    judgeModels?: string[]
  ) {
    return fetchJson<PairwiseComparisonResponse>('/optimizer/compare', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        plans,
        judge_models: judgeModels || [],
      }),
    });
  },
};
