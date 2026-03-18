"""API route modules — aggregated into a single router."""

from __future__ import annotations

from . import chat, export, spaces, tables, upload, users

# All sub-module routers, included by app.py onto the main API router
sub_routers = [
    chat.router,
    tables.router,
    spaces.router,
    users.router,
    export.router,
    upload.router,
]
