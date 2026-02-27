import { fetchJson } from './client';
import type {
  CreateSessionResponse,
  ModelsResponse,
  Plan,
  ProposalComparison,
  ProposalsResponse,
  ScenariosResponse,
  SessionHistoryQuery,
  SessionsListResponse,
} from '../types';

export const planApi = {
  createSession(userIntent: string, scenarioName?: string) {
    return fetchJson<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        user_intent: userIntent,
        scenario_name: scenarioName,
      }),
    });
  },

  getSession(sessionId: string) {
    return fetchJson<Plan>(`/sessions/${sessionId}`);
  },

  answerQuestions(sessionId: string, answers: Record<string, string>) {
    return fetchJson<Record<string, unknown>>(`/sessions/${sessionId}/questions`, {
      method: 'POST',
      body: JSON.stringify(answers),
    });
  },

  async getProposals(sessionId: string) {
    const result = await fetchJson<ProposalsResponse>(`/sessions/${sessionId}/proposals`);
    return result.proposals;
  },

  selectProposal(sessionId: string, proposalId: string) {
    return fetchJson<Record<string, unknown>>(
      `/sessions/${sessionId}/proposals/${proposalId}/select`,
      { method: 'POST' },
    );
  },

  approvePlan(sessionId: string) {
    return fetchJson<Record<string, unknown>>(`/sessions/${sessionId}/approve`, {
      method: 'POST',
    });
  },

  executePlan(sessionId: string, context?: Record<string, unknown>) {
    return fetchJson<Record<string, unknown>>(`/sessions/${sessionId}/execute`, {
      method: 'POST',
      body: JSON.stringify(context ?? {}),
    });
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
    return fetchJson<SessionsListResponse>(`/sessions${suffix ? `?${suffix}` : ''}`);
  },

  compareProposals(sessionId: string, proposalIds: string[]) {
    return fetchJson<ProposalComparison>(`/sessions/${sessionId}/compare-proposals`, {
      method: 'POST',
      body: JSON.stringify({ proposal_ids: proposalIds }),
    });
  },
};
