# Contributing

## Development Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
3. Install in editable mode: `pip install -e .`
4. Run tests: `pytest tests/` (when tests are added)

## Project Structure

- `src/azure/functions_connectors/` — package source
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
