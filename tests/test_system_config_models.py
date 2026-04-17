from __future__ import annotations

from nextlabs_sdk._cloudaz._system_config_models import SystemConfig


def test_system_config_from_response_roundtrips_settings():
    raw = {
        "skydrm.installed": "false",
        "dashboard.widget.top-policies-and-trends.enabled": "true",
        "application.version": "2025.02",
    }
    config = SystemConfig.from_response(raw)
    assert config.settings == raw


def test_system_config_get_behaviour():
    config = SystemConfig.from_response({"app.version": "1.0"})
    assert config.get("app.version") == "1.0"
    assert config.get("missing.key") is None
    assert config.get("missing.key", "fallback") == "fallback"


def test_system_config_settings_are_iterable():
    config = SystemConfig.from_response({"key1": "val1", "key2": "val2"})
    assert set(config.settings.keys()) == {"key1", "key2"}


def test_system_config_empty_response():
    config = SystemConfig.from_response({})
    assert config.settings == {}
    assert config.get("any") is None
