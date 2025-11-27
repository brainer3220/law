"""FastAPI entrypoint that composes the share and workspace services."""

from __future__ import annotations

from fastapi import FastAPI

from law_shared.legal_tools.share.api import ShareSettings, create_app as create_share_app
from law_shared.legal_tools.workspace.api import (
    WorkspaceSettings,
    create_app as create_workspace_app,
)

__all__ = ["app", "create_app"]


from app.routers import transcribe

def create_app(
    *,
    share_settings: ShareSettings | None = None,
    workspace_settings: WorkspaceSettings | None = None,
) -> FastAPI:
    """Build the FastAPI application used by the API service."""

    share_app = create_share_app(share_settings)
    workspace_app = create_workspace_app(workspace_settings)

    @share_app.get("/v1/healthz", tags=["health"])  # type: ignore[misc]
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    share_app.include_router(transcribe.router)
    share_app.mount("/workspace", workspace_app)
    return share_app


app = create_app()
