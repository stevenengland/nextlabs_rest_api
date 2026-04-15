from __future__ import annotations

import pytest

from nextlabs_sdk._config import HttpConfig, RetryConfig


def test_retry_config_defaults() -> None:
    config = RetryConfig()
    assert config.max_retries == 3
    assert config.base_delay == pytest.approx(1.0)
    assert config.max_delay == pytest.approx(30.0)


def test_retry_config_custom_values() -> None:
    config = RetryConfig(max_retries=5, base_delay=2.0, max_delay=60.0)
    assert config.max_retries == 5
    assert config.base_delay == pytest.approx(2.0)
    assert config.max_delay == pytest.approx(60.0)


def test_retry_config_is_frozen() -> None:
    config = RetryConfig()
    with pytest.raises(AttributeError):
        config.max_retries = 10  # type: ignore[misc]


def test_http_config_defaults() -> None:
    config = HttpConfig()
    assert config.timeout == pytest.approx(30.0)
    assert config.verify_ssl is True
    assert config.retry == RetryConfig()


def test_http_config_custom_retry() -> None:
    retry = RetryConfig(max_retries=0)
    config = HttpConfig(timeout=10.0, verify_ssl=False, retry=retry)
    assert config.timeout == pytest.approx(10.0)
    assert config.verify_ssl is False
    assert config.retry.max_retries == 0
