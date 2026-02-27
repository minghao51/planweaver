import { Star, TrendingUp, Clock, DollarSign, Layers } from 'lucide-react';
import { cn } from '../../utils';
import type { ModelRating, OptimizedVariant } from '../../types';

interface ComparisonPanelProps {
  plans: Array<{
    id: string;
    title: string;
    variantType?: string;
    metadata?: {
      step_count: number;
      complexity_score: string;
      estimated_time_minutes: number;
      estimated_cost_usd: number;
    };
    ratings?: Record<string, ModelRating>;
    averageScore?: number;
  }>;
  selectedPlanId: string | null;
  onSelectPlan: (planId: string) => void;
}

export function ComparisonPanel({ plans, selectedPlanId, onSelectPlan }: ComparisonPanelProps) {
  if (plans.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 rounded-2xl bg-surface border border-white/5">
        <p className="text-text-muted">No plans to compare</p>
      </div>
    );
  }

  // Get all unique criteria across all ratings
  const allCriteria = Array.from(
    new Set(
      plans.flatMap(plan =>
        Object.values(plan.ratings || {}).flatMap(rating =>
          Object.keys(rating.ratings || {})
        )
      )
    )
  ).sort();

  // Get all unique models
  const allModels = Array.from(
    new Set(
      plans.flatMap(plan => Object.keys(plan.ratings || {}))
    )
  );

  return (
    <div className="space-y-6">
      {/* Metrics Comparison Table */}
      <div className="rounded-2xl bg-surface border border-white/5 overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5">
          <h3 className="text-lg font-bold text-white">Metrics Comparison</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-muted">Metric</th>
                {plans.map(plan => (
                  <th
                    key={plan.id}
                    className={cn(
                      'px-6 py-4 text-center text-sm font-bold',
                      selectedPlanId === plan.id ? 'text-primary' : 'text-white'
                    )}
                  >
                    {plan.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Steps */}
              <tr className="border-b border-white/5">
                <td className="px-6 py-4 flex items-center gap-2 text-sm text-text-muted">
                  <Layers size={16} />
                  Steps
                </td>
                {plans.map(plan => (
                  <td key={plan.id} className="px-6 py-4 text-center">
                    <span className="text-lg font-bold text-white">
                      {plan.metadata?.step_count || '-'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Time */}
              <tr className="border-b border-white/5">
                <td className="px-6 py-4 flex items-center gap-2 text-sm text-text-muted">
                  <Clock size={16} />
                  Est. Time
                </td>
                {plans.map(plan => (
                  <td key={plan.id} className="px-6 py-4 text-center">
                    <span className="text-lg font-bold text-white">
                      {plan.metadata?.estimated_time_minutes
                        ? `${plan.metadata.estimated_time_minutes}m`
                        : '-'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Cost */}
              <tr className="border-b border-white/5">
                <td className="px-6 py-4 flex items-center gap-2 text-sm text-text-muted">
                  <DollarSign size={16} />
                  Est. Cost
                </td>
                {plans.map(plan => (
                  <td key={plan.id} className="px-6 py-4 text-center">
                    <span className="text-lg font-bold text-white">
                      {plan.metadata?.estimated_cost_usd !== undefined
                        ? `$${plan.metadata.estimated_cost_usd.toFixed(2)}`
                        : '-'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Overall Score */}
              <tr>
                <td className="px-6 py-4 flex items-center gap-2 text-sm text-text-muted">
                  <Star size={16} />
                  Overall Score
                </td>
                {plans.map(plan => (
                  <td key={plan.id} className="px-6 py-4 text-center">
                    <div
                      className={cn(
                        'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-lg',
                        plan.averageScore !== undefined
                          ? plan.averageScore >= 8
                            ? 'bg-success/20 text-success'
                            : plan.averageScore >= 6
                            ? 'bg-warning/20 text-warning'
                            : 'bg-danger/20 text-danger'
                          : 'bg-white/5 text-text-muted'
                      )}
                    >
                      {plan.averageScore !== undefined ? (
                        <>
                          <TrendingUp size={16} />
                          {plan.averageScore.toFixed(1)}
                        </>
                      ) : (
                        '-'
                      )}
                    </div>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Ratings by Model */}
      {allModels.length > 0 && (
        <div className="rounded-2xl bg-surface border border-white/5 overflow-hidden">
          <div className="px-6 py-4 border-b border-white/5">
            <h3 className="text-lg font-bold text-white">AI Model Ratings</h3>
          </div>

          <div className="p-6 space-y-6">
            {allModels.map(modelName => {
              const prettyName = modelName.split('-')[0];
              return (
                <div key={modelName} className="space-y-3">
                  <h4 className="text-sm font-semibold text-text-muted uppercase tracking-wider">
                    {prettyName}
                  </h4>
                  <div className="space-y-2">
                    {allCriteria.map(criterion => {
                      const scores = plans.map(plan => {
                        const rating = plan.ratings?.[modelName];
                        return rating?.ratings?.[criterion];
                      });

                      const maxScore = Math.max(...scores.filter(s => s !== undefined));

                      return (
                        <div key={criterion} className="space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-muted capitalize">
                              {criterion.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex gap-2">
                            {plans.map((plan, idx) => {
                              const score = scores[idx];
                              const isSelected = selectedPlanId === plan.id;
                              if (score === undefined) return null;

                              return (
                                <div
                                  key={plan.id}
                                  className={cn(
                                    'flex-1 h-8 rounded-lg flex items-center justify-center text-sm font-bold transition-all',
                                    isSelected
                                      ? 'bg-primary text-white'
                                      : 'bg-white/5 text-text-muted',
                                    score === maxScore && !isSelected && 'ring-1 ring-success/50'
                                  )}
                                >
                                  {score.toFixed(1)}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Selection Actions */}
      <div className="flex justify-center">
        <div className="inline-flex rounded-xl bg-surface border border-white/5 p-1 gap-1">
          {plans.map(plan => (
            <button
              key={plan.id}
              onClick={() => onSelectPlan(plan.id)}
              className={cn(
                'px-6 py-3 rounded-lg text-sm font-bold transition-all duration-300',
                selectedPlanId === plan.id
                  ? 'bg-primary text-white shadow-lg'
                  : 'text-text-muted hover:text-white hover:bg-white/5'
              )}
            >
              {plan.variantType || plan.title}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
