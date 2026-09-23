from typing import List
from pathlib import Path
from sqlalchemy import URL
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Identificación del Proyecto
    PROJECT_NAME: str = "Plataforma Colaborativa UML 2.5"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Seguridad y Criptografía (JWT)
    SECRET_KEY: str = Field(default="tu_clave_secreta_jwt_para_desarrollo_local_12345", min_length=32, repr=False)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # Conexión a PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(default="postgrespassword", min_length=1, repr=False)
    POSTGRES_DB: str = "uml_platform_db"

    # CORS: Orígenes permitidos (para conectar con React en Vite por defecto)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Proveedores de IA (Multimodalidad y Voice Assistant)
    GEMINI_API_KEY: str = Field(default="", repr=False)
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", min_length=1, max_length=100, pattern=r'^gemini-[A-Za-z0-9.\-]+$')
    GCP_LOCATION: str = Field(default="us-central1")
    AI_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=120)
    OPENAI_API_KEY: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Construye la URI asíncrona requerida por SQLAlchemy 2.0 y asyncpg.
        Formato: postgresql+asyncpg://user:pass@host:port/dbname
        """
        return URL.create(
            "postgresql+asyncpg", username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD, host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT, database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)


settings = Settings()
