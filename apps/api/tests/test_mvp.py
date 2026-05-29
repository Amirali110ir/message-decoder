import os
import json
import hmac
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///./test_message_decoder.db"

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import db, init_db
from app.main import app
from app.config import Settings, get_settings
from app.services import auth as auth_service
from app.services import telegram as telegram_service


client = TestClient(app)
_auth_counter = 0


def setup_module():
    try:
        os.remove("test_message_decoder.db")
    except FileNotFoundError:
        pass
    init_db()


def auth_headers():
    global _auth_counter
    _auth_counter += 1
    phone = f"09123456{_auth_counter:03d}"
    requested = client.post("/auth/request-otp", json={"phone": phone}).json()
    res = client.post("/auth/verify-otp", json={"phone": phone, "code": requested["dev_otp_code"]})
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_free_decode_has_no_copy_ready_reply():
    res = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["free_output"]["dominant_lens"]["key"] == "oxytocin"
    assert "copy_ready_reply" not in body["free_output"]


def test_free_decode_includes_lens_mix_and_tone_stress():
    res = client.post(
        "/decode/free",
        json={
            "message_text": "این گزارش قرار بود دیروز آماده باشد. چرا هنوز باید پیگیری کنم؟",
            "relationship_type": "manager_colleague",
            "user_goal": "professional_reply",
            "privacy_consent": "none",
        },
    )
    assert res.status_code == 200
    output = res.json()["free_output"]
    mix = output["lens_mix"]
    dominant = output["dominant_lens"]["key"]
    assert sum(mix.values()) == 100
    assert mix[dominant] == max(mix.values())
    assert 0 <= output["tone_stress"]["intensity"] <= 100
    assert output["tone_stress"]["label"]


def test_ghost_mode_does_not_persist_message_or_decode():
    with db() as conn:
        before_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        before_decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]

    res = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "history",
            "optional_context": "اسم و جزئیات حساس دارد",
            "ghost_mode": True,
        },
    )
    assert res.status_code == 200

    with db() as conn:
        after_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        after_decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]
    assert after_messages == before_messages
    assert after_decodes == before_decodes


def test_paid_decode_for_ghost_decode_returns_not_found_before_credit_check():
    headers = auth_headers()
    token = headers["Authorization"].removeprefix("Bearer ")
    with db() as conn:
        row = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
        conn.execute("UPDATE users SET credit_balance = 0 WHERE id = ?", (row["user_id"],))

    ghost = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "history",
            "ghost_mode": True,
        },
        headers=headers,
    ).json()

    res = client.post("/decode/paid", json={"decode_id": ghost["decode_id"]}, headers=headers)
    assert res.status_code == 404


def test_ghost_paid_decode_consumes_credit_without_persisting_decode():
    headers = auth_headers()
    token = headers["Authorization"].removeprefix("Bearer ")
    with db() as conn:
        user = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
        before_balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user["user_id"],)).fetchone()["credit_balance"]
        before_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        before_decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]

    ghost = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "history",
            "ghost_mode": True,
        },
        headers=headers,
    )
    assert ghost.status_code == 200
    ghost_body = ghost.json()

    paid = client.post(
        "/decode/paid/ghost",
        json={
            "decode_id": ghost_body["decode_id"],
            "free_output": ghost_body["free_output"],
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
        },
        headers=headers,
    )
    assert paid.status_code == 200
    body = paid.json()
    assert body["decode_id"] == ghost_body["decode_id"]
    assert body["credit_balance"] == before_balance - 1
    assert body["paid_output"]["reply_options"]

    with db() as conn:
        after_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        after_decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]
    assert after_messages == before_messages
    assert after_decodes == before_decodes


def test_decode_with_contact_increments_interaction_count():
    headers = auth_headers()
    contact = client.post(
        "/contacts",
        json={
            "name": "سارا",
            "relationship_type": "romantic",
            "default_goal": "avoid_needy",
            "profile_summary": "معمولاً به سکوت حساس است و بهتر است مستقیم اطمینان بگیرد.",
        },
        headers=headers,
    )
    assert contact.status_code == 201
    contact_id = contact.json()["id"]

    res = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
            "contact_id": contact_id,
        },
        headers=headers,
    )
    assert res.status_code == 200

    contacts = client.get("/contacts", headers=headers).json()
    saved = next(item for item in contacts if item["id"] == contact_id)
    assert saved["interaction_count"] == 1


def test_decode_auto_creates_and_updates_contact_memory_from_named_context():
    headers = auth_headers()
    res = client.post(
        "/decode/free",
        json={
            "message_text": "من اشتباه کردم داروخانه زدم",
            "relationship_type": "friend",
            "user_goal": "understand_only",
            "privacy_consent": "history",
            "optional_context": "امیرعلی این پیام را فرستاده و معمولاً روی تصمیم‌های کاری سخت‌گیر است.",
        },
        headers=headers,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["contact_id"]
    assert "داروخانه" in body["free_output"]["message_focus"]
    assert "پرونده" in (body["free_output"]["personalization_note"] or "")

    contacts = client.get("/contacts", headers=headers).json()
    amirali = next(item for item in contacts if item["id"] == body["contact_id"])
    assert amirali["name"] == "امیرعلی"
    assert amirali["interaction_count"] == 1
    assert "داروخانه" in (amirali["memory_summary"] or amirali["profile_summary"])


def test_admin_decode_listing_is_anonymized_and_filterable():
    res = client.post(
        "/decode/free",
        json={
            "message_text": "شماره من 09123456789 است. این سفارش چرا هنوز آماده نیست؟",
            "relationship_type": "customer",
            "user_goal": "professional_reply",
            "privacy_consent": "anonymized",
        },
    )
    assert res.status_code == 200

    listing = client.get(
        "/admin/decodes?relationship_type=customer",
        headers={"X-Admin-Token": "change-me-admin-token"},
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 1
    assert body["items"]
    assert all(item["relationship_type"] == "customer" for item in body["items"])
    encoded = json.dumps(body, ensure_ascii=False)
    assert "09123456789" not in encoded
    assert "raw_text" not in encoded
    assert "[شماره موبایل]" in encoded


def test_user_history_only_contains_opted_in_decodes_and_can_delete_one():
    headers = auth_headers()
    kept = client.post(
        "/decode/free",
        json={
            "message_text": "این پیام باید در تاریخچه من بماند.",
            "relationship_type": "friend",
            "user_goal": "understand_only",
            "privacy_consent": "history",
        },
        headers=headers,
    ).json()
    hidden = client.post(
        "/decode/free",
        json={
            "message_text": "این پیام نباید در تاریخچه نمایش داده شود.",
            "relationship_type": "friend",
            "user_goal": "understand_only",
            "privacy_consent": "none",
        },
        headers=headers,
    ).json()

    history = client.get("/decode/history", headers=headers)
    assert history.status_code == 200
    ids = [item["id"] for item in history.json()["items"]]
    assert kept["decode_id"] in ids
    assert hidden["decode_id"] not in ids

    delete_res = client.delete(f"/decode/{kept['decode_id']}", headers=headers)
    assert delete_res.status_code == 200
    history_after = client.get("/decode/history", headers=headers).json()
    assert kept["decode_id"] not in [item["id"] for item in history_after["items"]]


def test_user_stored_data_delete_removes_history_and_contacts():
    headers = auth_headers()
    client.post(
        "/contacts",
        json={
            "name": "علی",
            "relationship_type": "friend",
            "default_goal": "understand_only",
            "profile_summary": "دوست قدیمی",
        },
        headers=headers,
    )
    client.post(
        "/decode/free",
        json={
            "message_text": "برای حذف کامل داده ذخیره می‌شود.",
            "relationship_type": "friend",
            "user_goal": "understand_only",
            "privacy_consent": "history",
        },
        headers=headers,
    )

    res = client.delete("/user/stored-data", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["deleted_decodes"] >= 1
    assert body["deleted_messages"] >= 1
    assert body["deleted_contacts"] >= 1
    assert client.get("/decode/history", headers=headers).json()["items"] == []
    assert client.get("/contacts", headers=headers).json() == []


def test_paid_decode_includes_reaction_predictions_and_selected_reply_feedback():
    headers = auth_headers()
    contact = client.post(
        "/contacts",
        json={
            "name": "مینا",
            "relationship_type": "romantic",
            "default_goal": "avoid_needy",
            "profile_summary": "به توضیح مستقیم بهتر پاسخ می‌دهد.",
        },
        headers=headers,
    ).json()
    free = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
            "contact_id": contact["id"],
        },
        headers=headers,
    ).json()
    paid = client.post("/decode/paid", json={"decode_id": free["decode_id"]}, headers=headers)
    assert paid.status_code == 200
    replies = paid.json()["paid_output"]["reply_options"]
    assert replies
    assert all(reply["reaction_prediction"] for reply in replies)

    selected = client.post(
        "/feedback/selected-reply",
        json={
            "decode_id": free["decode_id"],
            "selected_reply_label": replies[0]["label"],
            "copied_response": True,
            "outcome": "تنش کمتر شد",
        },
        headers=headers,
    )
    assert selected.status_code == 200
    with db() as conn:
        signal = conn.execute(
            "SELECT signal_value FROM quality_signals WHERE decode_id = ? AND signal_name = 'selected_reply_label'",
            (free["decode_id"],),
        ).fetchone()
        updated_contact = conn.execute("SELECT profile_summary FROM contacts WHERE id = ?", (contact["id"],)).fetchone()
    assert signal["signal_value"] == replies[0]["label"]
    assert replies[0]["label"] in updated_contact["profile_summary"]
    assert "تنش کمتر شد" in updated_contact["profile_summary"]


def test_relationship_thermometer_for_contact():
    headers = auth_headers()
    contact = client.post(
        "/contacts",
        json={
            "name": "رضا",
            "relationship_type": "friend",
            "default_goal": "set_boundary",
            "profile_summary": "به احترام مستقیم حساس است.",
        },
        headers=headers,
    ).json()
    client.post(
        "/decode/free",
        json={
            "message_text": "این کار اصلاً محترمانه نبود و انتظار بیشتری داشتم.",
            "relationship_type": "friend",
            "user_goal": "set_boundary",
            "privacy_consent": "none",
            "contact_id": contact["id"],
        },
        headers=headers,
    )

    res = client.get(f"/contacts/{contact['id']}/thermometer", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["contact_id"] == contact["id"]
    assert body["interaction_count"] == 1
    assert 0 <= body["warmth_score"] <= 100
    assert -100 <= body["defensive_trend"] <= 100
    assert body["label"]


def test_paid_decode_requires_credit():
    headers = auth_headers()
    token = headers["Authorization"].removeprefix("Bearer ")
    with db() as conn:
        row = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
        conn.execute("UPDATE users SET credit_balance = 0 WHERE id = ?", (row["user_id"],))
    free = client.post(
        "/decode/free",
        json={
            "message_text": "این گزارش قرار بود دیروز آماده باشد. چرا هنوز باید پیگیری کنم؟",
            "relationship_type": "manager_colleague",
            "user_goal": "professional_reply",
            "privacy_consent": "anonymized",
        },
    ).json()
    res = client.post("/decode/paid", json={"decode_id": free["decode_id"]}, headers=headers)
    assert res.status_code == 402


def test_successful_login_grants_signup_credit_only_once():
    phone = "09120000000"
    first_otp = client.post("/auth/request-otp", json={"phone": phone}).json()["dev_otp_code"]
    first = client.post("/auth/verify-otp", json={"phone": phone, "code": first_otp}).json()
    second_otp = client.post("/auth/request-otp", json={"phone": phone}).json()["dev_otp_code"]
    second = client.post("/auth/verify-otp", json={"phone": phone, "code": second_otp}).json()
    assert first["credit_balance"] >= 1
    assert second["credit_balance"] == first["credit_balance"]


def test_otp_is_single_use():
    phone = "09127770000"
    code = client.post("/auth/request-otp", json={"phone": phone}).json()["dev_otp_code"]
    assert client.post("/auth/verify-otp", json={"phone": phone, "code": code}).status_code == 200
    assert client.post("/auth/verify-otp", json={"phone": phone, "code": code}).status_code == 401


def test_otp_payload_is_created_for_linked_telegram_user(monkeypatch):
    phone = "09123334444"
    settings = Settings(
        otp_provider="kavenegar",
        kavenegar_api_key="test-key",
        kavenegar_method="send",
        kavenegar_sender="10001",
        kavenegar_message_template="رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}",
        telegram_bridge_secret="bridge-secret",
    )

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "112233")
    monkeypatch.setattr(auth_service, "send_kavenegar_otp", lambda *a, **kw: None)

    with db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel)
            VALUES ('user_telegram_otp', ?, '778899', datetime('now'), 1, 'telegram')
            """,
            (phone,),
        )

    code, payload = auth_service.request_otp_code(phone, settings)

    assert code is None  # non-mock providers do not expose the code
    assert payload is not None
    assert payload["chat_id"] == "778899"
    assert payload["text"] == "رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: 112233\n\nشماره درخواست‌کننده: 09123334444"
    expected_signature = hmac.new(
        b"bridge-secret",
        f"{payload['chat_id']}|{payload['text']}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert payload["signature"] == expected_signature


def test_otp_payload_matches_telegram_country_code_phone(monkeypatch):
    settings = Settings(
        otp_provider="kavenegar",
        kavenegar_api_key="test-key",
        kavenegar_method="send",
        kavenegar_sender="10001",
        telegram_bridge_secret="bridge-secret",
    )

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "112244")
    monkeypatch.setattr(auth_service, "send_kavenegar_otp", lambda *a, **kw: None)

    with db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel)
            VALUES ('user_telegram_country_phone', '09123335555', '778811', datetime('now'), 1, 'telegram')
            """
        )

    code, payload = auth_service.request_otp_code("+989123335555", settings)

    assert code is None
    assert payload is not None
    assert payload["chat_id"] == "778811"


def test_smsir_otp_payload_uses_smsir_message_template_for_linked_telegram_user(monkeypatch):
    phone = "09124446666"
    settings = Settings(
        otp_provider="smsir",
        smsir_api_key="test-smsir-key",
        smsir_method="bulk",
        smsir_line_number="300089931441",
        smsir_message_template="کد ورود دکودر: {code}",
        telegram_bridge_secret="bridge-secret",
    )

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"status": 1, "message": "ok", "data": {"messageIds": [123]}}

    with db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel)
            VALUES ('user_smsir_telegram_otp', ?, '778822', datetime('now'), 1, 'telegram')
            """,
            (phone,),
        )

    def fake_post(url, json, headers, timeout):
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "932841")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    dev_code, payload = auth_service.request_otp_code(phone, settings)

    assert dev_code is None
    assert payload is not None
    assert payload["chat_id"] == "778822"
    assert payload["text"] == "کد ورود دکودر: 932841\n\nشماره درخواست‌کننده: 09124446666"


def test_otp_payload_is_absent_without_bridge_secret():
    phone = "09123334445"
    settings = Settings(otp_provider="mock", dev_otp_code="445566")

    with db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel)
            VALUES ('user_telegram_relay_otp', ?, '778800', datetime('now'), 1, 'telegram')
            """,
            (phone,),
        )

    code, payload = auth_service.request_otp_code(phone, settings)

    assert code == "445566"
    assert payload is None


def test_magic_otp_code_does_not_bypass_stored_code():
    phone = "09124444444"
    with db() as conn:
        conn.execute(
            """
            INSERT INTO auth_otps (phone, code, created_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(phone) DO UPDATE SET code = excluded.code, created_at = excluded.created_at
            """,
            (phone, "111111"),
        )
    res = client.post("/auth/verify-otp", json={"phone": phone, "code": "25367286503"})
    assert res.status_code == 401


def test_kavenegar_provider_sends_lookup_and_stores_generated_code(monkeypatch):
    phone = "۰۹۱۲۳۴۵۶۷۸۹"
    settings = Settings(
        otp_provider="kavenegar",
        kavenegar_method="verify_lookup",
        kavenegar_api_key="test-key",
        kavenegar_template="message-decoder-login",
    )
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"return": {"status": 200, "message": "ok"}}

    def fake_post(url, data, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "738291")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    dev_code, telegram_payload = auth_service.request_otp_code(phone, settings)

    assert dev_code is None
    assert telegram_payload is None
    assert captured["url"] == "https://api.kavenegar.com/v1/test-key/verify/lookup.json"
    assert captured["data"] == {
        "receptor": "09123456789",
        "token": "738291",
        "template": "message-decoder-login",
        "type": "sms",
    }
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", ("09123456789",)).fetchone()
    assert otp["code"] == "738291"


def test_kavenegar_provider_can_send_plain_sms_otp(monkeypatch):
    phone = "۰۹۱۲۳۴۵۶۷۸۹"
    settings = Settings(
        otp_provider="kavenegar",
        kavenegar_method="send",
        kavenegar_api_key="test-key",
        kavenegar_sender="2000660110",
        kavenegar_message_template="رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}",
    )
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"return": {"status": 200, "message": "ok"}}

    def fake_post(url, data, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "654321")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    dev_code, telegram_payload = auth_service.request_otp_code(phone, settings)

    assert dev_code is None
    assert telegram_payload is None
    assert captured["url"] == "https://api.kavenegar.com/v1/test-key/sms/send.json"
    assert captured["data"] == {
        "receptor": "09123456789",
        "sender": "2000660110",
        "message": "رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: 654321",
    }
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", ("09123456789",)).fetchone()
    assert otp["code"] == "654321"


def test_smsir_provider_sends_verify_template_and_logs_success(monkeypatch):
    phone = "۰۹۱۲۳۴۵۶۷۸۹"
    settings = Settings(
        otp_provider="smsir",
        smsir_api_key="test-smsir-key",
        smsir_template_id="678614",
        smsir_parameter_name="Code",
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"status": 1, "message": "ok", "data": {"messageId": 98765}}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "738291")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    dev_code, telegram_payload = auth_service.request_otp_code(phone, settings)

    assert dev_code is None
    assert telegram_payload is None
    assert captured["url"] == "https://api.sms.ir/v1/send/verify"
    assert captured["json"] == {
        "mobile": "09123456789",
        "templateId": 678614,
        "parameters": [{"name": "Code", "value": "738291"}],
    }
    assert captured["headers"]["x-api-key"] == "test-smsir-key"
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", ("09123456789",)).fetchone()
        log = conn.execute(
            "SELECT provider, purpose, phone, template_id, message_id, status FROM sms_send_logs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert otp["code"] == "738291"
    assert dict(log) == {
        "provider": "smsir",
        "purpose": "otp",
        "phone": "09123456789",
        "template_id": "678614",
        "message_id": "98765",
        "status": "sent",
    }


def test_smsir_provider_logs_rejected_send_without_storing_otp(monkeypatch):
    phone = "09129999999"
    settings = Settings(
        otp_provider="smsir",
        smsir_api_key="test-smsir-key",
        smsir_template_id="678614",
    )

    class FakeResponse:
        status_code = 400

        def json(self):
            return {"status": 0, "message": "template not found"}

    def fake_post(url, json, headers, timeout):
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "829173")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    with pytest.raises(HTTPException) as exc:
        auth_service.request_otp_code(phone, settings)
    assert exc.value.status_code == 502
    # User-facing detail is now a clean Persian message; raw provider message is kept in the log.
    assert "ارسال پیامک" in exc.value.detail
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", (phone,)).fetchone()
        log = conn.execute(
            "SELECT status, error_message FROM sms_send_logs WHERE phone = ? ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
    assert otp is None
    assert log["status"] == "failed"
    assert log["error_message"] == "template not found"


def test_smsir_provider_can_send_bulk_otp_without_template_and_logs_success(monkeypatch):
    phone = "۰۹۱۲۳۴۵۶۷۸۹"
    settings = Settings(
        otp_provider="smsir",
        smsir_method="bulk",
        smsir_api_key="test-smsir-key",
        smsir_line_number="300089931441",
        smsir_message_template="رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}",
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"status": 1, "message": "ok", "data": {"packId": "pack_1", "messageIds": [414521489], "cost": 1}}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(auth_service, "generate_otp_code", lambda: "482913")
    monkeypatch.setattr(auth_service.httpx, "post", fake_post)

    dev_code, telegram_payload = auth_service.request_otp_code(phone, settings)

    assert dev_code is None
    assert telegram_payload is None
    assert captured["url"] == "https://api.sms.ir/v1/send/bulk"
    assert captured["json"] == {
        "lineNumber": 300089931441,
        "messageText": "رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: 482913",
        "mobiles": ["09123456789"],
        "sendDateTime": None,
    }
    assert captured["headers"]["x-api-key"] == "test-smsir-key"
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", ("09123456789",)).fetchone()
        log = conn.execute(
            "SELECT provider, purpose, phone, message_id, status FROM sms_send_logs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert otp["code"] == "482913"
    assert dict(log) == {
        "provider": "smsir",
        "purpose": "otp",
        "phone": "09123456789",
        "message_id": "414521489",
        "status": "sent",
    }


def test_payment_verify_adds_credits_and_paid_consumes_one():
    headers = auth_headers()
    payment = client.post("/payment/create", json={"package_id": "credits_5"}, headers=headers).json()
    verify = client.post(
        "/payment/verify",
        json={"payment_id": payment["payment_id"], "status": "sandbox_success"},
        headers=headers,
    )
    assert verify.json()["credit_balance"] >= 5
    free = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
        },
    ).json()
    paid = client.post("/decode/paid", json={"decode_id": free["decode_id"]}, headers=headers)
    assert paid.status_code == 200
    assert paid.json()["credit_balance"] >= 4


def test_production_paid_decode_does_not_charge_without_ai(monkeypatch):
    headers = auth_headers()
    free = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
        },
    ).json()
    before = client.get("/user/credits", headers=headers).json()["credit_balance"]
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    try:
        paid = client.post("/decode/paid", json={"decode_id": free["decode_id"]}, headers=headers)
        after = client.get("/user/credits", headers=headers).json()["credit_balance"]
    finally:
        get_settings.cache_clear()

    assert paid.status_code == 503
    assert after == before


def test_production_startup_rejects_default_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_PHONE", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    try:
        Settings().validate_for_startup()
        assert False, "production startup should reject default or missing secrets"
    except RuntimeError as exc:
        message = str(exc)
    assert "JWT_SECRET" in message
    assert "ADMIN_TOKEN" in message
    assert "ADMIN_PHONE" in message
    assert "ADMIN_PASSWORD" in message


def test_failed_payment_does_not_add_credits():
    headers = auth_headers()
    before = client.get("/user/credits", headers=headers).json()["credit_balance"]
    payment = client.post("/payment/create", json={"package_id": "credits_5"}, headers=headers).json()
    client.post("/payment/verify", json={"payment_id": payment["payment_id"], "status": "failed"}, headers=headers)
    after = client.get("/user/credits", headers=headers).json()["credit_balance"]
    assert after == before


def test_telegram_onboarding_contact_and_free_decode(monkeypatch):
    sent = []

    async def fake_send(chat_id, text, reply_markup=None):
        sent.append({"chat_id": str(chat_id), "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send)

    start = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1001},
                "from": {"id": 501},
                "text": "/start",
            }
        },
    )
    assert start.status_code == 200
    assert sent[-1]["reply_markup"]["keyboard"][0][0]["request_contact"] is True

    contact = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1001},
                "from": {"id": 501},
                "contact": {"user_id": 501, "phone_number": "09125550101"},
            }
        },
    )
    assert contact.status_code == 200

    message = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1001},
                "from": {"id": 501},
                "text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            }
        },
    )
    assert message.status_code == 200
    assert sent[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("rel:")

    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "from": {"id": 501},
                "message": {"chat": {"id": 1001}},
                "data": "rel:romantic",
            }
        },
    )
    assert sent[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("goal:")

    free = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "from": {"id": 501},
                "message": {"chat": {"id": 1001}},
                "data": "goal:avoid_needy",
            }
        },
    )
    assert free.status_code == 200
    assert "تحلیل سریع" in sent[-1]["text"]
    assert sent[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("paid:")


def test_telegram_ghost_free_decode_has_no_paid_button(monkeypatch):
    sent = []

    async def fake_send(chat_id, text, reply_markup=None):
        sent.append({"chat_id": str(chat_id), "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send)
    client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1002},
                "from": {"id": 502},
                "contact": {"user_id": 502, "phone_number": "09125550102"},
            }
        },
    )
    client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 1002}, "from": {"id": 502}, "text": "/ghost"}},
    )
    client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1002},
                "from": {"id": 502},
                "text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            }
        },
    )
    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "from": {"id": 502},
                "message": {"chat": {"id": 1002}},
                "data": "rel:romantic",
            }
        },
    )
    res = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "from": {"id": 502},
                "message": {"chat": {"id": 1002}},
                "data": "goal:avoid_needy",
            }
        },
    )
    assert res.status_code == 200
    assert "Ghost Mode" in sent[-1]["text"]
    assert sent[-1]["reply_markup"] is None


def test_production_zarinpal_create_and_verify_shape(monkeypatch):
    calls = []

    def fake_post(path, payload):
        calls.append((path, payload))
        if path.endswith("/request.json"):
            return {"data": {"code": 100, "authority": "A000000000000000000000000000000001"}}
        return {"data": {"code": 100, "ref_id": 987654321}}

    monkeypatch.setenv("ZARINPAL_MERCHANT_ID", "merchant-test")
    monkeypatch.setenv("ZARINPAL_START_PAY_URL", "https://www.zarinpal.com/pg/StartPay")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.payments._post_zarinpal", fake_post)

    headers = auth_headers()
    before = client.get("/user/credits", headers=headers).json()["credit_balance"]
    payment = client.post("/payment/create", json={"package_id": "credits_5"}, headers=headers)
    assert payment.status_code == 200
    payment_body = payment.json()
    assert payment_body["authority"] == "A000000000000000000000000000000001"
    assert payment_body["payment_url"].endswith("/A000000000000000000000000000000001")
    assert calls[0][0].endswith("/request.json")
    assert calls[0][1]["merchant_id"] == "merchant-test"
    assert calls[0][1]["callback_url"].endswith(f"payment_id={payment_body['payment_id']}")

    verified = client.post(
        "/payment/verify",
        json={
            "payment_id": payment_body["payment_id"],
            "authority": payment_body["authority"],
            "status": "OK",
        },
        headers=headers,
    )
    assert verified.status_code == 200
    verify_body = verified.json()
    assert verify_body["status"] == "verified"
    assert verify_body["ref_id"] == "987654321"
    assert verify_body["credit_balance"] == before + 5
    assert calls[1][0].endswith("/verify.json")
    assert calls[1][1]["authority"] == payment_body["authority"]
    get_settings.cache_clear()


def test_production_zarinpal_rejects_mismatched_authority(monkeypatch):
    monkeypatch.setenv("ZARINPAL_MERCHANT_ID", "merchant-test")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.payments._post_zarinpal",
        lambda path, payload: {"data": {"code": 100, "authority": "A-match"}},
    )

    headers = auth_headers()
    payment = client.post("/payment/create", json={"package_id": "credits_5"}, headers=headers).json()
    res = client.post(
        "/payment/verify",
        json={"payment_id": payment["payment_id"], "authority": "A-other", "status": "OK"},
        headers=headers,
    )
    assert res.status_code == 400
    get_settings.cache_clear()


def test_safety_message_uses_safety_mode():
    res = client.post(
        "/decode/free",
        json={
            "message_text": "اگه جواب ندی میام دم خونتون و می‌فهمی چی می‌شه.",
            "relationship_type": "ex",
            "user_goal": "calm_conflict",
            "privacy_consent": "none",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["safety_label"] == "high_risk"
    assert body["safety_output"]["warning_title"] == "هشدار امنیتی"
