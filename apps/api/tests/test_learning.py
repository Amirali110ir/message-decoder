import os

os.environ["DATABASE_URL"] = "sqlite:///./test_learning.db"

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


client = TestClient(app)


def setup_module():
    try:
        os.remove("test_learning.db")
    except FileNotFoundError:
        pass
    init_db()


def test_admin_daily_learning_report_returns_metrics():
    free = client.post(
        "/decode/free",
        json={
            "message_text": "باشه، هر جور راحتی. معلومه برات مهم نیست.",
            "relationship_type": "romantic",
            "user_goal": "avoid_needy",
            "privacy_consent": "none",
        },
    ).json()
    client.post("/copy-event", json={"decode_id": free["decode_id"], "reply_label": "نرم"})
    client.post(
        "/feedback",
        json={
            "decode_id": free["decode_id"],
            "user_rating": "good",
            "outcome": "helpful",
            "regret_score": 1,
        },
    )

    report = client.get("/admin/learning/daily", headers={"X-Admin-Token": "change-me-admin-token"})

    assert report.status_code == 200
    body = report.json()
    assert "metrics" in body
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
