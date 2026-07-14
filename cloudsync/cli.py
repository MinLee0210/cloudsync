import argparse
import sys

from .providers import PROVIDERS
from .state import SyncState
from .sync import sync, check_quota


def build_provider(args):
    if args.provider == "gdrive":
        from .providers import GoogleDriveProvider

        return GoogleDriveProvider(
            credentials_file=args.credentials,
            token_file=args.token,
            root_folder_id=args.root_folder_id or "root",
        )
    elif args.provider in ("s3", "minio"):
        missing = [
            name
            for name, value in (
                ("--bucket", args.bucket),
                ("--access-key", args.access_key),
                ("--secret-key", args.secret_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"{args.provider} requires: {', '.join(missing)}")

        from .providers import S3Provider

        return S3Provider(
            bucket=args.bucket,
            access_key=args.access_key,
            secret_key=args.secret_key,
            endpoint_url=args.endpoint_url,
        )
    raise ValueError(f"Unknown provider: {args.provider}")


def main():
    parser = argparse.ArgumentParser(prog="cloudsync")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("local_dir")
    common.add_argument("--provider", choices=PROVIDERS.keys(), required=True)
    common.add_argument("--remote-root", default="")
    common.add_argument("--db", default=".cloudsync_state.db")
    common.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent workers for operations",
    )
    common.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Glob pattern of file/directory names to ignore",
    )
    # gdrive options
    common.add_argument("--credentials", default="credentials.json")
    common.add_argument("--token", default="token.json")
    common.add_argument("--root-folder-id", default=None)
    # s3/minio options
    common.add_argument("--bucket")
    common.add_argument("--access-key")
    common.add_argument("--secret-key")
    common.add_argument("--endpoint-url")

    sync_p = sub.add_parser("sync", parents=[common])
    sync_p.add_argument(
        "--no-delete",
        action="store_true",
        help="Do not delete remote files removed locally",
    )

    sub.add_parser("quota", parents=[common])

    args = parser.parse_args()
    try:
        provider = build_provider(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "sync":
        state = SyncState(args.db)
        result = sync(
            args.local_dir,
            provider,
            remote_root=args.remote_root,
            state=state,
            delete_remote=not args.no_delete,
            workers=args.workers,
            ignore_patterns=args.ignore,
        )
        state.close()
        print(result)

    elif args.command == "quota":
        info = check_quota(
            args.local_dir,
            provider,
            ignore_patterns=args.ignore,
        )
        print(info)


if __name__ == "__main__":
    sys.exit(main())
