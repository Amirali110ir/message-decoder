from app.config import get_settings
from app.services.ai import current_model_version


def test_task_specific_models_use_new_env(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "liara")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "legacy-model")
    monkeypatch.setenv("AI_FREE_MODEL", "fast-free-model")
    monkeypatch.setenv("AI_PAID_MODEL", "quality-paid-model")

    assert current_model_version("free") == "fast-free-model"
    assert current_model_version("paid") == "quality-paid-model"
    get_settings.cache_clear()


def test_task_specific_models_fall_back_to_legacy_model(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "liara")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "legacy-model")
    monkeypatch.delenv("AI_FREE_MODEL", raising=False)
    monkeypatch.delenv("AI_PAID_MODEL", raising=False)

    assert current_model_version("free") == "legacy-model"
    assert current_model_version("paid") == "legacy-model"
    get_settings.cache_clear()
