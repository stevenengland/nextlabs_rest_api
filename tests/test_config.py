from __future__ import annotations

import pytest

from nextlabs_sdk._config import HttpConfig, RetryConfig


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        pytest.param({}, (3, 1.0, 30.0), id="defaults"),
        pytest.param(
            {"max_retries": 5, "base_delay": 2.0, "max_delay": 60.0},
            (5, 2.0, 60.0),
            id="custom",
        ),
    ],
)
def test_retry_config_values(kwargs, expected):
    config = RetryConfig(**kwargs)
    assert config.max_retries == expected[0]
    assert config.base_delay == pytest.approx(expected[1])
    assert config.max_delay == pytest.approx(expected[2])


def test_retry_config_is_frozen():
    config = RetryConfig()
    with pytest.raises(AttributeError):
        config.max_retries = 10  # type: ignore[misc]


def test_http_config_defaults():
    config = HttpConfig()
    assert config.timeout == pytest.approx(30.0)
    assert config.verify_ssl is True
    assert config.retry == RetryConfig()


def test_http_config_custom_retry():
    retry = RetryConfig(max_retries=0)
    config = HttpConfig(timeout=10.0, verify_ssl=False, retry=retry)
    assert config.timeout == pytest.approx(10.0)
    assert config.verify_ssl is False
    assert config.retry.max_retries == 0
