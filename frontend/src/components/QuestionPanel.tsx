import { useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan } from '../types';

interface QuestionPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

export function QuestionPanel({ plan, onUpdated }: QuestionPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const { answerQuestions, loading } = usePlanApi();

  const unansweredQuestions = plan.open_questions?.filter((q) => !q.answered) || [];

  async function handleSubmit() {
    await answerQuestions(plan.session_id, answers);
    onUpdated();
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Clarifying Questions</h2>
      <p style={styles.subtitle}>Help us understand your requirements better.</p>

      <div style={styles.questions}>
        {unansweredQuestions.map((q) => (
          <div key={q.id} style={styles.question}>
            <label style={styles.label}>{q.question}</label>
            <input
              style={styles.input}
              placeholder="Your answer..."
              value={answers[q.id] || ''}
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
            />
          </div>
        ))}
      </div>

      {unansweredQuestions.length > 0 && (
        <button
          style={{...styles.button, opacity: loading ? 0.5 : 1}}
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Submitting...' : 'Submit Answers'}
        </button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: '#1e1e36',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '24px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#fff',
    marginBottom: '4px',
  },
  subtitle: {
    color: '#a0a0b0',
    fontSize: '14px',
    marginBottom: '20px',
  },
  questions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginBottom: '20px',
  },
  question: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    color: '#e0e0e0',
    fontSize: '14px',
    fontWeight: '500',
  },
  input: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #3d3d5c',
    backgroundColor: '#16162a',
    color: '#fff',
    fontSize: '14px',
  },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#6366f1',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
};
