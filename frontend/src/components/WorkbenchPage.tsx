import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, Layers3, Rocket, SearchCode } from 'lucide-react';
import { OptimizerStage } from './optimizer';
import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import { cn } from '../utils';
import type {
  CandidatePlan,
  Plan,
  SessionHistoryItem,
  StrawmanProposal,
} from '../types';

type LaunchSelection =
  | {
      kind: 'proposal';
      id: string;
      title: string;
      description: string;
    }
  | {
      kind: 'candidate';
      id: string;
      title: string;
      description: string;
    };

export function WorkbenchPage() {
  const [sessionId, setSessionId] = useState('');
  const [selectedSession, setSelectedSession] = useState<Plan | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionHistoryItem[]>(
    []
  );
  const [selectedProposalId, setSelectedProposalId] = useState('');
  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [launched, setLaunched] = useState(false);

  const { getSession, listSessions, isLoading } = usePlanApi();
  const { error: showError, info: showInfo } = useToast();

  const loadRecentSessions = useCallback(async () => {
    try {
      const result = await listSessions({ limit: 8 });
      setRecentSessions(result.sessions);
    } catch {
      showError('Failed to load recent sessions.');
    }
  }, [listSessions, showError]);

  useEffect(() => {
    void loadRecentSessions();
  }, [loadRecentSessions]);

  const loadSession = useCallback(
    async (nextSessionId: string) => {
      const trimmed = nextSessionId.trim();
      if (!trimmed) {
        setSelectedSession(null);
        setSelectedProposalId('');
        setSelectedCandidateId('');
        return;
      }

      try {
        const plan = await getSession(trimmed);
        setSelectedSession(plan);
        setSessionId(trimmed);

        const preselected = plan.strawman_proposals.find(
          (proposal) => proposal.selected
        );
        const fallback = preselected || plan.strawman_proposals[0];
        setSelectedProposalId(fallback?.id || '');
        setSelectedCandidateId(getPreferredCandidate(plan)?.candidate_id || '');

        if (!plan.strawman_proposals.length) {
          if (plan.candidate_plans.length > 0) {
            showInfo(
              'No proposals found, but existing candidate plans can still be opened in the workbench.'
            );
          } else {
            showInfo(
              'This session has no proposals yet. Generate proposals first from the plan view.'
            );
          }
        }
      } catch {
        setSelectedSession(null);
        setSelectedProposalId('');
        setSelectedCandidateId('');
        showError(
          'Failed to load that session. Check the session ID and try again.'
        );
      }
    },
    [getSession, showError, showInfo]
  );

  const selectedProposal = useMemo<StrawmanProposal | null>(() => {
    return (
      selectedSession?.strawman_proposals.find(
        (proposal) => proposal.id === selectedProposalId
      ) || null
    );
  }, [selectedProposalId, selectedSession]);

  const selectedCandidate = useMemo<CandidatePlan | null>(() => {
    return (
      selectedSession?.candidate_plans.find(
        (candidate) => candidate.candidate_id === selectedCandidateId
      ) || null
    );
  }, [selectedCandidateId, selectedSession]);

  const selectedLaunchItem = useMemo<LaunchSelection | null>(() => {
    if (selectedProposal) {
      return {
        kind: 'proposal',
        id: selectedProposal.id,
        title: selectedProposal.title,
        description: selectedProposal.description,
      };
    }

    if (selectedCandidate) {
      return {
        kind: 'candidate',
        id: selectedCandidate.proposal_id || selectedCandidate.candidate_id,
        title: selectedCandidate.title,
        description: selectedCandidate.summary,
      };
    }

    return null;
  }, [selectedCandidate, selectedProposal]);

  const canLaunch = Boolean(selectedSession && selectedLaunchItem);

  if (launched && selectedSession && selectedLaunchItem) {
    return (
      <OptimizerStage
        sessionId={selectedSession.session_id}
        selectedProposalId={selectedLaunchItem.id}
        selectedProposalTitle={selectedLaunchItem.title}
        selectedProposalDescription={selectedLaunchItem.description}
        onComplete={() => {}}
        onBack={() => setLaunched(false)}
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-10 py-8 sm:py-12 animate-in fade-in duration-700">
      <div className="text-center space-y-5">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-cyan-300/20 text-primary shadow-[0_18px_40px_-24px_rgba(56,189,248,0.9)]">
          <Layers3 size={28} />
        </div>
        <h1 className="font-heading text-4xl font-bold tracking-tight text-white lg:text-6xl">
          Planning <span className="text-primary">Workbench</span>
        </h1>
        <p className="mx-auto max-w-3xl text-lg text-text-muted">
          Open the full planning workspace directly: optimized variants, manual
          plans, rubric evaluation, and pairwise comparison in one place.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div className="rounded-[28px] border border-border/40 bg-surface p-6 shadow-2xl glassmorphism sm:p-8">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-2xl bg-primary/10 p-3 text-primary">
              <Rocket size={22} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                Open A Real Session
              </h2>
              <p className="mt-2 text-sm text-text-muted">
                Pick a recent session or load one by ID, then choose which
                proposal or candidate to send into the workbench.
              </p>
            </div>
          </div>

          <div className="space-y-5">
            <label className="block space-y-2">
              <span className="text-xs font-bold uppercase tracking-widest text-text-muted">
                Session ID
              </span>
              <div className="flex gap-3">
                <input
                  value={sessionId}
                  onChange={(event) => setSessionId(event.target.value)}
                  placeholder="proj_abc123"
                  className="w-full rounded-2xl border border-border/45 bg-surface-alt/80 p-4 text-text-body outline-none transition-all duration-300 placeholder:text-text-muted/45 focus:border-primary focus:ring-2 focus:ring-primary/30"
                />
                <button
                  type="button"
                  onClick={() => void loadSession(sessionId)}
                  disabled={!sessionId.trim() || isLoading('getSession')}
                  className={cn(
                    'rounded-2xl px-5 py-3 text-sm font-bold transition-all duration-300',
                    sessionId.trim()
                      ? 'bg-primary/15 text-primary border border-primary/25 hover:bg-primary/20'
                      : 'bg-white/5 text-text-muted cursor-not-allowed'
                  )}
                >
                  Load
                </button>
              </div>
            </label>

            {recentSessions.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-text-muted">
                    Recent Sessions
                  </span>
                  <button
                    type="button"
                    onClick={() => void loadRecentSessions()}
                    className="text-xs font-bold uppercase tracking-widest text-primary"
                  >
                    Refresh
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {recentSessions.map((session) => (
                    <button
                      key={session.session_id}
                      type="button"
                      onClick={() => void loadSession(session.session_id)}
                      className={cn(
                        'rounded-2xl border px-4 py-4 text-left transition-all duration-300',
                        selectedSession?.session_id === session.session_id
                          ? 'border-primary/40 bg-primary/10'
                          : 'border-white/5 bg-white/5 hover:bg-white/10'
                      )}
                    >
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-primary">
                          {session.session_id}
                        </span>
                        <span className="text-[10px] uppercase tracking-wider text-text-muted">
                          {session.status}
                        </span>
                      </div>
                      <p className="line-clamp-3 text-sm text-text-body">
                        {session.user_intent}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedSession && (
              <div className="space-y-4 rounded-2xl border border-white/5 bg-black/15 p-5">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-text-muted">
                    Loaded Session
                  </p>
                  <p className="mt-2 text-sm text-text-body">
                    {selectedSession.user_intent}
                  </p>
                </div>

                <div className="space-y-3">
                  <p className="text-xs font-bold uppercase tracking-widest text-text-muted">
                    {selectedSession.strawman_proposals.length > 0
                      ? 'Proposals'
                      : 'Candidate Plans'}
                  </p>
                  {selectedSession.strawman_proposals.length > 0 ? (
                    <div className="space-y-3">
                      {selectedSession.strawman_proposals.map((proposal) => (
                        <button
                          key={proposal.id}
                          type="button"
                          onClick={() => setSelectedProposalId(proposal.id)}
                          className={cn(
                            'w-full rounded-2xl border px-4 py-4 text-left transition-all duration-300',
                            selectedProposalId === proposal.id
                              ? 'border-primary/40 bg-primary/10'
                              : 'border-white/5 bg-white/5 hover:bg-white/10'
                          )}
                        >
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <p className="font-bold text-white">
                              {proposal.title}
                            </p>
                            <span className="font-mono text-[11px] uppercase tracking-wider text-primary">
                              {proposal.id}
                            </span>
                          </div>
                          <p className="text-sm text-text-muted">
                            {proposal.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  ) : selectedSession.candidate_plans.length > 0 ? (
                    <div className="space-y-3">
                      {selectedSession.candidate_plans.map((candidate) => (
                        <button
                          key={candidate.candidate_id}
                          type="button"
                          onClick={() =>
                            setSelectedCandidateId(candidate.candidate_id)
                          }
                          className={cn(
                            'w-full rounded-2xl border px-4 py-4 text-left transition-all duration-300',
                            selectedCandidateId === candidate.candidate_id
                              ? 'border-primary/40 bg-primary/10'
                              : 'border-white/5 bg-white/5 hover:bg-white/10'
                          )}
                        >
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <p className="font-bold text-white">
                              {candidate.title}
                            </p>
                            <span className="font-mono text-[11px] uppercase tracking-wider text-primary">
                              {candidate.status}
                            </span>
                          </div>
                          <p className="text-sm text-text-muted">
                            {candidate.summary}
                          </p>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-5 text-sm text-text-muted">
                      No proposals or candidate plans found for this session
                      yet.
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  disabled={!canLaunch}
                  onClick={() => setLaunched(true)}
                  className={cn(
                    'flex h-14 w-full items-center justify-center gap-2 rounded-2xl text-base font-bold transition-all duration-500',
                    canLaunch
                      ? 'bg-gradient-to-r from-primary to-cyan-300 text-slate-950 shadow-lg shadow-primary/25 hover:scale-[1.01] active:scale-100'
                      : 'cursor-not-allowed bg-white/5 text-text-muted opacity-50'
                  )}
                >
                  Open Workbench
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-border/40 bg-surface-alt/70 p-6 shadow-2xl sm:p-8">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-2xl bg-cyan-300/10 p-3 text-cyan-200">
              <SearchCode size={22} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Workflow</h2>
              <p className="mt-2 text-sm text-text-muted">
                The standalone workbench now pulls from real sessions instead of
                asking you to guess hidden IDs.
              </p>
            </div>
          </div>

          <div className="space-y-4 text-sm text-text-muted">
            <div className="rounded-2xl border border-white/5 bg-black/15 p-4">
              Choose a recent session or paste a session ID and load it.
            </div>
            <div className="rounded-2xl border border-white/5 bg-black/15 p-4">
              Pick one of the actual proposals generated for that session, or
              fall back to an existing candidate plan when proposals are absent.
            </div>
            <div className="rounded-2xl border border-white/5 bg-black/15 p-4">
              Launch the workbench and use the `Manual Plan`, `Evaluate`, and
              `Compare` tabs from there.
            </div>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/"
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-text-body transition-all hover:bg-white/10"
            >
              Create New Plan
            </Link>
            <Link
              to="/history"
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-text-body transition-all hover:bg-white/10"
            >
              Browse History
            </Link>
          </div>

          {selectedSession && selectedLaunchItem && (
            <div className="mt-8 rounded-2xl border border-primary/20 bg-primary/10 p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-bold text-white">
                  {selectedLaunchItem.kind === 'proposal'
                    ? 'Selected proposal'
                    : 'Selected candidate'}
                </p>
                <ExternalLink size={16} className="text-primary" />
              </div>
              <p className="text-sm font-semibold text-text-body">
                {selectedLaunchItem.title}
              </p>
              <p className="mt-2 text-sm text-text-muted">
                {selectedLaunchItem.description}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function getPreferredCandidate(plan: Plan): CandidatePlan | null {
  return (
    plan.candidate_plans.find(
      (candidate) => candidate.candidate_id === plan.approved_candidate_id
    ) ||
    plan.candidate_plans.find(
      (candidate) => candidate.candidate_id === plan.selected_candidate_id
    ) ||
    plan.candidate_plans[0] ||
    null
  );
}
