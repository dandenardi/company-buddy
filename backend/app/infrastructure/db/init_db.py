
from app.infrastructure.db.session import engine
from app.infrastructure.db.base import Base


def init_database() -> None:
    """
    Cria as tabelas no banco (apenas para ambiente de desenvolvimento).
    Em produção, o ideal é usar migrações (Alembic).
    """
    Base.metadata.create_all(bind=engine)
