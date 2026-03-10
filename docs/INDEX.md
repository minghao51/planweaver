# PlanWeaver Documentation Index

Complete index of PlanWeaver documentation organized by audience and purpose.

## 📚 Documentation Map

```
docs/
├── INDEX.md                    # This file - documentation index
├── architecture.md             # Comprehensive system architecture
├── api-reference.md            # Complete API endpoint reference
├── deployment-guide.md         # Deployment and production setup
├── external-context-guide.md   # External context feature guide
├── plan-optimizer-guide.md     # Plan Optimizer feature guide
├── TEST.md                     # Testing guide and strategies
└── troubleshooting.md          # (planned) Troubleshooting guide
```

---

## 🚀 Quick Start

**New to PlanWeaver?** Start here:

1. **[README.md](../README.md)** - Project overview, quick start, and basic usage
2. **[architecture.md](architecture.md)** - System design and component overview
3. **[deployment-guide.md](deployment-guide.md)** - Running PlanWeaver locally or in production

---

## 👥 For Users

### Getting Started

| Document | Description | Audience |
|----------|-------------|----------|
| [README.md](../README.md) | Quick start, features, and basic usage | All users |
| [external-context-guide.md](external-context-guide.md) | Using GitHub, web search, and file uploads | Users wanting enhanced planning |
| [plan-optimizer-guide.md](20260227-plan-optimizer-guide.md) | Using the Plan Optimizer feature | Users wanting optimized variants |

### API Documentation

| Document | Description |
|----------|-------------|
| [api-reference.md](api-reference.md) | Complete API endpoint reference with examples |
| [Swagger UI](http://localhost:8000/docs) | Interactive API documentation (requires running server) |

---

## 🔧 For Contributors

### Development Setup

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Development setup, code style, and contribution guidelines |
| [frontend/README.md](../frontend/README.md) | Frontend development guide and component architecture |

### Testing

| Document | Description |
|----------|-------------|
| [TEST.md](TEST.md) | Testing guide and current test coverage |

### Project Structure

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | System architecture and component details |
| [.planning/codebase/](../.planning/codebase/) | Detailed codebase documentation (7 files) |

---

## 🏗️ Architecture Documentation

### Primary Documents

| Document | Description | Last Updated |
|----------|-------------|--------------|
| [architecture.md](architecture.md) | **PRIMARY** - Comprehensive architecture reference | 2025-02-27 |
| [20250215-ARCHITECTURE.md](../20250215-ARCHITECTURE.md) | Earlier architecture document (superseded) | 2025-02-15 |

### Research Documents (Historical)

| Document | Description | Date |
|----------|-------------|------|
| [20260227-superpowers-analysis.md](20260227-superpowers-analysis.md) | Superpowers framework analysis | 2025-02-27 |
| [20260227-plan-optimizer-implementation-summary.md](20260227-plan-optimizer-implementation-summary.md) | Plan Optimizer implementation summary | 2025-02-27 |
| [20260226-planning-enhancement-research.md](20260226-planning-enhancement-research.md) | Planning enhancement research | 2025-02-26 |
| [20260226-planning-frameworks-research.md](20260226-planning-frameworks-research.md) | Planning frameworks research | 2025-02-26 |
| [plans/2026-03-08-planning-evaluation-architecture.md](plans/2026-03-08-planning-evaluation-architecture.md) | Proposed planning and evaluation architecture | 2026-03-08 |
| [20260216-project-docs.md](20260216-project-docs.md) | Project documentation | 2025-02-16 |

**Note:** Research documents are historical and may not reflect current implementation.

---

## 🚢 Deployment & Operations

### Deployment

| Document | Description |
|----------|-------------|
| [deployment-guide.md](deployment-guide.md) | Docker, Docker Compose, cloud deployment, monitoring |

### Operations

| Document | Description | Status |
|----------|-------------|--------|
| [troubleshooting.md](troubleshooting.md) | Common issues and solutions | Planned |
| [CHANGELOG.md](../CHANGELOG.md) | Version history and changes | Published |

---

## 📖 Feature Guides

### Core Features

| Document | Feature | Description |
|----------|---------|-------------|
| [external-context-guide.md](external-context-guide.md) | External Context | Enhance plans with GitHub repos, web search, and files |
| [plan-optimizer-guide.md](20260227-plan-optimizer-guide.md) | Plan Optimizer | Generate AI-optimized variants with multi-model rating |

### Advanced Features

See [api-reference.md](api-reference.md) for all API capabilities including:
- Interactive planning with clarifying questions
- Strawman proposal generation
- DAG-based execution
- Model selection and overrides

---

## 🔌 API Reference

| Document | Description | Format |
|----------|-------------|--------|
| [api-reference.md](api-reference.md) | Complete API documentation with examples | Markdown |
| [Swagger UI](http://localhost:8000/docs) | Interactive API explorer | Web UI |
| [ReDoc](http://localhost:8000/redoc) | Alternative API documentation | Web UI |

---

## 📝 Project Documentation

### Project Files

| File | Description |
|------|-------------|
| [README.md](../README.md) | Project overview and quick start |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |
| [CHANGELOG.md](../CHANGELOG.md) | Version history |
| [LICENSE](../LICENSE) | License information |

### Planning & Research

| Directory | Description |
|-----------|-------------|
| [docs/plans/](plans/) | Implementation plans and designs |
| [.planning/codebase/](../.planning/codebase/) | Codebase documentation (7 comprehensive files) |

---

## 📂 Documentation by Location

### Root Directory

```
planweaver/
├── README.md                 # Project overview
├── CONTRIBUTING.md           # Contributing guidelines
├── CHANGELOG.md              # Version history
└── 20250215-ARCHITECTURE.md  # Legacy architecture doc
```

### Frontend Directory

```
frontend/
└── README.md                 # Frontend development guide
```

### Docs Directory

```
docs/
├── INDEX.md                              # This index
├── architecture.md                        # System architecture (PRIMARY)
├── api-reference.md                       # API documentation
├── deployment-guide.md                    # Deployment guide
├── external-context-guide.md              # External context feature
├── plan-optimizer-guide.md                # Plan optimizer feature
├── TEST.md                                # Testing guide
└── plans/                                 # Implementation plans
```

---

## 🎯 Documentation by Use Case

### "I want to use PlanWeaver"

1. Read [README.md](../README.md)
2. Follow [deployment-guide.md](deployment-guide.md) to get started
3. Explore [external-context-guide.md](external-context-guide.md) for advanced features

### "I want to contribute code"

1. Read [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Study [architecture.md](architecture.md)
3. Check [TEST.md](TEST.md) for testing guidelines
4. See [frontend/README.md](../frontend/README.md) for frontend work

### "I want to integrate with the API"

1. Review [api-reference.md](api-reference.md)
2. Check [Swagger UI](http://localhost:8000/docs) for interactive testing
3. See [README.md](../README.md) for code examples

### "I want to deploy to production"

1. Read [deployment-guide.md](deployment-guide.md)
2. Configure environment variables
3. Set up monitoring and backups
4. Review security considerations

### "I want to understand the architecture"

1. Start with [architecture.md](architecture.md) (comprehensive)
2. Review component documentation in-code
3. Check [.planning/codebase/](../.planning/codebase/) for detailed analysis

### "I'm having trouble"

1. Check [troubleshooting.md](troubleshooting.md) (when available)
2. Review [deployment-guide.md](deployment-guide.md) (common issues section)
3. Search existing GitHub issues
4. Create new issue with details

---

## 🔍 Finding Information

### By Keyword

- **Planning**: [architecture.md](architecture.md), [README.md](../README.md)
- **Execution**: [architecture.md](architecture.md), [api-reference.md](api-reference.md)
- **External Context**: [external-context-guide.md](external-context-guide.md)
- **Plan Optimizer**: [plan-optimizer-guide.md](20260227-plan-optimizer-guide.md)
- **API**: [api-reference.md](api-reference.md)
- **Deployment**: [deployment-guide.md](deployment-guide.md)
- **Testing**: [TEST.md](TEST.md)
- **Frontend**: [frontend/README.md](../frontend/README.md)
- **Models**: [README.md](../README.md), [api-reference.md](api-reference.md)
- **Scenarios**: [architecture.md](architecture.md), [api-reference.md](api-reference.md)

### By Component

- **Orchestrator**: [architecture.md](architecture.md), `orchestrator.py:127`
- **Planner**: [architecture.md](architecture.md), `services/planner.py`
- **Router**: [architecture.md](architecture.md), `services/router.py`
- **LLM Gateway**: [architecture.md](architecture.md), `services/llm_gateway.py`
- **Context Service**: [architecture.md](architecture.md), [external-context-guide.md](external-context-guide.md)
- **Optimizer**: [plan-optimizer-guide.md](20260227-plan-optimizer-guide.md), [architecture.md](architecture.md)

---

## 📊 Documentation Status

### ✅ Complete

- README.md - Project overview
- architecture.md - System architecture
- api-reference.md - API documentation
- deployment-guide.md - Deployment guide
- CONTRIBUTING.md - Contributing guidelines
- CHANGELOG.md - Version history
- frontend/README.md - Frontend guide
- external-context-guide.md - External context feature
- plan-optimizer-guide.md - Plan optimizer feature
- TEST.md - Testing guide

### 🚧 In Progress

- troubleshooting.md - Troubleshooting guide

### 📋 Planned

- Advanced configuration guide
- Performance tuning guide
- Security best practices
- Migration guide (between versions)

---

## 🔄 Keeping Documentation Updated

When making changes to PlanWeaver:

1. **Update this index** if adding/removing documents
2. **Update relevant guides** for feature changes
3. **Update CHANGELOG.md** for user-facing changes
4. **Update api-reference.md** for API changes
5. **Check architecture.md** for structural changes

---

## 💡 Documentation Tips

### Writing Good Documentation

- **Be concise**: Less is more
- **Provide examples**: Code samples are worth 1000 words
- **Keep it current**: Update docs with code changes
- **Use clear language**: Avoid jargon when possible
- **Organize logically**: Group related information

### Naming Convention

Documentation files follow this pattern:
- **Permanent names**: `feature-guide.md`, `architecture.md`
- **Dated research**: `YYYYMMDD-topic.md` (historical/reference only)
- **Implementation plans**: `docs/plans/YYYYMMDD-feature.md`

---

## 📮 Feedback

Found an issue with the documentation?

1. Check for existing issues on GitHub
2. Create new issue with label "documentation"
3. Submit PR with improvements

---

## 🔗 External Resources

- **GitHub Repository**: [Link to repo]
- **Issue Tracker**: [Link to issues]
- **Discussions**: [Link to discussions]
- **Release Notes**: See CHANGELOG.md

---

**Last Updated:** 2025-02-28

**Maintained By:** PlanWeaver Team
