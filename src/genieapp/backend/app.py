"""FastAPI application entry point."""

from .core import create_app, create_router
from .routes import sub_routers

router = create_router()
for sub in sub_routers:
    router.include_router(sub)

app = create_app(routers=[router])
