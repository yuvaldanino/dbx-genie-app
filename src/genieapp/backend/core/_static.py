"""Static file serving with SPA fallback."""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles


class CachedStaticFiles(StaticFiles):
    """Static files with cache headers for immutable assets."""

    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        if response and hasattr(response, "headers"):
            path = str(args[1]) if len(args) > 1 else ""
            if "/assets/" in path:
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "no-cache"
        return response


def add_not_found_handler(app: FastAPI) -> None:
    """Add SPA fallback: serve index.html for unmatched routes."""
    from ..._metadata import dist_dir

    @app.exception_handler(404)
    async def spa_fallback(request: Request, _exc: Exception) -> Response:
        if request.url.path.startswith("/api"):
            return Response(status_code=404, content="Not Found")
        index = dist_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        return Response(status_code=404, content="Not Found")
