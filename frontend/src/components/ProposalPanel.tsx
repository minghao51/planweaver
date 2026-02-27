import { useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import { Plan, ProposalWithAnalysis } from '../types';
import {
  Lightbulb,
  Check,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  ChevronRight,
  Scale
} from 'lucide-react';
import { cn } from '../utils';
import { ProposalComparisonView } from './ProposalComparisonView';

interface ProposalPanelProps {
  plan: Plan;
  onSelected: () => void;
}

export function ProposalPanel({ plan, onSelected }: ProposalPanelProps) {
  const [showComparison, setShowComparison] = useState(false);
  const { selectProposal, isLoading, error } = usePlanApi();
  const { error: showError } = useToast();

  async function handleSelect(proposalId: string) {
    try {
      await selectProposal(plan.session_id, proposalId);
      onSelected();
    } catch (error) {
      showError('Failed to select proposal. Please try again.');
    }
  }

  const selecting = isLoading('selectProposal');

  // Convert proposals to ProposalWithAnalysis format
  const proposalsWithAnalysis: ProposalWithAnalysis[] = (plan.strawman_proposals || []).map(p => ({
    proposal_id: p.id,
    title: p.title,
    description: p.description,
    pros: p.pros,
    cons: p.cons,
    selected: p.selected,
    estimated_step_count: 0, // These would come from the backend if available
    complexity_score: 'Medium' as const,
    estimated_time_minutes: 0,
    estimated_cost_usd: 0,
    risk_factors: [],
  }));

  return (
    <div className="space-y-8 animate-in slide-in-from-bottom-6 duration-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-warning/10 flex items-center justify-center text-warning">
            <Lightbulb size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Strawman Proposals</h2>
            <p className="text-text-muted font-medium">Select an architectural approach to proceed with execution.</p>
          </div>
        </div>
        {(plan.strawman_proposals?.length ?? 0) >= 2 && (
          <button
            onClick={() => setShowComparison(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 font-bold text-sm transition-all duration-300"
          >
            <Scale size={16} />
            Compare All
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {plan.strawman_proposals?.map((proposal) => (
          <div
            key={proposal.id}
            className={cn(
              "flex flex-col p-8 rounded-3xl bg-surface border transition-all duration-500 group relative overflow-hidden",
              proposal.selected
                ? "border-primary shadow-2xl shadow-primary/10 ring-1 ring-primary/20"
                : "border-white/5 hover:border-white/20 hover:bg-surface-alt shadow-xl"
            )}
          >
            {proposal.selected && (
              <div className="absolute top-0 right-0 p-4">
                <Check className="text-primary h-6 w-6" />
              </div>
            )}

            <div className="space-y-6 flex-1">
              <div>
                <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors duration-300">
                  {proposal.title}
                </h3>
                <p className="mt-3 text-text-body leading-relaxed text-sm opacity-80">
                  {proposal.description}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-6">
                <div className="space-y-3">
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-success/80 flex items-center gap-1.5">
                    <ShieldCheck size={12} />
                    Advantages
                  </h4>
                  <ul className="space-y-2">
                    {proposal.pros.map((pro, i) => (
                      <li key={i} className="text-xs text-text-body flex items-start gap-2">
                        <div className="h-1 w-1 rounded-full bg-success mt-1.5 shrink-0" />
                        {pro}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-danger/80 flex items-center gap-1.5">
                    <ShieldAlert size={12} />
                    Trade-offs
                  </h4>
                  <ul className="space-y-2">
                    {proposal.cons.map((con, i) => (
                      <li key={i} className="text-xs text-text-body flex items-start gap-2">
                        <div className="h-1 w-1 rounded-full bg-danger mt-1.5 shrink-0" />
                        {con}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            <button
              onClick={() => handleSelect(proposal.id)}
              disabled={selecting || proposal.selected}
              className={cn(
                "mt-8 w-full h-12 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 transition-all duration-300",
                proposal.selected
                  ? "bg-primary/10 text-primary border border-primary/20 cursor-default"
                  : "bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/10 hover:scale-[1.02] active:scale-100"
              )}
            >
              {selecting ? (
                <Loader2 className="animate-spin w-5 h-5" />
              ) : proposal.selected ? (
                <>
                  <Check size={16} /> Selected
                </>
              ) : (
                <>
                  Select Approach
                  <ChevronRight size={16} />
                </>
              )}
            </button>
          </div>
        ))}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm">
          {error}
        </div>
      )}

      {showComparison && (
        <ProposalComparisonView
          sessionId={plan.session_id}
          proposals={proposalsWithAnalysis}
          onClose={() => setShowComparison(false)}
          onSelectProposal={(proposalId) => {
            handleSelect(proposalId);
          }}
        />
      )}
    </div>
  );
}
