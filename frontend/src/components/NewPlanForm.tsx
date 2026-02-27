import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import {
  PlusCircle,
  Sparkles,
  ChevronRight,
  Loader2,
  Search,
  FileText
} from 'lucide-react';
import { cn } from '../utils';

interface NewPlanFormProps {
  onPlanCreated: (sessionId: string) => void;
}

export function NewPlanForm({ onPlanCreated }: NewPlanFormProps) {
  const [intent, setIntent] = useState('');
  const [scenario, setScenario] = useState('');
  const [scenarios, setScenarios] = useState<string[]>([]);
  const { createSession, listScenarios, isLoading, error } = usePlanApi();
  const { error: showError, success: showSuccess } = useToast();

  useEffect(() => {
    void loadScenarios();
  }, [listScenarios]);

  async function loadScenarios() {
    try {
      setScenarios(await listScenarios());
    } catch (error) {
      showError('Failed to load scenarios.');
      setScenarios([]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!intent.trim()) return;

    try {
      const result = await createSession(intent, scenario || undefined);
      showSuccess('Plan created successfully!');
      onPlanCreated(result.session_id);
    } catch (error) {
      showError('Failed to create plan. Please try again.');
    }
  }

  const submitting = isLoading('createSession');
  const submitDisabled = submitting || !intent.trim();

  return (
    <div className="max-w-4xl mx-auto space-y-12 py-8 sm:py-12 animate-in fade-in duration-700">
      <div className="text-center space-y-5">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-teal-300/20 text-primary mb-2 shadow-[0_14px_34px_-18px_rgba(56,189,248,0.9)]">
          <PlusCircle size={28} />
        </div>
        <h1 className="font-heading text-4xl font-bold tracking-tight text-white lg:text-6xl">
          Start a new <span className="text-primary">Plan</span>
        </h1>
        <p className="text-text-muted text-lg max-w-2xl mx-auto">
          Describe your objective, and PlanWeaver's dual-LLM engine will weave an execution strategy.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 p-6 sm:p-8 rounded-[28px] bg-surface border border-border/40 shadow-2xl glassmorphism">
        <div className="space-y-4">
          <label className="text-xs font-bold uppercase tracking-widest text-text-muted flex items-center gap-2">
            <Sparkles size={14} className="text-primary" />
            Core Intent
          </label>
          <textarea
            className="w-full bg-surface-alt/80 border border-border/45 rounded-2xl p-6 text-text-body text-lg focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all duration-300 min-h-[160px] placeholder:text-text-muted/45"
            placeholder="e.g., Architect a microservices deployment on AWS using Terraform..."
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
          />
        </div>

        <div className="space-y-4">
          <label className="text-xs font-bold uppercase tracking-widest text-text-muted flex items-center gap-2">
            <FileText size={14} className="text-primary" />
            Scenario Template
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setScenario('')}
              className={cn(
                "p-4 rounded-xl border text-left transition-all duration-200",
                scenario === ''
                  ? "bg-primary/15 border-primary/70 text-primary"
                  : "bg-surface-alt/80 border-border/45 text-text-muted hover:bg-white/5"
              )}
            >
              <div className="font-bold text-sm">Auto-detect</div>
              <div className="text-[10px] opacity-60">Let the planner choose the best scenario</div>
            </button>
            {scenarios.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setScenario(s)}
                className={cn(
                  "p-4 rounded-xl border text-left transition-all duration-200",
                  scenario === s
                    ? "bg-primary/15 border-primary/70 text-primary"
                    : "bg-surface-alt/80 border-border/45 text-text-muted hover:bg-white/5"
                )}
              >
                <div className="font-bold text-sm uppercase tracking-tighter">{s.replace('_', ' ')}</div>
                <div className="text-[10px] opacity-60">Specific workflow for {s}</div>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2 animate-pulse">
            <Search size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitDisabled}
          className={cn(
            "w-full h-16 rounded-2xl font-bold text-lg flex items-center justify-center gap-2 transition-all duration-500",
            submitDisabled
              ? "bg-white/5 text-text-muted opacity-50 cursor-not-allowed"
              : "bg-gradient-to-r from-primary to-cyan-300 hover:to-cyan-200 text-slate-950 shadow-lg shadow-primary/25 hover:scale-[1.01] active:scale-100"
          )}
        >
          {submitting ? (
            <Loader2 className="animate-spin" />
          ) : (
            <>
              Commence Planning
              <ChevronRight size={20} />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
