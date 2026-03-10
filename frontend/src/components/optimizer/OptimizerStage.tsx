import { useEffect, useMemo, useState } from 'react';
import {
  ChevronRight,
  FlaskConical,
  GitCompareArrows,
  LayoutPanelTop,
  Loader2,
  PencilRuler,
  Sparkles,
  Star,
} from 'lucide-react';
import { useOptimizer, useOptimizerStage } from '../../hooks/useOptimizer';
import { useToast } from '../../hooks/useToast';
import { PlanCard } from './PlanCard';
import { ComparisonPanel } from './ComparisonPanel';
import { cn } from '../../utils';
import type {
  NormalizedPlan,
  PairwiseComparisonResponse,
  PlanEvaluationResponse,
  RankedPlan,
  RubricPlanEvaluation,
  VariantType,
} from '../../types';

interface OptimizerStageProps {
  sessionId: string;
  selectedProposalId: string;
  selectedProposalTitle: string;
  selectedProposalDescription: string;
  onComplete: (selectedPlanId: string) => void;
  onBack: () => void;
}

type WorkbenchTab = 'variants' | 'manual' | 'evaluate' | 'compare';

interface CandidatePlan {
  id: string;
  title: string;
  description: string;
  sourceType: 'llm_generated' | 'manual' | 'optimized_variant';
  sourceModel: string;
  planningStyle: string;
  variantType?: string;
  metadata?: {
    step_count: number;
    complexity_score: string;
    estimated_time_minutes: number;
    estimated_cost_usd: number;
    optimization_notes?: string;
  };
  payload: Record<string, unknown>;
}

const WORKBENCH_TABS: Array<{
  id: WorkbenchTab;
  label: string;
  icon: typeof Sparkles;
  description: string;
}> = [
  { id: 'variants', label: 'Variants', icon: Sparkles, description: 'Generate and inspect optimized candidates.' },
  { id: 'manual', label: 'Manual Plan', icon: PencilRuler, description: 'Submit a human-written plan into the same pipeline.' },
  { id: 'evaluate', label: 'Evaluate', icon: FlaskConical, description: 'Run rubric-based scoring across current candidates.' },
  { id: 'compare', label: 'Compare', icon: GitCompareArrows, description: 'Rank candidates with pairwise comparison.' },
];

export function OptimizerStage({
  sessionId,
  selectedProposalId,
  selectedProposalTitle,
  selectedProposalDescription,
  onComplete,
  onBack,
}: OptimizerStageProps) {
  const {
    optimizePlan,
    saveUserRating,
    submitManualPlan,
    evaluatePlans,
    comparePlans,
    isLoading,
  } = useOptimizer();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [optimizationTypes] = useState<VariantType[]>(['simplified', 'enhanced', 'cost-optimized']);
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('variants');
  const [userRating, setUserRating] = useState<number>(0);
  const [userComment, setUserComment] = useState<string>('');
  const [manualTitle, setManualTitle] = useState<string>('Manual baseline');
  const [manualSummary, setManualSummary] = useState<string>('');
  const [manualPlanText, setManualPlanText] = useState<string>('');
  const [manualSuccessCriteria, setManualSuccessCriteria] = useState<string>('');
  const [manualRisks, setManualRisks] = useState<string>('');
  const [manualResult, setManualResult] = useState<NormalizedPlan | null>(null);
  const [evaluationResult, setEvaluationResult] = useState<PlanEvaluationResponse | null>(null);
  const [comparisonResult, setComparisonResult] = useState<PairwiseComparisonResponse | null>(null);
  const [candidatePlans, setCandidatePlans] = useState<CandidatePlan[]>([
    {
      id: selectedProposalId,
      title: selectedProposalTitle,
      description: selectedProposalDescription,
      sourceType: 'llm_generated',
      sourceModel: 'selected-proposal',
      planningStyle: 'baseline',
      metadata: {
        step_count: 0,
        complexity_score: 'Medium',
        estimated_time_minutes: 0,
        estimated_cost_usd: 0,
      },
      payload: {
        id: selectedProposalId,
        title: selectedProposalTitle,
        description: selectedProposalDescription,
        source_model: 'selected-proposal',
        planning_style: 'baseline',
      },
    },
  ]);

  const {
    variants,
    ratings,
    selectedPlanId: internalSelectedPlanId,
    status,
    setSelectedPlanId,
    setVariants,
    setRatings,
    setStatus,
  } = useOptimizerStage(sessionId, selectedProposalId);

  useEffect(() => {
    async function runOptimization() {
      try {
        setStatus('generating_variants');
        const result = await optimizePlan(selectedProposalId, optimizationTypes);

        if (result.variants) {
          setVariants(result.variants);
          setCandidatePlans((current) => {
            const base = current.filter((plan) => plan.sourceType !== 'optimized_variant');
            const variantCandidates = result.variants.map((variant) => ({
              id: variant.id,
              title: `${variant.variant_type} Variant`,
              description:
                variant.metadata.optimization_notes ||
                `AI-optimized ${variant.variant_type} version`,
              sourceType: 'optimized_variant' as const,
              sourceModel: 'variant-generator',
              planningStyle: variant.variant_type,
              variantType: variant.variant_type,
              metadata: variant.metadata,
              payload: {
                id: variant.id,
                title: `${variant.variant_type} Variant`,
                description:
                  variant.metadata.optimization_notes ||
                  `AI-optimized ${variant.variant_type} version`,
                execution_graph: variant.execution_graph,
                metadata: variant.metadata,
                source_model: 'variant-generator',
                planning_style: variant.variant_type,
              },
            }));
            return [...base, ...variantCandidates];
          });
        }

        if (result.ratings) {
          setRatings(result.ratings);
        }

        setStatus('completed');
        showSuccess('Optimization complete. Review the workbench tabs.');
      } catch (error) {
        console.error('Optimization failed:', error);
        setStatus('error');
        showError('Failed to generate optimized variants. Please try again.');
      }
    }

    runOptimization();
  }, [selectedProposalId, optimizationTypes, optimizePlan, setRatings, setStatus, setVariants, showError, showSuccess]);

  const plans = useMemo(() => {
    return [
      {
        id: selectedProposalId,
        title: 'Original Proposal',
        description: selectedProposalDescription,
        metadata: {
          step_count: 0,
          complexity_score: 'Medium' as const,
          estimated_time_minutes: 0,
          estimated_cost_usd: 0,
        },
        ratings: ratings[selectedProposalId]?.ratings || {},
        averageScore: ratings[selectedProposalId]?.average_score,
      },
      ...variants.map((variant) => ({
        id: variant.id,
        title: `${variant.variant_type} Variant`,
        description:
          variant.metadata.optimization_notes ||
          `AI-optimized ${variant.variant_type} version`,
        variantType: variant.variant_type,
        metadata: variant.metadata,
        ratings: ratings[variant.id]?.ratings || {},
        averageScore: ratings[variant.id]?.average_score,
      })),
      ...candidatePlans
        .filter((plan) => plan.sourceType === 'manual')
        .map((plan) => ({
          id: plan.id,
          title: plan.title,
          description: plan.description,
          variantType: 'manual',
          metadata: plan.metadata || {
            step_count: 0,
            complexity_score: 'Medium',
            estimated_time_minutes: 0,
            estimated_cost_usd: 0,
          },
          ratings: {},
          averageScore:
            evaluationResult?.ranking.find((item) => item.plan_id === plan.id)?.final_score ||
            comparisonResult?.ranking.find((item) => item.plan_id === plan.id)?.final_score,
        })),
    ];
  }, [candidatePlans, comparisonResult, evaluationResult, ratings, selectedProposalDescription, selectedProposalId, variants]);

  const handleSelectPlan = (planId: string) => {
    setSelectedPlanId(planId);
  };

  const handleComplete = async () => {
    if (!internalSelectedPlanId) {
      showError('Please select a plan to continue');
      return;
    }

    if (userRating > 0) {
      try {
        await saveUserRating(internalSelectedPlanId, userRating, userComment);
        showSuccess('Thank you for your feedback.');
      } catch (error) {
        console.error('Failed to save rating:', error);
      }
    }

    onComplete(internalSelectedPlanId);
  };

  const handleManualSubmit = async () => {
    if (!manualTitle.trim() || !manualPlanText.trim()) {
      showError('Add a title and a manual plan before submitting.');
      return;
    }

    try {
      const result = await submitManualPlan({
        session_id: sessionId,
        title: manualTitle.trim(),
        summary: manualSummary.trim(),
        plan_text: manualPlanText.trim(),
        success_criteria: toList(manualSuccessCriteria),
        risks: toList(manualRisks),
      });
      setManualResult(result.normalized_plan);
      setCandidatePlans((current) => {
        const next = current.filter((plan) => plan.id !== result.normalized_plan.id);
        return [
          ...next,
          {
            id: result.normalized_plan.id,
            title: result.normalized_plan.title,
            description: result.normalized_plan.summary,
            sourceType: 'manual',
            sourceModel: 'human',
            planningStyle: 'manual',
            variantType: 'manual',
            metadata: {
              step_count: result.normalized_plan.steps.length,
              complexity_score: result.normalized_plan.steps.length > 4 ? 'High' : 'Medium',
              estimated_time_minutes: result.normalized_plan.estimated_time_minutes || 0,
              estimated_cost_usd: Number(result.normalized_plan.estimated_cost_usd || 0),
            },
            payload: {
              id: result.normalized_plan.id,
              title: result.normalized_plan.title,
              summary: result.normalized_plan.summary,
              success_criteria: result.normalized_plan.success_criteria,
              risks: result.normalized_plan.risks,
              fallbacks: result.normalized_plan.fallbacks,
              steps: result.normalized_plan.steps,
              source_model: 'human',
              planning_style: 'manual',
            },
          },
        ];
      });
      showSuccess('Manual plan added to the candidate pool.');
      setActiveTab('evaluate');
    } catch (error) {
      console.error('Failed to submit manual plan:', error);
      showError('Failed to process the manual plan.');
    }
  };

  const handleEvaluate = async () => {
    if (candidatePlans.length === 0) {
      showInfo('No candidate plans available yet.');
      return;
    }

    try {
      const result = await evaluatePlans(
        candidatePlans.map((plan) => plan.payload),
        sessionId
      );
      setEvaluationResult(result);
      showSuccess('Evaluation complete.');
    } catch (error) {
      console.error('Evaluation failed:', error);
      showError('Failed to evaluate plans.');
    }
  };

  const handleCompare = async () => {
    if (candidatePlans.length < 2) {
      showInfo('Add at least two candidate plans before comparing.');
      return;
    }

    try {
      const result = await comparePlans(
        candidatePlans.map((plan) => plan.payload),
        sessionId
      );
      setComparisonResult(result);
      if (!internalSelectedPlanId && result.ranking[0]) {
        setSelectedPlanId(result.ranking[0].plan_id);
      }
      showSuccess('Comparison complete.');
    } catch (error) {
      console.error('Comparison failed:', error);
      showError('Failed to compare plans.');
    }
  };

  const isOptimizing = status === 'generating_variants' || isLoading('optimize');
  const hasSelection = internalSelectedPlanId !== null;

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-6 duration-700">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-white">
            <LayoutPanelTop size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Planning Workbench</h2>
            <p className="text-text-muted font-medium">
              Variants, manual baselines, rubric evaluation, and pairwise comparison
            </p>
          </div>
        </div>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-text-muted font-bold text-sm transition-all duration-300"
        >
          Back
        </button>
      </div>

      <div className="grid gap-3 rounded-2xl border border-white/5 bg-surface p-3 md:grid-cols-4">
        {WORKBENCH_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'rounded-xl border px-4 py-4 text-left transition-all duration-300',
                activeTab === tab.id
                  ? 'border-primary/40 bg-primary/10 text-white'
                  : 'border-white/5 bg-white/5 text-text-muted hover:bg-white/10'
              )}
            >
              <div className="mb-2 flex items-center gap-2 font-bold">
                <Icon size={16} />
                {tab.label}
              </div>
              <p className="text-xs leading-relaxed opacity-80">{tab.description}</p>
            </button>
          );
        })}
      </div>

      {isOptimizing && (
        <div className="flex flex-col items-center justify-center py-16 rounded-2xl bg-surface border border-white/5">
          <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">Generating Optimized Variants</h3>
          <p className="text-text-muted text-sm">
            AI is synthesizing alternative plan structures from the selected proposal.
          </p>
        </div>
      )}

      {!isOptimizing && status !== 'error' && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr,0.9fr]">
          <div className="space-y-6">
            {activeTab === 'variants' && (
              <>
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-white">Variant Candidates</h3>
                  <div className="space-y-4">
                    {plans.map((plan) => (
                      <PlanCard
                        key={plan.id}
                        id={plan.id}
                        title={plan.title}
                        description={plan.description}
                        variantType={plan.variantType}
                        executionGraphLength={plan.metadata.step_count}
                        metadata={plan.metadata}
                        ratings={plan.ratings}
                        averageScore={plan.averageScore}
                        selected={internalSelectedPlanId === plan.id}
                        onSelect={() => handleSelectPlan(plan.id)}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeTab === 'manual' && (
              <div className="rounded-2xl border border-white/5 bg-surface p-6 space-y-5">
                <div>
                  <h3 className="text-lg font-bold text-white">Manual Baseline Plan</h3>
                  <p className="text-sm text-text-muted">
                    Add a human-written plan and send it through the same normalization and judging pipeline.
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-semibold text-text-muted">Title</span>
                    <input
                      value={manualTitle}
                      onChange={(event) => setManualTitle(event.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-primary/40"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-sm font-semibold text-text-muted">Summary</span>
                    <input
                      value={manualSummary}
                      onChange={(event) => setManualSummary(event.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-primary/40"
                      placeholder="Optional short summary"
                    />
                  </label>
                </div>
                <label className="space-y-2 block">
                  <span className="text-sm font-semibold text-text-muted">Plan Steps</span>
                  <textarea
                    value={manualPlanText}
                    onChange={(event) => setManualPlanText(event.target.value)}
                    className="min-h-[180px] w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-primary/40"
                    placeholder={'One step per line\nAudit the current implementation\nDefine the migration path\nValidate the rollout'}
                  />
                </label>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-semibold text-text-muted">Success Criteria</span>
                    <textarea
                      value={manualSuccessCriteria}
                      onChange={(event) => setManualSuccessCriteria(event.target.value)}
                      className="min-h-[96px] w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-primary/40"
                      placeholder="Comma or line-separated criteria"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-sm font-semibold text-text-muted">Known Risks</span>
                    <textarea
                      value={manualRisks}
                      onChange={(event) => setManualRisks(event.target.value)}
                      className="min-h-[96px] w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none focus:border-primary/40"
                      placeholder="Comma or line-separated risks"
                    />
                  </label>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <p className="text-xs text-text-muted">
                    Manual plans are normalized before evaluation, so missing structure will show up as warnings.
                  </p>
                  <button
                    onClick={handleManualSubmit}
                    disabled={isLoading('submitManualPlan')}
                    className="rounded-xl bg-gradient-to-r from-primary to-purple-600 px-5 py-3 text-sm font-bold text-white transition-all hover:shadow-lg hover:shadow-primary/20 disabled:opacity-60"
                  >
                    {isLoading('submitManualPlan') ? 'Submitting...' : 'Add Manual Plan'}
                  </button>
                </div>

                {manualResult && (
                  <div className="rounded-2xl border border-white/5 bg-white/5 p-5 space-y-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <h4 className="font-bold text-white">{manualResult.title}</h4>
                        <p className="text-sm text-text-muted">{manualResult.summary}</p>
                      </div>
                      <div className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-primary">
                        normalized
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <MetricPill label="Steps" value={String(manualResult.steps.length)} />
                      <MetricPill label="Warnings" value={String(manualResult.normalization_warnings.length)} />
                      <MetricPill label="Success Criteria" value={String(manualResult.success_criteria.length)} />
                    </div>
                    {manualResult.normalization_warnings.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-bold uppercase tracking-wider text-warning">Normalization warnings</p>
                        <ul className="space-y-2 text-sm text-text-muted">
                          {manualResult.normalization_warnings.map((warning) => (
                            <li key={warning} className="rounded-lg border border-warning/20 bg-warning/10 px-3 py-2">
                              {warning}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'evaluate' && (
              <div className="rounded-2xl border border-white/5 bg-surface p-6 space-y-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">Rubric Evaluation</h3>
                    <p className="text-sm text-text-muted">
                      Score every current candidate across completeness, feasibility, dependency quality, verification, and readiness.
                    </p>
                  </div>
                  <button
                    onClick={handleEvaluate}
                    disabled={isLoading('evaluatePlans')}
                    className="rounded-xl bg-gradient-to-r from-primary to-purple-600 px-5 py-3 text-sm font-bold text-white transition-all hover:shadow-lg hover:shadow-primary/20 disabled:opacity-60"
                  >
                    {isLoading('evaluatePlans') ? 'Evaluating...' : 'Evaluate Candidates'}
                  </button>
                </div>

                {evaluationResult ? (
                  <div className="space-y-5">
                    <RankingList
                      title="Evaluation Ranking"
                      ranking={evaluationResult.ranking}
                      onSelect={handleSelectPlan}
                      selectedPlanId={internalSelectedPlanId}
                    />
                    <RubricGrid
                      evaluations={evaluationResult.evaluations}
                      plans={evaluationResult.normalized_plans}
                    />
                  </div>
                ) : (
                  <EmptyState text="Run evaluation to populate rubric scores for the current candidate set." />
                )}
              </div>
            )}

            {activeTab === 'compare' && (
              <div className="rounded-2xl border border-white/5 bg-surface p-6 space-y-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">Pairwise Comparison</h3>
                    <p className="text-sm text-text-muted">
                      Compare the current candidate pool and surface a ranked recommendation with rationale.
                    </p>
                  </div>
                  <button
                    onClick={handleCompare}
                    disabled={isLoading('comparePlans')}
                    className="rounded-xl bg-gradient-to-r from-primary to-purple-600 px-5 py-3 text-sm font-bold text-white transition-all hover:shadow-lg hover:shadow-primary/20 disabled:opacity-60"
                  >
                    {isLoading('comparePlans') ? 'Comparing...' : 'Compare Candidates'}
                  </button>
                </div>

                {comparisonResult ? (
                  <div className="space-y-5">
                    <RankingList
                      title="Comparison Ranking"
                      ranking={comparisonResult.ranking}
                      onSelect={handleSelectPlan}
                      selectedPlanId={internalSelectedPlanId}
                    />
                    <div className="grid gap-4">
                      {comparisonResult.comparisons.map((comparison) => (
                        <div key={`${comparison.left_plan_id}-${comparison.right_plan_id}`} className="rounded-2xl border border-white/5 bg-white/5 p-4">
                          <div className="mb-2 flex items-center justify-between gap-4">
                            <p className="text-sm font-bold text-white">
                              {comparison.left_plan_id} vs {comparison.right_plan_id}
                            </p>
                            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-primary">
                              {comparison.margin}
                            </span>
                          </div>
                          <p className="text-sm text-text-muted">{comparison.rationale}</p>
                          {comparison.preference_factors.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {comparison.preference_factors.map((factor) => (
                                <span key={factor} className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-text-muted">
                                  {factor.replace(/_/g, ' ')}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState text="Run comparison after you have at least two candidates." />
                )}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-white/5 bg-surface p-6">
              <h3 className="mb-4 text-lg font-bold text-white">Candidate Pool</h3>
              <div className="space-y-3">
                {candidatePlans.map((plan) => (
                  <button
                    key={plan.id}
                    onClick={() => handleSelectPlan(plan.id)}
                    className={cn(
                      'w-full rounded-xl border px-4 py-3 text-left transition-all duration-300',
                      internalSelectedPlanId === plan.id
                        ? 'border-primary/40 bg-primary/10'
                        : 'border-white/5 bg-white/5 hover:bg-white/10'
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-bold text-white">{plan.title}</p>
                        <p className="text-xs text-text-muted">
                          {plan.sourceType.replace('_', ' ')} · {plan.planningStyle}
                        </p>
                      </div>
                      <span className="rounded-full bg-black/20 px-2.5 py-1 text-[11px] uppercase tracking-wider text-text-muted">
                        {plan.variantType || plan.sourceType}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <ComparisonPanel
              plans={plans}
              selectedPlanId={internalSelectedPlanId}
              onSelectPlan={handleSelectPlan}
            />

            {hasSelection && (
              <div className="rounded-2xl bg-surface border border-white/5 p-6 space-y-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Star size={20} className="text-primary" />
                  Rate This Planning Pass
                </h3>
                <div className="space-y-3">
                  <label className="text-sm font-semibold text-text-muted">Overall Rating</label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setUserRating(star)}
                        className={cn(
                          'h-10 w-10 rounded-lg flex items-center justify-center transition-all duration-200',
                          userRating >= star
                            ? 'bg-primary text-white'
                            : 'bg-white/5 text-text-muted hover:bg-white/10'
                        )}
                      >
                        <Star size={18} fill={userRating >= star ? 'currentColor' : 'none'} />
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={userComment}
                  onChange={(event) => setUserComment(event.target.value)}
                  placeholder="Optional comments about the chosen plan"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
                  rows={3}
                />
                <button
                  onClick={handleComplete}
                  disabled={!hasSelection || isLoading('saveUserRating')}
                  className={cn(
                    'flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3 font-bold text-white transition-all duration-300',
                    hasSelection
                      ? 'bg-gradient-to-r from-primary to-purple-600 hover:shadow-lg hover:shadow-primary/20'
                      : 'bg-white/5 text-text-muted cursor-not-allowed'
                  )}
                >
                  {isLoading('saveUserRating') ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      Continue with Selected Plan
                      <ChevronRight size={18} />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/5 bg-black/20 px-4 py-3">
      <p className="text-[11px] font-bold uppercase tracking-wider text-text-muted">{label}</p>
      <p className="mt-1 text-lg font-bold text-white">{value}</p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-8 text-center text-sm text-text-muted">
      {text}
    </div>
  );
}

function RankingList({
  title,
  ranking,
  selectedPlanId,
  onSelect,
}: {
  title: string;
  ranking: RankedPlan[];
  selectedPlanId: string | null;
  onSelect: (planId: string) => void;
}) {
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-bold uppercase tracking-wider text-text-muted">{title}</h4>
      <div className="space-y-3">
        {ranking.map((item) => (
          <button
            key={item.plan_id}
            onClick={() => onSelect(item.plan_id)}
            className={cn(
              'w-full rounded-2xl border px-4 py-4 text-left transition-all duration-300',
              selectedPlanId === item.plan_id
                ? 'border-primary/40 bg-primary/10'
                : 'border-white/5 bg-white/5 hover:bg-white/10'
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-white">
                  #{item.rank} · {item.plan_id}
                </p>
                <p className="mt-1 text-sm text-text-muted">{item.recommendation_reason}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-white">{item.final_score.toFixed(1)}</p>
                <p className="text-xs uppercase tracking-wider text-text-muted">
                  {item.disagreement_level} disagreement
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function RubricGrid({
  evaluations,
  plans,
}: {
  evaluations: Record<string, Record<string, RubricPlanEvaluation>>;
  plans: NormalizedPlan[];
}) {
  const criteria = Array.from(
    new Set(
      Object.values(evaluations).flatMap((byJudge) =>
        Object.values(byJudge).flatMap((evaluation) => Object.keys(evaluation.rubric_scores))
      )
    )
  );

  return (
    <div className="overflow-hidden rounded-2xl border border-white/5">
      <div className="grid grid-cols-[1.2fr,repeat(3,minmax(0,1fr))] gap-px bg-white/5">
        <div className="bg-surface px-4 py-3 text-xs font-bold uppercase tracking-wider text-text-muted">Plan</div>
        <div className="bg-surface px-4 py-3 text-xs font-bold uppercase tracking-wider text-text-muted">Score</div>
        <div className="bg-surface px-4 py-3 text-xs font-bold uppercase tracking-wider text-text-muted">Verdict</div>
        <div className="bg-surface px-4 py-3 text-xs font-bold uppercase tracking-wider text-text-muted">Top Signal</div>
        {plans.map((plan) => {
          const byJudge = evaluations[plan.id] || {};
          const all = Object.values(byJudge);
          const avgScore =
            all.reduce((sum, item) => sum + item.overall_score, 0) / Math.max(all.length, 1);
          const primary = all[0];
          const topCriterion = criteria
            .map((criterion) => ({
              criterion,
              score:
                all.reduce((sum, item) => sum + (item.rubric_scores[criterion] || 0), 0) /
                Math.max(all.length, 1),
            }))
            .sort((left, right) => right.score - left.score)[0];

          return (
            <div key={plan.id} className="contents">
              <div className="bg-surface px-4 py-4">
                <p className="font-bold text-white">{plan.title}</p>
                <p className="text-xs text-text-muted">{plan.source_type}</p>
              </div>
              <div className="bg-surface px-4 py-4 text-white">{avgScore.toFixed(1)}</div>
              <div className="bg-surface px-4 py-4 text-text-muted">{primary?.verdict || '-'}</div>
              <div className="bg-surface px-4 py-4 text-text-muted">
                {topCriterion ? topCriterion.criterion.replace(/_/g, ' ') : '-'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function toList(value: string): string[] {
  return value
    .split(/\n|,/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}
