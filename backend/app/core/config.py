from typing import List, Any
import json
import logging

from pydantic import AnyHttpUrl, SecretStr, Field, field_validator
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer


class Settings(BaseSettings):
    # =========================
    # App
    # =========================
    project_name: str = "Company Buddy"
    api_v1_prefix: str = "/api/v1"

    # =========================
    # URLs públicas
    # =========================
    backend_public_url: AnyHttpUrl = Field(
        env="BACKEND_PUBLIC_URL",
    )

    frontend_public_url: AnyHttpUrl = Field(
        env="FRONTEND_BASE_URL",
    )

    # =========================
    # CORS (LEIA COMO STR!)
    # =========================
    backend_cors_origins: Any = Field(
        default="",
        env="BACKEND_CORS_ORIGINS",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value) -> List[str]:
        """
        Aceita:
        - string vazia
        - string única
        - CSV
        - JSON list
        """
        if not value:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            value = value.strip()

            # JSON list
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass

            # CSV ou string única
            return [v.strip() for v in value.split(",") if v.strip()]

        return []

    # =========================
    # Database
    # =========================
    database_url: str = Field(
        env="DATABASE_URL",
    )

    # =========================
    # Auth / JWT
    # =========================
    jwt_secret_key: SecretStr = SecretStr(env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24

    oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
        tokenUrl="/api/v1/auth/login"
    )

    # =========================
    # Google OAuth
    # =========================
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")

    google_redirect_uri: AnyHttpUrl = Field(
        env="GOOGLE_REDIRECT_URI",
    )
    google_api_key: str | None = Field(default=None, env="GOOGLE_API_KEY")
    

    # =========================
    # Vector / Search
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

logger = logging.getLogger(__name__)

logger.info("Google redirect_uri usado: %s", settings.google_redirect_uri)
logger.info("Frontend public URL (base): %s", settings.frontend_public_url)
