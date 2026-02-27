import React, { useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import { Plan } from '../types';
import {
  HelpCircle,
  Send,
  MessageSquare,
  Loader2
} from 'lucide-react';
import { cn } from '../utils';

interface QuestionPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

export function QuestionPanel({ plan, onUpdated }: QuestionPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const { answerQuestions, isLoading, error } = usePlanApi();
  const { error: showError } = useToast();

  const openQuestions = plan.open_questions?.filter((q) => !q.answered) || [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (Object.keys(answers).length === 0) return;

    try {
      await answerQuestions(plan.session_id, answers);
      onUpdated();
    } catch (error) {
      showError('Failed to submit answer. Please try again.');
    }
  }

  const submitting = isLoading('answerQuestions');

  return (
    <div className="p-8 rounded-3xl bg-surface border border-primary/20 shadow-2xl glassmorphism animate-in zoom-in-95 duration-500">
      <div className="flex items-center gap-4 mb-8">
        <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
          <HelpCircle size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Clarification Required</h2>
          <p className="text-text-muted font-medium">The planner needs more information to weave an accurate strategy.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {openQuestions.map((q) => (
          <div key={q.id} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-primary" />
              <label className="text-sm font-bold text-text-body leading-tight">
                {q.question}
              </label>
            </div>
            <textarea
              className="w-full bg-surface-alt border border-white/5 rounded-2xl p-4 text-text-body text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all duration-300 min-h-[100px] placeholder:text-white/10"
              placeholder="Provide context or answer here..."
              value={answers[q.id] || ''}
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
            />
          </div>
        ))}

        {error && (
          <div className="p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2">
            <MessageSquare size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || Object.keys(answers).length < openQuestions.length}
          className={cn(
            "w-full h-14 rounded-2xl font-bold text-base flex items-center justify-center gap-2 transition-all duration-300",
            (submitting || Object.keys(answers).length < openQuestions.length)
              ? "bg-white/5 text-text-muted opacity-50 cursor-not-allowed"
              : "bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/20"
          )}
        >
          {submitting ? (
            <Loader2 className="animate-spin" />
          ) : (
            <>
              Submit Implementation Context
              <Send size={18} />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
