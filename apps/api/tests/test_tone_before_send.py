import os

os.environ["DATABASE_URL"] = "sqlite:///./test_tone_before_send.db"

from fastapi.testclient import TestClient

from app.database import db, init_db
from app.main import app
from app.services import telegram as telegram_service


client = TestClient(app)
_auth_counter = 0


def setup_module():
    try:
        os.remove("test_tone_before_send.db")
    except FileNotFoundError:
        pass
    init_db()


def auth_headers():
    global _auth_counter
    _auth_counter += 1
    phone = f"09127777{_auth_counter:03d}"
    requested = client.post("/auth/request-otp", json={"phone": phone}).json()
    res = client.post("/auth/verify-otp", json={"phone": phone, "code": requested["dev_otp_code"]})
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_tone_edit_requires_auth():
    res = client.post("/decode/tone-edit", json={"reply_text": "باشه هرجور راحتی", "target_tone": "softer"})
    assert res.status_code == 401


def test_tone_edit_shorter_returns_text():
    res = client.post(
        "/decode/tone-edit",
        json={"reply_text": "این کار درست نیست. لطفا دوباره بررسی کن. ممنون.", "target_tone": "shorter"},
        headers=auth_headers(),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tone"] == "shorter"
    assert body["tone_label"] == "کوتاه‌تر"
    assert body["text"].strip()


def test_tone_edit_all_tones():
    headers = auth_headers()
    for tone, label in [
        ("softer", "نرم‌تر"),
        ("firmer", "قاطع‌تر"),
        ("warmer", "گرم‌تر"),
        ("formal", "رسمی‌تر"),
    ]:
        res = client.post(
            "/decode/tone-edit",
            json={"reply_text": "نظر من این است.", "target_tone": tone},
            headers=headers,
        )
        assert res.status_code == 200, tone
        assert res.json()["tone_label"] == label


def test_before_send_requires_auth():
    res = client.post("/decode/before-send", json={"draft_text": "سلام"})
    assert res.status_code == 401


def test_before_send_low_risk():
    res = client.post(
        "/decode/before-send",
        json={"draft_text": "ممنون که خبر دادی، فردا هماهنگ می‌کنیم.", "relationship_type": "friend"},
        headers=auth_headers(),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["risk_level"] in ("کم", "متوسط", "زیاد")
    assert 0 <= body["risk_score"] <= 100
    assert body["flags"]
    assert body["suggestions"]


def test_before_send_high_risk_flags_blame_and_offers_improved():
    res = client.post(
        "/decode/before-send",
        json={
            "draft_text": "تو همیشه همینطوری، مشکل خودته و بی‌شعوری",
            "relationship_type": "romantic",
        },
        headers=auth_headers(),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["risk_level"] in ("متوسط", "زیاد")
    assert body["improved_text"]
    assert len(body["flags"]) >= 1


def test_telegram_referral_deep_link_awards_referrer(monkeypatch):
    async def fake_send(chat_id, text, reply_markup=None):
        return None

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send)

    # Referrer signs up via web and gets a referral code.
    headers = auth_headers()
    referral = client.get("/user/referral", headers=headers).json()
    code = referral["referral_code"]
    token = headers["Authorization"].removeprefix("Bearer ")
    with db() as conn:
        referrer = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
        referrer_id = referrer["user_id"]
        before = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (referrer_id,)).fetchone()["credit_balance"]

    # New telegram user opens the deep link and shares contact.
    client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 2002}, "from": {"id": 9090}, "text": f"/start ref_{code}"}},
    )
    client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 2002}, "from": {"id": 9090}, "contact": {"user_id": 9090, "phone_number": "09129990909"}}},
    )

    with db() as conn:
        after = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (referrer_id,)).fetchone()["credit_balance"]
        new_user = conn.execute("SELECT referred_by_user_id FROM users WHERE telegram_id = '9090'").fetchone()
    assert after == before + 5
    assert new_user["referred_by_user_id"] == referrer_id


def test_telegram_referral_command_returns_code(monkeypatch):
    captured = []

    async def fake_send(chat_id, text, reply_markup=None):
        captured.append(text)

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send)

    client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 3003}, "from": {"id": 7070}, "contact": {"user_id": 7070, "phone_number": "09127070707"}}},
    )
    client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 3003}, "from": {"id": 7070}, "text": "/referral"}},
    )
    assert "کد معرفی" in captured[-1]
    assert "t.me/MeDecoderBot?start=ref_" in captured[-1]
