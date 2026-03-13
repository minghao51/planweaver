import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { WorkbenchPage } from './WorkbenchPage';
import * as apiHooks from '../hooks/useApi';
import * as toastHooks from '../hooks/useToast';

vi.mock('../hooks/useApi', () => ({
  usePlanApi: vi.fn(),
}));

vi.mock('../hooks/useToast', () => ({
  useToast: vi.fn(),
}));

vi.mock('./optimizer', () => ({
  OptimizerStage: (props: {
    selectedProposalId: string;
    selectedProposalTitle: string;
    selectedProposalDescription: string;
  }) => (
    <div>
      <div>Optimizer Stage</div>
      <div>{props.selectedProposalId}</div>
      <div>{props.selectedProposalTitle}</div>
      <div>{props.selectedProposalDescription}</div>
    </div>
  ),
}));

describe('WorkbenchPage', () => {
  const mockGetSession = vi.fn();
  const mockListSessions = vi.fn();
  const mockShowError = vi.fn();
  const mockShowInfo = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(apiHooks, 'usePlanApi').mockReturnValue({
      getSession: mockGetSession,
      listSessions: mockListSessions,
      isLoading: vi.fn(() => false),
    } as any);

    vi.spyOn(toastHooks, 'useToast').mockReturnValue({
      error: mockShowError,
      info: mockShowInfo,
    } as any);

    mockListSessions.mockResolvedValue({
      sessions: [],
      total: 0,
      limit: 8,
      offset: 0,
    });
  });

  it('launches from a selected proposal when proposals are available', async () => {
    mockGetSession.mockResolvedValue({
      session_id: 'session-1',
      user_intent: 'Test session',
      strawman_proposals: [
        {
          id: 'proposal-1',
          title: 'Proposal One',
          description: 'Proposal summary',
          pros: [],
          cons: [],
          selected: true,
          context_references: [],
          planning_style: 'baseline',
        },
      ],
      candidate_plans: [],
    });

    render(
      <MemoryRouter>
        <WorkbenchPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('proj_abc123'), {
      target: { value: 'session-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    await screen.findByRole('button', { name: /proposal one/i });
    fireEvent.click(screen.getByRole('button', { name: /open workbench/i }));

    expect(await screen.findByText('Optimizer Stage')).toBeInTheDocument();
    expect(screen.getByText('proposal-1')).toBeInTheDocument();
  });

  it('falls back to candidate plans when proposals are absent', async () => {
    mockGetSession.mockResolvedValue({
      session_id: 'session-2',
      user_intent: 'Candidate-only session',
      strawman_proposals: [],
      selected_candidate_id: 'candidate-1',
      approved_candidate_id: null,
      candidate_plans: [
        {
          candidate_id: 'candidate-1',
          title: 'Candidate Alpha',
          summary: 'Candidate summary',
          proposal_id: null,
          status: 'selected',
        },
      ],
    });

    render(
      <MemoryRouter>
        <WorkbenchPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('proj_abc123'), {
      target: { value: 'session-2' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    await screen.findByRole('button', { name: /candidate alpha/i });
    await waitFor(() => {
      expect(mockShowInfo).toHaveBeenCalledWith(
        'No proposals found, but existing candidate plans can still be opened in the workbench.'
      );
    });

    fireEvent.click(screen.getByRole('button', { name: /open workbench/i }));

    expect(await screen.findByText('Optimizer Stage')).toBeInTheDocument();
    expect(screen.getByText('candidate-1')).toBeInTheDocument();
    expect(screen.getByText('Candidate Alpha')).toBeInTheDocument();
  });
});
