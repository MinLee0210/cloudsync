# Contributing

## Development setup

```bash
python -m pip install -e '.[dev]'
pytest -q
```

The test suite focuses on filesystem scanning and sync decisions with a fake provider, so it does not require cloud credentials.

## Documentation preview

```bash
python -m pip install -e '.[docs]'
mkdocs serve
```

Keep examples executable where practical, describe destructive behavior explicitly, and add regression coverage for changes to sync decisions.
