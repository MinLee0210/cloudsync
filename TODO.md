# Cloudsync roadmap

This checklist tracks the work needed to move cloudsync from an early prototype
to a safe, production-ready synchronization tool. Complete the phases in order;
state isolation and deletion safety are release blockers.

## Already in place

- [x] Provide one-way local-to-remote synchronization.
- [x] Implement Google Drive and S3/MinIO providers.
- [x] Persist basic synchronization state in SQLite.
- [x] Expose Python and command-line interfaces.
- [x] Support basic remote storage/quota reporting.
- [x] Configure pre-commit hooks for whitespace, YAML/TOML, Ruff, and formatting.
- [x] Produce a source distribution and wheel successfully.
- [x] Ignore common credentials, local databases, environments, and build output.

## P0: data safety and state correctness

- [x] Add a `sync_jobs` table and scope every file record to a job ID.
- [x] Define job identity from the canonical local root, provider destination, and
      remote root; prevent accidental state reuse across different jobs.
- [x] Add a versioned state schema and migrations from the current schema.
- [x] Disable remote deletion by default; replace `--no-delete` with explicit
      `--delete` opt-in.
- [x] Add a non-mutating `plan` command and `sync --dry-run`.
- [x] Add deletion guards: maximum count/percentage limits for large
      deletion batches.
- [x] Validate that the local root exists, is a readable directory, and completed
      scanning successfully before any remote mutation.
- [x] Move default state into a platform-specific application data directory, or
      exclude the active SQLite DB plus WAL/journal files from scanning.
- [x] Use context managers or `try/finally` so state is always closed.
- [x] Define transaction and recovery behavior for partial or interrupted runs.

## P0: foundational tests

- [x] Create an in-memory fake provider implementing the full provider contract.
- [x] Test new, changed, unchanged, renamed, and removed files.
- [x] Test that separate jobs with identical relative paths cannot affect each
      other.
- [x] Test provider failures and retry behavior.
- [x] Test missing, empty, and state-containing local roots.
- [x] Test dry-run produces no local-state or remote mutations.
- [x] Test deletion limits and explicit deletion opt-in.
- [x] Test Unicode, spaces, apostrophes, and exclusion patterns.
- [x] Test state migrations and interrupted-run recovery.

## P1: reconciliation engine

- [x] Build a sync plan from local snapshot, remote snapshot, and previous state.
- [x] Use `provider.list_files()` to detect remote deletion/modification instead
      of treating local SQLite state as remote truth.
- [x] Define conflict policies for remote changes and expose them in plan output.
- [x] Recover safely when the state database is missing or stale.
- [x] Detect files that change between stat and hashing.
- [x] Define rename behavior as upload plus optional managed-file deletion.
- [x] Normalize remote paths and reject traversal, empty names, and ambiguous
      separators.
- [x] Add exclude patterns and safe symlink, permission, and special-file handling.
- [x] Calculate quota requirements from the planned upload delta rather than the
      full local directory size.
- [x] Represent unknown provider quota as unknown rather than `fits=True`.

## P1: provider hardening

### Google Drive

- [x] Escape Drive query values, including folder names containing apostrophes.
- [ ] Make folder lookup/creation safe against duplicate-folder races.
- [x] Ensure `list_files()` never creates folders as a side effect.
- [ ] Define behavior for duplicate names, shortcuts, Google-native documents,
      shared drives, and trashed objects.
- [ ] Add retry/backoff, timeouts, resumable-upload recovery, and typed provider
      errors.

### S3 and MinIO

- [x] Support boto3's standard credential chain, profiles, IAM roles, session
      tokens, and environment credentials.
- [x] Avoid recommending access keys in CLI arguments or examples.
- [ ] Expose region, profile, TLS verification, addressing style, storage class,
      and server-side encryption settings.
- [x] Do not assume multipart S3 ETags are MD5 content hashes.
- [ ] Test and enforce that operations remain inside the configured key prefix.
- [ ] Add provider contract tests using botocore Stubber or a local S3 emulator.

## P1: CLI and observability

- [x] Validate provider-specific required arguments with clear errors.
- [x] Add structured `--json` plan and result output.
- [ ] Add verbosity controls, actionable logging, progress, throughput, and a
      detailed final summary.
- [ ] Define stable success, partial-failure, conflict, and usage exit codes.
- [ ] Support a config file and environment variables without exposing secrets.
- [ ] Add retry, concurrency, include/exclude, and human-readable size options.
- [ ] Handle cancellation signals gracefully.
- [x] Use dataclasses and explicit types for local files, remote files, plans,
      operations, results, and errors.

## P2: quality, packaging, and releases

- [x] Remove `pre-commit` from runtime dependencies.
- [x] Add Ruff, pytest coverage, a type checker, and build tooling to the dev
      dependency group; make the configured checks runnable after dev install.
- [x] Make provider dependencies optional with lazy provider imports.
- [x] Remove unimplemented GCS support from package metadata.
- [x] Add project URLs, authors, license metadata, classifiers, and keywords.
- [x] Add `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `SECURITY.md`.
- [x] Add CI across all supported Python versions for lint, format, typing,
      tests/coverage, build, and installed-wheel smoke tests.
- [ ] Add dependency and security scanning plus automated release publishing.
- [x] Expand the README with safety semantics, recovery, configuration, provider
      limitations, exit codes, and realistic examples.
- [x] Keep the compact flat package layout; installed-wheel CI guards imports.

## P3: performance and future capabilities

- [ ] Cache hashes using trusted size/mtime metadata while preserving a forced
      verification mode.
- [ ] Add bounded parallel hashing and uploads with rate limiting.
- [ ] Add multipart/resumable transfer tuning and useful progress reporting.
- [ ] Benchmark large file counts, large files, deep trees, and slow networks.
- [ ] Consider encryption, retention/versioning, watch/daemon mode, and
      bidirectional sync only after safety and recovery guarantees are mature.

## Definition of production-ready v1

- [x] No state from one sync job can mutate another job's destination.
- [x] Every destructive action appears in a previewable plan and passes deletion
      guards.
- [x] Interrupted operations can be retried without duplicate or unintended
      destructive changes.
- [x] Local, remote, and stored state divergences have documented outcomes.
- [x] Provider contract and safety tests run in CI on every supported Python
      version.
- [x] Installation, configuration, credentials, limitations, recovery, and
      release processes are documented.
