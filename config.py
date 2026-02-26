"""Configuration management for Enterprise RAG system."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # LLM Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-3-small"

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "enterprise_rag"

    # Application Configuration
    upload_dir: Path = Path("./data/uploads")

    @field_validator("upload_dir", mode="before")
    @classmethod
    def coerce_upload_dir(cls, v: Path | str) -> Path:
        """Ensure upload_dir is always a Path for consistency in Docker and locally."""
        if isinstance(v, str):
            return Path(v)
        return v
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Evaluation
    eval_mode: str = "development"
    min_relevance_score: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_required(self) -> None:
        """
        Validate that required settings are set for running the application.
        Call at app startup to fail fast with a clear error.
        """
        if not (self.openai_api_key or "").strip():
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Set it in your environment or in a .env file (see .env.example)."
            )


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
Path("./data/processed").mkdir(parents=True, exist_ok=True)
Path("./logs").mkdir(parents=True, exist_ok=True)
