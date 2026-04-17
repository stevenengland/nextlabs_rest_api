from __future__ import annotations

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide


def test_absent_when_no_refresh_token() -> None:
    assert decide(refresh_token=None, refresh_expires_at=None, now=100.0) == (
        RefreshDecision.ABSENT
    )


def test_absent_even_when_expiry_is_set() -> None:
    """An absent refresh token always resolves to ABSENT regardless of expiry."""
    assert (
        decide(refresh_token=None, refresh_expires_at=99.0, now=100.0)
        == RefreshDecision.ABSENT
    )


def test_use_refresh_when_expiry_unknown() -> None:
    assert (
        decide(refresh_token="rt", refresh_expires_at=None, now=100.0)
        == RefreshDecision.USE_REFRESH
    )


def test_use_refresh_when_expiry_in_future() -> None:
    assert (
        decide(refresh_token="rt", refresh_expires_at=200.0, now=100.0)
        == RefreshDecision.USE_REFRESH
    )


def test_known_expired_at_boundary() -> None:
    assert (
        decide(refresh_token="rt", refresh_expires_at=100.0, now=100.0)
        == RefreshDecision.KNOWN_EXPIRED
    )


def test_known_expired_when_now_past_expiry() -> None:
    assert (
        decide(refresh_token="rt", refresh_expires_at=100.0, now=101.0)
        == RefreshDecision.KNOWN_EXPIRED
    )


def test_use_refresh_just_before_expiry() -> None:
    assert (
        decide(refresh_token="rt", refresh_expires_at=100.0, now=99.999)
        == RefreshDecision.USE_REFRESH
    )
