import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import { Plan } from '../types';
import {
  CheckCircle2,
  PlayCircle,
  AlertCircle,
  ChevronRight,
  Cpu
} from 'lucide-react';
import { cn } from '../utils';
import { getStepStyles } from '../lib/statusStyles';

interface ExecutionPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

export function ExecutionPanel({ plan, onUpdated }: ExecutionPanelProps) {
  const { approvePlan, executePlan, isLoading, error } = usePlanApi();
  const { error: showError } = useToast();

  async function handleApprove() {
    try {
      await approvePlan(plan.session_id);
      onUpdated();
    } catch (error) {
      showError('Failed to approve plan. Please try again.');
    }
  }

  async function handleExecute() {
    try {
      await executePlan(plan.session_id);
      onUpdated();
    } catch (error) {
      showError('Failed to execute plan. Please try again.');
    }
  }

  const completedSteps = plan.execution_graph?.filter((s) => s.status === 'COMPLETED').length || 0;
  const totalSteps = plan.execution_graph?.length || 0;
  const approving = isLoading('approvePlan');
  const executing = isLoading('executePlan');

  return (
    <div className="flex flex-col gap-6 animate-in slide-in-from-right-4 duration-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Cpu size={20} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Step Manifest</h2>
            <p className="text-xs text-text-muted font-medium uppercase tracking-wider">{completedSteps} of {totalSteps} completed</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {plan.status === 'AWAITING_APPROVAL' && (
            <button
              className={cn(
                "px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-300 flex items-center gap-2",
                approving
                  ? "bg-white/5 text-text-muted opacity-50 cursor-not-allowed"
                  : "bg-success hover:bg-success/90 text-white shadow-lg shadow-success/20 hover:scale-[1.02]"
              )}
              onClick={handleApprove}
              disabled={approving}
            >
              {approving ? <Cpu className="w-4 h-4 animate-spin" /> : <CheckCircle2 size={16} />}
              Approve Design
            </button>
          )}
          {plan.status === 'EXECUTING' && (
            <button
              className={cn(
                "px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-300 flex items-center gap-2",
                executing
                  ? "bg-white/5 text-text-muted opacity-50 cursor-not-allowed"
                  : "bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/20 hover:scale-[1.02]"
              )}
              onClick={handleExecute}
              disabled={executing}
            >
              {executing ? <Cpu className="w-4 h-4 animate-spin" /> : <PlayCircle size={16} />}
              Continue Weave
            </button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {plan.execution_graph?.map((step) => (
          <div
            key={step.step_id}
            className={cn(
              "group p-4 rounded-2xl border transition-all duration-300",
              getStepStyles(step.status).container
            )}
          >
            <div className="flex items-start gap-4">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center shrink-0 border transition-transform duration-500 group-hover:scale-110",
                getStepStyles(step.status, step.step_id).iconContainer
              )}>
                {renderStepIcon(step.status, step.step_id)}
              </div>

              <div className="flex-1 min-w-0 py-1">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-sm font-bold text-white truncate group-hover:text-primary transition-colors cursor-default">
                    {step.task}
                  </h4>
                  <span className="text-[10px] bg-black/20 px-2 py-0.5 rounded-full font-mono text-text-muted">
                    {step.assigned_model.split('/').pop()}
                  </span>
                </div>

                {step.status === 'IN_PROGRESS' && (
                  <div className="h-1 w-full bg-primary/20 rounded-full overflow-hidden mt-2">
                    <div className="h-full bg-primary animate-[shimmer_2s_infinite] w-1/3" />
                  </div>
                )}
              </div>

              <ChevronRight size={16} className="text-white/10 mt-2" />
            </div>

            {step.output && (
              <div className="mt-4 p-4 rounded-xl bg-black/40 border border-white/5 font-mono text-xs text-text-muted overflow-auto max-h-48 scrollbar-hide">
                <pre>{step.output}</pre>
              </div>
            )}

            {step.error && (
              <div className="mt-4 p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-xs font-medium flex items-center gap-2">
                <AlertCircle size={14} />
                {step.error}
              </div>
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}
    </div>
  );
}

function renderStepIcon(status: string, stepId?: number) {
  const styles = getStepStyles(status, stepId);
  switch (styles.iconLabel) {
    case 'spinner':
      return <Cpu className="w-5 h-5 animate-spin" />;
    case 'check':
      return <CheckCircle2 size={16} />;
    case 'alert':
      return <AlertCircle size={16} />;
    default:
      return <span className="text-xs font-bold font-mono opacity-40">{styles.iconLabel}</span>;
  }
}

