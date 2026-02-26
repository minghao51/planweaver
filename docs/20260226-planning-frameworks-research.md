# Planning Frameworks and Methodologies Research

**Date:** 2026-02-26
**Status:** Research Document
**Purpose:** Analyze academic and industry planning frameworks relevant to LLM-based planning systems

## Executive Summary

This document reviews classical AI planning frameworks, modern LLM-based planning approaches, and their relevance to PlanWeaver's architecture. PlanWeaver currently implements a hybrid approach combining LLM reasoning with structured execution, which aligns well with contemporary research trends in neuro-symbolic planning.

---

## 1. Classical AI Planning Frameworks

### 1.1 STRIPS (Stanford Research Institute Problem Solver)

**Overview:** Foundational formalism for symbolic planning (1971)

**Core Components:**
- **States:** Sets of logical propositions (fluents)
- **Actions:** Defined by preconditions, add lists, delete lists
- **Goals:** Set of propositions to achieve
- **Initial State:** Starting configuration

**Key Algorithms:**
- Forward/Backward state-space search
- Heuristic search (A*, WA*, GBFS)
- Planning graphs (Graphplan)
- SAT-based planning

**Relevance to PlanWeaver:**
- PlanWeaver's `locked_constraints` similar to STRIPS state representation
- Execution step dependencies mirror STRIPS action prerequisites
- Could benefit from STRIPS-inspired validation of plan correctness

**Use Cases:**
- Verification that execution graph is acyclic
- Detecting unreachable goals early
- Optimizing step ordering

---

### 1.2 PDDL (Planning Domain Definition Language)

**Overview:** Standardized language for classical planning (1998)

**Structure:**
- **Domain File:** Defines action schemas, predicates, types
- **Problem File:** Specifies objects, initial state, goal

**Key Features:**
- Separation of domain knowledge from problem instances
- Hierarchical typing system
- Support for derived predicates and constraints

**Modern Extensions:**
- **Temporal PDDL:** Time constraints, durations
- **Numeric PDDL:** Continuous variables
- **PDDL3.0:** Soft constraints and preferences

**Relevance to PlanWeaver:**
- PlanWeaver's YAML scenario templates resemble PDDL structure
- Could formalize scenario definitions using PDDL-inspired syntax
- Input/output schemas already similar to typed predicates

**Integration Opportunities:**
```
Current PlanWeaver Scenario:
```yaml
name: "Code Refactoring"
input_schema:
  fields:
    - name: source_files
      type: array
output_schema:
  fields:
    - name: code
      type: string
```

**PDDL-inspired Enhancement:**
```yaml
domain: "code_refactoring"
predicates:
  - (has_file ?path - string)
  - (uses_language ?lang - string)
action: "refactor_file"
parameters:
  - ?file - file_path
precondition: (and (has_file ?file))
effect: (and (not (legacy_code ?file)) (modern_code ?file))
```

---

### 1.3 HTN (Hierarchical Task Networks)

**Overview:** Planning paradigm focused on task decomposition (1970s-80s)

**Core Concepts:**
- **Tasks:** Primitive (executable) vs. Compound (decomposable)
- **Methods:** Rules for decomposing compound tasks into subtasks
- **Task Networks:** Partially ordered sets of tasks with constraints

**Key Features:**
- Natural hierarchy mirrors human problem-solving
- Domain knowledge encoded in decomposition methods
- Efficient for structured domains

**Algorithms:**
- **SHOP/SHOP2:** Simple Hierarchical Ordered Planner
- **HTN-DL:** Distributed HTN planning
- **PyHTN:** Python implementations

**Relevance to PlanWeaver:**
- **STRONG ALIGNMENT** with PlanWeaver's approach
- Current implementation is essentially LLM-based HTN:
  - `decompose_into_steps()` = HTN decomposition
  - `ExecutionStep` tasks = primitive/compound tasks
  - `dependencies` = task network constraints

**PlanWeaver as LLM-HTN Hybrid:**
```
Classical HTN:                    PlanWeaver LLM-HTN:
┌──────────────┐                 ┌──────────────┐
│ Decompose    │                 │ LLM Planner  │
│ Task        │──────────────▶  │ Decompose    │
│ (Methods)   │   Task Network  │ (Prompt)     │
└──────────────┘                 └──────────────┘
       │                                │
       ▼                                ▼
┌──────────────┐                 ┌──────────────┐
│ Execute      │                 │ Execute      │
│ Primitive    │◀───────────────│ Primitive    │
│ Tasks        │  Execution Order│ Steps        │
└──────────────┘                 └──────────────┘
```

**Enhancement Opportunities:**
1. **Formal HTN Methods:** Define decomposition patterns explicitly
2. **Validation:** Verify decompositions maintain soundness
3. **Reuse:** Cache successful decompositions for similar intents
4. **Hierarchical Scenarios:** Multi-level scenario templates

---

### 1.4 GOAP (Goal-Oriented Action Planning)

**Overview:** Planning algorithm popular in game AI and robotics (2000s)

**Key Features:**
- Forward state-space search with heuristics
- Real-time planning capability
- Action cost-based optimization

**Algorithm:**
```
1. Start from initial state
2. For each goal:
   - Find action that achieves goal
   - Add action's preconditions as subgoals
   - Recursively solve subgoals
   - Build plan backwards from goal
```

**Relevance to PlanWeaver:**
- Less directly applicable than HTN
- Could inspire cost-based step selection
- Useful for execution routing optimization

**Potential Application:**
- Assign "costs" to different models (speed vs. quality)
- Optimize execution graph for minimal cost
- Real-time replanning if steps fail

---

## 2. Modern LLM-Based Planning Approaches

### 2.1 Chain-of-Thought (CoT) Planning

**Overview:** Prompting technique to make LLMs show reasoning (Wei et al., 2022)

**Key Papers:**
- "Chain-of-Thought Prompting Elicits Reasoning" (Wei et al., 2022)
- "Zero-shot CoT" (Kojima et al., 2022)

**Methodology:**
```
Input: "Roger has 5 tennis balls. He buys 2 cans of 3 balls. How many?"

CoT Prompt: "Let's think step by step.
Roger started with 5 balls.
2 cans of 3 balls = 6 balls.
5 + 6 = 11 balls."
```

**Relevance to PlanWeaver:**
- Already implicitly used in planner prompts
- Could make CoT steps explicit in `analyze_intent()`
- Useful for debugging plan quality

**Enhancement:**
```python
def analyze_intent_with_cot(self, user_intent: str, plan: Plan):
    prompt = f"""
    Think step-by-step about this request:
    {user_intent}

    Show your reasoning:
    1. What is the user asking for?
    2. What information is known vs. unknown?
    3. What are the logical steps to solve this?

    Then provide your JSON analysis.
    """
    # Returns both CoT reasoning and structured analysis
```

---

### 2.2 ReAct (Reasoning + Acting)

**Overview:** Framework combining reasoning traces with task execution (Yao et al., 2022)

**Key Paper:** "ReAct: Synergizing Reasoning and Acting in Language Models"

**Methodology:**
```
Thought: [Reasoning about what to do]
Action: [Tool/API call]
Observation: [Result of action]
... (repeat)
Thought: [Final answer based on observations]
Answer: [Conclusion]
```

**Relevance to PlanWeaver:**
- **STRONG ALIGNMENT** with current architecture
- Planning phase = "Thought" traces
- Execution phase = "Action" execution
- Already separates reasoning from acting

**Current Implementation vs. ReAct:**
```
ReAct Loop:                      PlanWeaver:
┌─────────┐                     ┌──────────────┐
│ Thought │──────────────────▶  │ Planner      │
│ Reason  │  Formulate action   │ (Reasoning)  │
└─────────┘                     └──────────────┘
    │                                  │
    ▼                                  ▼
┌─────────┐                     ┌──────────────┐
│ Action  │◀───────────────────│ Execution    │
│ Execute │  Execute action     │ Router       │
└─────────┘                     └──────────────┘
    │                                  │
    ▼                                  ▼
┌─────────┐                     ┌──────────────┐
│Observn  │──────────────────▶  │ Step Output  │
│ Result  │  Observe result     │ Aggregation  │
└─────────┘                     └──────────────┘
```

**Enhancement Opportunities:**
1. **Interactive ReAct:** Allow user to interject during execution
2. **Self-Monitoring:** Each step evaluates if goal is achieved
3. **Dynamic Replanning:** Adjust plan based on observations
4. **Tool Use:** Explicit tool invocation in execution steps

---

### 2.3 Tree of Thoughts (ToT)

**Overview:** Deliberate problem-solving by exploring multiple reasoning paths (Yao et al., 2023)

**Key Paper:** "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"

**Methodology:**
```
Current State
    │
    ├── Thought 1 ──► Evaluation 1
    │
    ├── Thought 2 ──► Evaluation 2
    │
    └── Thought 3 ──► Evaluation 3
              │
              ▼
         Select Best
              │
              ▼
         Continue from Best Path
```

**Relevance to PlanWeaver:**
- `generate_strawman_proposals()` already implements ToT concept
- Current proposals are parallel "thoughts"
- User selects best approach (manual evaluation)

**Enhancement Opportunities:**
1. **Automatic Evaluation:** LLM scores proposals on feasibility, cost, quality
2. **Backtracking:** Explore alternative approaches if first fails
3. **Tree Search:** BFS/DFS through proposal space
4. **Monte Carlo ToT:** Sample and evaluate multiple approaches

**Implementation:**
```python
def generate_and_score_proposals(self, user_intent: str, num_proposals=3):
    proposals = self.generate_strawman_proposals(user_intent)

    # Score each proposal
    for proposal in proposals:
        proposal.score = self.evaluate_proposal(
            user_intent=user_intent,
            proposal=proposal,
            criteria=["feasibility", "cost", "quality"]
        )

    # Sort by score
    return sorted(proposals, key=lambda p: p.score, reverse=True)
```

---

### 2.4 Task Decomposition with LLMs

**Overview:** Breaking complex tasks into subtasks using language models

**Key Approaches:**

**a) Plan-and-Solve (Wang et al., 2023)**
- Generate high-level plan
- Execute each step with detailed reasoning
- Reduces hallucination through structured approach

**b) Reflexion (Shinn et al., 2023)**
- Generate initial plan
- Execute and collect feedback
- Reflect on failures
- Generate improved plan

**c) TaskMatrix (Liang et al., 2023)**
- Multimodal task decomposition
- API calls for subtasks
- Visual grounding

**d) AutoGPT / BabyAGI (2023)**
- Autonomous task generation
- Self-directed planning
- Recursive decomposition

**Relevance to PlanWeaver:**
- `decompose_into_steps()` is core LLM decomposition
- Could incorporate Reflexion-style feedback loops
- AutoGPT-style autonomy could be optional mode

**Current Limitations:**
- One-shot decomposition (no iteration)
- No self-reflection on plan quality
- Fixed depth (single-level decomposition)

**Enhancement: Reflexion-Inspired Planning**
```python
def decompose_with_reflection(self, user_intent, constraints, max_iterations=3):
    for i in range(max_iterations):
        steps = self.decompose_into_steps(user_intent, constraints)

        # Self-evaluate
        evaluation = self.evaluate_plan(
            user_intent=user_intent,
            steps=steps
        )

        if evaluation["is_valid"]:
            return steps

        # Refine based on issues
        constraints.update(evaluation["missing_constraints"])

    return steps  # Return best effort after iterations
```

---

### 2.5 Multi-Agent Planning

**Overview:** Multiple LLM agents collaborating on complex tasks

**Key Frameworks:**
- **CAMEL:** Communicative agents for role-playing
- **AutoGen:** Microsoft's multi-agent framework
- **MetaGPT:** Software company simulation
- **ChatDev:** Multi-agent software development

**Architectures:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Agent 1   │    │   Agent 2   │    │   Agent 3   │
│  (Planner)  │───▶│  (Coder)    │───▶│  (Tester)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                    Coordination
```

**Relevance to PlanWeaver:**
- Currently single-agent (planner → executor)
- Could assign specialized roles to execution steps
- Natural fit for `code_refactoring.yaml` scenario

**Enhancement: Multi-Agent Execution**
```python
class SpecialistAgent:
    def __init__(self, role, expertise):
        self.role = role  # "architect", "coder", "tester", "reviewer"
        self.expertise = expertise

    def execute_step(self, step, context):
        # Role-specific execution
        pass

# In router.py
def execute_with_agents(self, plan):
    agents = {
        "architecture": SpecialistAgent("architect", "system design"),
        "coding": SpecialistAgent("coder", "implementation"),
        "testing": SpecialistAgent("tester", "validation")
    }

    for step in plan.execution_graph:
        agent = agents.get(step.agent_role, default_agent)
        step.output = agent.execute_step(step, context)
```

---

## 3. Industry-Standard Planning Approaches

### 3.1 Workflow Engines

**Overview:** Business process management and orchestration systems

**Examples:**
- **Apache Airflow:** DAG-based workflow orchestration
- **Prefect:** Modern workflow engine
- **Temporal:** Durable execution system
- **Argo Workflows:** Kubernetes-native workflows

**Key Features:**
- DAG-based execution (like PlanWeaver)
- Retries, caching, state management
- Monitoring and observability
- Scaling and distribution

**Relevance to PlanWeaver:**
- ExecutionRouter already implements DAG execution
- Could adopt industry patterns for robustness

**Enhancement Opportunities:**

**a) State Persistence (Temporal-style):**
```python
class DurableExecutionStep(ExecutionStep):
    checkpoint_key: Optional[str] = None

    def save_checkpoint(self, state):
        # Save to durable store
        pass

    def restore_from_checkpoint(self):
        # Resume from saved state
        pass
```

**b) Dynamic DAG Updates:**
```python
def execute_with_replanning(self, plan):
    for step in plan.execution_graph:
        result = self.execute_step(step)

        # Dynamic step insertion based on results
        if result["needs_testing"]:
            new_step = ExecutionStep(
                task="Generate test cases",
                dependencies=[step.step_id]
            )
            plan.add_step(new_step)
```

**c) Observability (Airflow-style):**
```python
class ObservableRouter:
    def execute_plan(self, plan):
        with self.observer.span("plan_execution") as span:
            span.set_attribute("session_id", plan.session_id)

            for step in plan.execution_graph:
                with self.observer.span("step_execution") as step_span:
                    step_span.set_attribute("step_id", step.step_id)
                    result = self.execute_step(step)
                    step_span.set_attribute("status", "completed")
```

---

### 3.2 Agile and Scrum Planning

**Overview:** Industry-standard iterative development frameworks

**Key Concepts:**
- Sprints/Iterations (2-4 weeks)
- Backlog refinement
- Story points estimation
- Retrospective improvement

**Relevance to PlanWeaver:**
- PlanWeaver plans resemble sprint backlogs
- Execution steps are like sprint tasks
- Could incorporate agile terminology/metrics

**Enhancement: Agile-Inspired Planning**
```python
class AgilePlan(Plan):
    sprint_duration: int = Field(default=7)  # days
    story_points_total: int = Field(default=0)
    velocity_history: List[int] = Field(default_factory=list)

    def estimate_velocity(self):
        """Estimate completion based on historical velocity"""
        if not self.velocity_history:
            return None
        avg_velocity = sum(self.velocity_history) / len(self.velocity_history)
        return self.story_points_total / avg_velocity

    def split_into_sprints(self, sprint_capacity):
        """Divide execution graph into sprints"""
        sprints = []
        current_sprint = []
        current_points = 0

        for step in self.execution_graph:
            if current_points + step.story_points <= sprint_capacity:
                current_sprint.append(step)
                current_points += step.story_points
            else:
                sprints.append(current_sprint)
                current_sprint = [step]
                current_points = step.story_points

        return sprints
```

---

### 3.3 DevOps and CI/CD Pipelines

**Overview:** Automated software delivery pipelines

**Examples:**
- Jenkins, GitHub Actions, GitLab CI
- Stages: Build → Test → Deploy → Monitor

**Relevance to PlanWeaver:**
- Linear DAG with stages
- Conditional execution based on test results
- Parallel execution where possible

**Enhancement: Stage-Based Execution**
```python
class ExecutionStage(str, Enum):
    PREPARATION = "PREPARATION"
    IMPLEMENTATION = "IMPLEMENTATION"
    VALIDATION = "VALIDATION"
    DEPLOYMENT = "DEPLOYMENT"

class StagedExecutionStep(ExecutionStep):
    stage: ExecutionStage
    gate_conditions: List[str] = Field(default_factory=list)

def execute_by_stages(self, plan):
    stages = {
        ExecutionStage.PREPARATION: [],
        ExecutionStage.IMPLEMENTATION: [],
        ExecutionStage.VALIDATION: [],
        ExecutionStage.DEPLOYMENT: []
    }

    # Group steps by stage
    for step in plan.execution_graph:
        stages[step.stage].append(step)

    # Execute sequentially through stages
    for stage in ExecutionStage:
        for step in stages[stage]:
            # Check gate conditions
            if all(self.check_condition(c) for c in step.gate_conditions):
                self.execute_step(step)
```

---

## 4. Comparative Analysis: Planning Paradigms for LLMs

### 4.1 Comparison Matrix

| Paradigm | Strengths | Weaknesses | LLM Fit | PlanWeaver Fit |
|----------|-----------|------------|---------|----------------|
| **STRIPS** | Formal verification, soundness | Brittle, doesn't scale | Low (symbolic) | Medium (validation) |
| **PDDL** | Standardized, expressive | Complex syntax | Low | Medium (scenarios) |
| **HTN** | Natural hierarchy, efficient | Requires domain methods | **High** | **Very High** |
| **GOAP** | Real-time, cost-optimal | Simple domains | Medium | Low (not needed) |
| **CoT** | Improves reasoning | Can still hallucinate | **High** | **High** (implicit) |
| **ReAct** | Reasoning + acting | Slow, many calls | **High** | **Very High** (core pattern) |
| **ToT** | Explores alternatives | Computationally expensive | Medium | **High** (proposals) |
| **Multi-Agent** | Parallelization, specialization | Coordination overhead | High | Medium (future) |

### 4.2 Use Case Suitability

**Complex Problem Decomposition:**
- Best: HTN, ToT, Reflexion
- PlanWeaver: Already uses HTN + ToT
- Enhancement: Add Reflexion-style iteration

**Real-Time Execution:**
- Best: GOAP, ReAct
- PlanWeaver: ReAct-style already
- Enhancement: Add streaming execution

**Uncertain Environments:**
- Best: Reflexion, ReAct with replanning
- PlanWeaver: Limited (static execution graph)
- Enhancement: Dynamic replanning on failure

**Multi-Step Reasoning:**
- Best: CoT, ToT
- PlanWeaver: Implicit CoT in planner
- Enhancement: Make CoT explicit and inspectable

**Collaborative Planning:**
- Best: Multi-agent systems
- PlanWeaver: Single-agent
- Enhancement: Specialist agents per step type

---

## 5. Recommended Framework Combinations for PlanWeaver

### 5.1 Core Foundation: HTN + ReAct

**Rationale:** This is already PlanWeaver's implicit architecture. Formalize and enhance.

**Enhancements:**
1. **Explicit HTN Methods:** Define decomposition patterns in scenarios
   ```yaml
   decomposition_methods:
     - name: "refactor_to_typescript"
       compound_task: "Refactor codebase to TypeScript"
       subtasks:
         - task: "Analyze codebase structure"
           type: "analysis"
         - task: "Generate type definitions"
           type: "generation"
           depends_on: ["analyze_structure"]
         - task: "Migrate files to TS"
           type: "implementation"
           depends_on: ["generate_types"]
         - task: "Update tests"
           type: "validation"
           depends_on: ["migrate_files"]
   ```

2. **ReAct Traces:** Make reasoning explicit and visible
   ```python
   class ReasoningTrace(BaseModel):
       thought: str
       action: str
       observation: Optional[str] = None
       timestamp: datetime

   class AnalyzedPlan(Plan):
       reasoning_history: List[ReasoningTrace] = []
   ```

3. **Self-Monitoring:** Each step evaluates if goal is achieved
   ```python
   def execute_step_with_monitoring(self, step, context):
       result = self.execute_step(step, context)

       # Self-evaluation
       evaluation = self.llm.complete(
           prompt=f"""
           Did this step successfully achieve its goal?

           Step: {step.task}
           Result: {result}
           Original Intent: {plan.user_intent}

           Evaluate: SUCCESS, PARTIAL, or FAILED
           Reasoning: [explain why]
           """
       )

       return result, evaluation
   ```

---

### 5.2 Quality Enhancement: ToT + Reflexion

**Rationale:** Improve plan quality through exploration and iteration.

**Implementation:**

**a) Proposal Exploration (ToT):**
```python
def explore_proposal_space(self, user_intent, num_proposals=5):
    """Generate and explore multiple approaches"""
    proposals = []

    for i in range(num_proposals):
        # Generate diverse proposals
        proposal = self.generate_proposal(
            user_intent=user_intent,
            diversity_prompt=f"Think of a different angle than previous proposals"
        )
        proposals.append(proposal)

    # Evaluate all proposals
    scored_proposals = []
    for proposal in proposals:
        score = self.evaluate_proposal(proposal, user_intent)
        scored_proposals.append((proposal, score))

    # Return top 3 for user selection
    return sorted(scored_proposals, key=lambda x: x[1], reverse=True)[:3]
```

**b) Iterative Refinement (Reflexion):**
```python
def refine_plan_with_reflection(self, plan, max_iterations=3):
    """Iteratively improve the plan"""
    for iteration in range(max_iterations):
        # Reflect on current plan
        reflection = self.reflect_on_plan(plan)

        if reflection["is_satisfactory"]:
            break

        # Refine based on reflection
        plan = self.refine_plan(
            plan=plan,
            feedback=reflection["improvement_suggestions"]
        )

    return plan

def reflect_on_plan(self, plan):
    """LLM evaluates plan quality"""
    return self.llm.complete(
        prompt=f"""
        Critique this execution plan:

        Intent: {plan.user_intent}
        Steps: {[s.task for s in plan.execution_graph]}

        Evaluate:
        1. Are all necessary steps included?
        2. Are steps in logical order?
        3. Are there missing dependencies?
        4. Is any step redundant?

        Return JSON with "is_satisfactory" and "improvement_suggestions"
        """,
        json_mode=True
    )
```

---

### 5.3 Robustness Enhancement: Classical Planning Validation

**Rationale:** Use formal methods to catch logical errors.

**Implementation:**

**a) DAG Validation:**
```python
def validate_execution_graph(self, steps):
    """Ensure execution graph is valid DAG"""
    # Check for cycles
    if self.has_cycles(steps):
        raise ValueError("Execution graph contains cycles")

    # Check for unreachable steps
    reachable = self.get_reachable_steps(steps)
    unreachable = [s for s in steps if s not in reachable]
    if unreachable:
        logger.warning(f"Unreachable steps: {[s.task for s in unreachable]}")

    # Check for dead ends (steps not leading to output)
    dead_ends = self.find_dead_ends(steps)
    if dead_ends:
        logger.warning(f"Dead-end steps: {[s.task for s in dead_ends]}")

    return True
```

**b) STRIPS-style Precondition Checking:**
```python
class ValidatedExecutionStep(ExecutionStep):
    preconditions: List[str] = Field(default_factory=list)
    expected_effects: List[str] = Field(default_factory=list)

def validate_step_preconditions(self, step, completed_steps):
    """Verify all preconditions are met before execution"""
    for precondition in step.preconditions:
        if not self.check_precondition(precondition, completed_steps):
            raise ValueError(
                f"Step {step.task} precondition not met: {precondition}"
            )
    return True
```

---

### 5.4 User Experience Enhancement: Agile + Interactive

**Rationale:** Make planning feel collaborative and transparent.

**Implementation:**

**a) Interactive Planning Session:**
```python
class InteractivePlanner:
    async def plan_collaboratively(self, user_intent):
        """Plan with user at each step"""
        # Step 1: Initial analysis
        analysis = await self.analyze_intent(user_intent)
        await self.show_to_user("Analysis", analysis)

        # Step 2: Clarifying questions
        for question in analysis["missing_information"]:
            answer = await self.ask_user(question)
            analysis["locked_constraints"][question] = answer

        # Step 3: Generate proposals
        proposals = await self.generate_proposals(user_intent, analysis)
        selected = await self.ask_user("Select approach", proposals)

        # Step 4: Decompose (with preview)
        steps = await self.decompose_into_steps(user_intent, analysis)
        await self.show_to_user("Proposed steps", steps)

        if not await self.confirm_user("Proceed with these steps?"):
            refined = await self.refine_with_feedback(steps, user_feedback)
            steps = refined

        # Step 5: Execute (with checkpoints)
        for step in steps:
            result = await self.execute_step(step)
            await self.show_to_user(f"Completed: {step.task}", result)

            if not await self.confirm_user("Continue?"):
                # Allow replanning
                steps = await self.adjust_remaining_plan(steps, step)
```

**b) Sprint-Based Progress Tracking:**
```python
class SprintProgress:
    sprint_number: int
    total_steps: int
    completed_steps: int
    estimated_remaining: timedelta

    def get_progress_percentage(self):
        return (self.completed_steps / self.total_steps) * 100

    def get_eta(self):
        """Estimate time to completion"""
        avg_time_per_step = self.total_time / self.completed_steps
        remaining_steps = self.total_steps - self.completed_steps
        return timedelta(seconds=avg_time_per_step * remaining_steps)
```

---

## 6. Future Research Directions

### 6.1 Neuro-Symbolic Planning

**Concept:** Combine neural LLM reasoning with symbolic planners.

**Approaches:**
- LLM translates natural language to PDDL
- Classical planner finds optimal plan
- LLM translates plan back to execution steps

**Benefits:**
- Optimal plans (from classical planner)
- Natural language interface (from LLM)
- Verifiable correctness (from formal methods)

**Research Papers:**
- "LLM-PDDL: Translating Natural Language to Planning Domains"
- "SymTree: Symbolic Tree Search with Language Models"
- "PlanGuard: Verified Planning with LLMs"

---

### 6.2 Planning with Memory

**Concept:** LLM planners learn from past plans.

**Approaches:**
- Vector database of successful plans
- Retrieve similar plans as examples
- Adapt retrieved plans to current context

**Benefits:**
- Faster planning (reuse successful patterns)
- Better quality (learn from experience)
- Consistency (standard approaches to common tasks)

**Implementation:**
```python
class PlanMemory:
    def __init__(self, vector_db):
        self.db = vector_db

    def store_plan(self, plan, success_rating):
        """Store successful plan for reuse"""
        embedding = self.embed_intent(plan.user_intent)
        self.db.store(
            embedding=embedding,
            plan=plan,
            metadata={"success": success_rating}
        )

    def retrieve_similar_plans(self, user_intent, k=3):
        """Find similar past plans"""
        embedding = self.embed_intent(user_intent)
        return self.db.search(embedding, k=k)

    def adapt_plan(self, template_plan, new_context):
        """Adapt retrieved plan to new context"""
        return self.llm.complete(
            prompt=f"""
            Adapt this template plan to the new context:

            Template: {template_plan.execution_graph}
            New Intent: {new_context}

            Return adapted execution steps.
            """
        )
```

---

### 6.3 Hierarchical Context Management

**Concept:** Multi-level context for different planning phases.

**Levels:**
1. **Global Context:** Project-level knowledge
2. **Session Context:** Current planning session
3. **Step Context:** Specific to execution step

**Benefits:**
- Reduces context window pressure
- Enables selective attention
- Improves plan coherence

**Implementation:**
```python
class HierarchicalContext:
    global_context: Dict[str, Any]  # Project-wide
    session_context: Dict[str, Any]  # Session-specific
    step_context: Dict[int, Dict[str, Any]]  # Per-step

    def get_context_for_step(self, step_id):
        """Assemble relevant context for step"""
        return {
            **self.global_context,  # Base context
            **self.session_context,  # Session overrides
            **self.step_context.get(step_id, {})  # Step-specific
        }

    def prune_context(self, max_tokens):
        """Optimize context size"""
        # Keep highest-relevance context items
        ranked = self.rank_by_relevance()
        return top_k_items(ranked, max_tokens)
```

---

### 6.4 Causal Planning

**Concept:** Plan based on causal models of system behavior.

**Approaches:**
- Extract causal chains from LLM reasoning
- Validate causal assumptions during execution
- Replan if causal chain breaks

**Benefits:**
- More robust to unexpected failures
- Better understanding of plan rationale
- Explainable plans

**Research:**
- "CausalPy: Causal Reasoning with LLMs"
- "Chain of Causation: Structured Planning"
- "CausalAgent: Causal Planning for Embodied AI"

---

## 7. Implementation Recommendations for PlanWeaver

### 7.1 Immediate Enhancements (1-2 weeks)

1. **Explicit Reasoning Traces**
   - Add `reasoning_history` to Plan model
   - Capture planner thoughts in `analyze_intent()`
   - Display to user for transparency

2. **Proposal Scoring**
   - Auto-score strawman proposals
   - Show scores to user alongside pros/cons
   - Sort by score for better UX

3. **DAG Validation**
   - Add cycle detection in execution graph
   - Warn about unreachable steps
   - Validate dependencies are satisfied

4. **Step Preconditions**
   - Add optional `preconditions` to ExecutionStep
   - Validate before execution
   - Better error messages when preconditions fail

---

### 7.2 Medium-Term Enhancements (1-2 months)

1. **Reflexion-Inspired Iteration**
   - Add plan self-evaluation
   - Iterate on plan quality
   - Learn from failed executions

2. **HTN Method Definitions**
   - Define decomposition patterns in scenarios
   - More structured task decomposition
   - Reusable decomposition methods

3. **Interactive Execution**
   - Allow user to interject during execution
   - Adjust remaining steps based on feedback
   - Real-time progress monitoring

4. **Plan Memory**
   - Store successful plans in vector DB
   - Retrieve similar plans for reuse
   - Adapt plans to new contexts

---

### 7.3 Long-Term Research (3-6 months)

1. **Neuro-Symbolic Planning**
   - LLM → PDDL translation
   - Classical planning optimization
   - PDDL → execution steps

2. **Multi-Agent Execution**
   - Specialist agents for step types
   - Agent collaboration protocols
   - Distributed execution

3. **Causal Planning**
   - Extract causal models from plans
   - Validate causal assumptions
   - Causal replanning on failures

4. **Hierarchical Context**
   - Multi-level context management
   - Context pruning and optimization
   - Context relevance scoring

---

## 8. Conclusion

PlanWeaver's current architecture aligns well with modern LLM-based planning research, particularly the **HTN + ReAct** paradigm. The system already implements:

- Hierarchical task decomposition (HTN-style)
- Separation of reasoning and execution (ReAct-style)
- Strawman proposal generation (ToT-style)
- External context integration (context-aware planning)

**Key Recommendations:**

1. **Formalize HTN structure:** Make decomposition methods explicit in scenarios
2. **Add reasoning traces:** Capture and display planner thought process
3. **Implement Reflexion:** Iterate on plan quality with self-evaluation
4. **Classical validation:** Use formal methods to catch logical errors
5. **Build plan memory:** Learn from and reuse successful plans

**Strategic Positioning:**

PlanWeaver sits at the intersection of:
- Classical AI planning (HTN, DAGs)
- LLM reasoning (CoT, ReAct)
- Industry workflows (DAG execution, agile planning)

This hybrid approach is both theoretically sound and practically valuable, positioning PlanWeaver as a robust framework for LLM-based planning and execution.

---

## 9. References

### Classical Planning
- Fikes & Nilsson (1971). "STRIPS: A New Approach to the Application of Theorem Proving"
- Ghallab et al. (2004). "Automated Planning: Theory & Practice"
- Erol et al. (1994). "HTN Planning: Complexity and Expressivity"

### LLM Planning
- Wei et al. (2022). "Chain-of-Thought Prompting Elicits Reasoning"
- Yao et al. (2022). "ReAct: Synergizing Reasoning and Acting in Language Models"
- Yao et al. (2023). "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
- Shinn et al. (2023). "Reflexion: Language Agents with Verbal Reinforcement Learning"
- Wang et al. (2023). "Plan-and-Solve: Breaking Down Complex Problems"

### Multi-Agent Systems
- Liang et al. (2023). "TaskMatrix: Multi-Agent Collaborative Planning"
- Qian et al. (2023). "Communicative Agents for Role Playing"
- Wu et al. (2023). "AutoGen: Enabling Multi-Agent LLM Applications"

### Neuro-Symbolic Planning
- Silver et al. (2023). "LLM-PDDL: Translating Natural Language to Planning Domains"
- Jinnai et al. (2023). "SymTree: Symbolic Tree Search with Language Models"

---

**Document Version:** 1.0
**Last Updated:** 2026-02-26
**Next Review:** 2026-03-31
