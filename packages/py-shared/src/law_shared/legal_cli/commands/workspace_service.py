"""CLI command for workspace API server."""

import uvicorn


def run(args, runtime):
    """Start the workspace API server."""
    from law_shared.legal_tools.workspace import WorkspaceSettings, create_app

    settings = WorkspaceSettings.from_env()
    app = create_app(settings)

    host = args.host or "127.0.0.1"
    port = args.port or 8082
    reload = args.reload or False

    print(f"🚀 Starting Workspace API server on http://{host}:{port}")
    print(f"📚 API docs at http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")


def register(subparsers):
    """Register workspace-serve command."""
    parser = subparsers.add_parser(
        "workspace-serve",
        help="Start the workspace API server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Port to bind (default: 8082)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.set_defaults(handler=run)
