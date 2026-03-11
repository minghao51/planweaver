# Contributing to PlanWeaver

Thank you for your interest in contributing to PlanWeaver! This document provides guidelines and instructions for contributors.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ (for frontend development)
- Git

### Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/planweaver.git
   cd planweaver
   ```

2. **Install Python dependencies using uv:**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   uv sync
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Install frontend dependencies (optional):**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_planner.py

# Run with coverage
uv run pytest --cov=src/planweaver

# Run frontend tests
cd frontend
npm test
```

## Code Style Guidelines

### Python

- Use **ruff** for linting and formatting:
  ```bash
  uv run ruff check src/           # Lint
  uv run ruff format src/          # Format
  ```

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for all public classes, methods, and functions

### TypeScript/React

- Use **ESLint** for linting:
  ```bash
  cd frontend
  npm run lint
  ```

- Use **Prettier** for formatting:
  ```bash
  cd frontend
  npm run format
  ```

- Follow React best practices
- Use functional components with hooks
- Keep components small and focused

### Documentation

- Keep documentation up-to-date with code changes
- Use clear, concise language
- Include examples for API endpoints and public methods
- Update README.md for user-facing changes

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, simple code
- Add tests for new functionality
- Update documentation as needed
- Follow the code style guidelines

### 3. Test Your Changes

```bash
# Run Python tests
uv run pytest

# Run frontend tests (if applicable)
cd frontend && npm test

# Check linting
uv run ruff check src/
cd frontend && npm run lint
```

### 4. Commit Your Changes

Use clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add new optimization feature"
```

Commit message prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

## Pull Request Process

### Before Submitting

1. **Update documentation** - Ensure docs reflect your changes
2. **Add tests** - All new features should have tests
3. **Run tests locally** - Make sure everything passes
4. **Update CHANGELOG.md** - Add entry for your changes

### Submitting a Pull Request

1. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request on GitHub with:
   - Clear title describing the change
   - Detailed description of what you did and why
   - Reference any related issues
   - Screenshots for UI changes (if applicable)

3. Respond to review feedback and make requested changes

### Review Criteria

- Code follows style guidelines
- Tests are included and passing
- Documentation is updated
- Changes are minimal and focused
- No breaking changes without discussion

## Reporting Issues

### Bug Reports

Include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Error messages and stack traces
- Relevant code snippets

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Possible implementation approach (if known)
- Examples of similar features in other tools

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Read existing code for patterns

## Development Tips

### Running the Development Server

```bash
# Backend API server
uv run uvicorn src.planweaver.api.main:app --reload

# Frontend dev server (in separate terminal)
cd frontend
npm run dev
```

### Database

PlanWeaver uses SQLite by default. The database file is created automatically at `./planweaver.db`.

To reset the database:
```bash
rm planweaver.db
```

### Adding New Scenarios

Create YAML files in the `scenarios/` directory following the existing templates. See `docs/reference/architecture.md` for details.

### Adding New API Endpoints

1. Add route handler in `src/planweaver/api/routes.py`
2. Add schema definitions in `src/planweaver/api/schemas.py`
3. Add tests in `tests/test_api.py`
4. Update API documentation

## Project Structure

```
planweaver/
├── src/planweaver/          # Main Python package
│   ├── api/                 # FastAPI application
│   ├── db/                  # Database models and repositories
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── cli.py               # Command-line interface
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── api/             # API client
│   │   └── hooks/           # Custom hooks
│   └── package.json
├── tests/                   # Python tests
├── scenarios/               # YAML scenario templates
└── docs/                    # Documentation
```

## License

By contributing to PlanWeaver, you agree that your contributions will be licensed under the same license as the project.
