import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./message_decoder.db")
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_model_version: str = os.getenv("AI_MODEL_VERSION", "mock-v0.1")
    ai_api_base_url: str = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4.1-mini")
    otp_provider: str = os.getenv("OTP_PROVIDER", "mock")
    dev_otp_code: str = os.getenv("DEV_OTP_CODE", "123456")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    admin_token: str = os.getenv("ADMIN_TOKEN", "change-me-admin-token")
    zarinpal_merchant_id: str = os.getenv("ZARINPAL_MERCHANT_ID", "sandbox")
    zarinpal_callback_url: str = os.getenv("ZARINPAL_CALLBACK_URL", "http://localhost:3000/payment/callback")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
