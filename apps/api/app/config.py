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
    # Free decode: light analysis, a little creativity is fine.
    # Paid decode: the final reply the user sends — keep it low for stable, safe,
    # predictable output. Reply variety comes from prompt structure + frequency
    # penalty, not from a high temperature.
    ai_free_temperature: float = field(default_factory=lambda: float(os.getenv("AI_FREE_TEMPERATURE", "0.6")))
    ai_paid_temperature: float = field(default_factory=lambda: float(os.getenv("AI_PAID_TEMPERATURE", "0.4")))
    # Penalises token repetition so replies feel varied (0 = off, 1 = maximum)
    ai_frequency_penalty: float = field(default_factory=lambda: float(os.getenv("AI_FREQUENCY_PENALTY", "0.4")))
    # Paid self-critique pass (generate→critique→revise). Default on for quality.
    # When off, the always-on quality critique is skipped to halve paid latency,
    # but forbidden phrases are STILL scrubbed (the inspector runs regardless).
    ai_paid_self_critique_enabled: bool = field(
        default_factory=lambda: os.getenv("AI_PAID_SELF_CRITIQUE_ENABLED", "true").lower() not in ("false", "0", "no")
    )
    # --- Semantic cache ---
    # Set to "false" to disable the SQLite semantic response cache
    ai_semantic_cache_enabled: bool = field(
        default_factory=lambda: os.getenv("AI_SEMANTIC_CACHE_ENABLED", "true").lower() not in ("false", "0", "no")
    )
    otp_provider: str = field(default_factory=lambda: os.getenv("OTP_PROVIDER", "mock"))
    dev_otp_code: str = field(default_factory=lambda: os.getenv("DEV_OTP_CODE", "25367286503"))
    otp_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("OTP_TTL_SECONDS", "300")))
    otp_max_attempts: int = field(default_factory=lambda: int(os.getenv("OTP_MAX_ATTEMPTS", "5")))
    signup_bonus_credits: int = field(default_factory=lambda: int(os.getenv("SIGNUP_BONUS_CREDITS", "5")))
    kavenegar_api_key: str = field(default_factory=lambda: os.getenv("KAVENEGAR_API_KEY", ""))
    kavenegar_method: str = field(default_factory=lambda: os.getenv("KAVENEGAR_METHOD", "send"))
    kavenegar_sender: str = field(default_factory=lambda: os.getenv("KAVENEGAR_SENDER", ""))
    kavenegar_template: str = field(default_factory=lambda: os.getenv("KAVENEGAR_TEMPLATE", ""))
    kavenegar_message_template: str = field(
        default_factory=lambda: os.getenv(
            "KAVENEGAR_MESSAGE_TEMPLATE",
            "رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}",
        )
    )
    kavenegar_type: str = field(default_factory=lambda: os.getenv("KAVENEGAR_TYPE", "sms"))
    kavenegar_api_base_url: str = field(
        default_factory=lambda: os.getenv("KAVENEGAR_API_BASE_URL", "https://api.kavenegar.com")
    )
    smsir_api_key: str = field(default_factory=lambda: os.getenv("SMSIR_API_KEY", ""))
    smsir_method: str = field(default_factory=lambda: os.getenv("SMSIR_METHOD", "auto"))
    smsir_template_id: str = field(default_factory=lambda: os.getenv("SMSIR_TEMPLATE_ID", ""))
    smsir_parameter_name: str = field(default_factory=lambda: os.getenv("SMSIR_PARAMETER_NAME", "Code"))
    smsir_line_number: str = field(default_factory=lambda: os.getenv("SMSIR_LINE_NUMBER", ""))
    smsir_message_template: str = field(
        default_factory=lambda: os.getenv(
            "SMSIR_MESSAGE_TEMPLATE",
            "رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}",
        )
    )
    smsir_api_base_url: str = field(default_factory=lambda: os.getenv("SMSIR_API_BASE_URL", "https://api.sms.ir"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-in-production"))
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", "change-me-admin-token"))
    admin_phone: str = field(default_factory=lambda: os.getenv("ADMIN_PHONE", ""))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    zarinpal_merchant_id: str = field(default_factory=lambda: os.getenv("ZARINPAL_MERCHANT_ID", "sandbox"))
    zarinpal_callback_url: str = field(default_factory=lambda: os.getenv("ZARINPAL_CALLBACK_URL", "http://localhost:3000/payment/callback"))
    zarinpal_api_base_url: str = field(default_factory=lambda: os.getenv("ZARINPAL_API_BASE_URL", "https://api.zarinpal.com"))
    zarinpal_start_pay_url: str = field(default_factory=lambda: os.getenv("ZARINPAL_START_PAY_URL", "https://www.zarinpal.com/pg/StartPay"))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_webhook_secret: str = field(default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_SECRET", ""))
    telegram_api_base_url: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org")
    )
    telegram_api_bypass_secret: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_BYPASS_SECRET", ""))
    telegram_bridge_secret: str = field(default_factory=lambda: os.getenv("TELEGRAM_BRIDGE_SECRET", ""))
    cors_origins: str = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002,http://127.0.0.1:3002,https://message-decoder-py.liara.run,https://message-decoder-amirali6020s-projects.vercel.app,https://message-decoder-enlqw4wua-amirali6020s-projects.vercel.app,https://message-decoder-45lyfp2vk-amirali6020s-projects.vercel.app",
        )
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "")).lower() in {"prod", "production"}

    def validate_for_startup(self) -> None:
        if not self.is_production:
            return
        insecure_values = {
            "JWT_SECRET": self.jwt_secret == "change-me-in-production",
            "ADMIN_TOKEN": self.admin_token == "change-me-admin-token",
            "ADMIN_PHONE": not self.admin_phone,
            "ADMIN_PASSWORD": not self.admin_password,
        }
        missing = [name for name, invalid in insecure_values.items() if invalid]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Unsafe production configuration: set secure values for {joined}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
