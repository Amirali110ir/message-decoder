from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
HEADERS = {"X-Admin-Token": "change-me-admin-token"}


def test_admin_rule_engine_explain_returns_scores_and_playbook():
    response = client.post(
        "/admin/rule-engine/explain",
        headers=HEADERS,
        json={
            "message_text": "حق نداری با اون آدم بری بیرون. اگه رفتی دیگه به من پیام نده.",
            "relationship_type": "romantic",
            "user_goal": "set_boundary",
            "privacy_consent": "none",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["dominant_lens"] == "dopamine"
    assert "lens_scores" in body["analysis"]
    assert "relationship_playbook" in body["paid_reply_playbook"]


def test_admin_rule_engine_eval_returns_metrics():
    response = client.get("/admin/rule-engine/eval", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["case_count"] >= 10
    assert "recommendations" in body


def test_admin_rule_engine_candidate_cases_returns_review_queue():
    response = client.get("/admin/rule-engine/candidate-cases?limit=5", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert "candidate_cases" in body
    assert "selection_rule" in body
