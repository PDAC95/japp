from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server Configuration
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str

    # Database Configuration
    DATABASE_URL: str

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL: int = 3600  # 1 hour default

    # Claude API Configuration
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-3-sonnet-20241022"
    CLAUDE_MAX_TOKENS: int = 1000
    CLAUDE_TEMPERATURE: float = 0.3

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_DAY: int = 1000

    # Security
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://jappi.health"
    ]
    SECRET_KEY: str

    # External Services
    STRIPE_SECRET_KEY: str = ""
    SENDGRID_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
