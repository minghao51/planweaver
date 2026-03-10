import { useCallback, useMemo, useState } from 'react';
import { planApi } from '../api/planApi';
import { RateLimitError } from '../api/client';
import type { SessionHistoryQuery } from '../types';

type ActionName =
  | 'createSession'
  | 'getSession'
  | 'answerQuestions'
  | 'getProposals'
  | 'compareProposals'
  | 'selectProposal'
  | 'approvePlan'
  | 'executePlan'
  | 'listScenarios'
  | 'listModels'
  | 'listSessions';

type LoadingState = Partial<Record<ActionName, boolean>>;

export type ApiError = {
  message: string;
  isRateLimit: boolean;
  retryAfter: number;
};

const getErrorMessage = (error: unknown): ApiError => {
  if (error instanceof RateLimitError) {
    return {
      message: error.message,
      isRateLimit: true,
      retryAfter: error.retryAfter,
    };
  }
  if (error instanceof Error) return { message: error.message, isRateLimit: false, retryAfter: 0 };
  if (typeof error === 'string') return { message: error, isRateLimit: false, retryAfter: 0 };
  if (error && typeof error === 'object' && 'detail' in error) {
    return { message: String(error.detail), isRateLimit: false, retryAfter: 0 };
  }
  return { message: 'An unexpected error occurred. Please try again.', isRateLimit: false, retryAfter: 0 };
};

export function usePlanApi() {
  const [loadingByAction, setLoadingByAction] = useState<LoadingState>({});
  const [error, setError] = useState<ApiError | null>(null);

  const runAction = useCallback(async <T,>(
    action: ActionName,
    request: () => Promise<T>,
  ): Promise<T> => {
    setLoadingByAction((prev) => ({ ...prev, [action]: true }));
    setError(null);
    try {
      return await request();
    } catch (e) {
      const errorInfo = getErrorMessage(e);
      setError(errorInfo);
      throw e;
    } finally {
      setLoadingByAction((prev) => ({ ...prev, [action]: false }));
    }
  }, []);

  const createSession = useCallback(
    (userIntent: string, scenarioName?: string, plannerModel?: string, executorModel?: string) =>
      runAction('createSession', () => planApi.createSession(userIntent, scenarioName, plannerModel, executorModel)),
    [runAction],
  );

  const getSession = useCallback(
    (sessionId: string) => runAction('getSession', () => planApi.getSession(sessionId)),
    [runAction],
  );

  const answerQuestions = useCallback(
    (sessionId: string, answers: Record<string, string>) =>
      runAction('answerQuestions', () => planApi.answerQuestions(sessionId, answers)),
    [runAction],
  );

  const getProposals = useCallback(
    (sessionId: string) => runAction('getProposals', () => planApi.getProposals(sessionId)),
    [runAction],
  );

  const compareProposals = useCallback(
    (sessionId: string, proposalIds: string[]) =>
      runAction('compareProposals', () => planApi.compareProposals(sessionId, proposalIds)),
    [runAction],
  );

  const selectProposal = useCallback(
    (sessionId: string, proposalId: string) =>
      runAction('selectProposal', () => planApi.selectProposal(sessionId, proposalId)),
    [runAction],
  );

  const approvePlan = useCallback(
    (sessionId: string) => runAction('approvePlan', () => planApi.approvePlan(sessionId)),
    [runAction],
  );

  const executePlan = useCallback(
    (sessionId: string, context?: Record<string, unknown>) =>
      runAction('executePlan', () => planApi.executePlan(sessionId, context)),
    [runAction],
  );

  const listScenarios = useCallback(
    () => runAction('listScenarios', () => planApi.listScenarios()),
    [runAction],
  );

  const listModels = useCallback(
    () => runAction('listModels', () => planApi.listModels()),
    [runAction],
  );

  const listSessions = useCallback(
    (query?: SessionHistoryQuery) => runAction('listSessions', () => planApi.listSessions(query)),
    [runAction],
  );

  const loading = useMemo(
    () => Object.values(loadingByAction).some(Boolean),
    [loadingByAction],
  );

  const isLoading = useCallback(
    (action: ActionName) => Boolean(loadingByAction[action]),
    [loadingByAction],
  );

  return {
    loading,
    loadingByAction,
    isLoading,
    error,
    createSession,
    getSession,
    answerQuestions,
    getProposals,
    compareProposals,
    selectProposal,
    approvePlan,
    executePlan,
    listScenarios,
    listModels,
    listSessions,
  };
}
