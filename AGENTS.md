# Repository Guidelines

## Project Structure & Module Organization
- `babayaga/orchestrator` coordinates audit flows and wires the analysis, LLM, and reporting engines.
- `babayaga/agents` stores agent playbooks plus `base.py` for shared behaviours; keep new agents colocated.
- `babayaga/modules` and `babayaga/core` bundle concrete analyzers, data models, and shared utilities.
- `babayaga/cli/main.py` exposes the Typer entry points, while `client.py` offers the interactive shell.
- Tests live under `tests/unit` and `tests/integration`; sample contracts sit in `tests/fixtures`.

## Build, Test, and Development Commands
- `python install.py` runs the guided installer for tools, models, and default config.
- `uv pip install -e .[dev]` sets up editable dependencies, including pytest and pre-commit hooks.
- `uv run babayaga audit ./contracts` executes a full audit pipeline against a target path.
- `uv run pytest` runs the complete test suite; add `tests/unit` or `tests/integration` to scope runs.
- `uv run pytest --cov=babayaga --cov-report=term-missing` verifies coverage expectations before submitting.

## Coding Style & Naming Conventions
- Target Python 3.12, four-space indentation, and PEP 8 spacing; prefer explicit type hints across public APIs.
- Use `snake_case` for functions, `PascalCase` for classes, and UPPER_SNAKE for constants.
- Keep agent names descriptive (`hunter_gamma.py` pattern) and mirror directory naming when adding docs.
- Structure modules so orchestration logic stays in `orchestrator` and heavy analysis in `engines` or `modules`.
- Run `uv run pre-commit run --all-files` before committing if hooks are installed.

## Testing Guidelines
- Unit tests belong in `tests/unit/test_<feature>.py`; integration flows in `tests/integration`.
- Favor `pytest` fixtures for sample contracts (`tests/fixtures/sample_contracts.py`).
- Ensure new analyzers include at least one unit test and, when behaviour spans agents, an integration check.
- Aim for ≥80% coverage on touched files; document deviations in the PR description.

## Commit & Pull Request Guidelines
- Follow the existing imperative commit style (`Integrate Ollama oversight`, `Change default model ...`).
- Keep subject lines ≤72 characters, add detail in the body when behaviour changes.
- PRs should link issues, describe testing (`pytest`, manual CLI checks), and flag new configuration or tool requirements.
- Include screenshots or sample report excerpts when UI or output formatting shifts.

## Security & Configuration Tips
- Never commit API keys or private audit data; store overrides in `~/.babayaga/config.toml` or env vars.
- Update `mcp_servers.json.example` when adding a new MCP integration, but keep secrets out of the template.
- Document any new Docker or Compose options in `docker-compose.yml` comments and reference them in the PR.
