# Roadmap Divergence Analysis
**Generated:** 2026-03-23
**Analysis of:** Current uncommitted changes vs. `docs/technical_roadmap.md`

---

## Executive Summary

The current implementation represents a **partial and inconsistent realization** of the technical roadmap. While some Phase 3 patterns (Specialist Sub-planners, Ensemble, Debate) are implemented but uncommitted, several foundational Phase 1 components (Memory Layer, MCP Server, Minimal UI) and critical Phase 2 patterns (Critic, Context Synthesis) are missing entirely.

**Critical Finding:** The implementation has jumped to Phase 3 patterns without completing Phase 1-2 foundations, creating an architectural gap that violates the roadmap's explicit dependency structure.

---

## Implementation Status by Phase

### ✅ Phase 1: Foundation (Weeks 1-4) — **35% Complete**

| Component | Roadmap Spec | Actual State | Divergence |
|-----------|--------------|--------------|------------|
| **Session State Machine** | `session.py` with VALID_TRANSITIONS | ✅ EXISTS (modified) | Partial - state transitions simplified |
| **Negotiator** | `negotiator.py` intent classifier | ✅ EXISTS | Minor divergence in API |
| **Memory Layer** | `memory.py` with embedding-based retrieval | ❌ MISSING | Critical foundation gap |
| **MCP Server** | `mcp_server.py` with 4 core tools | ❌ MISSING | No MCP integration |
| **Minimal UI** | ~200-line static HTML/JS | ❌ MISSING | React removed, no replacement |
| **API Routes** | Collapsed to 6 endpoints centered on session message loop | ⚠️ PARTIAL | Some routes exist but not session-centric |

**Impact:** Without memory layer and MCP server, Patterns 4 (Context Synthesis) and 7 (Debate) cannot function as specified. The roadmap states these are "prerequisites for every other pattern."

---

### ⚠️ Phase 2: Adversarial Quality Layer (Weeks 5-8) — **40% Complete**

| Component | Roadmap Spec | Actual State | Divergence |
|-----------|--------------|--------------|------------|
| **Critic (Pattern 1)** | `critic.py` with adversarial review | ❌ MISSING | Critical - "highest quality improvement per effort" |
| **Context Synthesis (Pattern 4)** | `context_synthesis.py` with PlanBrief | ❌ MISSING | Affects all downstream planning quality |
| **Scout (Pattern 5)** | `scout.py` with precondition validation | ✅ EXISTS | Probes implemented, uncommitted |
| **Probes** | 5+ precondition types in `probes/` | ✅ EXISTS (6 types) | api_probe, env_var_probe, file_probe, import_probe, service_probe |

**Impact:** Missing Critic means no adversarial review. Missing Context Synthesis means Planner receives raw context instead of pre-digested briefs. Both are specified as having "highest quality improvement per effort invested."

---

### ✅ Phase 3: Specialist & Ensemble Planning (Weeks 9-14) — **60% Complete**

| Component | Roadmap Spec | Actual State | Divergence |
|-----------|--------------|--------------|------------|
| **Coordinator (Pattern 2)** | `coordinator.py` with YAML registry | ✅ EXISTS (uncommitted) | In `services/` not root |
| **Sub-planners** | `subplanners/` directory with domain specialists | ❌ MISSING | Coordinator exists but no specialists |
| **Ensemble (Pattern 3)** | `ensemble.py` with Judge | ✅ EXISTS (uncommitted) | Judge logic embedded, not separate |
| **Judge** | `judge.py` with rubric scoring | ⚠️ PARTIAL | Evaluation logic in ensemble.py |
| **Debate (Pattern 7)** | `debate.py` with Proposer/Opposer/Synthesizer | ✅ EXISTS (uncommitted) | In `services/` not root |

**Impact:** Phase 3 patterns are implemented ahead of their dependencies. Without memory layer, Debate cannot store `DecisionRecord` objects for retrieval in future context synthesis.

---

### ❌ Phase 4: Adaptive Execution (Weeks 15-18) — **0% Complete**

| Component | Roadmap Spec | Actual State | Divergence |
|-----------|--------------|--------------|------------|
| **Observer (Pattern 6)** | `observer.py` with reactive re-planning | ❌ MISSING | Not started |

**Impact:** No reactive re-planning capability. System remains blind during execution.

---

## Architectural Violations

### 1. Dependency Inversion
**Roadmap Rule:** "The patterns described here are cumulative. Each pattern addresses a specific structural weakness... and they compose cleanly."

**Violation:** Phase 3 patterns (Coordinator, Ensemble, Debate) are implemented without their Phase 1-2 dependencies (Memory, MCP, Critic, Context Synthesis).

**Consequence:**
- Debate cannot store/retrieve decision records
- Context agents cannot retrieve similar past plans
- No session-centric API for agent-to-agent communication

### 2. File Structure Divergence
**Roadmap Spec:** Components at root level (`src/planweaver/coordinator.py`)

**Actual:** Components in `services/` subdirectory (`src/planweaver/services/coordinator.py`)

**Impact:** Minor, but creates inconsistency with roadmap documentation.

### 3. Missing Universal Endpoint
**Roadmap Spec:** "Build `POST /sessions/{id}/message` as the universal input endpoint"

**Actual:** API routes modified but not fully session-centric

**Impact:** Violates the "every agent output is a session message" principle.

---

## Missing Data Schema

The roadmap specifies these tables (Part 4, Data Schema Additions):

| Table | Status | Impact |
|-------|--------|--------|
| `sessions` | ⚠️ PARTIAL | Basic session exists, missing state machine metadata |
| `session_messages` | ❌ MISSING | Cannot store message history for Negotiator |
| `plan_versions` | ❌ MISSING | Cannot track critic objections across iterations |
| `execution_outcomes` | ❌ MISSING | Cannot feed Observer findings into memory layer |
| `plan_templates` | ❌ MISSING | Cannot store embedding-indexed templates |
| `decision_records` | ❌ MISSING | Debate outcomes not persistable |
| `precondition_results` | ❌ MISSING | Scout probe results not stored |

**Consequence:** Without `session_messages` and `plan_versions`, the entire session loop architecture cannot function as specified.

---

## Specific Pattern Divergences

### Pattern 1: Adversarial Critic
**Roadmap:** Critic outputs `CriticObjection` with severity, category, suggested_fix

**Actual:** Not implemented

**Missing Features:**
- Adversarial system prompt
- Structured objection schema
- Severity escalation policy
- Max-rounds limit

### Pattern 2: Specialist Sub-planners
**Roadmap:** Coordinator dispatches to YAML-configured domain specialists

**Actual:** Coordinator exists but:
- No `subplanners/` directory
- No domain specialist implementations
- No `SubPlannerRegistry` (YAML config exists but unused)
- Merge logic is simplified (renumber dependencies)

### Pattern 3: Ensemble Planning
**Roadmap:** Judge with rubric scoring (completeness, feasibility, safety, efficiency)

**Actual:** Ensemble uses `PlanEvaluator` but:
- Judge logic not separated
- No explicit `PlanScore` output schema
- No synthesis step

### Pattern 4: Context Synthesis
**Roadmap:** PlanBrief with RepoAnalyser, MemoryRetriever, ConstraintExtractor, WebResearcher

**Actual:** Not implemented

**Missing Features:**
- PlanBrief schema
- Four parallel context agents
- Brief synthesizer merge logic

### Pattern 5: Scout Agents
**Roadmap:** PreconditionScout with probes for file_exists, api_reachable, import_available, permission_granted, env_var_set, service_running

**Actual:** Scout exists with 6 probe types:
- ✅ `api_probe.py`
- ✅ `env_var_probe.py`
- ✅ `file_probe.py`
- ✅ `import_probe.py`
- ✅ `service_probe.py`
- ✅ `base.py`

**Assessment:** This is the closest match to roadmap spec.

### Pattern 6: Observer
**Roadmap:** Observer with step evaluation and re-planning signals

**Actual:** Not implemented

### Pattern 7: Debate Planning
**Roadmap:** DebateOrchestrator with Proposer, Opposer, Synthesiser

**Actual:** DebateService exists but:
- In `services/` not root
- No `DecisionRecord` storage (memory layer missing)
- Cannot retrieve past debates for context synthesis

---

## Critical Gaps Summary

### Must-Have Before Merge
1. **Memory Layer** - Prerequisite for Context Synthesis, Debate, and Ensemble
2. **Session Message Storage** - Prerequisite for Negotiator and session loop
3. **Critic** - Identified as "highest quality improvement per effort"
4. **Minimal UI** - Roadmap specifies ~200-line HTML to replace React (currently removed with no replacement)

### Should-Have Before Merge
1. **MCP Server** - Required for agent-to-agent communication
2. **Context Synthesis** - Required for high-quality planning
3. **Database Schema** - Missing tables prevent full functionality

### Nice-to-Have
1. **Observer** - Phase 4 feature, less critical
2. **Judge Separation** - Can be refactored later
3. **File Structure Consistency** - Minor cosmetic issue

---

## Recommendations

### Immediate Actions (Before Commit)
1. **Implement Memory Layer** - `src/planweaver/memory.py` with embedding-based retrieval
2. **Add Session Message Storage** - Database schema for `session_messages` table
3. **Implement Critic** - `src/planweaver/critic.py` with adversarial review
4. **Add Minimal UI** - `static/index.html` (~200 lines) to replace React
5. **Commit Uncommitted Files** - coordinator.py, ensemble.py, debate.py, scout.py

### Short-term (Within 2 Weeks)
1. **Implement Context Synthesis** - `src/planweaver/context_synthesis.py`
2. **Add MCP Server** - `src/planweaver/mcp_server.py`
3. **Create Domain Specialists** - At least 3 sub-planners (Code, Infra, Research)
4. **Database Migration** - Add all missing tables with proper migrations

### Medium-term (Within 1 Month)
1. **Implement Observer** - `src/planweaver/observer.py`
2. **Separate Judge** - Extract from ensemble.py
3. **Add Decision Records** - Storage for Debate outcomes
4. **Integration Tests** - Full multiagent pattern testing

---

## Conclusion

The current implementation represents a **well-intentioned but premature optimization**. By jumping to Phase 3 patterns without completing Phase 1-2 foundations, the codebase has created complexity that cannot be fully utilized.

**The roadmap is sound.** Its phased approach and dependency ordering are logical. The divergence is not in the roadmap's design, but in the implementation's failure to follow it.

**Recommended Path:** Revert to Phase 1 completion, implement sequentially, and ensure each phase's foundations are solid before building the next phase on top.

---

## Appendix: File Inventory

### Exists (Uncommitted)
- `src/planweaver/services/coordinator.py` (Pattern 2)
- `src/planweaver/services/ensemble.py` (Pattern 3)
- `src/planweaver/services/debate.py` (Pattern 7)
- `src/planweaver/scout.py` (Pattern 5, modified)
- `src/planweaver/session.py` (Phase 1, modified)
- `src/planweaver/negotiator.py` (Phase 1, exists)
- `src/planweaver/probes/*.py` (Pattern 5, 6 files)
- `src/planweaver/models/coordination.py` (New coordination models)
- `tests/test_coordinator.py`
- `tests/test_ensemble.py`
- `tests/test_debate.py`
- `tests/test_scout.py`
- `tests/test_multiagent_integration.py`

### Missing (Roadmap Specified)
- `src/planweaver/memory.py` (Phase 1)
- `src/planweaver/mcp_server.py` (Phase 1)
- `src/planweaver/critic.py` (Phase 2, Pattern 1)
- `src/planweaver/context_synthesis.py` (Phase 2, Pattern 4)
- `src/planweaver/observer.py` (Phase 4, Pattern 6)
- `src/planweaver/judge.py` (Phase 3, Pattern 3 - partial)
- `src/planweaver/subplanners/` (Phase 3, Pattern 2)
- `static/index.html` (Phase 1, minimal UI)
- `config/domains/` (Phase 3, YAML configs)
