import os

os.environ["DATABASE_URL"] = "sqlite:///./test_message_decoder.db"

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


client = TestClient(app)


def setup_module():
    try:
        os.remove("test_message_decoder.db")
    except FileNotFoundError:
        pass
    init_db()


def auth_headers():
    client.post("/auth/request-otp", json={"phone": "09123456789"})
    res = client.post("/auth/verify-otp", json={"phone": "09123456789", "code": "123456"})
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


def test_paid_decode_requires_credit():
    headers = auth_headers()
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

