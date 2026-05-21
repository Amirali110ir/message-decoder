import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./message_decoder.db"))
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "mock"))
    ai_model_version: str = field(default_factory=lambda: os.getenv("AI_MODEL_VERSION", "mock-v0.1"))
    # Base URL used for both tasks unless task-specific overrides are set.
    # For Liara: set AI_API_BASE_URL to the Mirzakhani (cheap) endpoint and
    # AI_PAID_API_BASE_URL to the Turing (quality) endpoint.
    ai_api_base_url: str = field(default_factory=lambda: os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1"))
    ai_paid_api_base_url: str = field(
        default_factory=lambda: os.getenv("AI_PAID_API_BASE_URL", os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1"))
    )
    ai_api_key: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    # Task-specific API keys (optional — falls back to AI_API_KEY)
    ai_paid_api_key: str = field(
        default_factory=lambda: os.getenv("AI_PAID_API_KEY", os.getenv("AI_API_KEY", ""))
    )
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "gpt-4.1-mini"))
    # Free layer: cheap/fast model (e.g. gemini-2.0-flash on Liara Mirzakhani)
    ai_free_model: str = field(default_factory=lambda: os.getenv("AI_FREE_MODEL", os.getenv("AI_MODEL", "gpt-4.1-mini")))
    # Paid layer: higher-quality model (e.g. gemini-2.5-flash on Liara Turing)
    ai_paid_model: str = field(default_factory=lambda: os.getenv("AI_PAID_MODEL", os.getenv("AI_MODEL", "gpt-4.1-mini")))
    # --- Generation quality knobs ---
    # Free decode: lower creativity acceptable; Paid decode: richer variety needed
    ai_free_temperature: float = field(default_factory=lambda: float(os.getenv("AI_FREE_TEMPERATURE", "0.7")))
    ai_paid_temperature: float = field(default_factory=lambda: float(os.getenv("AI_PAID_TEMPERATURE", "0.8")))
    # Penalises token repetition so replies feel varied (0 = off, 1 = maximum)
    ai_frequency_penalty: float = field(default_factory=lambda: float(os.getenv("AI_FREQUENCY_PENALTY", "0.4")))
    # --- Semantic cache ---
    # Set to "false" to disable the SQLite semantic response cache
    ai_semantic_cache_enabled: bool = field(
        default_factory=lambda: os.getenv("AI_SEMANTIC_CACHE_ENABLED", "true").lower() not in ("false", "0", "no")
    )
    otp_provider: str = field(default_factory=lambda: os.getenv("OTP_PROVIDER", "mock"))
    dev_otp_code: str = field(default_factory=lambda: os.getenv("DEV_OTP_CODE", "25367286503"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-in-production"))
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", "change-me-admin-token"))
    zarinpal_merchant_id: str = field(default_factory=lambda: os.getenv("ZARINPAL_MERCHANT_ID", "sandbox"))
    zarinpal_callback_url: str = field(default_factory=lambda: os.getenv("ZARINPAL_CALLBACK_URL", "http://localhost:3000/payment/callback"))
    cors_origins: str = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002,http://127.0.0.1:3002",
        )
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
