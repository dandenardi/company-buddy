from typing import List, Optional
from datetime import timedelta
from pydantic import AnyHttpUrl, SecretStr, Field
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer


class Settings(BaseSettings):
    project_name: str = "Company Buddy"
    api_v1_prefix: str = "/api/v1"

    backend_cors_origins: List[AnyHttpUrl] = []

    # Banco
    # Agora usamos Postgres por padrão, mas pode ser sobrescrito via variável de ambiente DATABASE_URL
    database_url: str = Field(
        default="postgresql+psycopg2://companybuddy:companybuddy@localhost:5432/companybuddy",
        env="DATABASE_URL",
    )

    # Auth / JWT
    jwt_secret_key: SecretStr = SecretStr("change-me-in-.env")
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 24h

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
        tokenUrl="/api/v1/auth/login"
    )

    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="", env="GOOGLE_REDIRECT_URI")
    google_api_key: str | None = Field(default=None, env="GOOGLE_API_KEY")
   

    qdrant_url: AnyHttpUrl
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "company_buddy_chunks"

    # Hybrid Search
    hybrid_search_enabled: bool = True
    hybrid_vector_weight: float = 0.5
    hybrid_bm25_weight: float = 0.5
    hybrid_rrf_k: int = 60

settings = Settings()
