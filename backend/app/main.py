from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import text  # 👈 novo
from app.infrastructure.db.session import SessionLocal  # 👈 novo (ajusta se o path for outro)

from app.core.config import settings
from app.api.v1.routes.health import health_router
from app.api.v1.routes.auth import auth_router
from app.infrastructure.db.init_db import init_database
from app.api.v1.routes.documents import router as documents_router


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.project_name,
    )

    application.add_middleware(
        SessionMiddleware,
        secret_key=str(settings.jwt_secret_key.get_secret_value()),
        same_site="lax",
        session_cookie="cb_session",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.backend_cors_origins] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.on_event("startup")
    async def on_startup() -> None:
        # Importa os models só para registrá-los no SQLAlchemy
        import app.infrastructure.db.models.user_model      # noqa: F401
        import app.infrastructure.db.models.tenant_model    # noqa: F401
        import app.infrastructure.db.models.document_model  # noqa: F401

        # Cria tabelas básicas (se ainda não existirem)
        init_database()

       

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

    application.include_router(
        documents_router,
        prefix=settings.api_v1_prefix + "/documents",
        tags=["documents"],
    )

    return application


app = create_app()
