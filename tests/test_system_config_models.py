from __future__ import annotations

from nextlabs_sdk._cloudaz._system_config_models import SystemConfig


def test_system_config_from_response() -> None:
    raw = {
        "skydrm.installed": "false",
        "dashboard.widget.top-policies-and-trends.enabled": "true",
        "application.version": "2025.02",
    }
    config = SystemConfig.from_response(raw)
    assert config.settings == raw


def test_system_config_get_existing_key() -> None:
    config = SystemConfig.from_response({"app.version": "1.0"})
    assert config.get("app.version") == "1.0"


def test_system_config_get_missing_key_returns_default() -> None:
    config = SystemConfig.from_response({"app.version": "1.0"})
    assert config.get("missing.key") is None
    assert config.get("missing.key", "fallback") == "fallback"


def test_system_config_settings_are_iterable() -> None:
    raw = {"key1": "val1", "key2": "val2"}
    config = SystemConfig.from_response(raw)
    assert set(config.settings.keys()) == {"key1", "key2"}


def test_system_config_empty_response() -> None:
    config = SystemConfig.from_response({})
    assert config.settings == {}
    assert config.get("any") is None
