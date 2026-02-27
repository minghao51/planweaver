import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PlanCard } from './PlanCard';

describe('PlanCard', () => {
  const mockProps = {
    id: 'plan-1',
    title: 'Test Plan',
    description: 'A test plan description',
    executionGraphLength: 5,
    metadata: {
      step_count: 5,
      complexity_score: 'Medium',
      estimated_time_minutes: 30,
      estimated_cost_usd: 1.50,
    },
    selected: false,
    onSelect: vi.fn(),
  };

  it('should render plan title and description', () => {
    render(<PlanCard {...mockProps} />);

    expect(screen.getByText('Test Plan')).toBeInTheDocument();
    expect(screen.getByText('A test plan description')).toBeInTheDocument();
  });

  it('should display metadata when provided', () => {
    render(<PlanCard {...mockProps} />);

    expect(screen.getByText('5')).toBeInTheDocument(); // step_count
    expect(screen.getByText('Medium')).toBeInTheDocument(); // complexity
    expect(screen.getByText('$1.50')).toBeInTheDocument(); // cost
  });

  it('should show variant type badge', () => {
    render(<PlanCard {...mockProps} variantType="simplified" />);

    expect(screen.getByText('simplified')).toBeInTheDocument();
  });

  it('should show selected state with check icon', () => {
    const { container } = render(<PlanCard {...mockProps} selected={true} />);

    // Should have the check icon (selected indicator)
    const checkIcon = container.querySelector('svg');
    expect(checkIcon).toBeInTheDocument();

    // Should not have select button when selected
    expect(screen.queryByRole('button', { name: /select this plan/i })).not.toBeInTheDocument();
  });

  it('should call onSelect when select button is clicked', () => {
    render(<PlanCard {...mockProps} />);

    const selectButton = screen.getByRole('button', { name: /select this plan/i });
    fireEvent.click(selectButton);

    expect(mockProps.onSelect).toHaveBeenCalledTimes(1);
  });

  it('should not be interactive when loading', () => {
    const { container } = render(<PlanCard {...mockProps} loading={true} />);

    const card = container.querySelector('.opacity-50');
    expect(card).toBeInTheDocument();
  });

  it('should display ratings when provided', () => {
    const propsWithRatings = {
      ...mockProps,
      ratings: {
        'claude-3.5-sonnet': {
          model_name: 'claude-3.5-sonnet',
          ratings: { feasibility: 8.5, cost_efficiency: 7.0 },
          overall_score: 7.75,
          reasoning: 'Good plan',
        },
      },
      averageScore: 7.75,
    };

    render(<PlanCard {...propsWithRatings} />);

    expect(screen.getByText('AI Ratings')).toBeInTheDocument();
    // Check that ratings section is present
    expect(screen.getByText('claude')).toBeInTheDocument(); // model name (first part)
  });

  it('should show high score in success color', () => {
    const propsWithHighScore = {
      ...mockProps,
      ratings: {},
      averageScore: 8.5,
    };

    const { container } = render(<PlanCard {...propsWithHighScore} />);

    // Look for the score in the DOM with the success class
    const scoreElement = container.querySelector('.text-success');
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement?.textContent).toContain('8.5');
  });
});
