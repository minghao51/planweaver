# Superpowers Framework Analysis & Integration Report

**Date:** 2026-02-27  
**Source:** https://github.com/obra/superpowers  
**Analysis Type:** Multi-perspective (Technical, Process, Integration)

---

## Executive Summary

Superpowers is an agentic skills framework (~63.7k stars) that provides a comprehensive software development methodology for coding agents. It emphasizes systematic workflows, evidence-based verification, and human-in-the-loop checkpoints. This report analyzes its applicability to the PlanWeaver project and identifies enhancement opportunities.

---

## Part 1: Technical Analysis

### Core Architecture

| Component | Description |
|-----------|-------------|
| **Skill Format** | Markdown with YAML frontmatter (`SKILL.md`) |
| **Skill Structure** | Overview → When to Use → Process → Checklist → Red Flags |
| **Skill Priority** | Project skills > Personal skills > Superpowers skills |
| **Triggering** | Hook-based session injection + agent rule checking |

### Key Technical Patterns

| Pattern | Description | Value |
|---------|-------------|-------|
| **Evidence-Based Verification** | Run fresh verification commands before claiming completion | High |
| **Task Granularity (2-5 min)** | Small units with exact file paths + complete code | High |
| **HARD-GATE Markers** | Non-negotiable rules in skill documentation | High |
| **Two-Stage Review** | Spec compliance → Code quality (sequential) | High |
| **Isolation via Worktrees** | Clean branch per feature | Medium |
| **TDD Enforcement** | RED-GREEN-REFACTOR mandatory | High |

### Technical Limitations

- **Skill Overhead**: 6+ skills in workflow path can feel bureaucratic
- **No Built-in Rollback**: Subagent failures require manual recovery
- **Prompt Injection Risk**: Skills loaded via system prompt
- **Platform-Specific**: Different plugin mechanisms per platform

---

## Part 2: Process/Workflow Analysis

### Core Workflow

```
brainstorming → design approval → writing-plans → subagent-driven-development → review → finish
```

### Process Patterns Worth Adopting

| Pattern | Description |
|---------|-------------|
| **HARD-GATE design approval** | No code before design sign-off |
| **Bite-sized task granularity** | 2-5 minute tasks with exact file paths + code |
| **Two-stage review** | Spec compliance → code quality |
| **TDD enforcement** | Delete code written before tests |
| **Systematic debugging** | 4 phases before any fix |
| **Fresh subagent per task** | No context carryover |

### Identified Process Gaps

| Gap | Recommendation |
|-----|----------------|
| No explicit rollback protocol | Add "if 3+ review failures, abort task and rollback" |
| No time/budget boundaries | Add task timeout or iteration limits |
| Missing cross-task dependency validation | Add task order verification checkpoint |
| No explicit documentation update gate | Add docs verification to review checklist |

---

## Part 3: Integration Recommendations for PlanWeaver

### Direct Adoption Opportunities

| Superpowers Skill | Fit | Notes |
|-------------------|-----|-------|
| `brainstorming` | High | Socratic design refinement |
| `systematic-debugging` | High | 4-phase root cause process |
| `test-driven-development` | High | Formalize existing patterns |
| `finishing-a-development-branch` | Medium | Merge/PR workflow |

### Recommended Custom Skills

#### Priority 1: Intent Brainstorming (`planweaver:intent-brainstorming`)

**Purpose**: Before generating execution plans, refine user intent through questions.

**Process**:
1. Identify scenario type from intent
2. Ask clarifying questions about constraints
3. Propose 2-3 planning approaches
4. Output refined intent for planner

#### Priority 2: Plan Execution (`planweaver:plan-execution`)

**Purpose**: Execute generated plans with verification checkpoints.

**Adaptations**:
- Task granularity: 5-15 min per task (vs 2-5 min)
- Include verification steps for LLM outputs
- Add context-aware checkpoints

#### Priority 3: Context Analysis (`planweaver:context-analysis`)

**Purpose**: Before using external context sources (GitHub, Web Search, Files).

**Key questions**:
- What context sources are relevant?
- How should context be weighted?
- What specific aspects need analysis?

---

## Part 4: Specific Enhancement Proposals

### 1. Planning Template Skills

Create skills for common planning patterns:
- Load scenario YAML
- Generate clarifying questions
- Create proposals
- Execute plan

### 2. Verification Checkpoints

Add skill for verifying execution outputs:
1. Check step outputs match expected format
2. Validate dependencies resolved correctly
3. Verify final output completeness
4. Test edge cases

### 3. Multi-Source Context Integration

```
# Context Fusion Skill
- Combine GitHub + Web Search + File contexts
- Weight and prioritize sources
- Handle conflicts
- Generate unified context for planner
```

### 4. Risk-Aware Planning

Enhance writing-plans with:
- Risk identification per task
- Dependency mapping for tightly-coupled tasks
- Acceptance criteria beyond test verification

---

## Implementation Roadmap

| Priority | Enhancement | Effort | Impact |
|----------|-------------|--------|--------|
| 1 | Install superpowers framework | 30 min | High |
| 2 | Adopt systematic-debugging | 1 day | High |
| 3 | Create intent-brainstorming | 2 days | High |
| 4 | Formalize TDD in plans | 1 day | Medium |
| 5 | Create plan-execution skill | 3 days | High |
| 6 | Add verification checkpoints | 2 days | Medium |

---

## Directory Structure for Custom Skills

```
.opencode/skills/
├── intent-brainstorming/
│   └── SKILL.md
├── plan-execution/
│   └── SKILL.md
├── verification/
│   └── SKILL.md
└── context-analysis/
    └── SKILL.md
```

---

## Key Insights Summary

1. **Superpowers provides a proven methodology** for systematic agentic software development with strong emphasis on TDD and evidence-based verification

2. **The workflow is gate-based**: brainstorming → design → plan → execute → review, with human approval at key points

3. **Task granularity is critical**: 2-5 minute tasks with exact file paths eliminate ambiguity

4. **Two-stage review pattern** (spec compliance → code quality) prevents over/under-building

5. **Integration opportunity exists**: PlanWeaver can adopt core skills while creating domain-specific custom skills for planning

6. **Key gap to address**: Add explicit rollback protocols and time boundaries to prevent runaway subagent execution

---

## References

- Main Repository: https://github.com/obra/superpowers
- Installation Guide: https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
- Writing Plans Skill: https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/writing-plans/SKILL.md
- Brainstorming Skill: https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/brainstorming/SKILL.md
