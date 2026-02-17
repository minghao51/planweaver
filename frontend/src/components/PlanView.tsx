import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan } from '../types';
import { QuestionPanel } from './QuestionPanel';
import { ProposalPanel } from './ProposalPanel';
import { ExecutionPanel } from './ExecutionPanel';

interface PlanViewProps {
  sessionId: string;
}

export function PlanView({ sessionId }: PlanViewProps) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [view, setView] = useState<'loading' | 'questions' | 'proposals' | 'execution' | 'completed'>('loading');
  const { getSession, loading, error } = usePlanApi();

  useEffect(() => {
    loadPlan();
  }, [sessionId]);

  async function loadPlan() {
    try {
      const p = await getSession(sessionId);
      setPlan(p);
      updateView(p);
    } catch (e) {
      console.error('Failed to load plan');
    }
  }

  function updateView(p: Plan) {
    const unansweredQuestions = p.open_questions?.filter((q) => !q.answered).length || 0;
    if (p.status === 'COMPLETED' || p.status === 'FAILED') {
      setView('completed');
    } else if (p.execution_graph && p.execution_graph.length > 0 && p.status === 'APPROVED') {
      setView('execution');
    } else if (p.strawman_proposals && p.strawman_proposals.length > 0) {
      setView('proposals');
    } else if (unansweredQuestions > 0) {
      setView('questions');
    } else if (p.execution_graph && p.execution_graph.length > 0) {
      setView('execution');
    }
  }

  function handleUpdate() {
    loadPlan();
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

      {view === 'questions' && plan.open_questions && (
        <QuestionPanel plan={plan} onUpdated={handleUpdate} />
      )}

      {view === 'proposals' && (
        <ProposalPanel plan={plan} onSelected={handleUpdate} />
      )}

      {(view === 'execution' || view === 'completed') && plan.execution_graph && (
        <ExecutionPanel plan={plan} onUpdated={handleUpdate} />
      )}

      {view === 'completed' && plan.final_output && (
        <div style={styles.result}>
          <h3 style={styles.resultTitle}>Final Output</h3>
          <pre style={styles.resultPre}>{JSON.stringify(plan.final_output, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

function getStatusColor(status: string) {
  switch (status) {
    case 'BRAINSTORMING': return '#f59e0b';
    case 'AWAITING_APPROVAL': return '#3b82f6';
    case 'APPROVED': return '#22c55e';
    case 'EXECUTING': return '#8b5cf6';
    case 'COMPLETED': return '#10b981';
    case 'FAILED': return '#ef4444';
    default: return '#6b7280';
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    color: '#fff',
  },
  status: {
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#fff',
  },
  intent: {
    backgroundColor: '#1e1e36',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '20px',
  },
  intentLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#a0a0b0',
    textTransform: 'uppercase',
    marginBottom: '8px',
  },
  intentText: {
    color: '#e0e0e0',
    fontSize: '16px',
    lineHeight: '1.6',
  },
  constraints: {
    marginBottom: '20px',
  },
  constraintsLabel: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#a0a0b0',
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
    backgroundColor: '#2d2d44',
    color: '#e0e0e0',
    fontSize: '13px',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px',
    color: '#a0a0b0',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #2d2d44',
    borderTopColor: '#6366f1',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '16px',
  },
  error: {
    padding: '24px',
    backgroundColor: '#2d1f1f',
    borderRadius: '8px',
    color: '#ff6b6b',
  },
  result: {
    marginTop: '24px',
    backgroundColor: '#1e1e36',
    borderRadius: '12px',
    padding: '24px',
  },
  resultTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#fff',
    marginBottom: '16px',
  },
  resultPre: {
    backgroundColor: '#0f0f1a',
    padding: '16px',
    borderRadius: '8px',
    color: '#9ca3af',
    fontSize: '13px',
    overflow: 'auto',
    maxHeight: '400px',
  },
};
