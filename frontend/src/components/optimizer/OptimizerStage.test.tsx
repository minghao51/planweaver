import { render, screen, waitFor } from '@testing-library/react';
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
  const mockShowSuccess = vi.fn();
  const mockShowError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useOptimizer
    vi.spyOn(hooks, 'useOptimizer').mockReturnValue({
      optimizePlan: mockOptimizePlan,
      saveUserRating: mockSaveUserRating,
      loading: false,
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
      showSuccess: mockShowSuccess,
      showError: mockShowError,
      showInfo: vi.fn(),
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

    expect(screen.getByText('Plan Optimizer')).toBeInTheDocument();
    expect(screen.getByText(/AI-generated variants/i)).toBeInTheDocument();
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
      loading: true,
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

  it('should show error if no plan selected on complete', () => {
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

    const continueButton = screen.getByRole('button', { name: /continue/i });
    continueButton.click();

    expect(mockShowError).toHaveBeenCalledWith('Please select a plan to continue');
    expect(mockOnComplete).not.toHaveBeenCalled();
  });

  it('should save user rating when provided', async () => {
    const mockOnComplete = vi.fn();

    // Mock useOptimizerStage to return a selected plan
    vi.spyOn(hooks, 'useOptimizerStage').mockReturnValue({
      sessionId: 'session-1',
      selectedProposalId: 'proposal-1',
      variants: [],
      ratings: {},
      selectedPlanId: 'plan-1',  // User has selected a plan
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

    // Click 5th star
    const stars = screen.getAllByRole('button').filter(b => b.querySelector('svg'));
    stars[4].click();

    const continueButton = screen.getByRole('button', { name: /continue/i });
    continueButton.click();

    await waitFor(() => {
      expect(mockSaveUserRating).toHaveBeenCalledWith('plan-1', 5, '');
    });
  });
});
