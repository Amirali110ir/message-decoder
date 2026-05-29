import hashlib
import hmac
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_otp_flow.db"

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import db, init_db
from app.main import app
from app.config import Settings, get_settings
from app.services import auth as auth_service


client = TestClient(app)


def setup_module():
    try:
        os.remove("test_otp_flow.db")
    except FileNotFoundError:
        pass
    init_db()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------- mock provider ----------


def test_mock_provider_returns_code_in_dev(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "mock")
    monkeypatch.setenv("DEV_OTP_CODE", "123456")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    get_settings.cache_clear()

    res = client.post("/auth/request-otp", json={"phone": "09120000001"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["dev_otp_code"] == "123456"
    assert body["telegram_payload"] is None


def test_mock_provider_hides_code_in_production(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "mock")
    monkeypatch.setenv("DEV_OTP_CODE", "123456")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()

    res = client.post("/auth/request-otp", json={"phone": "09120000002"})
    assert res.status_code == 200
    body = res.json()
    assert body["dev_otp_code"] is None


def test_mock_does_not_trigger_telegram_path(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "mock")
    monkeypatch.setenv("TELEGRAM_BRIDGE_SECRET", "test-secret")
    get_settings.cache_clear()

    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel, referral_code) "
            "VALUES (?, ?, ?, datetime('now'), 0, 'web', ?)",
            ("user_mock_tg", "09120000003", "12345678", "ABCDE123"),
        )

    res = client.post("/auth/request-otp", json={"phone": "09120000003"})
    assert res.status_code == 200
    assert res.json()["telegram_payload"] is None


# ---------- smsir provider ----------


def test_smsir_missing_api_key(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "smsir")
    monkeypatch.setenv("SMSIR_API_KEY", "")
    get_settings.cache_clear()

    res = client.post("/auth/request-otp", json={"phone": "09120000004"})
    assert res.status_code == 500
    assert "کلید API" in res.json()["detail"]


def test_smsir_missing_template_when_method_verify(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "smsir")
    monkeypatch.setenv("SMSIR_API_KEY", "fake")
    monkeypatch.setenv("SMSIR_METHOD", "verify")
    monkeypatch.setenv("SMSIR_TEMPLATE_ID", "")
    get_settings.cache_clear()

    res = client.post("/auth/request-otp", json={"phone": "09120000005"})
    assert res.status_code == 500
    assert "قالب" in res.json()["detail"]


# ---------- kavenegar provider ----------


def test_kavenegar_missing_api_key(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "")
    get_settings.cache_clear()

    res = client.post("/auth/request-otp", json={"phone": "09120000006"})
    assert res.status_code == 500


# ---------- telegram bridge ----------


def test_telegram_payload_built_with_linked_user(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "fake")
    monkeypatch.setenv("KAVENEGAR_METHOD", "send")
    monkeypatch.setenv("KAVENEGAR_SENDER", "10001")
    monkeypatch.setenv("TELEGRAM_BRIDGE_SECRET", "bridge-secret-xyz")
    get_settings.cache_clear()

    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel, referral_code) "
            "VALUES (?, ?, ?, datetime('now'), 0, 'web', ?)",
            ("user_tg_link", "09120000007", "999888777", "REF12345"),
        )

    captured = {}

    def fake_send(phone, code, settings):
        captured["phone"] = phone
        captured["code"] = code

    monkeypatch.setattr(auth_service, "send_kavenegar_otp", fake_send)

    res = client.post("/auth/request-otp", json={"phone": "09120000007"})
    assert res.status_code == 200, res.json()
    payload = res.json()["telegram_payload"]
    assert payload is not None
    assert payload["chat_id"] == "999888777"
    assert "کلید ورود" in payload["text"]

    expected_message = f"{payload['chat_id']}|{payload['text']}".encode("utf-8")
    expected_sig = hmac.new(b"bridge-secret-xyz", expected_message, hashlib.sha256).hexdigest()
    assert payload["signature"] == expected_sig


def test_telegram_payload_none_when_secret_missing(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "fake")
    monkeypatch.setenv("KAVENEGAR_METHOD", "send")
    monkeypatch.setenv("KAVENEGAR_SENDER", "10001")
    monkeypatch.delenv("TELEGRAM_BRIDGE_SECRET", raising=False)
    get_settings.cache_clear()

    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel, referral_code) "
            "VALUES (?, ?, ?, datetime('now'), 0, 'web', ?)",
            ("user_no_secret", "09120000008", "555", "REFABC"),
        )

    monkeypatch.setattr(auth_service, "send_kavenegar_otp", lambda *a, **kw: None)

    res = client.post("/auth/request-otp", json={"phone": "09120000008"})
    assert res.status_code == 200
    assert res.json()["telegram_payload"] is None


def test_telegram_payload_none_when_user_not_linked(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "fake")
    monkeypatch.setenv("KAVENEGAR_METHOD", "send")
    monkeypatch.setenv("KAVENEGAR_SENDER", "10001")
    monkeypatch.setenv("TELEGRAM_BRIDGE_SECRET", "bridge-secret-xyz")
    get_settings.cache_clear()

    monkeypatch.setattr(auth_service, "send_kavenegar_otp", lambda *a, **kw: None)

    res = client.post("/auth/request-otp", json={"phone": "09120000009"})
    assert res.status_code == 200
    assert res.json()["telegram_payload"] is None


# ---------- template newline unescape ----------


def test_template_unescape_newlines(monkeypatch):
    monkeypatch.setenv("SMSIR_MESSAGE_TEMPLATE", "خط ۱.\\nخط ۲: {code}")
    monkeypatch.setenv("OTP_PROVIDER", "smsir")
    get_settings.cache_clear()
    settings = get_settings()
    msg = auth_service.format_otp_login_message("999", settings)
    assert msg == "خط ۱.\nخط ۲: 999"


# ---------- verify flow ----------


def test_verify_with_mock_code(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "mock")
    monkeypatch.setenv("DEV_OTP_CODE", "987654")
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()

    phone = "09120009999"
    requested = client.post("/auth/request-otp", json={"phone": phone}).json()
    assert requested["dev_otp_code"] == "987654"

    verified = client.post("/auth/verify-otp", json={"phone": phone, "code": "987654"})
    assert verified.status_code == 200
    assert "token" in verified.json()
