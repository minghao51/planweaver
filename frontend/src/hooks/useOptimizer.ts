import { useCallback, useMemo, useState } from 'react';
import { planApi } from '../api/planApi';
import type {
  OptimizedVariant,
  RatedPlan,
  VariantType,
  OptimizationStatus,
  OptimizerStageData,
  ManualPlanRequest,
} from '../types';

type OptimizerActionName =
  | 'optimize'
  | 'getResults'
  | 'ratePlans'
  | 'saveUserRating'
  | 'getState'
  | 'submitManualPlan'
  | 'normalizePlan'
  | 'evaluatePlans'
  | 'comparePlans';

type LoadingState = Partial<Record<OptimizerActionName, boolean>>;

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object' && 'detail' in error) {
    return String(error.detail);
  }
  return 'An unexpected error occurred. Please try again.';
};

export function useOptimizer() {
  const [loadingByAction, setLoadingByAction] = useState<LoadingState>({});
  const [error, setError] = useState<string | null>(null);

  const runAction = useCallback(
    async <T>(
      action: OptimizerActionName,
      request: () => Promise<T>
    ): Promise<T> => {
      setLoadingByAction((prev) => ({ ...prev, [action]: true }));
      setError(null);
      try {
        return await request();
      } catch (e) {
        const message = getErrorMessage(e);
        setError(message);
        throw e;
      } finally {
        setLoadingByAction((prev) => ({ ...prev, [action]: false }));
      }
    },
    []
  );

  const optimizePlan = useCallback(
    (
      sessionId: string,
      candidateId: string,
      optimizationTypes?: VariantType[],
      userContext?: string
    ) =>
      runAction('optimize', () =>
        planApi.optimizePlan(
          sessionId,
          candidateId,
          optimizationTypes || ['simplified', 'enhanced'],
          userContext
        )
      ),
    [runAction]
  );

  const getOptimizationResults = useCallback(
    (sessionId: string) =>
      runAction('getResults', () => planApi.getOptimizationResults(sessionId)),
    [runAction]
  );

  const ratePlans = useCallback(
    (planIds: string[], models?: string[], criteria?: string[]) =>
      runAction('ratePlans', () =>
        planApi.ratePlans(planIds, models, criteria)
      ),
    [runAction]
  );

  const saveUserRating = useCallback(
    (planId: string, rating: number, comment?: string, rationale?: string) =>
      runAction('saveUserRating', () =>
        planApi.saveUserRating(planId, rating, comment, rationale)
      ),
    [runAction]
  );

  const getOptimizationState = useCallback(
    (sessionId: string) =>
      runAction('getState', () => planApi.getOptimizationState(sessionId)),
    [runAction]
  );

  const submitManualPlan = useCallback(
    (payload: ManualPlanRequest) =>
      runAction('submitManualPlan', () => planApi.submitManualPlan(payload)),
    [runAction]
  );

  const normalizePlan = useCallback(
    (
      plan: Record<string, unknown>,
      options?: {
        sessionId?: string;
        sourceType?: 'llm_generated' | 'manual' | 'optimized_variant';
        sourceModel?: string;
        planningStyle?: string;
        persist?: boolean;
      }
    ) =>
      runAction('normalizePlan', () =>
        planApi.normalizePlan({
          session_id: options?.sessionId,
          plan,
          source_type: options?.sourceType,
          source_model: options?.sourceModel,
          planning_style: options?.planningStyle,
          persist: options?.persist ?? true,
        })
      ),
    [runAction]
  );

  const evaluatePlans = useCallback(
    (
      plans: Record<string, unknown>[],
      sessionId?: string,
      judgeModels?: string[]
    ) =>
      runAction('evaluatePlans', () =>
        planApi.evaluatePlans(plans, sessionId, judgeModels)
      ),
    [runAction]
  );

  const comparePlans = useCallback(
    (
      plans: Record<string, unknown>[],
      sessionId?: string,
      judgeModels?: string[]
    ) =>
      runAction('comparePlans', () =>
        planApi.comparePlans(plans, sessionId, judgeModels)
      ),
    [runAction]
  );

  const loading = useMemo(
    () => Object.values(loadingByAction).some(Boolean),
    [loadingByAction]
  );

  const isLoading = useCallback(
    (action: OptimizerActionName) => Boolean(loadingByAction[action]),
    [loadingByAction]
  );

  return {
    loading,
    loadingByAction,
    isLoading,
    error,
    optimizePlan,
    getOptimizationResults,
    ratePlans,
    saveUserRating,
    getOptimizationState,
    submitManualPlan,
    normalizePlan,
    evaluatePlans,
    comparePlans,
  };
}

export function useOptimizerStage(
  sessionId: string,
  selectedProposalId: string
): OptimizerStageData & {
  setSelectedPlanId: (planId: string | null) => void;
  setStatus: (status: OptimizationStatus) => void;
  setVariants: (variants: OptimizedVariant[]) => void;
  setRatings: (ratings: Record<string, RatedPlan>) => void;
} {
  const [variants, setVariants] = useState<OptimizedVariant[]>([]);
  const [ratings, setRatings] = useState<Record<string, RatedPlan>>({});
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [status, setStatus] = useState<OptimizationStatus>('idle');

  return {
    sessionId,
    selectedProposalId,
    variants,
    ratings,
    selectedPlanId,
    status,
    setSelectedPlanId,
    setStatus,
    setVariants,
    setRatings,
  };
}
