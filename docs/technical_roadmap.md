# PlanWeaver: Multi-agent planning roadmap

## The core thesis

A single planning LLM has a hard ceiling. It reasons from one perspective, within one context window, using one implicit model of what "good" looks like. Every plan it produces reflects that single perspective — including its blindspots.

Multi-agent planning breaks this ceiling by introducing *productive tension* into the planning loop. Different agents can hold different goals (planner vs critic), different knowledge domains (code vs ops vs research), or different execution strategies (conservative vs aggressive). The interaction between them produces plans that are more robust, more creative, and more explicitly justified than any single agent could generate alone.

The patterns described here are cumulative. Each one addresses a specific structural weakness in single-agent planning, and they compose cleanly with PlanWeaver's existing Planner → Negotiator → DAG Executor architecture.

---

## Part 1: What a single planner fundamentally cannot do

Before proposing solutions it is worth being precise about the limitations being addressed.

**Context window as the planning ceiling.** A single planner must fit the entire goal, all relevant context, all constraints, and all prior decisions into one prompt. For complex goals this means either truncation (losing information) or shallow reasoning (processing information superficially to stay within limits). A coordinator-plus-subplanners architecture distributes this load, allowing each agent to reason deeply about a smaller, well-scoped portion.

**No self-adversarialism.** A planner optimising for "produce a good plan" has no incentive to attack its own output. It will miss edge cases, over-assume stable preconditions, and underestimate steps in its own domain of competence. A dedicated Critic agent with an adversarial objective finds these weaknesses before execution does.

**Single domain knowledge profile.** Prompting one model to be simultaneously expert in Python, cloud infrastructure, SQL performance, and security is a dilution of all four. A specialist sub-planner prompted narrowly as a database expert will produce materially better steps for database work than a generalist planner treating it as one section among many.

**No forward-uncertainty reasoning.** A single planner commits to a path. It cannot model "I am 60% confident this API exists" and hedge the downstream steps accordingly. A scout agent that probes assumptions before the planner finalises the DAG adds probabilistic realism to the plan structure.

**No monitoring or reactive re-planning.** Once execution starts, a single-planner system is blind. If step 4 produces unexpected output that makes step 7 invalid, nothing catches that until step 7 fails. An observer agent watching execution in real-time can surface replanning triggers before failures cascade.

---

## Part 2: Multi-agent planning patterns

### Pattern 1 — Adversarial critic (Planner + Critic pair)

**What it does.** After the Planner proposes a DAG, a Critic agent independently reviews it with an adversarial objective: find the weaknesses. The Critic is not trying to improve the plan — it is trying to break it. It outputs a structured list of objections: invalid assumptions, missing steps, impossible dependencies, security risks, underspecified inputs. The Planner then revises against these objections. The loop runs until the Critic cannot find further objections above a severity threshold, or until a max-rounds limit is reached.

**Why this goes beyond the current abstraction.** The current Optimizer generates variants and rates them, but all variants come from the same planner with the same implicit biases. The Critic comes from an explicitly adversarial posture and can be prompted with a different knowledge profile than the Planner — for instance, a Planner focused on feature delivery paired with a Critic focused on operational risk.

**Implementation.**

New component: `Critic` — an LLM call with an adversarial system prompt and access to the current plan DAG plus the original goal. Outputs structured objections:

```python
class CriticObjection(BaseModel):
    step_id: str | None          # None means plan-level objection
    severity: Literal["fatal", "high", "low"]
    category: Literal["invalid_assumption", "missing_step", "impossible_dep",
                       "security", "underspecified", "resource_risk"]
    description: str
    suggested_fix: str | None

class CriticOutput(BaseModel):
    objections: list[CriticObjection]
    overall_verdict: Literal["reject", "revise", "approve"]
    rounds_remaining: int
```

New session state transition: `planning → critic_review → (revise → planning)*  → negotiating`. The Critic runs automatically after every Planner proposal, before the plan is surfaced to the caller. The caller only sees plans that have survived Critic review (or explicitly requested the raw proposal).

The Critic's objections are stored in the session history and surfaced in the Negotiator's context, so human and agent callers can see why the plan evolved between proposals.

**Effort:** 1.5 weeks. Primarily prompt engineering the Critic and defining the severity escalation policy.

**Key risk:** Critic over-rejection causing planning loops. Mitigate with a `max_critic_rounds` param (default 2) and a `severity_threshold` below which objections are logged but do not force revision.

---

### Pattern 2 — Specialist sub-planners (Coordinator + domain experts)

**What it does.** A Coordinator agent receives the goal and decomposes it into domains (code, infrastructure, data, research, security, etc.). It dispatches each domain slice to a specialist sub-planner whose system prompt is narrowly scoped to that domain. Each sub-planner returns a partial DAG covering its domain. The Coordinator merges the partial DAGs, resolves cross-domain dependencies, and produces the final unified plan.

**Why this goes beyond the current abstraction.** A generalist planner prompted to handle a goal like "build and deploy a data pipeline with a security audit" must context-switch between software engineering, DevOps, and security reasoning in the same chain of thought. Domain specialists operate with tighter, higher-quality prompts, tool access scoped to their domain (a CodePlanner has access to the repo, a SecurityPlanner has access to CVE databases), and can be independently swapped for better models without affecting other domains.

**Implementation.**

New components: `Coordinator`, `SubPlannerRegistry`, and one `SubPlanner` instantiation per domain.

The Coordinator outputs a domain dispatch manifest:

```python
class DomainDispatch(BaseModel):
    domain: str                  # "code" | "infra" | "data" | "security" | "research"
    goal_slice: str              # The portion of the goal this domain handles
    required_inputs: list[str]   # What this sub-plan needs from other domains
    produces: list[str]          # What this sub-plan produces for other domains

class CoordinatorOutput(BaseModel):
    dispatches: list[DomainDispatch]
    coordination_notes: str      # Cross-domain constraints the Coordinator will enforce
```

Each `SubPlanner` runs in parallel (via `asyncio.gather`). Sub-plans are partial DAGs with named boundary nodes representing their `required_inputs` and `produces`. The Coordinator's merge step stitches boundary nodes together into the final DAG, detects and resolves conflicts (two sub-plans claiming to own the same output), and flags unresolvable cross-domain dependencies for human review.

The `SubPlannerRegistry` is a YAML-driven configuration mapping domain names to: system prompt file, default model, tool access list, max steps. This makes adding a new domain a configuration change, not a code change.

**Integration with existing architecture.** The Planner in the current system becomes the Coordinator. The `src/planweaver/planner.py` module gains a `dispatch_mode: bool` flag. When True, it runs Coordinator logic; when False, it runs the existing single-planner logic. This preserves backward compatibility.

**Effort:** 3 weeks. The hardest part is the merge and conflict-resolution logic; partial DAG stitching requires careful handling of dependency edges that cross domain boundaries.

**Key risk:** Coordinator hallucinating cross-domain dependencies that don't exist, causing phantom blocking relationships in the DAG. Mitigate by validating all boundary node connections against the actual outputs declared by sub-plans.

---

### Pattern 3 — Ensemble planning with tournament selection

**What it does.** Rather than one Planner generating one proposal, N Planner instances (3–5) generate N independent proposals for the same goal — using different model temperatures, different few-shot examples from the memory layer, or different planning heuristics. A Judge agent scores each proposal across rubric dimensions (completeness, feasibility, safety, efficiency) and either selects the best or synthesises a hybrid plan that takes the strongest sections from each.

**Why this goes beyond the current abstraction.** The current Optimizer generates variants by prompting the same model to "generate alternatives." This produces variations on a theme — the model's mode plus some noise. Ensemble planning with genuinely different seeds (different models, different context injections, different temperature settings) explores a wider region of plan-space. Tournament selection with a rubric-driven Judge produces an explicit, auditable reason for why one plan was chosen over another — a reason the Negotiator can surface to callers.

**Implementation.**

The Ensemble runner wraps the existing Planner with parallel invocation:

```python
async def run_ensemble(
    goal: str,
    context: PlanContext,
    n_planners: int = 3,
    seeds: list[EnsembleSeed] | None = None,
) -> EnsembleResult:
    seeds = seeds or default_seeds(n_planners)
    proposals = await asyncio.gather(*[
        planner.propose(goal, context, seed=s) for s in seeds
    ])
    judgment = await judge.evaluate(proposals, rubric=default_rubric())
    return EnsembleResult(
        proposals=proposals,
        judgment=judgment,
        selected=judgment.winner,
        hybrid=judgment.synthesized_plan,
    )
```

The `EnsembleSeed` carries model name, temperature, few-shot template ID from the memory layer, and a planning heuristic hint (e.g., "prefer fewer, broader steps" vs "prefer granular, verifiable steps").

The Judge outputs structured scores:

```python
class PlanScore(BaseModel):
    proposal_id: str
    completeness: float      # 0-1: does the plan fully cover the goal?
    feasibility: float       # 0-1: are all steps executable given the constraints?
    safety: float            # 0-1: are irreversible steps appropriately guarded?
    efficiency: float        # 0-1: minimal steps without unnecessary complexity?
    justification: str

class JudgmentOutput(BaseModel):
    scores: list[PlanScore]
    winner: str              # proposal_id of best single plan
    synthesized_plan: Plan | None   # Judge's hybrid if synthesis was attempted
    synthesis_notes: str
```

The ensemble is opt-in at the session level: `POST /sessions` with `{"planning_mode": "ensemble", "n_planners": 3}`. Default remains single-planner for speed.

**Effort:** 2 weeks. The parallelisation and Judge prompt are the main work; the synthesis step is optional and can ship as a later improvement.

**Key risk:** Cost. Three planner calls plus one Judge call is 4x the planning token cost. Mitigate by only running ensemble mode when explicitly requested, or when the Coordinator flags a goal as high-complexity.

---

### Pattern 4 — Context synthesis agents (parallel pre-planning)

**What it does.** Before the Planner sees the goal, a set of context agents run in parallel to build a richer brief. A `RepoAnalyser` summarises relevant code in the linked repository. A `MemoryRetriever` finds similar past plans and their outcomes. A `ConstraintExtractor` identifies unstated constraints implied by the goal (deadline, resource limits, tool restrictions). A `WebResearcher` fetches current information needed to plan (API docs, library versions, recent security advisories). Their outputs are synthesised into a structured `PlanBrief` that becomes the Planner's primary input.

**Why this goes beyond the current abstraction.** The current system allows external context (GitHub, web search, file uploads) but passes it raw to the Planner. The Planner then must summarise, filter, and reason over this context simultaneously with planning — an expensive and error-prone use of its reasoning budget. Dedicated context agents produce pre-digested, structured summaries. The Planner starts with a better brief, not a larger prompt.

**Implementation.**

New module: `src/planweaver/context_synthesis.py`

```python
class PlanBrief(BaseModel):
    goal: str
    codebase_summary: str | None        # from RepoAnalyser
    similar_past_plans: list[PastPlan]  # from MemoryRetriever
    inferred_constraints: list[Constraint]  # from ConstraintExtractor
    external_facts: list[ExternalFact]  # from WebResearcher
    synthesis_confidence: float         # 0-1: how complete is this brief?
    missing_context: list[str]          # gaps that clarifying questions should fill

async def synthesise_context(goal: str, session: Session) -> PlanBrief:
    results = await asyncio.gather(
        repo_analyser.run(goal, session.github_context),
        memory_retriever.run(goal, session.memory_layer),
        constraint_extractor.run(goal),
        web_researcher.run(goal, session.web_context),
        return_exceptions=True
    )
    return brief_synthesiser.merge(goal, results)
```

Each context agent is small and fast — they are summarisation calls, not planning calls. The `PlanBrief` replaces the current ad-hoc context assembly in the Planner's prompt construction. The `missing_context` field feeds directly into the Planner's clarifying question generation, making questions more targeted.

**Effort:** 1.5 weeks. The individual context agents are lightweight; the `brief_synthesiser` merge step requires careful prompt design to avoid information loss.

---

### Pattern 5 — Scout agents for assumption validation

**What it does.** Before the Planner finalises a DAG for execution, a Scout agent identifies steps with unverified preconditions — steps that assume a file exists, an API is reachable, a library version is compatible, a permission is granted. For each such step, it runs a lightweight probe: an HTTP HEAD request, an `import` check, a file stat, a permission test. Steps that fail probing are flagged in the plan with a `precondition_failed` status. The Planner can then revise those steps before they reach execution.

**Why this goes beyond the current abstraction.** Plans routinely fail on invalid assumptions that were easily checkable. The Critic (Pattern 1) catches logical flaws in the plan structure; Scouts catch empirical flaws about the state of the world. This is particularly valuable in multi-agent orchestration contexts where the calling agent may have out-of-date knowledge about the execution environment.

**Implementation.**

New component: `PreconditionScout`

```python
class Precondition(BaseModel):
    step_id: str
    precondition_type: Literal["file_exists", "api_reachable", "import_available",
                                "permission_granted", "env_var_set", "service_running"]
    check_expression: str    # what to verify
    probe_result: bool | None = None
    probe_error: str | None = None

class ScoutReport(BaseModel):
    preconditions: list[Precondition]
    failed: list[Precondition]
    unverifiable: list[Precondition]   # checks that require execution environment access

async def scout_plan(plan: Plan, env_config: EnvConfig) -> ScoutReport:
    preconditions = await precondition_extractor.identify(plan)
    probed = await asyncio.gather(*[
        probe(p, env_config) for p in preconditions
    ])
    return ScoutReport(...)
```

The Scout runs after the Critic and before the plan is surfaced to the caller. Failed preconditions are annotated on the relevant DAG steps. The Negotiator surfaces them clearly: "Step 4 assumes `requests==2.31.0` is installed — this could not be verified in the current environment."

**Effort:** 1 week for the Scout framework. Probe implementations per precondition type add ~1 day each; the first version can ship with the 5 most common types.

---

### Pattern 6 — Observer agent with reactive re-planning

**What it does.** An Observer agent subscribes to the execution event stream. After each step completes, it evaluates whether the step's output is consistent with the plan's assumptions for subsequent steps. If it detects drift — an unexpected output shape, a performance metric outside expected bounds, a partial failure that doesn't trigger a retry — it raises a re-planning signal. Execution pauses at the next safe checkpoint, the Observer's findings are fed to the Planner as new context, and a revised sub-plan is generated for the remaining steps. The original plan is preserved; the revision is a branch appended to the DAG.

**Why this goes beyond the current abstraction.** The current system has retries but no intelligence about whether retrying the same step is the right response. An Observer can distinguish between "this step failed and should be retried" and "this step succeeded but its output makes the next three steps invalid and the plan needs to change." This is the difference between error recovery and adaptive re-planning.

**Integration with the Negotiator.** The Observer's re-planning signal re-enters the system as a message on the session, identical in structure to a human or agent feedback message. The Negotiator processes it, recognises the intent as "mid-execution re-plan triggered by output drift," and routes to the Planner with the Observer's findings as context. No special code path is needed — the session loop handles it naturally.

```python
class ObservationResult(BaseModel):
    step_id: str
    expected_output_schema: dict
    actual_output: dict
    drift_detected: bool
    drift_description: str | None
    recommended_action: Literal["continue", "retry_step", "replan_from_here", "abort"]
    affected_step_ids: list[str]   # downstream steps invalidated by the drift

class Observer:
    async def on_step_complete(self, step: ExecutedStep, plan: Plan) -> ObservationResult:
        ...
    async def synthesise_replan_message(self, findings: list[ObservationResult]) -> str:
        # Returns a natural-language message suitable for re-entering the Negotiator
        ...
```

**Effort:** 2 weeks. The Observer's step evaluation prompt and the checkpoint mechanism for pausing execution are the main work. The session loop integration is minimal.

**Key risk:** Excessive re-planning on noisy step outputs. Mitigate with a drift confidence threshold and a `max_replans_per_session` limit.

---

### Pattern 7 — Debate planning for high-stakes decisions

**What it does.** When the Planner detects a decision point in the goal where multiple fundamentally different approaches exist (e.g., batch vs streaming, monolith vs microservice, SQL vs NoSQL), it spawns a two-agent debate: a Proposer argues for approach A, an Opposer argues for approach B. Each has access to the same context but different objectives. A Synthesiser adjudicates, selecting an approach and recording the reasoning. The selected approach and the losing arguments both become part of the plan's provenance — visible in the session history and searchable in the memory layer.

**Why this goes beyond the current abstraction.** High-stakes architectural decisions made silently by a single planner have no documented reasoning. When an agent caller or a human reviewer later asks "why did you choose approach A," there is no answer. Debate planning externalises the reasoning process, creates auditable decision records, and surfaces trade-offs that would otherwise be implicit.

**Implementation.**

New component: `DebateOrchestrator`, invoked by the Planner when it detects a high-branching decision node.

```python
class DebatePosition(BaseModel):
    approach: str
    arguments_for: list[str]
    arguments_against_opposition: list[str]
    evidence: list[str]

class DebateOutcome(BaseModel):
    decision_question: str
    proposer_position: DebatePosition
    opposer_position: DebatePosition
    synthesiser_ruling: str
    selected_approach: str
    rejected_approach: str
    ruling_rationale: str
    confidence: float

async def run_debate(decision_question: str, context: PlanContext) -> DebateOutcome:
    proposer_pos = await proposer.argue(decision_question, context)
    opposer_pos = await opposer.argue(decision_question, context, against=proposer_pos)
    proposer_rebuttal = await proposer.rebut(opposer_pos)
    return await synthesiser.rule(decision_question, proposer_rebuttal, opposer_pos)
```

Debate outcomes are stored in the session and in the memory layer as `DecisionRecord` objects, indexed by the decision question. Future plans facing the same question can retrieve past rulings as part of the context synthesis brief (Pattern 4), creating a compounding institutional memory of design decisions.

**Effort:** 1.5 weeks. The debate prompts are the core work; the `DecisionRecord` storage integrates with the memory layer built in Phase 1.

---

## Part 3: Implementation roadmap

The patterns above are ordered by their dependency relationships and their return on investment relative to implementation cost. They are grouped into four implementation phases.

---

### Phase 1 — Foundation (weeks 1–4)

**Goal.** Build the session loop and memory layer. These are prerequisites for every other pattern. No multi-agent patterns ship in this phase, but the architecture is built to receive them.

**Week 1–2: Session state machine + Negotiator**

Implement `POST /sessions/{id}/message` as the universal input endpoint. Build the session state machine: `goal_received → clarifying → planning → negotiating → executing → done`. Implement the Negotiator as an LLM call that classifies message intent and outputs a structured plan mutation. This replaces the current binary approve/reject flow.

Deliverables: session model in DB, state machine in `src/planweaver/session.py`, Negotiator in `src/planweaver/negotiator.py`, updated API routes, convergence detector.

**Week 3: Memory layer**

Implement SQLite (local) or Postgres (deployed) persistence for sessions, plan versions, and execution outcomes. Add `sqlite-vec` for embedding-based template retrieval. Port the existing `scenarios/` YAML files as seed templates. Expose `GET /sessions/{id}/similar` for retrieving past plans by semantic similarity to the current goal.

Deliverables: `src/planweaver/memory.py`, DB schema, migration scripts, embedding indexing pipeline.

**Week 4: MCP server adapter + minimal UI**

Wrap the four core session operations (`create_session`, `send_message`, `execute`, `get_state`) as MCP tools. Replace the React frontend with a ~200-line static HTML/JS file served by FastAPI. Drop the TypeScript build pipeline.

Deliverables: `src/planweaver/mcp_server.py`, `static/index.html`, removal of `frontend/` directory.

---

### Phase 2 — Adversarial quality layer (weeks 5–8)

**Goal.** Add the Critic and Scout — the two patterns with the highest quality improvement per effort invested.

**Week 5–6: Adversarial Critic (Pattern 1)**

Build the Critic component with adversarial system prompt and structured `CriticObjection` output. Integrate into the session loop after every Planner proposal. Tune severity thresholds and max-rounds defaults. Write evals using the existing `scenarios/` test cases to measure whether Critic-revised plans have fewer execution failures than unreviewed plans.

Deliverables: `src/planweaver/critic.py`, updated session state transitions, eval harness in `tests/test_critic.py`.

**Week 7: Context synthesis agents (Pattern 4)**

Build `PlanBrief` and the four parallel context agents: `RepoAnalyser`, `MemoryRetriever` (uses memory layer from Phase 1), `ConstraintExtractor`, `WebResearcher`. Replace ad-hoc context assembly in `planner.py` with `synthesise_context()`. Measure reduction in clarifying questions needed after the brief improves Planner input quality.

Deliverables: `src/planweaver/context_synthesis.py`, updated Planner prompt construction.

**Week 8: Scout agents (Pattern 5)**

Build the `PreconditionScout` and implement probes for the five most common precondition types: `file_exists`, `api_reachable`, `import_available`, `env_var_set`, `service_running`. Integrate into the session loop post-Critic, pre-surfacing to caller. Annotate failed preconditions on DAG step objects.

Deliverables: `src/planweaver/scout.py`, `src/planweaver/probes/`, updated DAG step schema.

---

### Phase 3 — Specialist and ensemble planning (weeks 9–14)

**Goal.** Add the coordination patterns that expand plan quality through parallel specialisation.

**Week 9–11: Specialist sub-planners (Pattern 2)**

Build the `Coordinator`, `SubPlannerRegistry` (YAML-driven), and the DAG merge/conflict-resolution logic. Implement three initial domain specialists: `CodePlanner`, `InfraPlanner`, `ResearchPlanner`. The hardest part is the merge step — budget two weeks for this. Ship with `dispatch_mode: false` as default; enable per session via `{"planning_mode": "specialist"}`.

Deliverables: `src/planweaver/coordinator.py`, `src/planweaver/subplanners/`, `config/domains/`, merge logic in `src/planweaver/dag_merge.py`.

**Week 12–13: Ensemble planning with tournament selection (Pattern 3)**

Build the ensemble runner and Judge agent. Implement parallel Planner invocation with configurable seeds (model, temperature, few-shot template). Implement rubric-based scoring and winner selection. Ship the hybrid synthesis step as a separate flag (`{"synthesis": true}`) initially, since it is expensive.

Deliverables: `src/planweaver/ensemble.py`, `src/planweaver/judge.py`, updated session API params.

**Week 14: Debate planning for high-stakes decisions (Pattern 7)**

Build the `DebateOrchestrator` with Proposer, Opposer, and Synthesiser roles. Integrate decision detection into the Planner — a simple heuristic first (goal contains "vs", "or", "alternative") then an LLM-based detector. Store `DecisionRecord` objects in the memory layer. Connect to context synthesis (past decisions surfaced in briefs).

Deliverables: `src/planweaver/debate.py`, `DecisionRecord` schema, memory layer integration.

---

### Phase 4 — Adaptive execution (weeks 15–18)

**Goal.** Add the Observer to make execution intelligent rather than merely robust.

**Week 15–17: Observer agent with reactive re-planning (Pattern 6)**

Build the `Observer` with step evaluation logic and re-planning signal generation. Implement the checkpoint mechanism that pauses execution at safe boundaries. Wire Observer findings back into the session as messages processed by the Negotiator. Add `max_replans_per_session` guard and drift confidence threshold.

Deliverables: `src/planweaver/observer.py`, checkpoint logic in `src/planweaver/executor.py`, integration tests for the re-planning cycle.

**Week 18: Cross-pattern integration and eval suite**

Run end-to-end evals across the full pattern stack using a set of benchmark goals from the `scenarios/` library. Measure: planning latency, execution success rate, re-plan frequency, Critic round counts. Tune all threshold defaults based on eval results. Write the updated architecture documentation.

Deliverables: `tests/evals/`, updated `docs/reference/architecture.md`, performance baseline report.

---

## Part 4: Architectural changes summary

### New components

| Component | Module | Phase | Purpose |
|---|---|---|---|
| `Negotiator` | `negotiator.py` | 1 | Classifies feedback intent, produces plan mutations |
| `SessionStateMachine` | `session.py` | 1 | Orchestrates state transitions across the session lifecycle |
| `MemoryLayer` | `memory.py` | 1 | Cross-session persistence, embedding-based retrieval |
| `MCPServer` | `mcp_server.py` | 1 | Exposes session ops as MCP tools |
| `Critic` | `critic.py` | 2 | Adversarial plan review with structured objections |
| `ContextSynthesiser` | `context_synthesis.py` | 2 | Parallel pre-planning context agents |
| `PreconditionScout` | `scout.py` | 2 | Assumption validation probes before execution |
| `Coordinator` | `coordinator.py` | 3 | Domain dispatch and sub-plan merge |
| `SubPlannerRegistry` | `subplanners/` | 3 | YAML-driven domain specialist configuration |
| `EnsembleRunner` | `ensemble.py` | 3 | Parallel planner invocation with seed variation |
| `Judge` | `judge.py` | 3 | Rubric-based plan scoring and winner selection |
| `DebateOrchestrator` | `debate.py` | 3 | Two-agent debate for high-stakes decisions |
| `Observer` | `observer.py` | 4 | Real-time execution monitoring and re-plan triggering |

### Modified components

| Component | Change |
|---|---|
| `Planner` | Gains `dispatch_mode` flag; plan output feeds Coordinator or remains direct |
| `DAGExecutor` | Gains checkpoint mechanism; emits step events to Observer subscription |
| `API routes` | Collapsed to 6 endpoints centred on session message loop |
| `Config` | `SubPlannerRegistry` YAML replaces hard-coded model defaults |

### Removed components

| Component | Reason |
|---|---|
| React frontend | Replaced by ~200-line static HTML/JS |
| TypeScript build pipeline | No longer needed |
| Separate optimizer route | Folded into first Planner response; Ensemble replaces it |
| Manual normalization endpoint | Replaced by schema validation inline in Planner |
| Session model-selection UI | Moved to API params |

### Data schema additions

```
sessions            — id, goal, status, created_at, metadata
session_messages    — id, session_id, role, content, intent, created_at
plan_versions       — id, session_id, version, dag_json, critic_objections, created_at
execution_outcomes  — id, plan_version_id, step_id, status, output, duration, created_at
plan_templates      — id, name, dag_json, embedding, success_rate, use_count
decision_records    — id, session_id, question, outcome_json, created_at
precondition_results — id, plan_version_id, step_id, type, result, created_at
```

---

## Part 5: Key design principles across all patterns

**Every agent output is a session message.** The Critic's objections, the Scout's findings, the Observer's drift signal, the Debate's ruling — all enter the system as structured messages on the session. The Negotiator processes them. This means the entire multi-agent reasoning chain is inspectable, replayable, and storable in the memory layer without special-casing any agent type.

**Patterns are opt-in at the session level.** A caller requests `{"planning_mode": "ensemble", "critic": true, "scout": true}`. Single-planner mode remains the default. This preserves PlanWeaver's value for simple tasks while making the full multi-agent stack available for complex ones.

**All agents are replaceable.** The Critic, Judge, Coordinator, and Observer are LLM calls with well-defined input/output contracts (Pydantic models). Any of them can be swapped for a different model, a different prompt, or a non-LLM implementation (a static analyser as the Scout, for example) without touching the rest of the system.

**Memory compounds across all patterns.** Past plan quality scores (from the Judge), past Critic objection patterns, past decision records (from Debate), and past execution outcomes (from the Observer) all feed into future context synthesis briefs. The system gets measurably better with every run — not because any model is fine-tuned, but because the context agents surface increasingly relevant prior art.

**The human or agent caller is always an equal participant in the session loop.** The multi-agent patterns run inside the planning engine, improving the quality of what reaches the caller. The caller's interface — the `POST /sessions/{id}/message` endpoint — does not change. Whether the plan was produced by a single planner or a Coordinator-and-specialists ensemble, the caller interacts with the result through the same conversational feedback loop.
