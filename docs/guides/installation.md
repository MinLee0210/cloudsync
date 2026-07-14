# Installation

## Install the package

Requires Python 3.9 or newer.

```bash
python -m pip install -e .
```

For local development, install the test tools too:

```bash
python -m pip install -e '.[dev]'
```

To build this documentation site:

```bash
python -m pip install -e '.[docs]'
mkdocs serve
```

MkDocs serves the site at `http://127.0.0.1:8000/` and reloads it as files change.

## Verify the install

```bash
cloudsync --help
pytest -q
```

## Credentials and secrets

Keep OAuth files and access keys outside source control. The default Google Drive files are `credentials.json` and `token.json`; add them to your ignore rules if they live in the repository directory.
