import { useCallback, useEffect, useRef, useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan, PlanStatus } from '../types';
import { QuestionPanel } from './QuestionPanel';
import { ProposalPanel } from './ProposalPanel';
import { ExecutionPanel } from './ExecutionPanel';
import { colors, sharedStyles } from '../styles/ui';

interface PlanViewProps {
  sessionId: string;
}

const POLL_BASE_MS = 3000;
const POLL_MAX_MS = 30000;

export function PlanView({ sessionId }: PlanViewProps) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const { getSession, loading, error } = usePlanApi();
  const pollTimerRef = useRef<number | null>(null);

  const loadPlan = useCallback(async () => {
    try {
      const p = await getSession(sessionId);
      setPlan(p);
      return true;
    } catch {
      return false;
    }
  }, [getSession, sessionId]);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  useEffect(() => {
    if (plan?.status !== 'EXECUTING') {
      return;
    }

    let stopped = false;
    let consecutiveFailures = 0;

    const clearPending = () => {
      if (pollTimerRef.current !== null) {
        window.clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const nextDelay = () =>
      Math.min(POLL_BASE_MS * 2 ** consecutiveFailures, POLL_MAX_MS);

    const schedule = (delayMs: number) => {
      clearPending();
      if (stopped || document.visibilityState === 'hidden') {
        return;
      }
      pollTimerRef.current = window.setTimeout(() => {
        void runPoll();
      }, delayMs);
    };

    const runPoll = async () => {
      if (stopped || document.visibilityState === 'hidden') {
        return;
      }
      const ok = await loadPlan();
      consecutiveFailures = ok ? 0 : Math.min(consecutiveFailures + 1, 4);
      schedule(nextDelay());
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        consecutiveFailures = 0;
        void runPoll();
      } else {
        clearPending();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    schedule(POLL_BASE_MS);

    return () => {
      stopped = true;
      clearPending();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [plan?.status, loadPlan]);

  function handleUpdate() {
    void loadPlan();
  }

  if (loading && !plan) {
    return (
      <div style={styles.loading}>
        <div style={styles.spinner} />
        <p>Loading plan...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.error}>
        <p>Error loading plan: {error}</p>
      </div>
    );
  }

  if (!plan) {
    return null;
  }

  const stage = getPlanStage(plan);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Plan: {plan.session_id}</h1>
        <span style={{...styles.status, backgroundColor: getStatusColor(plan.status)}}>
          {plan.status}
        </span>
      </div>

      <div style={styles.intent}>
        <h3 style={styles.intentLabel}>Your Request</h3>
        <p style={styles.intentText}>{plan.user_intent}</p>
      </div>

      {plan.locked_constraints && Object.keys(plan.locked_constraints).length > 0 && (
        <div style={styles.constraints}>
          <h4 style={styles.constraintsLabel}>Locked Constraints</h4>
          <div style={styles.constraintsList}>
            {Object.entries(plan.locked_constraints).map(([key, value]) => (
              <span key={key} style={styles.constraint}>{key}: {String(value)}</span>
            ))}
          </div>
        </div>
      )}

      {stage === 'questions' && plan.open_questions && (
        <QuestionPanel plan={plan} onUpdated={handleUpdate} />
      )}

      {stage === 'proposals' && (
        <ProposalPanel plan={plan} onSelected={handleUpdate} />
      )}

      {(stage === 'execution' || stage === 'completed') && plan.execution_graph && (
        <ExecutionPanel plan={plan} onUpdated={handleUpdate} />
      )}

      {stage === 'completed' && plan.final_output && (
        <div style={styles.result}>
          <h3 style={styles.resultTitle}>Final Output</h3>
          <pre style={styles.resultPre}>{JSON.stringify(plan.final_output, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

type PlanStage = 'questions' | 'proposals' | 'execution' | 'completed';

function getPlanStage(plan: Plan): PlanStage {
  const unansweredQuestions = plan.open_questions?.some((q) => !q.answered);
  const hasProposals = (plan.strawman_proposals?.length ?? 0) > 0;
  const hasExecutionGraph = (plan.execution_graph?.length ?? 0) > 0;
  const isTerminal = plan.status === 'COMPLETED' || plan.status === 'FAILED';

  if (isTerminal) return 'completed';
  if (hasExecutionGraph) return 'execution';
  if (hasProposals) return 'proposals';
  if (unansweredQuestions) return 'questions';
  return 'execution';
}

function getStatusColor(status: PlanStatus) {
  switch (status) {
    case 'BRAINSTORMING': return colors.warning;
    case 'AWAITING_APPROVAL': return colors.info;
    case 'APPROVED': return colors.success;
    case 'EXECUTING': return colors.violet;
    case 'COMPLETED': return colors.successSoft;
    case 'FAILED': return colors.danger;
    default: return colors.gray;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: sharedStyles.pageContainer,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    color: colors.text,
  },
  status: {
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    color: colors.text,
  },
  intent: {
    ...sharedStyles.panel,
    padding: '20px',
    marginBottom: '20px',
  },
  intentLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: colors.textMuted,
    textTransform: 'uppercase',
    marginBottom: '8px',
  },
  intentText: {
    color: colors.textBody,
    fontSize: '16px',
    lineHeight: '1.6',
  },
  constraints: {
    marginBottom: '20px',
  },
  constraintsLabel: {
    fontSize: '14px',
    fontWeight: '500',
    color: colors.textMuted,
    marginBottom: '8px',
  },
  constraintsList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  constraint: {
    padding: '4px 10px',
    borderRadius: '4px',
    backgroundColor: colors.borderMuted,
    color: colors.textBody,
    fontSize: '13px',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px',
    color: colors.textMuted,
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: `3px solid ${colors.borderMuted}`,
    borderTopColor: colors.primary,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '16px',
  },
  error: { ...sharedStyles.errorBox, padding: '24px' },
  result: {
    marginTop: '24px',
    backgroundColor: colors.surface,
    borderRadius: '12px',
    padding: '24px',
  },
  resultTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: colors.text,
    marginBottom: '16px',
  },
  resultPre: {
    backgroundColor: colors.surfaceMuted,
    padding: '16px',
    borderRadius: '8px',
    color: '#9ca3af',
    fontSize: '13px',
    overflow: 'auto',
    maxHeight: '400px',
  },
};
