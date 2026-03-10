# Contributing

## Development Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
3. Install in editable mode: `pip install -e ".[dev]"`
4. Run tests: `pytest tests/`

## Project Structure

- `src/azure/functions/connector_triggers/` — package source
- `tests/` — unit tests
- `samples/` — sample Function Apps
- `notes/` — research and design docs

## Pull Requests

- Create a feature branch from `main`
- Add tests for new functionality
- Ensure all existing tests pass
- Update README if adding new features

## Architecture

See `notes/timer-blob-alternate-plan.md` for the full architecture design.
