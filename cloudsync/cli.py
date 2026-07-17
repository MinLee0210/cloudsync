from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .providers import PROVIDERS
from .state import SyncState
from .sync import SyncSafetyError, apply_plan, check_quota, create_plan, default_state_path


def build_provider(args):
    if args.provider == "gdrive":
        from .providers import GoogleDriveProvider

        return GoogleDriveProvider(args.credentials, args.token, args.root_folder_id or "root")
    if args.provider in ("s3", "minio"):
        from .providers import S3Provider

        if not args.bucket:
            raise ValueError("--bucket is required for S3 and MinIO")
        return S3Provider(
            bucket=args.bucket,
            access_key=args.access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=args.secret_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            session_token=args.session_token or os.getenv("AWS_SESSION_TOKEN"),
            endpoint_url=args.endpoint_url,
            region=args.region,
            profile=args.profile,
        )
    raise ValueError(f"Unknown provider: {args.provider}")


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("local_dir")
    parser.add_argument("--provider", choices=PROVIDERS.keys(), required=True)
    parser.add_argument("--remote-root", default="")
    parser.add_argument("--db", default=default_state_path())
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--credentials", default="credentials.json")
    parser.add_argument("--token", default="token.json")
    parser.add_argument("--root-folder-id")
    parser.add_argument("--bucket")
    parser.add_argument("--access-key", help=argparse.SUPPRESS)
    parser.add_argument("--secret-key", help=argparse.SUPPRESS)
    parser.add_argument("--session-token", help=argparse.SUPPRESS)
    parser.add_argument("--endpoint-url")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloudsync")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "sync", "quota"):
        child = sub.add_parser(command)
        _common(child)
        if command in {"plan", "sync"}:
            child.add_argument(
                "--delete", action="store_true", help="delete managed remote files removed locally"
            )
        if command == "sync":
            child.add_argument("--dry-run", action="store_true")
            child.add_argument("--max-delete", type=int, default=100)
            child.add_argument("--max-delete-percent", type=float, default=25.0)
    return parser


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    try:
        provider = build_provider(args)
        with SyncState(args.db) as state:
            if args.command == "quota":
                output = check_quota(
                    args.local_dir, provider, remote_root=args.remote_root, state=state
                )
            else:
                plan = create_plan(
                    args.local_dir,
                    provider,
                    remote_root=args.remote_root,
                    state=state,
                    delete_remote=args.delete,
                    exclude=args.exclude,
                )
                if args.command == "plan":
                    output = plan.to_dict()
                else:
                    output = apply_plan(
                        plan,
                        provider,
                        state,
                        remote_root=args.remote_root,
                        dry_run=args.dry_run,
                        max_delete=args.max_delete,
                        max_delete_percent=args.max_delete_percent,
                    ).to_dict()
        print(json.dumps(output, indent=2, sort_keys=True) if args.json else output)
        return 0
    except (ValueError, SyncSafetyError, OSError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
