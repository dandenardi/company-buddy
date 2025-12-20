import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import text
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.init_db import init_database

from app.core.config import settings
from app.api.v1.routes.health import health_router
from app.api.v1.routes.auth import auth_router
from app.api.v1.routes.ask import router as ask_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.qdrant import router as qdrant_router
from app.api.v1.routes.tenants import router as tenants_router
from app.api.v1.routes.feedback import router as feedback_router
from app.api.v1.routes.analytics import router as analytics_router

logging.basicConfig(level=logging.INFO)

def run_startup_migrations() -> None:
    """
    Pequenas migrations automáticas na inicialização.

    IMPORTANTE: isso é um quebra-galho pro MVP.
    Para algo mais sério, o ideal é usar Alembic.
    """
    from app.infrastructure.db.models.document_model import DocumentModel  # noqa: F401

    logging.info("Rodando migrations simples de startup...")
    database_session = SessionLocal()

    try:
        # Exemplo: adicionar coluna stored_path
        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS stored_path VARCHAR(512);
                """
            )
        )
        
        # Backfill stored_path for existing records
        database_session.execute(
            text(
                """
                UPDATE documents
                SET stored_path = stored_filename
                WHERE stored_path IS NULL;
                """
            )
        )

        # Exemplo: adicionar coluna original_filename
        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);
                """
            )
        )

        # Exemplo: adicionar coluna mime_type
        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS mime_type VARCHAR(255);
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE tenants
                ADD COLUMN IF NOT EXISTS custom_prompt TEXT;
                """
            )
        )

        # Add document metadata columns
        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS category VARCHAR(255);
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'pt-BR';
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS page_count INTEGER;
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS chunks_count INTEGER;
                """
            )
        )

        # Create index on content_hash if it doesn't exist
        database_session.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_content_hash 
                ON documents(content_hash);
                """
            )
        )

        database_session.execute(
            text(
                """
                ALTER TABLE query_logs
                ADD COLUMN IF NOT EXISTS conversation_id INTEGER;
                """
            )
        )

        database_session.commit()
        logging.info("Migrations simples finalizadas com sucesso.")
    except Exception as error:  # noqa: BLE001
        logging.exception("Erro ao rodar migrations simples: %s", error)
        database_session.rollback()
    finally:
        database_session.close()

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
        allow_origins=[str(origin) for origin in settings.backend_cors_origins],
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
        import app.infrastructure.db.models.feedback_model  # noqa: F401
        import app.infrastructure.db.models.query_log_model # noqa: F401
        import app.infrastructure.db.models.chunk_hash_model # noqa: F401
        import app.infrastructure.db.models.conversation_model # noqa: F401

        # Check database connection before running migrations
        try:
            logging.info("Verificando conexão com o banco de dados...")
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logging.info("Conexão com o banco de dados estabelecida com sucesso.")
        except Exception as e:
            logging.error(f"Não foi possível conectar ao banco de dados: {e}")
            logging.error("Verifique se o Docker está rodando e se o serviço do banco de dados está acessível.")
            # We might want to stop startup here or just let it fail later, 
            # but logging it clearly helps the user know WHY it's hanging/failing.
            # For now, we'll let it proceed but the logs will be clear.

        # Cria tabelas básicas (se ainda não existirem)
        init_database()
        run_startup_migrations()

        # Ensure Qdrant collection exists (Idempotent)
        try:
            from app.services.qdrant_service import QdrantService
            logging.info("Verificando coleção no Qdrant...")
            QdrantService() # This calls _ensure_collection() in __init__
            logging.info("Coleção do Qdrant verificada/criada com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao inicializar Qdrant: {e}")


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

    application.include_router(
        qdrant_router,
        prefix=settings.api_v1_prefix + "/qdrant",
        tags=["qdrant"],
    )

    application.include_router(
        ask_router,
        prefix=settings.api_v1_prefix + "/ask",
        tags=["ask"],
    )

    application.include_router(
        tenants_router,
        prefix=settings.api_v1_prefix + "/tenants",
        tags=["tenants"],
    )

    application.include_router(
        feedback_router,
        prefix=settings.api_v1_prefix + "/feedback",
        tags=["feedback"],
    )

    application.include_router(
        analytics_router,
        prefix=settings.api_v1_prefix + "/analytics",
        tags=["analytics"],
    )

    return application

    return application


app = create_app()
