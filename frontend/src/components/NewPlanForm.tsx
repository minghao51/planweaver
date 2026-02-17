import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';

interface NewPlanFormProps {
  onPlanCreated: (sessionId: string) => void;
}

export function NewPlanForm({ onPlanCreated }: NewPlanFormProps) {
  const [intent, setIntent] = useState('');
  const [scenario, setScenario] = useState('');
  const [scenarios, setScenarios] = useState<string[]>([]);
  const { createSession, loading, error } = usePlanApi();

  useEffect(() => {
    loadScenarios();
  }, []);

  async function loadScenarios() {
    try {
      const list = await new Promise<string[]>((resolve) => {
        setTimeout(() => resolve(['Code Refactoring', 'Market Competitor Analysis', 'Blog Post Generation', 'Data Analysis Report']), 100);
      });
      setScenarios(list);
    } catch (e) {
      console.error('Failed to load scenarios');
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!intent.trim()) return;

    try {
      const result = await createSession(intent, scenario || undefined);
      onPlanCreated(result.session_id);
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  }

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
          style={{...styles.button, opacity: loading || !intent.trim() ? 0.5 : 1}}
          disabled={loading || !intent.trim()}
        >
          {loading ? 'Creating...' : 'Start Planning'}
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
    color: '#fff',
    marginBottom: '8px',
  },
  subtitle: {
    color: '#a0a0b0',
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
    color: '#e0e0e0',
    fontSize: '14px',
    fontWeight: '500',
  },
  textarea: {
    padding: '16px',
    borderRadius: '8px',
    border: '1px solid #3d3d5c',
    backgroundColor: '#16162a',
    color: '#fff',
    fontSize: '16px',
    resize: 'vertical',
    minHeight: '120px',
  },
  select: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #3d3d5c',
    backgroundColor: '#16162a',
    color: '#fff',
    fontSize: '16px',
  },
  error: {
    padding: '12px 16px',
    borderRadius: '8px',
    backgroundColor: '#2d1f1f',
    color: '#ff6b6b',
    fontSize: '14px',
  },
  button: {
    padding: '14px 24px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#6366f1',
    color: '#fff',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    marginTop: '8px',
  },
};
