import { useState, useCallback } from 'react';
import { Plan } from '../types';

const API_BASE = '/api/v1';

async function fetchJson(url: string, options?: RequestInit) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export function usePlanApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = useCallback(async (userIntent: string, scenarioName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions`, {
        method: 'POST',
        body: JSON.stringify({ user_intent: userIntent, scenario_name: scenarioName }),
      });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}`);
      return result as Plan;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const answerQuestions = useCallback(async (sessionId: string, answers: Record<string, string>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}/questions`, {
        method: 'POST',
        body: JSON.stringify(answers),
      });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const getProposals = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}/proposals`);
      return result.proposals;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const selectProposal = useCallback(async (sessionId: string, proposalId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}/proposals/${proposalId}/select`, {
        method: 'POST',
      });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const approvePlan = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}/approve`, {
        method: 'POST',
      });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const executePlan = useCallback(async (sessionId: string, context?: Record<string, unknown>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson(`${API_BASE}/sessions/${sessionId}/execute`, {
        method: 'POST',
        body: JSON.stringify(context || {}),
      });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const listScenarios = useCallback(async () => {
    try {
      const result = await fetchJson(`${API_BASE}/scenarios`);
      return result.scenarios as string[];
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    }
  }, []);

  const listModels = useCallback(async () => {
    try {
      const result = await fetchJson(`${API_BASE}/models`);
      return result.models;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    }
  }, []);

  return {
    loading,
    error,
    createSession,
    getSession,
    answerQuestions,
    getProposals,
    selectProposal,
    approvePlan,
    executePlan,
    listScenarios,
    listModels,
  };
}
