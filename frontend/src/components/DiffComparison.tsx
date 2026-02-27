import type { ProposalComparison } from '../types';
import {
  Zap,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  Split,
  Maximize2,
  ChevronRight
} from 'lucide-react';

interface DiffComparisonProps {
  comparison: ProposalComparison;
  onExpand: () => void;
  onSelectProposal: (proposalId: string) => void;
}

export function DiffComparison({
  comparison,
  onExpand,
  onSelectProposal,
}: DiffComparisonProps) {
  const proposals = comparison.proposals;

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-center">
        <button
          onClick={onExpand}
          className="group flex items-center gap-2 px-6 py-2.5 rounded-full bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/20 text-sm font-bold text-text-muted hover:text-white transition-all duration-300"
        >
          <Maximize2 size={16} className="group-hover:scale-110 transition-transform" />
          Detail Analysis (Side-by-Side)
        </button>
      </div>

      {/* Quick metrics cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {proposals.map((p) => (
          <div key={p.proposal_id} className="p-6 rounded-3xl bg-surface-alt border border-white/5 shadow-xl glassmorphism group hover:border-primary/50 transition-all duration-500 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-primary/20 group-hover:bg-primary transition-colors" />
            <h4 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-6 px-2">
              Approach {p.proposal_id.slice(0, 4)}
            </h4>

            <div className="grid grid-cols-3 gap-2 mb-8">
              <div className="flex flex-col items-center p-3 rounded-2xl bg-black/20 border border-white/5">
                <Zap size={16} className="text-warning mb-2" />
                <span className="text-xs font-bold text-white">{comparison.time_comparison[p.proposal_id]}m</span>
                <span className="text-[8px] text-text-muted uppercase font-bold mt-1">Time</span>
              </div>
              <div className="flex flex-col items-center p-3 rounded-2xl bg-black/20 border border-white/5">
                <DollarSign size={16} className="text-success mb-2" />
                <span className="text-xs font-bold text-white">${comparison.cost_comparison[p.proposal_id].toFixed(2)}</span>
                <span className="text-[8px] text-text-muted uppercase font-bold mt-1">Cost</span>
              </div>
              <div className="flex flex-col items-center p-3 rounded-2xl bg-black/20 border border-white/5">
                <AlertCircle size={16} className="text-danger mb-2" />
                <span className="text-xs font-bold text-white uppercase">{comparison.complexity_comparison[p.proposal_id]}</span>
                <span className="text-[8px] text-text-muted uppercase font-bold mt-1">Risk</span>
              </div>
            </div>

            <button
              onClick={() => onSelectProposal(p.proposal_id)}
              className="w-full py-3 rounded-xl bg-primary text-white text-xs font-extrabold uppercase tracking-widest hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all hover:scale-[1.02]"
            >
              Select Approach
            </button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Common steps */}
        {comparison.common_steps.length > 0 && (
          <div className="p-8 rounded-3xl bg-surface border border-white/5 glassmorphism h-fit">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-success/10 text-success">
                <CheckCircle2 size={20} />
              </div>
              <h3 className="text-lg font-bold text-white tracking-tight">Shared Foundations</h3>
            </div>
            <div className="space-y-3">
              {comparison.common_steps.map((step, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5 text-sm font-medium text-text-body">
                  <div className="h-1.5 w-1.5 rounded-full bg-success" />
                  {step.task}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unique steps per proposal */}
        <div className="space-y-6">
          <div className="flex items-center gap-3 mb-2 px-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Split size={20} />
            </div>
            <h3 className="text-lg font-bold text-white tracking-tight">Strategic Variance</h3>
          </div>

          <div className="space-y-4">
            {Object.entries(comparison.unique_steps_by_proposal).map(([propId, steps]) => (
              <div key={propId} className="p-6 rounded-3xl bg-surface-alt border border-white/5 glassmorphism">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-xs font-bold text-primary uppercase tracking-widest">
                    Unique to {propId.slice(0, 4)}
                  </h4>
                  <span className="text-[10px] text-text-muted font-mono">{steps.length} exclusive steps</span>
                </div>
                {steps.length > 0 ? (
                  <div className="space-y-2">
                    {steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-black/20 text-xs font-medium text-text-body italic">
                        <ChevronRight size={12} className="text-primary" />
                        {step.task}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-text-muted italic opacity-40 py-2">No divergent maneuvers identified.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
