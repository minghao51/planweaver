import { useEffect, useState } from 'react';
import {
  ArrowRightLeft,
  GitBranch,
  Pencil,
  Plus,
  RefreshCcw,
  Trash2,
  Wand2,
} from 'lucide-react';
import { usePlanApi } from '../hooks/useApi';
import { useToast } from '../hooks/useToast';
import { cn } from '../utils';
import type { CandidatePlan, ExecutionStep, Plan } from '../types';

interface CandidatePlanPanelProps {
  plan: Plan;
  onUpdated: () => void;
}

function getCurrentCandidate(plan: Plan): CandidatePlan | null {
  const preferredId = plan.approved_candidate_id || plan.selected_candidate_id;
  return (
    plan.candidate_plans.find(
      (candidate) => candidate.candidate_id === preferredId
    ) ||
    plan.candidate_plans[0] ||
    null
  );
}

export function CandidatePlanPanel({
  plan,
  onUpdated,
}: CandidatePlanPanelProps) {
  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(
    null
  );
  const [editStepId, setEditStepId] = useState<number | null>(null);
  const [editTask, setEditTask] = useState('');
  const [newStepTask, setNewStepTask] = useState('');
  const [branchTitle, setBranchTitle] = useState('');
  const [regenerationNote, setRegenerationNote] = useState('');

  const { approveCandidate, branchCandidate, refineCandidate, isLoading } =
    usePlanApi();
  const { error: showError, success: showSuccess } = useToast();

  useEffect(() => {
    const next = getCurrentCandidate(plan);
    setActiveCandidateId(next?.candidate_id || null);
    setEditStepId(null);
    setEditTask('');
  }, [plan]);

  const activeCandidate =
    plan.candidate_plans.find(
      (candidate) => candidate.candidate_id === activeCandidateId
    ) || getCurrentCandidate(plan);

  async function handleUseCandidate(candidateId: string) {
    try {
      await approveCandidate(plan.session_id, candidateId);
      showSuccess('Candidate applied to the session plan.');
      onUpdated();
    } catch {
      showError('Failed to apply that candidate.');
    }
  }

  async function handleBranch() {
    if (!activeCandidate) return;
    try {
      await branchCandidate(plan.session_id, activeCandidate.candidate_id, {
        title: branchTitle.trim() || undefined,
      });
      setBranchTitle('');
      showSuccess('Candidate branch created.');
      onUpdated();
    } catch {
      showError('Failed to branch the current candidate.');
    }
  }

  async function handleAddStep() {
    if (!activeCandidate || !newStepTask.trim()) return;
    try {
      await refineCandidate(plan.session_id, activeCandidate.candidate_id, {
        operation: 'add_step',
        task: newStepTask.trim(),
      });
      setNewStepTask('');
      showSuccess('Step added to the candidate.');
      onUpdated();
    } catch {
      showError('Failed to add a step.');
    }
  }

  async function handleDeleteStep(stepId: number) {
    if (!activeCandidate) return;
    try {
      await refineCandidate(plan.session_id, activeCandidate.candidate_id, {
        operation: 'delete_step',
        step_id: stepId,
      });
      showSuccess('Step removed from the candidate.');
      onUpdated();
    } catch {
      showError('Failed to delete the step.');
    }
  }

  async function handleEditStep() {
    if (!activeCandidate || editStepId === null || !editTask.trim()) return;
    try {
      await refineCandidate(plan.session_id, activeCandidate.candidate_id, {
        operation: 'edit_step',
        step_id: editStepId,
        task: editTask.trim(),
      });
      setEditStepId(null);
      setEditTask('');
      showSuccess('Step updated.');
      onUpdated();
    } catch {
      showError('Failed to edit the step.');
    }
  }

  async function handleRegenerate(stepId: number) {
    if (!activeCandidate) return;
    try {
      await refineCandidate(plan.session_id, activeCandidate.candidate_id, {
        operation: 'regenerate_from_step',
        step_id: stepId,
        note: regenerationNote.trim() || undefined,
      });
      showSuccess('Downstream steps regenerated.');
      onUpdated();
    } catch {
      showError('Failed to regenerate from that step.');
    }
  }

  if (plan.candidate_plans.length === 0) {
    return null;
  }

  return (
    <div className="space-y-5 rounded-3xl border border-white/5 bg-surface p-6 shadow-xl">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Candidate Plans</h3>
          <p className="text-sm text-text-muted">
            Apply a candidate to the session, branch it, or refine steps inline
            before approval.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={branchTitle}
            onChange={(event) => setBranchTitle(event.target.value)}
            placeholder="Optional branch title"
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white outline-none focus:border-primary/40"
          />
          <button
            type="button"
            onClick={() => void handleBranch()}
            disabled={!activeCandidate || isLoading('branchCandidate')}
            className="rounded-xl border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-bold text-primary transition-all hover:bg-primary/20 disabled:opacity-50"
          >
            <span className="inline-flex items-center gap-2">
              <GitBranch size={14} />
              Branch Candidate
            </span>
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {plan.candidate_plans.map((candidate) => {
          const isActive =
            candidate.candidate_id === activeCandidate?.candidate_id;
          const isApplied =
            candidate.candidate_id === plan.approved_candidate_id;
          return (
            <button
              key={candidate.candidate_id}
              type="button"
              onClick={() => setActiveCandidateId(candidate.candidate_id)}
              className={cn(
                'rounded-2xl border p-4 text-left transition-all duration-300',
                isActive
                  ? 'border-primary/40 bg-primary/10'
                  : 'border-white/5 bg-white/5 hover:bg-white/10'
              )}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="font-bold text-white">{candidate.title}</p>
                <span className="rounded-full bg-black/20 px-2.5 py-1 text-[10px] uppercase tracking-wider text-text-muted">
                  {candidate.planning_style}
                </span>
              </div>
              <p className="line-clamp-2 text-sm text-text-muted">
                {candidate.summary}
              </p>
              <div className="mt-3 flex items-center justify-between gap-2 text-xs text-text-muted">
                <span>{candidate.execution_graph.length} steps</span>
                {isApplied ? (
                  <span className="text-primary">Applied</span>
                ) : null}
              </div>
            </button>
          );
        })}
      </div>

      {activeCandidate && (
        <div className="space-y-4 rounded-2xl border border-white/5 bg-black/15 p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-sm font-bold text-white">
                {activeCandidate.title}
              </p>
              <p className="mt-1 text-sm text-text-muted">
                {activeCandidate.summary}
              </p>
              {activeCandidate.why_suggested ? (
                <p className="mt-2 text-xs text-primary/90">
                  {activeCandidate.why_suggested}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() =>
                void handleUseCandidate(activeCandidate.candidate_id)
              }
              disabled={isLoading('approveCandidate')}
              className="rounded-xl bg-gradient-to-r from-primary to-cyan-300 px-4 py-2 text-sm font-bold text-slate-950 transition-all hover:shadow-lg hover:shadow-primary/20 disabled:opacity-60"
            >
              <span className="inline-flex items-center gap-2">
                <ArrowRightLeft size={14} />
                Use This Candidate
              </span>
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-[1fr,auto]">
            <input
              value={newStepTask}
              onChange={(event) => setNewStepTask(event.target.value)}
              placeholder="Add a new step to this candidate"
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-primary/40"
            />
            <button
              type="button"
              onClick={() => void handleAddStep()}
              disabled={!newStepTask.trim() || isLoading('refineCandidate')}
              className="rounded-xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm font-bold text-primary transition-all hover:bg-primary/20 disabled:opacity-50"
            >
              <span className="inline-flex items-center gap-2">
                <Plus size={14} />
                Add Step
              </span>
            </button>
          </div>

          <div className="space-y-3">
            {activeCandidate.execution_graph.map((step) => (
              <StepEditor
                key={step.step_id}
                step={step}
                editStepId={editStepId}
                editTask={editTask}
                regenerationNote={regenerationNote}
                onSetEditStep={setEditStepId}
                onSetEditTask={setEditTask}
                onSetRegenerationNote={setRegenerationNote}
                onSaveEdit={() => void handleEditStep()}
                onDelete={() => void handleDeleteStep(step.step_id)}
                onRegenerate={() => void handleRegenerate(step.step_id)}
                isBusy={isLoading('refineCandidate')}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StepEditor({
  step,
  editStepId,
  editTask,
  regenerationNote,
  onSetEditStep,
  onSetEditTask,
  onSetRegenerationNote,
  onSaveEdit,
  onDelete,
  onRegenerate,
  isBusy,
}: {
  step: ExecutionStep;
  editStepId: number | null;
  editTask: string;
  regenerationNote: string;
  onSetEditStep: (stepId: number | null) => void;
  onSetEditTask: (value: string) => void;
  onSetRegenerationNote: (value: string) => void;
  onSaveEdit: () => void;
  onDelete: () => void;
  onRegenerate: () => void;
  isBusy: boolean;
}) {
  const isEditing = editStepId === step.step_id;

  return (
    <div className="rounded-2xl border border-white/5 bg-white/5 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex-1">
          <p className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
            Step {step.step_id}
          </p>
          {isEditing ? (
            <div className="mt-2 flex flex-col gap-3">
              <input
                value={editTask}
                onChange={(event) => onSetEditTask(event.target.value)}
                className="rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-primary/40"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onSaveEdit}
                  disabled={!editTask.trim() || isBusy}
                  className="rounded-xl border border-primary/20 bg-primary/10 px-3 py-2 text-sm font-bold text-primary transition-all hover:bg-primary/20 disabled:opacity-50"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onSetEditStep(null);
                    onSetEditTask('');
                  }}
                  className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm font-bold text-text-muted transition-all hover:bg-white/10"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="mt-1 text-sm text-white">{step.task}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              onSetEditStep(step.step_id);
              onSetEditTask(step.task);
            }}
            className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-bold text-text-muted transition-all hover:bg-white/10"
          >
            <span className="inline-flex items-center gap-2">
              <Pencil size={12} />
              Edit
            </span>
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-lg border border-danger/20 bg-danger/10 px-3 py-2 text-xs font-bold text-danger transition-all hover:bg-danger/20"
          >
            <span className="inline-flex items-center gap-2">
              <Trash2 size={12} />
              Delete
            </span>
          </button>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-3 md:flex-row">
        <input
          value={regenerationNote}
          onChange={(event) => onSetRegenerationNote(event.target.value)}
          placeholder="Optional guidance for regenerating from here"
          className="flex-1 rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-primary/40"
        />
        <button
          type="button"
          onClick={onRegenerate}
          disabled={isBusy}
          className="rounded-xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm font-bold text-primary transition-all hover:bg-primary/20 disabled:opacity-50"
        >
          <span className="inline-flex items-center gap-2">
            <RefreshCcw size={14} />
            Regenerate From Step
          </span>
        </button>
      </div>
      {step.dependencies.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {step.dependencies.map((dependency) => (
            <span
              key={dependency}
              className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] text-text-muted"
            >
              depends on {dependency}
            </span>
          ))}
        </div>
      ) : null}
      {step.assigned_model ? (
        <div className="mt-3">
          <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] text-text-muted">
            <span className="inline-flex items-center gap-2">
              <Wand2 size={12} />
              {step.assigned_model.split('/').pop()}
            </span>
          </span>
        </div>
      ) : null}
    </div>
  );
}
