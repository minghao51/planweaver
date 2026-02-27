import { useCallback, useEffect, useState } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { useSSE } from '../hooks/useSSE';
import { Plan } from '../types';
import { QuestionPanel } from './QuestionPanel';
import { ProposalPanel } from './ProposalPanel';
import { ExecutionPanel } from './ExecutionPanel';
import { FlowCanvas } from './FlowCanvas';
import { OptimizerStage } from './optimizer';
import {
  Target,
  Settings2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  Zap
} from 'lucide-react';
import { cn } from '../utils';
import { getStatusStyles } from '../lib/statusStyles';

interface PlanViewProps {
  sessionId: string;
}

export function PlanView({ sessionId }: PlanViewProps) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [showOptimizer, setShowOptimizer] = useState(false);
  const [selectedProposalForOptimizer, setSelectedProposalForOptimizer] = useState<{
    id: string;
    title: string;
    description: string;
  } | null>(null);
  const { getSession, selectProposal, loading, error } = usePlanApi();

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

  // Use SSE for real-time updates during execution
  useSSE(sessionId, {
    onConnected: () => {
      console.log('SSE connected for session', sessionId);
    },
    onStepCompleted: () => {
      // Reload plan when a step completes
      void loadPlan();
    },
    onStepFailed: () => {
      // Reload plan when a step fails
      void loadPlan();
    },
    onExecutionComplete: () => {
      // Final reload when execution completes
      void loadPlan();
    },
    onExecutionFailed: () => {
      // Reload plan when execution fails
      void loadPlan();
    },
    onError: (data) => {
      console.error('SSE error:', data.message);
    },
  });

  function handleUpdate() {
    void loadPlan();
  }

  if (loading && !plan) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
        <Loader2 className="w-10 h-10 text-primary animate-spin mb-4" />
        <p className="text-text-muted font-medium">Initializing orchestrator...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-danger/10 border border-danger/20 text-danger flex items-center gap-3">
        <AlertCircle size={20} />
        <p>Error in session {sessionId}: {error}</p>
      </div>
    );
  }

  if (!plan) return null;

  const stage = getPlanStage(plan);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in slide-in-from-bottom-4 duration-700">
      {/* Sidebar: Info & Constraints */}
      <div className="lg:col-span-4 flex flex-col gap-6">
        <div className="p-6 rounded-2xl bg-surface border border-white/5 shadow-xl glassmorphism">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Target className="text-primary" size={20} />
              Session Plan
            </h2>
            <div className={cn(
              "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border",
              getStatusStyles(plan.status)
            )}>
              {plan.status}
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-2">Intent</label>
              <p className="text-text-body leading-relaxed bg-white/5 p-4 rounded-xl border border-white/5 italic">
                "{plan.user_intent}"
              </p>
            </div>

            {plan.locked_constraints && Object.keys(plan.locked_constraints).length > 0 && (
              <div>
                <label className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-2">Constraints</label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(plan.locked_constraints).map(([key, value]) => (
                    <span key={key} className="px-3 py-1.5 rounded-lg bg-surface-alt border border-white/5 text-xs text-text-body flex items-center gap-2">
                      <Settings2 size={12} className="text-primary" />
                      <span className="font-medium opacity-60">{key}:</span> {String(value)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Progress Card */}
        <div className="p-6 rounded-2xl bg-surface border border-white/5 shadow-xl glassmorphism">
          <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted mb-4 flex items-center gap-2">
            <Zap size={16} className="text-warning" />
            Execution Pulse
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-bold uppercase tracking-tighter">
              <span>Overall Completion</span>
              <span className="text-primary">{getCompletionPercentage(plan)}%</span>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
              <div
                className="h-full bg-primary shadow-[0_0_10px_rgba(99,102,241,0.5)] transition-all duration-1000"
                style={{ width: `${getCompletionPercentage(plan)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content: Steps and Visualizer */}
      <div className="lg:col-span-8 flex flex-col gap-6">
        <div className="flex items-center gap-4 mb-2">
          <div className={cn(
            "h-3 w-3 rounded-full",
            stage === 'completed' ? "bg-success" : "bg-primary animate-pulse"
          )} />
          <h2 className="text-2xl font-bold tracking-tight">
            {stage.charAt(0).toUpperCase() + stage.slice(1)} Stage
          </h2>
          <ChevronRight size={20} className="text-white/20" />
          <span className="text-text-muted font-medium">Session {sessionId}</span>
        </div>

        {stage === 'questions' && plan.open_questions && (
          <QuestionPanel plan={plan} onUpdated={handleUpdate} />
        )}

        {stage === 'proposals' && !showOptimizer && (
          <ProposalPanel
            plan={plan}
            onSelected={() => {
              // Find selected proposal
              const selected = plan.strawman_proposals?.find(p => p.selected);
              if (selected) {
                setSelectedProposalForOptimizer({
                  id: selected.id,
                  title: selected.title,
                  description: selected.description,
                });
                setShowOptimizer(true);
              }
              handleUpdate();
            }}
          />
        )}

        {showOptimizer && selectedProposalForOptimizer && (
          <OptimizerStage
            sessionId={sessionId}
            selectedProposalId={selectedProposalForOptimizer.id}
            selectedProposalTitle={selectedProposalForOptimizer.title}
            selectedProposalDescription={selectedProposalForOptimizer.description}
            onComplete={async (optimizedPlanId) => {
              // Move to execution by selecting the optimized plan
              await selectProposal(sessionId, optimizedPlanId);
              setShowOptimizer(false);
              handleUpdate();
            }}
            onBack={() => {
              setShowOptimizer(false);
            }}
          />
        )}

        {(stage === 'execution' || stage === 'completed') && (
          <div className="flex flex-col gap-6">
            <FlowCanvas steps={plan.execution_graph || []} />
            <ExecutionPanel plan={plan} onUpdated={handleUpdate} />
          </div>
        )}

        {stage === 'completed' && plan.final_output && (
          <div className="p-8 rounded-2xl bg-surface-alt border border-success/20 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <CheckCircle2 size={120} className="text-success" />
            </div>
            <h3 className="text-xl font-bold text-success mb-6 flex items-center gap-2">
              <CheckCircle2 size={24} />
              Solution Reached
            </h3>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5 font-mono text-sm overflow-auto max-h-[500px]">
              <pre className="text-text-body">{JSON.stringify(plan.final_output, null, 2)}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function getCompletionPercentage(plan: Plan) {
  if (!plan.execution_graph || plan.execution_graph.length === 0) return 0;
  const completed = plan.execution_graph.filter(s => s.status === 'COMPLETED').length;
  return Math.round((completed / plan.execution_graph.length) * 100);
}

type PlanStage = 'questions' | 'proposals' | 'execution' | 'completed' | 'optimizer';

function getPlanStage(plan: Plan): PlanStage {
  const unansweredQuestions = plan.open_questions?.some((q) => !q.answered);
  const hasProposals = (plan.strawman_proposals?.length ?? 0) > 0 && !plan.strawman_proposals?.some(p => p.selected);
  const hasExecutionGraph = (plan.execution_graph?.length ?? 0) > 0;
  const isTerminal = plan.status === 'COMPLETED' || plan.status === 'FAILED';

  if (isTerminal) return 'completed';
  if (hasExecutionGraph) return 'execution';
  if (hasProposals) return 'proposals';
  if (unansweredQuestions) return 'questions';
  return 'execution';
}

