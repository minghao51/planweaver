import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComparisonPanel } from './ComparisonPanel';

describe('ComparisonPanel', () => {
  const mockPlans = [
    {
      id: 'plan-1',
      title: 'Original Plan',
      metadata: {
        step_count: 10,
        complexity_score: 'High',
        estimated_time_minutes: 60,
        estimated_cost_usd: 5.00,
      },
      ratings: {
        'claude-3.5-sonnet': {
          model_name: 'claude-3.5-sonnet',
          ratings: { feasibility: 8.0, cost_efficiency: 7.0 },
          overall_score: 7.5,
          reasoning: 'Good',
        },
      },
      averageScore: 7.5,
    },
    {
      id: 'plan-2',
      title: 'Simplified Variant',
      variantType: 'simplified',
      metadata: {
        step_count: 5,
        complexity_score: 'Low',
        estimated_time_minutes: 30,
        estimated_cost_usd: 2.50,
      },
      ratings: {
        'claude-3.5-sonnet': {
          model_name: 'claude-3.5-sonnet',
          ratings: { feasibility: 9.0, cost_efficiency: 8.5 },
          overall_score: 8.75,
          reasoning: 'Better',
        },
      },
      averageScore: 8.75,
    },
  ];

  it('should render comparison table with metrics', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('Metrics Comparison')).toBeInTheDocument();
    expect(screen.getByText('Original Plan')).toBeInTheDocument();
    expect(screen.getByText('Simplified Variant')).toBeInTheDocument();
  });

  it('should display step counts', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('should display estimated costs', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('$5.00')).toBeInTheDocument();
    expect(screen.getByText('$2.50')).toBeInTheDocument();
  });

  it('should display average scores', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText('8.8')).toBeInTheDocument(); // rounded
  });

  it('should show AI model ratings section', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('AI Model Ratings')).toBeInTheDocument();
    expect(screen.getByText('CLAUDE')).toBeInTheDocument();
  });

  it('should call onSelectPlan when plan button is clicked', () => {
    const handleSelect = vi.fn();
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId={null}
        onSelectPlan={handleSelect}
      />
    );

    const buttons = screen.getAllByRole('button');
    const originalButton = buttons.find(b => b.textContent === 'Original Plan');
    fireEvent.click(originalButton!);

    expect(handleSelect).toHaveBeenCalledWith('plan-1');
  });

  it('should highlight selected plan', () => {
    render(
      <ComparisonPanel
        plans={mockPlans}
        selectedPlanId="plan-1"}
        onSelectPlan={vi.fn()}
      />
    );

    const selectedButton = screen.getByRole('button', { name: /original plan/i });
    expect(selectedButton).toHaveClass('bg-primary');
  });

  it('should show empty state when no plans', () => {
    render(
      <ComparisonPanel
        plans={[]}
        selectedPlanId={null}
        onSelectPlan={vi.fn()}
      />
    );

    expect(screen.getByText('No plans to compare')).toBeInTheDocument();
  });
});
