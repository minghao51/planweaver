import { usePlanApi } from '../hooks/useApi';
import { Plan } from '../types';
import { colors, disabledStyle, sharedStyles } from '../styles/ui';

interface ExecutionPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

export function ExecutionPanel({ plan, onUpdated }: ExecutionPanelProps) {
  const { approvePlan, executePlan, isLoading, error } = usePlanApi();

  async function handleApprove() {
    try {
      await approvePlan(plan.session_id);
      onUpdated();
    } catch {}
  }

  async function handleExecute() {
    try {
      await executePlan(plan.session_id);
      onUpdated();
    } catch {}
  }

  const completedSteps = plan.execution_graph?.filter((s) => s.status === 'COMPLETED').length || 0;
  const totalSteps = plan.execution_graph?.length || 0;
  const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
  const approving = isLoading('approvePlan');
  const executing = isLoading('executePlan');

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Execution Plan</h2>
        <span style={styles.stepCount}>{completedSteps}/{totalSteps} steps</span>
      </div>

      <div style={styles.progressBar}>
        <div style={{...styles.progressFill, width: `${progress}%`}} />
      </div>

      <div style={styles.steps}>
        {plan.execution_graph?.map((step) => (
          <div key={step.step_id} style={{...styles.step, opacity: step.status === 'PENDING' ? 0.5 : 1}}>
            <div style={styles.stepStatus}>
              {step.status === 'COMPLETED' && <span style={styles.check}>✓</span>}
              {step.status === 'IN_PROGRESS' && <span style={styles.spinner}>⟳</span>}
              {step.status === 'PENDING' && <span style={styles.pending}>{step.step_id}</span>}
              {step.status === 'FAILED' && <span style={styles.fail}>✗</span>}
            </div>
            <div style={styles.stepContent}>
              <span style={styles.stepTask}>{step.task}</span>
              <span style={styles.stepModel}>{step.assigned_model}</span>
            </div>
            {step.output && (
              <div style={styles.stepOutput}>
                <pre style={styles.pre}>{step.output}</pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.actions}>
        {plan.status === 'AWAITING_APPROVAL' && (
          <button
            style={{
              ...styles.button,
              backgroundColor: colors.success,
              ...disabledStyle(approving),
            }}
            onClick={handleApprove}
            disabled={approving}
          >
            Approve & Execute
          </button>
        )}
        {plan.status === 'EXECUTING' && (
          <button
            style={{
              ...styles.button,
              backgroundColor: colors.primary,
              ...disabledStyle(executing),
            }}
            onClick={handleExecute}
            disabled={executing}
          >
            {executing ? 'Executing...' : 'Continue Execution'}
          </button>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: sharedStyles.panel,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: colors.text,
  },
  stepCount: {
    color: colors.textMuted,
    fontSize: '14px',
  },
  progressBar: {
    height: '6px',
    backgroundColor: colors.borderMuted,
    borderRadius: '3px',
    marginBottom: '20px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.primary,
    transition: 'width 0.3s ease',
  },
  steps: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginBottom: '20px',
  },
  step: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: colors.surfaceAlt,
  },
  stepStatus: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  check: {
    color: colors.success,
    fontSize: '14px',
    fontWeight: 'bold',
  },
  spinner: {
    color: colors.primary,
    fontSize: '16px',
    animation: 'spin 1s linear infinite',
  },
  pending: {
    color: colors.gray,
    fontSize: '12px',
    fontWeight: '600',
  },
  fail: {
    color: colors.danger,
    fontSize: '14px',
    fontWeight: 'bold',
  },
  stepContent: {
    flex: 1,
  },
  stepTask: {
    display: 'block',
    color: colors.textBody,
    fontSize: '14px',
    marginBottom: '4px',
  },
  stepModel: {
    display: 'block',
    color: colors.gray,
    fontSize: '12px',
  },
  stepOutput: {
    marginTop: '8px',
    padding: '8px',
    backgroundColor: colors.surfaceMuted,
    borderRadius: '4px',
  },
  pre: {
    margin: 0,
    color: '#9ca3af',
    fontSize: '12px',
    fontFamily: 'monospace',
    overflow: 'auto',
  },
  actions: {
    display: 'flex',
    gap: '12px',
  },
  error: { ...sharedStyles.errorBox, marginBottom: '16px' },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    color: colors.text,
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
};
