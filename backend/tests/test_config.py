from app.config import get_settings


def test_settings_loads_defaults():
    s = get_settings()
    assert s.app_name == "Airport360"
    assert s.api_v1_prefix == "/v1"
    assert s.access_token_expire_minutes == 480


def test_cors_origins_default():
    s = get_settings()
    assert "http://localhost:5173" in s.cors_origins
