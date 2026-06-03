from app.config import Settings


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "Custom API")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    settings = Settings()

    assert settings.PROJECT_NAME == "Custom API"
    assert settings.DEBUG is False
    assert settings.LLM_PROVIDER == "gemini"
