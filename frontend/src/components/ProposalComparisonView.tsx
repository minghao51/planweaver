import { useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import type { ProposalComparison, ProposalWithAnalysis } from '../types';
import { ProposalSelector } from './ProposalSelector';
import { DiffComparison } from './DiffComparison';
import { SideBySideComparison } from './SideBySideComparison';
import { X, Scale, Loader2, AlertCircle } from 'lucide-react';

interface ProposalComparisonViewProps {
  sessionId: string;
  proposals: ProposalWithAnalysis[];
  onClose: () => void;
  onSelectProposal: (proposalId: string) => void;
}

export function ProposalComparisonView({
  sessionId,
  proposals,
  onClose,
  onSelectProposal,
}: ProposalComparisonViewProps) {
  const [comparison, setComparison] = useState<ProposalComparison | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const { compareProposals, isLoading, error: apiError } = usePlanApi();

  const handleCompare = async (proposalIds: string[]) => {
    try {
      const result = await compareProposals(sessionId, proposalIds);
      setComparison(result);
    } catch (error) {
      console.error('Failed to compare proposals:', error);
    }
  };

  const handleSelectProposal = (proposalId: string) => {
    onSelectProposal(proposalId);
    onClose();
  };

  const loading = isLoading('compareProposals');

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8 animate-in fade-in duration-300">
      <div
        className="absolute inset-0 bg-bg/90 backdrop-blur-xl"
        onClick={onClose}
      />

      <div className="relative w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-3xl bg-surface border border-white/10 shadow-2xl flex flex-col glassmorphism-dark animate-in zoom-in-95 duration-500">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <Scale size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">Comparative Analysis</h2>
              <p className="text-xs text-text-muted font-medium uppercase tracking-widest">Multi-proposal Evaluation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-white/5 text-text-muted hover:text-white transition-all"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          {apiError && (
            <div className="mb-6 p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {apiError}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-24 gap-4">
              <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="text-primary animate-spin" size={32} />
              </div>
              <div className="text-center">
                <p className="font-bold text-white uppercase tracking-tighter text-lg">Synthesizing Comparison</p>
                <p className="text-text-muted text-sm italic">Evaluating performance, cost, and complexity across branches...</p>
              </div>
            </div>
          ) : !comparison ? (
            <ProposalSelector
              proposals={proposals}
              onCompare={handleCompare}
              loading={loading}
            />
          ) : isExpanded ? (
            <SideBySideComparison
              comparison={comparison}
              onCollapse={() => setIsExpanded(false)}
              onSelectProposal={handleSelectProposal}
            />
          ) : (
            <DiffComparison
              comparison={comparison}
              onExpand={() => setIsExpanded(true)}
              onSelectProposal={handleSelectProposal}
            />
          )}
        </div>
      </div>
    </div>
  );
}
