import type { ProposalComparison } from '../types';
import {
  AlertTriangle,
  Target,
  Zap,
  DollarSign,
  AlertCircle,
  LayoutGrid,
  ChevronRight,
  ArrowLeft
} from 'lucide-react';

interface SideBySideComparisonProps {
  comparison: ProposalComparison;
  onCollapse: () => void;
  onSelectProposal: (proposalId: string) => void;
}

export function SideBySideComparison({
  comparison,
  onCollapse,
  onSelectProposal,
}: SideBySideComparisonProps) {
  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-right-4 duration-500">
      <div className="flex justify-center">
        <button
          onClick={onCollapse}
          className="group flex items-center gap-2 px-6 py-2.5 rounded-full bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/20 text-sm font-bold text-text-muted hover:text-white transition-all duration-300"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          Summary Comparison
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {comparison.proposals.map((proposal) => (
          <div
            key={proposal.proposal_id}
            className="flex flex-col p-8 rounded-[40px] bg-surface border border-white/5 shadow-2xl glassmorphism-dark group hover:border-primary/30 transition-all duration-500"
          >
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                  <Target size={20} />
                </div>
                <h3 className="text-xl font-bold text-white">Approach {proposal.proposal_id.slice(0, 4)}</h3>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-8 p-4 rounded-3xl bg-black/40 border border-white/5">
              <div className="flex flex-col items-center">
                <Zap size={14} className="text-warning mb-1.5" />
                <span className="text-xs font-bold text-white">{comparison.time_comparison[proposal.proposal_id]}m</span>
              </div>
              <div className="flex flex-col items-center border-x border-white/10">
                <DollarSign size={14} className="text-success mb-1.5" />
                <span className="text-xs font-bold text-white">${comparison.cost_comparison[proposal.proposal_id].toFixed(2)}</span>
              </div>
              <div className="flex flex-col items-center">
                <AlertCircle size={14} className="text-danger mb-1.5" />
                <span className="text-xs font-bold text-white uppercase tracking-tighter">{comparison.complexity_comparison[proposal.proposal_id].slice(0, 3)}</span>
              </div>
            </div>

            <div className="flex-1 space-y-10">
              <div className="space-y-4">
                <div className="flex items-center gap-2 px-2 text-[10px] font-bold text-text-muted uppercase tracking-widest">
                  <LayoutGrid size={12} className="text-primary" />
                  Strategy Blueprint ({proposal.full_execution_graph.length} steps)
                </div>
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                  {proposal.full_execution_graph.length > 0 ? (
                    proposal.full_execution_graph.map((step, i) => (
                      <div key={i} className="group/item flex items-start gap-3 p-3 rounded-2xl bg-white/5 border border-white/5 text-[11px] font-medium text-text-body hover:bg-white/10 transition-colors">
                        <span className="text-primary opacity-40 font-mono mt-0.5">{i + 1}</span>
                        {step.task}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-text-muted italic py-4 text-center opacity-40">Blueprint unavailable.</p>
                  )}
                </div>
              </div>

              {proposal.all_risk_factors.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 px-2 text-[10px] font-bold text-danger uppercase tracking-widest">
                    <AlertTriangle size={12} />
                    Critical Risk Factors
                  </div>
                  <div className="space-y-2">
                    {proposal.all_risk_factors.map((risk, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-3 rounded-2xl bg-danger/5 border border-danger/10 text-[11px] font-medium text-text-body italic">
                        <div className="h-1 w-1 rounded-full bg-danger mt-1.5 shrink-0" />
                        {risk}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {proposal.generation_error && (
              <div className="mt-6 p-4 rounded-2xl bg-danger/10 border border-danger/20 text-danger text-[10px] font-bold uppercase tracking-wider flex items-center gap-2">
                <AlertCircle size={14} />
                {proposal.generation_error}
              </div>
            )}

            <button
              className="mt-8 w-full h-14 rounded-[20px] bg-primary text-white font-bold text-sm tracking-tight hover:bg-primary-hover shadow-xl shadow-primary/20 transition-all hover:scale-[1.02] active:scale-100 flex items-center justify-center gap-2"
              onClick={() => onSelectProposal(proposal.proposal_id)}
            >
              Select Approach
              <ChevronRight size={18} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
