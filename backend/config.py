from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables from backend/.env when present.
load_dotenv(BASE_DIR / ".env")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _cors_origins_env() -> list[str] | str:
    """Parse CORS origins and allow changing IPv4 LAN addresses during development."""
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    is_development = os.getenv("APP_ENV", "development").strip().lower() in {"development", "dev", "local"}
    local_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    local_network_pattern = r"^https?://(?:localhost|127\.0\.0\.1|(?:\d{1,3}\.){3}\d{1,3}):3000$"

    if not raw or raw == "*":
        # A wildcard is convenient locally, but development uses a scoped pattern
        # so production does not become open-ended when .env is copied over.
        return local_origins + [local_network_pattern] if is_development else local_origins

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if is_development:
        origins.extend(origin for origin in local_origins + [local_network_pattern] if origin not in origins)
    return origins or (local_origins + [local_network_pattern] if is_development else local_origins)


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = _bool_env("FLASK_DEBUG", True)
    host: str = os.getenv("FLASK_HOST", "0.0.0.0")
    port: int = int(os.getenv("FLASK_PORT", "5000"))
    cors_origins: list[str] | str = field(default_factory=_cors_origins_env)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    db_path: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "database" / "predictions.db")))
    ml_dir: Path = Path(os.getenv("ML_DIR", str(PROJECT_ROOT / "ml")))
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_timeout_seconds: int = int(os.getenv("GROQ_TIMEOUT_SECONDS", "25"))
    crop_confidence_threshold: float = float(os.getenv("CROP_CONFIDENCE_THRESHOLD", "0.80"))
    data_gov_api_key: str = os.getenv("DATA_GOV_API_KEY", os.getenv("MANDI_API_KEY", ""))
    mandi_api_url: str = os.getenv(
        "MANDI_API_URL",
        "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
    )
    mandi_api_timeout_seconds: int = int(os.getenv("MANDI_API_TIMEOUT_SECONDS", "12"))
    mandi_cache_ttl_seconds: int = int(os.getenv("MANDI_CACHE_TTL_SECONDS", "1800"))
    intervention_reminder_hours: int = int(os.getenv("INTERVENTION_REMINDER_HOURS", "24"))
    follow_up_reminder_hours: int = int(os.getenv("FOLLOW_UP_REMINDER_HOURS", "72"))
    outcome_min_evidence_cases: int = int(os.getenv("OUTCOME_MIN_EVIDENCE_CASES", "3"))


settings = Settings()
