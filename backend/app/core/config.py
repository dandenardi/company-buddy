from typing import List
from pydantic import AnyHttpUrl, SecretStr, Field
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer


class Settings(BaseSettings):
    # =========================
    # App
    # =========================
    project_name: str = "Company Buddy"

    # Prefixo interno de roteamento (APENAS FastAPI)
    api_v1_prefix: str = "/api/v1"

    # =========================
    # URLs públicas (externas)
    # =========================
    backend_public_url: AnyHttpUrl = Field(
        default="http://localhost:8000",
        env="BACKEND_PUBLIC_URL",
    )

    frontend_public_url: AnyHttpUrl = Field(
        default="http://localhost:3000",
        env="FRONTEND_BASE_URL",
    )

    # =========================
    # CORS
    # =========================
    backend_cors_origins: List[AnyHttpUrl] = []

    # =========================
    # Database
    # =========================
    database_url: str = Field(
        default="postgresql+psycopg2://companybuddy:companybuddy@localhost:5432/companybuddy",
        env="DATABASE_URL",
    )

    # =========================
    # Auth / JWT
    # =========================
    jwt_secret_key: SecretStr = SecretStr("change-me-in-.env")
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 24h

    # OAuth2PasswordBearer
    # ⚠️ tokenUrl é um detalhe INTERNO do OpenAPI
    oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
        tokenUrl="/api/v1/auth/login"
    )

    # =========================
    # Google OAuth
    # =========================
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")

    # Callback que o Google chama (URL PÚBLICA)
    google_redirect_uri: AnyHttpUrl = Field(
        default="http://localhost:8000/api/v1/auth/login/google/callback",
        env="GOOGLE_REDIRECT_URI",
    )

    google_api_key: str | None = Field(default=None, env="GOOGLE_API_KEY")

    # =========================
    # Vector Store / Search
    # =========================
    qdrant_url: AnyHttpUrl
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "company_buddy_chunks"

    hybrid_search_enabled: bool = True
    hybrid_vector_weight: float = 0.5
    hybrid_bm25_weight: float = 0.5
    hybrid_rrf_k: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
