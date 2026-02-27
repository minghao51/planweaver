import type { PlanStatus } from '../types';


export function getStatusStyles(status: PlanStatus): string {
  const styles: Record<string, string> = {
    BRAINSTORMING: 'bg-warning/10 text-warning border-warning/20',
    AWAITING_APPROVAL: 'bg-info/10 text-info border-info/20',
    APPROVED: 'bg-success/10 text-success border-success/20',
    EXECUTING: 'bg-primary/10 text-primary border-primary/20',
    COMPLETED: 'bg-success/20 text-success border-success/30',
    FAILED: 'bg-danger/10 text-danger border-danger/20',
  };
  return styles[status] ?? 'bg-white/5 text-text-muted border-white/10';
}

export interface StepStyleConfig {
  container: string;
  iconLabel: string;
  iconContainer: string;
}

export function getStepStyles(status: string, stepId?: number): StepStyleConfig {
  const configs: Record<string, StepStyleConfig> = {
    PENDING: {
      container: 'bg-surface border-white/5 opacity-50',
      iconLabel: String(stepId ?? '?'),
      iconContainer: 'border-white/10 text-text-muted bg-white/5',
    },
    IN_PROGRESS: {
      container: 'bg-primary/5 border-primary shadow-lg shadow-primary/5',
      iconLabel: 'spinner',
      iconContainer: 'border-primary text-primary bg-primary/10 shadow-[0_0_15px_rgba(56,189,248,0.32)]',
    },
    COMPLETED: {
      container: 'bg-success/5 border-success/30',
      iconLabel: 'check',
      iconContainer: 'border-success text-success bg-success/10',
    },
    FAILED: {
      container: 'bg-danger/5 border-danger/30',
      iconLabel: 'alert',
      iconContainer: 'border-danger text-danger bg-danger/10',
    },
  };
  return configs[status] ?? configs.PENDING;
}
