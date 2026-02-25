import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { colors, disabledStyle, sharedStyles } from '../styles/ui';

interface NewPlanFormProps {
  onPlanCreated: (sessionId: string) => void;
}

export function NewPlanForm({ onPlanCreated }: NewPlanFormProps) {
  const [intent, setIntent] = useState('');
  const [scenario, setScenario] = useState('');
  const [scenarios, setScenarios] = useState<string[]>([]);
  const { createSession, listScenarios, isLoading, error } = usePlanApi();

  useEffect(() => {
    void loadScenarios();
  }, [listScenarios]);

  async function loadScenarios() {
    try {
      setScenarios(await listScenarios());
    } catch {
      setScenarios([]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!intent.trim()) return;

    try {
      const result = await createSession(intent, scenario || undefined);
      onPlanCreated(result.session_id);
    } catch {}
  }

  const submitting = isLoading('createSession');
  const loadingScenarios = isLoading('listScenarios');
  const submitDisabled = submitting || !intent.trim();

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Create New Plan</h1>
      <p style={styles.subtitle}>Describe what you want to accomplish, and PlanWeaver will create an execution strategy.</p>

      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.field}>
          <label style={styles.label}>What do you want to accomplish?</label>
          <textarea
            style={styles.textarea}
            placeholder="e.g., Refactor my Python CLI tool into a FastAPI service with tests..."
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            rows={4}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Scenario (optional)</label>
          <select
            style={styles.select}
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            disabled={loadingScenarios}
          >
            <option value="">Auto-detect from request</option>
            {scenarios.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <button
          type="submit"
          style={{ ...styles.button, ...disabledStyle(submitDisabled) }}
          disabled={submitDisabled}
        >
          {submitting ? 'Creating...' : 'Start Planning'}
        </button>
      </form>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '700px',
    margin: '0 auto',
    padding: '40px 24px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '600',
    color: colors.text,
    marginBottom: '8px',
  },
  subtitle: {
    color: colors.textMuted,
    marginBottom: '32px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    ...sharedStyles.fieldLabel,
  },
  textarea: {
    padding: '16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    fontSize: '16px',
    resize: 'vertical',
    minHeight: '120px',
  },
  select: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    fontSize: '16px',
  },
  error: sharedStyles.errorBox,
  button: {
    padding: '14px 24px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: colors.primary,
    color: colors.text,
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    marginTop: '8px',
  },
};
