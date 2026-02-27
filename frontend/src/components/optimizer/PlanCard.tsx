import { Check, Star, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '../../utils';
import type { OptimizedVariant, ModelRating } from '../../types';

interface PlanCardProps {
  id: string;
  title: string;
  description: string;
  variantType?: string;
  executionGraphLength: number;
  metadata?: {
    step_count: number;
    complexity_score: string;
    estimated_time_minutes: number;
    estimated_cost_usd: number;
  };
  ratings?: Record<string, ModelRating>;
  averageScore?: number;
  selected: boolean;
  onSelect: () => void;
  loading?: boolean;
}

export function PlanCard({
  id,
  title,
  description,
  variantType,
  executionGraphLength,
  metadata,
  ratings,
  averageScore,
  selected,
  onSelect,
  loading = false,
}: PlanCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-success';
    if (score >= 6) return 'text-warning';
    return 'text-danger';
  };

  const getScoreIcon = (score: number) => {
    if (score >= 8) return TrendingUp;
    if (score >= 6) return Minus;
    return TrendingDown;
  };

  const ScoreIcon = averageScore !== undefined ? getScoreIcon(averageScore) : Minus;

  return (
    <div
      className={cn(
        'flex flex-col p-6 rounded-2xl bg-surface border transition-all duration-300 cursor-pointer group relative overflow-hidden',
        selected
          ? 'border-primary shadow-xl shadow-primary/10 ring-2 ring-primary/20'
          : 'border-white/5 hover:border-white/20 hover:bg-surface-alt',
        loading && 'opacity-50 pointer-events-none'
      )}
      onClick={!selected ? onSelect : undefined}
    >
      {selected && (
        <div className="absolute top-4 right-4">
          <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
            <Check className="text-primary h-5 w-5" />
          </div>
        </div>
      )}

      {/* Variant Type Badge */}
      {variantType && (
        <div className="absolute top-4 left-4">
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            {variantType}
          </span>
        </div>
      )}

      <div className="space-y-4 pt-8">
        {/* Title and Description */}
        <div>
          <h3 className="text-lg font-bold text-white group-hover:text-primary transition-colors">
            {title}
          </h3>
          <p className="mt-2 text-sm text-text-muted leading-relaxed">
            {description}
          </p>
        </div>

        {/* Metadata */}
        {metadata && (
          <div className="grid grid-cols-3 gap-3 py-3 px-4 rounded-xl bg-white/5">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{metadata.step_count}</div>
              <div className="text-xs text-text-muted mt-1">Steps</div>
            </div>
            <div className="text-center border-x border-white/10">
              <div className="text-2xl font-bold text-white">{metadata.complexity_score}</div>
              <div className="text-xs text-text-muted mt-1">Complexity</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">${metadata.estimated_cost_usd.toFixed(2)}</div>
              <div className="text-xs text-text-muted mt-1">Est. Cost</div>
            </div>
          </div>
        )}

        {/* Ratings */}
        {ratings && Object.keys(ratings).length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-text-muted">AI Ratings</span>
              {averageScore !== undefined && (
                <div className={cn('flex items-center gap-2', getScoreColor(averageScore))}>
                  <ScoreIcon size={16} />
                  <span className="text-lg font-bold">{averageScore.toFixed(1)}</span>
                  <span className="text-xs text-text-muted">/ 10</span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              {Object.entries(ratings).slice(0, 3).map(([modelName, rating]) => (
                <div key={modelName} className="flex items-center justify-between text-xs">
                  <span className="text-text-muted">{modelName.split('-')[0]}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className={cn(
                          'h-full transition-all duration-300',
                          rating.overall_score >= 8 ? 'bg-success' :
                          rating.overall_score >= 6 ? 'bg-warning' : 'bg-danger'
                        )}
                        style={{ width: `${(rating.overall_score / 10) * 100}%` }}
                      />
                    </div>
                    <span className="font-bold w-8 text-right">{rating.overall_score.toFixed(1)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Select Button */}
        {!selected && (
          <button
            className="w-full py-3 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary font-bold text-sm transition-all duration-300 border border-primary/20"
            onClick={(e) => {
              e.stopPropagation();
              onSelect();
            }}
          >
            Select This Plan
          </button>
        )}
      </div>
    </div>
  );
}
