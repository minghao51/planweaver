import { useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan } from '../types';
import { colors, disabledStyle, sharedStyles } from '../styles/ui';

interface QuestionPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

export function QuestionPanel({ plan, onUpdated }: QuestionPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const { answerQuestions, isLoading, error } = usePlanApi();

  const unansweredQuestions = plan.open_questions?.filter((q) => !q.answered) || [];

  async function handleSubmit() {
    try {
      await answerQuestions(plan.session_id, answers);
      onUpdated();
    } catch {}
  }

  const submitting = isLoading('answerQuestions');

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

      {error && <div style={styles.error}>{error}</div>}

      {unansweredQuestions.length > 0 && (
        <button
          style={{ ...styles.button, ...disabledStyle(submitting) }}
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? 'Submitting...' : 'Submit Answers'}
        </button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { ...sharedStyles.panel, marginBottom: '24px' },
  title: sharedStyles.sectionTitle,
  subtitle: sharedStyles.sectionSubtitle,
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
    ...sharedStyles.fieldLabel,
  },
  input: {
    ...sharedStyles.inputBase,
  },
  error: { ...sharedStyles.errorBox, marginBottom: '16px' },
  button: { ...sharedStyles.primaryButton, backgroundColor: colors.primary },
};
