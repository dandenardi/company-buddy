from typing import List, Any
import json

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
        default="http://localhost:8000",
        env="BACKEND_PUBLIC_URL",
    )

    frontend_public_url: AnyHttpUrl = Field(
        default="http://localhost:3000",
        env="FRONTEND_BASE_URL",
    )

    # =========================
    # CORS (ROBUSTO)
    # =========================
    backend_cors_origins: List[AnyHttpUrl] = Field(
        default=[],
        env="BACKEND_CORS_ORIGINS",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> List[str]:
        """
        Aceita:
        - JSON list
        - string única
        - CSV
        - None / vazio
        """
        if value is None or value == "":
            return []

        # Já é lista (caso ideal)
        if isinstance(value, list):
            return value

        # String
        if isinstance(value, str):
            value = value.strip()

            # Tenta JSON primeiro
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass

            # Fallback: CSV ou string única
            return [item.strip() for item in value.split(",") if item.strip()]

        # Qualquer outro caso
        return []

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
        default="http://localhost:8000/api/v1/auth/login/google/callback",
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
