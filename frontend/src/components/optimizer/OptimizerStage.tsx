import { useEffect, useState } from 'react';
import { Loader2, Sparkles, Star, ChevronRight } from 'lucide-react';
import { useOptimizer, useOptimizerStage } from '../../hooks/useOptimizer';
import { useToast } from '../../hooks/useToast';
import { PlanCard } from './PlanCard';
import { ComparisonPanel } from './ComparisonPanel';
import { cn } from '../../utils';
import type { OptimizedVariant, RatedPlan, VariantType } from '../../types';

interface OptimizerStageProps {
  sessionId: string;
  selectedProposalId: string;
  selectedProposalTitle: string;
  selectedProposalDescription: string;
  onComplete: (selectedPlanId: string) => void;
  onBack: () => void;
}

export function OptimizerStage({
  sessionId,
  selectedProposalId,
  selectedProposalTitle,
  selectedProposalDescription,
  onComplete,
  onBack,
}: OptimizerStageProps) {
  const { optimizePlan, saveUserRating, loading, isLoading } = useOptimizer();
  const { showSuccess, showError } = useToast();

  const [optimizationTypes] = useState<VariantType[]>(['simplified', 'enhanced', 'cost-optimized']);
  const [userRating, setUserRating] = useState<number>(0);
  const [userComment, setUserComment] = useState<string>('');

  // Use optimizer stage state
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

  // Trigger optimization on mount
  useEffect(() => {
    async function runOptimization() {
      try {
        setStatus('generating_variants');
        const result = await optimizePlan(selectedProposalId, optimizationTypes);

        if (result.variants) {
          setVariants(result.variants);
        }

        if (result.ratings) {
          setRatings(result.ratings);
        }

        setStatus('completed');
        showSuccess('Optimization complete! Review your options.');
      } catch (error) {
        console.error('Optimization failed:', error);
        setStatus('error');
        showError('Failed to generate optimized variants. Please try again.');
      }
    }

    runOptimization();
  }, [selectedProposalId, optimizationTypes]);

  // Prepare plans for display
  const plans = [
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
    ...variants.map(variant => ({
      id: variant.id,
      title: `${variant.variant_type} Variant`,
      description: variant.metadata.optimization_notes || `AI-optimized ${variant.variant_type} version`,
      variantType: variant.variant_type,
      metadata: variant.metadata,
      ratings: ratings[variant.id]?.ratings || {},
      averageScore: ratings[variant.id]?.average_score,
    })),
  ];

  const handleSelectPlan = (planId: string) => {
    setSelectedPlanId(planId);
  };

  const handleComplete = async () => {
    if (!internalSelectedPlanId) {
      showError('Please select a plan to continue');
      return;
    }

    // Save user rating if provided
    if (userRating > 0) {
      try {
        await saveUserRating(internalSelectedPlanId, userRating, userComment);
        showSuccess('Thank you for your feedback!');
      } catch (error) {
        console.error('Failed to save rating:', error);
      }
    }

    onComplete(internalSelectedPlanId);
  };

  const isOptimizing = status === 'generating_variants' || isLoading('optimize');
  const hasSelection = internalSelectedPlanId !== null;

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-6 duration-700">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-white">
            <Sparkles size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Plan Optimizer</h2>
            <p className="text-text-muted font-medium">
              AI-generated variants with multi-model ratings
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

      {/* Loading State */}
      {isOptimizing && (
        <div className="flex flex-col items-center justify-center py-16 rounded-2xl bg-surface border border-white/5">
          <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">Generating Optimized Variants</h3>
          <p className="text-text-muted text-sm">
            AI is analyzing your proposal and creating optimized versions...
          </p>
        </div>
      )}

      {/* Main Content - Split View */}
      {!isOptimizing && status !== 'error' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Plans List */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white">Available Plans</h3>
            <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
              {plans.map(plan => (
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

          {/* Right: Comparison Panel */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white">Comparison</h3>
            <div className="sticky top-4">
              <ComparisonPanel
                plans={plans}
                selectedPlanId={internalSelectedPlanId}
                onSelectPlan={handleSelectPlan}
              />
            </div>
          </div>
        </div>
      )}

      {/* User Rating Section */}
      {hasSelection && !isOptimizing && (
        <div className="rounded-2xl bg-surface border border-white/5 p-6 space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Star size={20} className="text-primary" />
            Rate Your Experience (Optional)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Star Rating */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-text-muted">Overall Rating</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map(star => (
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

            {/* Comment */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-text-muted">Feedback (Optional)</label>
              <textarea
                value={userComment}
                onChange={e => setUserComment(e.target.value)}
                placeholder="Tell us about your experience..."
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
                rows={2}
              />
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {!isOptimizing && status !== 'error' && (
        <div className="flex justify-between items-center">
          <button
            onClick={onBack}
            className="px-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-text-muted font-bold transition-all duration-300"
          >
            Go Back
          </button>
          <button
            onClick={handleComplete}
            disabled={!hasSelection || isLoading('saveUserRating')}
            className={cn(
              'flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-white transition-all duration-300',
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
  );
}
