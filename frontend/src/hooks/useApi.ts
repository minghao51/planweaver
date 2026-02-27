import { useCallback, useMemo, useState } from 'react';
import { planApi } from '../api/planApi';
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

export function usePlanApi() {
  const [loadingByAction, setLoadingByAction] = useState<LoadingState>({});
  const [error, setError] = useState<string | null>(null);

  const runAction = useCallback(async <T,>(
    action: ActionName,
    request: () => Promise<T>,
  ): Promise<T> => {
    setLoadingByAction((prev) => ({ ...prev, [action]: true }));
    setError(null);
    try {
      return await request();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setLoadingByAction((prev) => ({ ...prev, [action]: false }));
    }
  }, []);

  const createSession = useCallback(
    (userIntent: string, scenarioName?: string) =>
      runAction('createSession', () => planApi.createSession(userIntent, scenarioName)),
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
