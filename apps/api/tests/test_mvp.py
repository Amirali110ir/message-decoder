import os
import json

os.environ["DATABASE_URL"] = "sqlite:///./test_message_decoder.db"

from fastapi.testclient import TestClient

from app.database import db, init_db
from app.main import app
from app.config import get_settings


client = TestClient(app)


def setup_module():
    try:
        os.remove("test_message_decoder.db")
    except FileNotFoundError:
        pass
    init_db()


def auth_headers():
    client.post("/auth/request-otp", json={"phone": "09123456789"})
    res = client.post("/auth/verify-otp", json={"phone": "09123456789", "code": "25367286503"})
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


def test_successful_login_grants_credit_each_time():
    phone = "09120000000"
    client.post("/auth/request-otp", json={"phone": phone})
    first = client.post("/auth/verify-otp", json={"phone": phone, "code": "25367286503"}).json()
    client.post("/auth/request-otp", json={"phone": phone})
    second = client.post("/auth/verify-otp", json={"phone": phone, "code": "25367286503"}).json()
    assert first["credit_balance"] >= 1
    assert second["credit_balance"] == first["credit_balance"] + 1


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


def test_failed_payment_does_not_add_credits():
    headers = auth_headers()
    before = client.get("/user/credits", headers=headers).json()["credit_balance"]
    payment = client.post("/payment/create", json={"package_id": "credits_5"}, headers=headers).json()
    client.post("/payment/verify", json={"payment_id": payment["payment_id"], "status": "failed"}, headers=headers)
    after = client.get("/user/credits", headers=headers).json()["credit_balance"]
    assert after == before


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
