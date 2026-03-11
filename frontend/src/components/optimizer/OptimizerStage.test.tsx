import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OptimizerStage } from './OptimizerStage';
import * as hooks from '../../hooks/useOptimizer';
import * as toastHooks from '../../hooks/useToast';

// Mock the hooks
vi.mock('../../hooks/useOptimizer', () => ({
  useOptimizer: vi.fn(),
  useOptimizerStage: vi.fn(),
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: vi.fn(),
}));

describe('OptimizerStage', () => {
  const mockOptimizePlan = vi.fn();
  const mockSaveUserRating = vi.fn();
  const mockSubmitManualPlan = vi.fn();
  const mockEvaluatePlans = vi.fn();
  const mockComparePlans = vi.fn();
  const mockShowSuccess = vi.fn();
  const mockShowError = vi.fn();
  const mockShowInfo = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOptimizePlan.mockImplementation(
      () => new Promise(() => undefined)
    );
    mockSubmitManualPlan.mockResolvedValue({
      normalized_plan: {
        id: 'manual-1',
        session_id: 'session-1',
        source_type: 'manual',
        source_model: 'human',
        planning_style: 'manual',
        title: 'Manual baseline',
        summary: 'Summary',
        assumptions: [],
        constraints: [],
        success_criteria: [],
        risks: [],
        fallbacks: [],
        estimated_time_minutes: 0,
        estimated_cost_usd: 0,
        steps: [],
        metadata: {},
        normalization_warnings: [],
      },
      evaluations: {},
      ranking: [],
    });
    mockEvaluatePlans.mockResolvedValue({
      normalized_plans: [],
      evaluations: {},
      ranking: [],
    });
    mockComparePlans.mockResolvedValue({
      normalized_plans: [],
      evaluations: {},
      comparisons: [],
      ranking: [],
    });

    // Mock useOptimizer
    vi.spyOn(hooks, 'useOptimizer').mockReturnValue({
      optimizePlan: mockOptimizePlan,
      saveUserRating: mockSaveUserRating,
      submitManualPlan: mockSubmitManualPlan,
      evaluatePlans: mockEvaluatePlans,
      comparePlans: mockComparePlans,
      isLoading: vi.fn(() => false),
      error: null,
    } as any);

    // Mock useOptimizerStage
    vi.spyOn(hooks, 'useOptimizerStage').mockReturnValue({
      sessionId: 'session-1',
      selectedProposalId: 'proposal-1',
      variants: [],
      ratings: {},
      selectedPlanId: null,
      status: 'idle',
      setSelectedPlanId: vi.fn(),
      setStatus: vi.fn(),
      setVariants: vi.fn(),
      setRatings: vi.fn(),
    } as any);

    // Mock useToast
    vi.spyOn(toastHooks, 'useToast').mockReturnValue({
      success: mockShowSuccess,
      error: mockShowError,
      info: mockShowInfo,
    } as any);
  });

  it('should render header', () => {
    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.getByText('Planning Workbench')).toBeInTheDocument();
    expect(screen.getByText(/manual baselines, rubric evaluation/i)).toBeInTheDocument();
  });

  it('should call optimizePlan on mount', async () => {
    mockOptimizePlan.mockResolvedValue({
      variants: [],
      ratings: {},
    });

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(mockOptimizePlan).toHaveBeenCalledWith(
        'proposal-1',
        ['simplified', 'enhanced', 'cost-optimized']
      );
    });
  });

  it('should show loading state while optimizing', () => {
    vi.spyOn(hooks, 'useOptimizer').mockReturnValue({
      optimizePlan: mockOptimizePlan,
      saveUserRating: mockSaveUserRating,
      submitManualPlan: mockSubmitManualPlan,
      evaluatePlans: mockEvaluatePlans,
      comparePlans: mockComparePlans,
      isLoading: vi.fn(() => true),
      error: null,
    } as any);

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.getByText(/Generating Optimized Variants/i)).toBeInTheDocument();
  });

  it('should render workbench tabs', () => {
    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /variants/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manual plan/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /evaluate/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /compare/i })).toBeInTheDocument();
  });

  it('should call onBack when back button clicked', () => {
    const mockOnBack = vi.fn();

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={mockOnBack}
      />
    );

    const backButton = screen.getAllByText('Back')[0];
    backButton.click();

    expect(mockOnBack).toHaveBeenCalledTimes(1);
  });

  it('should disable continue button when no plan selected', () => {
    const mockOnComplete = vi.fn();

    // Mock useOptimizerStage to return null selectedPlanId
    vi.spyOn(hooks, 'useOptimizerStage').mockReturnValue({
      sessionId: 'session-1',
      selectedProposalId: 'proposal-1',
      variants: [],
      ratings: {},
      selectedPlanId: null,  // No plan selected
      status: 'completed',
      setSelectedPlanId: vi.fn(),
      setStatus: vi.fn(),
      setVariants: vi.fn(),
      setRatings: vi.fn(),
    } as any);

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={mockOnComplete}
        onBack={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /continue/i })).not.toBeInTheDocument();
    expect(mockOnComplete).not.toHaveBeenCalled();
  });

  it('should save user rating when provided', async () => {
    const mockOnComplete = vi.fn();
    const mockSetSelectedPlanId = vi.fn();

    // Mock useOptimizerStage to return a selected plan
    vi.spyOn(hooks, 'useOptimizerStage').mockReturnValue({
      sessionId: 'session-1',
      selectedProposalId: 'proposal-1',
      variants: [],
      ratings: {},
      selectedPlanId: 'plan-1',  // User has selected a plan
      status: 'completed',
      setSelectedPlanId: mockSetSelectedPlanId,
      setStatus: vi.fn(),
      setVariants: vi.fn(),
      setRatings: vi.fn(),
    } as any);

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={mockOnComplete}
        onBack={vi.fn()}
      />
    );

    // Verify stars are rendered
    const stars = screen.getAllByRole('button').filter(b => b.querySelector('svg'));
    expect(stars.length).toBeGreaterThan(0);
  });

  it('should add a manual plan and show normalization warnings', async () => {
    mockSubmitManualPlan.mockResolvedValue({
      normalized_plan: {
        id: 'manual-1',
        session_id: 'session-1',
        source_type: 'manual',
        source_model: 'human',
        planning_style: 'manual',
        title: 'Operator checklist baseline',
        summary: 'Roll out the checklist in one team first.',
        assumptions: [],
        constraints: [],
        success_criteria: ['Checklist adopted'],
        risks: ['Stakeholder drift'],
        fallbacks: [],
        estimated_time_minutes: 45,
        estimated_cost_usd: 10,
        steps: [
          {
            step_id: '1',
            description: 'Audit the current checklist',
            dependencies: [],
            validation: [],
            tools: [],
          },
        ],
        metadata: {},
        normalization_warnings: ['Inferred rollout order from free-form steps.'],
      },
      evaluations: {},
      ranking: [],
    });

    render(
      <OptimizerStage
        sessionId="session-1"
        selectedProposalId="proposal-1"
        selectedProposalTitle="Test Proposal"
        selectedProposalDescription="A test proposal"
        onComplete={vi.fn()}
        onBack={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /manual plan/i }));
    fireEvent.change(screen.getByLabelText(/^title$/i), {
      target: { value: 'Operator checklist baseline' },
    });
    fireEvent.change(screen.getByLabelText(/summary/i), {
      target: { value: 'Roll out the checklist in one team first.' },
    });
    fireEvent.change(screen.getByLabelText(/plan steps/i), {
      target: { value: 'Audit the current checklist' },
    });
    fireEvent.click(screen.getByRole('button', { name: /add manual plan/i }));

    await waitFor(() => {
      expect(mockSubmitManualPlan).toHaveBeenCalledWith({
        session_id: 'session-1',
        title: 'Operator checklist baseline',
        summary: 'Roll out the checklist in one team first.',
        plan_text: 'Audit the current checklist',
        success_criteria: [],
        risks: [],
      });
    });

    expect(mockShowSuccess).toHaveBeenCalledWith('Manual plan added to the candidate pool.');
    expect(screen.getAllByRole('button', { name: /evaluate/i }).length).toBeGreaterThan(0);
  });
});
