import { useState } from 'react';
import type { ProposalWithAnalysis } from '../types';
import { Check, Columns, Zap, DollarSign, AlertCircle, ChevronRight } from 'lucide-react';
import { cn } from '../utils';

interface ProposalSelectorProps {
  proposals: ProposalWithAnalysis[];
  onCompare: (proposalIds: string[]) => void;
  loading?: boolean;
}

export function ProposalSelector({
  proposals,
  onCompare,
  loading = false,
}: ProposalSelectorProps) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggleProposal = (id: string) => {
    if (selected.includes(id)) {
      setSelected(selected.filter((s) => s !== id));
    } else if (selected.length < 3) {
      setSelected([...selected, id]);
    }
  };

  const handleCompare = () => {
    if (selected.length >= 2) {
      onCompare(selected);
    }
  };

  return (
    <div className="space-y-8 py-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white tracking-tight">Select proposals to compare</h3>
        <span className="text-xs font-bold text-text-muted uppercase tracking-widest bg-white/5 px-3 py-1 rounded-full border border-white/5">
          {selected.length}/3 selected
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {proposals.map((proposal) => (
          <div
            key={proposal.proposal_id}
            className={cn(
              "group p-5 rounded-2xl border transition-all duration-300 cursor-pointer relative",
              selected.includes(proposal.proposal_id)
                ? "bg-primary/10 border-primary shadow-lg shadow-primary/5"
                : "bg-surface-alt border-white/5 hover:border-white/20 hover:bg-white/5"
            )}
            onClick={() => toggleProposal(proposal.proposal_id)}
          >
            {selected.includes(proposal.proposal_id) && (
              <div className="absolute top-3 right-3 h-5 w-5 rounded-full bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
                <Check size={12} className="text-white" />
              </div>
            )}

            <h4 className="text-sm font-bold text-white mb-2 group-hover:text-primary transition-colors">
              {proposal.title}
            </h4>
            <p className="text-xs text-text-muted line-clamp-2 mb-4">
              {proposal.description}
            </p>

            <div className="flex items-center gap-3 pt-3 border-t border-white/5">
              <div className="flex items-center gap-1 text-[10px] text-text-muted font-bold">
                <Zap size={10} className="text-warning" />
                {proposal.estimated_step_count}st
              </div>
              <div className="flex items-center gap-1 text-[10px] text-text-muted font-bold">
                <DollarSign size={10} className="text-success" />
                ${proposal.estimated_cost_usd.toFixed(2)}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-text-muted font-bold">
                <AlertCircle size={10} className="text-danger" />
                {proposal.complexity_score}
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        className={cn(
          "w-full h-14 rounded-2xl font-bold text-base flex items-center justify-center gap-2 transition-all duration-300",
          (selected.length < 2 || loading)
            ? "bg-white/5 text-text-muted opacity-50 cursor-not-allowed"
            : "bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/20 hover:scale-[1.01]"
        )}
        onClick={handleCompare}
        disabled={selected.length < 2 || loading}
      >
        <Columns size={18} />
        {loading ? 'Analyzing differences...' : `Execute Comparison (${selected.length})`}
        <ChevronRight size={18} />
      </button>
    </div>
  );
}
