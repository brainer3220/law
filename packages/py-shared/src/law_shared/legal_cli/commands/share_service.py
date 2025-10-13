"""Run the sharing FastAPI service."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "share-serve", help="Run the sharing FastAPI service"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument(
        "--db-url",
        dest="db_url",
        help="Override database URL (default: LAW_SHARE_DB_URL or sqlite)",
    )
    parser.set_defaults(handler=run)


def run(args: Namespace, config: RuntimeConfig) -> None:  # noqa: ARG001
    from law_shared.legal_tools.share import ShareSettings, create_app

    import uvicorn

    settings = ShareSettings.from_env()
    if getattr(args, "db_url", None):
        settings = ShareSettings(
            database_url=args.db_url,
            external_base_url=settings.external_base_url,
            default_link_ttl_days=settings.default_link_ttl_days,
            token_bytes=settings.token_bytes,
        )
    app = create_app(settings)
    uvicorn.run(app, host=getattr(args, "host", "127.0.0.1"), port=int(getattr(args, "port", 8081)))
