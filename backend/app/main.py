from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.routes.health import health_router
from app.api.v1.routes.auth import auth_router
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.project_name,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.backend_cors_origins] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import models so SQLAlchemy knows about them
    # (they just need to be imported, even if unused here)
    import app.infrastructure.db.models.user_model  # noqa: F401
    import app.infrastructure.db.models.tenant_model  # noqa: F401

    # Create tables (dev only – later we can move this to migrations)
    Base.metadata.create_all(bind=engine)

    # Routers
    application.include_router(
        health_router,
        prefix=settings.api_v1_prefix,
        tags=["health"],
    )

    application.include_router(
        auth_router,
        prefix=settings.api_v1_prefix + "/auth",
        tags=["auth"],
    )

    return application


app = create_app()
