# Contributing

Install all development and provider dependencies, then run the checks:

```bash
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pyright cloudsync
uv run pytest --cov=cloudsync.sync --cov=cloudsync.state --cov=cloudsync.scanner
uv build
```

Changes to synchronization behavior must include fake-provider tests. Changes
that can delete or overwrite data must document their safety and recovery
semantics.
