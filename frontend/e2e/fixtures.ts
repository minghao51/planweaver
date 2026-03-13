import { Page, Request } from '@playwright/test';

type ResponsePayload = {
  status?: number;
  body?: unknown;
  contentType?: string;
  headers?: Record<string, string>;
};

export interface SessionState {
  questionPlan: Record<string, unknown>;
  workbenchPlan: Record<string, unknown>;
  workbenchCandidates: Record<string, unknown>;
}

function createQuestionPlan() {
  return {
    session_id: 'session-question',
    status: 'BRAINSTORMING',
    user_intent: 'Launch a customer support portal',
    locked_constraints: {},
    open_questions: [
      {
        id: 'audience',
        question: 'Who is the primary user for this portal?',
        answered: false,
        answer: null,
        rationale: 'Knowing the core audience changes routing, permissions, and content structure.',
        context_references: [],
        confidence: 0.62,
      },
    ],
    strawman_proposals: [],
    execution_graph: [],
    external_contexts: [],
    context_suggestions: [],
    candidate_plans: [],
    candidate_revisions: [],
    planning_outcomes: [],
    selected_candidate_id: null,
    approved_candidate_id: null,
    final_output: null,
  };
}

function createWorkbenchPlan() {
  return {
    session_id: 'session-workbench',
    status: 'BRAINSTORMING',
    user_intent: 'Build an internal release checklist workflow',
    locked_constraints: {
      timeline: '2 weeks',
    },
    open_questions: [],
    strawman_proposals: [
      {
        id: 'proposal-alpha',
        title: 'Task-first rollout',
        description: 'Start with a minimal release checklist and expand by team.',
        pros: ['Fast onboarding', 'Simple governance'],
        cons: ['Requires iterative polish'],
        selected: true,
        why_suggested: 'This keeps the first rollout lightweight and measurable.',
        context_references: [],
        confidence: 0.8,
        planning_style: 'baseline',
      },
      {
        id: 'proposal-beta',
        title: 'Platform-first rollout',
        description: 'Build a reusable workflow engine before shipping templates.',
        pros: ['Reusable foundation'],
        cons: ['Higher initial cost'],
        selected: false,
        why_suggested: 'This creates a stronger long-term platform if the organization can absorb the setup cost.',
        context_references: [],
        confidence: 0.68,
        planning_style: 'platform_first',
      },
    ],
    execution_graph: [],
    external_contexts: [],
    context_suggestions: [],
    candidate_plans: [],
    candidate_revisions: [],
    planning_outcomes: [],
    selected_candidate_id: 'candidate-base',
    approved_candidate_id: null,
    final_output: null,
  };
}

function createWorkbenchCandidates() {
  return {
    session_id: 'session-workbench',
    selected_candidate_id: 'candidate-base',
    approved_candidate_id: null,
    candidates: [
      {
        candidate_id: 'candidate-base',
        session_id: 'session-workbench',
        title: 'Task-first rollout',
        summary: 'Start with a minimal release checklist and expand by team.',
        source_type: 'llm_generated',
        source_model: 'planner-fast',
        planning_style: 'baseline',
        proposal_id: 'proposal-alpha',
        status: 'selected',
        normalized_plan_id: 'normalized-base',
        normalized_plan: {
          id: 'normalized-base',
          title: 'Task-first rollout',
          summary: 'Start with a minimal release checklist and expand by team.',
        },
        execution_graph: [],
        context_references: [],
        metadata: {
          step_count: 3,
          complexity_score: 'Medium',
          estimated_time_minutes: 150,
          estimated_cost_usd: 40,
        },
      },
    ],
  };
}

export const sessionState: SessionState = {
  questionPlan: createQuestionPlan(),
  workbenchPlan: createWorkbenchPlan(),
  workbenchCandidates: createWorkbenchCandidates(),
};

const baseModels = [
  {
    id: 'planner-fast',
    name: 'Planner Fast',
    type: 'planner',
    provider: 'OpenAI',
  },
  {
    id: 'executor-safe',
    name: 'Executor Safe',
    type: 'executor',
    provider: 'Anthropic',
  },
];

const sessionHistory = [
  {
    session_id: 'session-workbench',
    status: 'BRAINSTORMING',
    user_intent: 'Build an internal release checklist workflow',
    updated_at: '2026-03-10T12:00:00Z',
  },
  {
    session_id: 'session-completed',
    status: 'COMPLETED',
    user_intent: 'Migrate analytics dashboards to the new schema',
    updated_at: '2026-03-09T08:30:00Z',
  },
];

export async function installApiMocks(page: Page) {
  let latestQuestionAnswerBody: unknown = null;
  sessionState.questionPlan = createQuestionPlan();
  sessionState.workbenchPlan = createWorkbenchPlan();
  sessionState.workbenchCandidates = createWorkbenchCandidates();

  await page.addInitScript(() => {
    window.localStorage.setItem('planweaver_demo_dismissed', 'true');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;

    const payload = resolveApiResponse(path, method, url, request, {
      getLatestQuestionAnswerBody: () => latestQuestionAnswerBody,
      setLatestQuestionAnswerBody: (body) => {
        latestQuestionAnswerBody = body;
      },
    });

    await route.fulfill({
      status: payload.status ?? 200,
      contentType: payload.contentType ?? 'application/json',
      headers: payload.headers,
      body:
        payload.contentType === 'text/event-stream'
          ? String(payload.body ?? '')
          : JSON.stringify(payload.body ?? {}),
    });
  });
}

function resolveApiResponse(
  path: string,
  method: string,
  url: URL,
  request: Request,
  state: {
    getLatestQuestionAnswerBody: () => unknown;
    setLatestQuestionAnswerBody: (body: unknown) => void;
  }
): ResponsePayload {
  if (path.endsWith('/scenarios') && method === 'GET') {
    return { body: { scenarios: ['blog_generation', 'market_analysis'] } };
  }

  if (path.endsWith('/models') && method === 'GET') {
    return { body: { models: baseModels } };
  }

  if (path.endsWith('/sessions') && method === 'POST') {
    return { body: { session_id: 'session-question' } };
  }

  if (path.endsWith('/sessions') && method === 'GET') {
    const q = url.searchParams.get('q')?.toLowerCase() ?? '';
    const status = url.searchParams.get('status') ?? '';
    const filtered = sessionHistory.filter((session) => {
      const matchesQuery =
        q.length === 0 ||
        session.session_id.toLowerCase().includes(q) ||
        session.user_intent.toLowerCase().includes(q);
      const matchesStatus = status.length === 0 || session.status === status;
      return matchesQuery && matchesStatus;
    });

    return {
      body: {
        sessions: filtered,
        total: filtered.length,
        limit: Number(url.searchParams.get('limit') ?? filtered.length),
        offset: Number(url.searchParams.get('offset') ?? 0),
      },
    };
  }

  if (path.endsWith('/sessions/session-question') && method === 'GET') {
    return { body: sessionState.questionPlan };
  }

  if (path.endsWith('/sessions/session-question/questions') && method === 'POST') {
    state.setLatestQuestionAnswerBody(request.postDataJSON());
    sessionState.questionPlan = {
      ...sessionState.questionPlan,
      open_questions: [
        {
          id: 'audience',
          question: 'Who is the primary user for this portal?',
          answered: true,
          answer: (state.getLatestQuestionAnswerBody() as Record<string, string>)?.audience ?? '',
          rationale: 'Knowing the core audience changes routing, permissions, and content structure.',
          context_references: [],
          confidence: 0.62,
        },
      ],
      strawman_proposals: [
        {
          id: 'proposal-q1',
          title: 'Support workspace',
          description: 'A central portal for agents with lightweight routing.',
          pros: ['Clear ownership'],
          cons: ['Requires queue definitions'],
          selected: false,
          why_suggested: 'It balances launch speed with enough structure for agent workflows.',
          context_references: [],
          confidence: 0.73,
          planning_style: 'baseline',
        },
      ],
    };
    return { body: { ok: true } };
  }

  if (path.endsWith('/sessions/session-workbench') && method === 'GET') {
    return { body: sessionState.workbenchPlan };
  }

  if (path.endsWith('/sessions/session-workbench/stream') && method === 'GET') {
    return {
      contentType: 'text/event-stream',
      headers: {
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: 'event: connected\ndata: {"session_id":"session-workbench"}\n\n',
    };
  }

  if (path.endsWith('/sessions/session-workbench/candidates') && method === 'GET') {
    return { body: sessionState.workbenchCandidates };
  }

  if (path.endsWith('/optimizer/optimize') && method === 'POST') {
    sessionState.workbenchCandidates = {
      ...sessionState.workbenchCandidates,
      candidates: [
        ...(sessionState.workbenchCandidates.candidates as Record<string, unknown>[]).filter(
          (candidate) =>
            !['variant-simplified', 'variant-enhanced'].includes(String(candidate.candidate_id))
        ),
        {
          candidate_id: 'candidate-base',
          session_id: 'session-workbench',
          title: 'Task-first rollout',
          summary: 'Start with a minimal release checklist and expand by team.',
          source_type: 'llm_generated',
          source_model: 'planner-fast',
          planning_style: 'baseline',
          proposal_id: 'proposal-alpha',
          status: 'selected',
          normalized_plan_id: 'normalized-base',
          normalized_plan: {
            id: 'normalized-base',
            title: 'Task-first rollout',
            summary: 'Start with a minimal release checklist and expand by team.',
          },
          execution_graph: [],
          context_references: [],
          metadata: {
            step_count: 3,
            complexity_score: 'Medium',
            estimated_time_minutes: 150,
            estimated_cost_usd: 40,
          },
        },
        {
          candidate_id: 'variant-simplified',
          session_id: 'session-workbench',
          title: 'Simplified variant',
          summary: 'Reduced handoffs and simplified approval gates.',
          source_type: 'optimized_variant',
          source_model: 'planner-fast',
          planning_style: 'simplified',
          parent_candidate_id: 'candidate-base',
          status: 'draft',
          normalized_plan_id: 'variant-simplified',
          normalized_plan: {
            id: 'variant-simplified',
            title: 'Simplified variant',
            summary: 'Reduced handoffs and simplified approval gates.',
          },
          execution_graph: [],
          context_references: [],
          metadata: {
            step_count: 4,
            complexity_score: 'Low',
            optimization_notes: 'Reduced handoffs and simplified approval gates.',
            estimated_time_minutes: 120,
            estimated_cost_usd: 50,
          },
        },
        {
          candidate_id: 'variant-enhanced',
          session_id: 'session-workbench',
          title: 'Enhanced variant',
          summary: 'Adds stronger auditability and rollout checks.',
          source_type: 'optimized_variant',
          source_model: 'planner-fast',
          planning_style: 'enhanced',
          parent_candidate_id: 'candidate-base',
          status: 'draft',
          normalized_plan_id: 'variant-enhanced',
          normalized_plan: {
            id: 'variant-enhanced',
            title: 'Enhanced variant',
            summary: 'Adds stronger auditability and rollout checks.',
          },
          execution_graph: [],
          context_references: [],
          metadata: {
            step_count: 6,
            complexity_score: 'Medium',
            optimization_notes: 'Adds stronger auditability and rollout checks.',
            estimated_time_minutes: 180,
            estimated_cost_usd: 90,
          },
        },
      ],
    };
    return {
      body: {
        optimization_id: 'opt-123',
        status: 'completed',
        session_id: 'session-workbench',
        variants: [
          {
            id: 'variant-simplified',
            proposal_id: 'proposal-alpha',
            variant_type: 'simplified',
            execution_graph: [],
            metadata: {
              step_count: 4,
              complexity_score: 'Low',
              optimization_notes: 'Reduced handoffs and simplified approval gates.',
              estimated_time_minutes: 120,
              estimated_cost_usd: 50,
            },
          },
          {
            id: 'variant-enhanced',
            proposal_id: 'proposal-alpha',
            variant_type: 'enhanced',
            execution_graph: [],
            metadata: {
              step_count: 6,
              complexity_score: 'Medium',
              optimization_notes: 'Adds stronger auditability and rollout checks.',
              estimated_time_minutes: 180,
              estimated_cost_usd: 90,
            },
          },
        ],
        ratings: {
          'variant-simplified': {
            plan_id: 'variant-simplified',
            average_score: 8.6,
            ratings: {},
          },
        },
      },
    };
  }

  if (path.endsWith('/optimizer/manual') && method === 'POST') {
    const body = request.postDataJSON() as Record<string, unknown>;
    sessionState.workbenchCandidates = {
      ...sessionState.workbenchCandidates,
      selected_candidate_id: 'manual-baseline',
      candidates: [
        ...(sessionState.workbenchCandidates.candidates as Record<string, unknown>[]).filter(
          (candidate) => candidate.candidate_id !== 'manual-baseline'
        ),
        {
          candidate_id: 'manual-baseline',
          session_id: 'session-workbench',
          title: String(body.title || 'Manual baseline'),
          summary: String(body.summary || 'Manual baseline summary'),
          source_type: 'manual',
          source_model: 'human',
          planning_style: 'manual',
          status: 'selected',
          normalized_plan_id: 'manual-baseline',
          normalized_plan: {
            id: 'manual-baseline',
            title: String(body.title || 'Manual baseline'),
            summary: String(body.summary || 'Manual baseline summary'),
          },
          execution_graph: [
            {
              step_id: 1,
              task: 'Audit release checklist',
              prompt_template_id: 'default',
              assigned_model: 'human',
              dependencies: [],
              status: 'PENDING',
              output: null,
              error: null,
            },
            {
              step_id: 2,
              task: 'Pilot with one team',
              prompt_template_id: 'default',
              assigned_model: 'human',
              dependencies: [1],
              status: 'PENDING',
              output: null,
              error: null,
            },
          ],
          context_references: [],
          metadata: {
            step_count: 2,
            complexity_score: 'Medium',
            estimated_time_minutes: 75,
            estimated_cost_usd: 15,
          },
        },
      ],
    };
    return {
      body: {
        normalized_plan: {
          id: 'manual-baseline',
          session_id: 'session-workbench',
          source_type: 'manual',
          source_model: 'human',
          planning_style: 'manual',
        title: String(body.title || 'Manual baseline'),
        summary: String(body.summary || 'Manual baseline summary'),
          assumptions: [],
          constraints: [],
          success_criteria: body.success_criteria || [],
          risks: body.risks || [],
          fallbacks: [],
          estimated_time_minutes: 75,
          estimated_cost_usd: 15,
          steps: [
            { step_id: '1', description: 'Audit release checklist', dependencies: [], validation: [], tools: [] },
            { step_id: '2', description: 'Pilot with one team', dependencies: ['1'], validation: [], tools: [] },
          ],
          metadata: {},
          normalization_warnings: ['Timeline assumptions were inferred from the draft plan.'],
        },
        evaluations: {},
        ranking: [],
      },
    };
  }

  if (path.endsWith('/optimizer/evaluate') && method === 'POST') {
    return {
      body: {
        normalized_plans: [
          { id: 'proposal-alpha', title: 'Original Proposal' },
          { id: 'manual-baseline', title: 'Manual baseline' },
        ],
        evaluations: {
          'proposal-alpha': {
            plan_id: 'proposal-alpha',
            final_score: 8.2,
            verdict: 'strong',
          },
          'manual-baseline': {
            plan_id: 'manual-baseline',
            final_score: 7.4,
            verdict: 'acceptable',
          },
        },
        ranking: [
          { plan_id: 'proposal-alpha', final_score: 8.2 },
          { plan_id: 'manual-baseline', final_score: 7.4 },
        ],
      },
    };
  }

  if (path.endsWith('/optimizer/compare') && method === 'POST') {
    return {
      body: {
        normalized_plans: [],
        evaluations: {},
        comparisons: [
          {
            left_plan_id: 'proposal-alpha',
            right_plan_id: 'manual-baseline',
            winner_plan_id: 'proposal-alpha',
            rationale: 'The original proposal has stronger rollout safeguards and clearer ownership.',
            margin: 'moderate',
            preference_factors: ['verification', 'dependency_quality'],
          },
        ],
        ranking: [
          { plan_id: 'proposal-alpha', final_score: 8.7 },
          { plan_id: 'manual-baseline', final_score: 7.5 },
        ],
      },
    };
  }

  if (path.includes('/proposals/') && path.endsWith('/select') && method === 'POST') {
    return { body: { ok: true } };
  }

  if (path.endsWith('/approve') && method === 'POST') {
    return { body: { ok: true } };
  }

  if (path.endsWith('/execute') && method === 'POST') {
    return { body: { ok: true } };
  }

  return { status: 404, body: { detail: `Unhandled mock for ${method} ${path}` } };
}
