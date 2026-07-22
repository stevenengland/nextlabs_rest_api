from __future__ import annotations

import pytest

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide


@pytest.mark.parametrize(
    "refresh_token,refresh_expires_at,now,expected",
    [
        pytest.param(None, None, 100.0, RefreshDecision.ABSENT, id="absent-no-token"),
        pytest.param(
            None, 99.0, 100.0, RefreshDecision.ABSENT, id="absent-even-with-expiry"
        ),
        pytest.param(
            "rt",
            None,
            100.0,
            RefreshDecision.USE_REFRESH,
            id="use-refresh-unknown-expiry",
        ),
        pytest.param(
            "rt",
            200.0,
            100.0,
            RefreshDecision.USE_REFRESH,
            id="use-refresh-future-expiry",
        ),
        pytest.param(
            "rt",
            100.0,
            100.0,
            RefreshDecision.KNOWN_EXPIRED,
            id="known-expired-at-boundary",
        ),
        pytest.param(
            "rt", 100.0, 101.0, RefreshDecision.KNOWN_EXPIRED, id="known-expired-past"
        ),
        pytest.param(
            "rt",
            100.0,
            99.999,
            RefreshDecision.USE_REFRESH,
            id="use-refresh-just-before-expiry",
        ),
    ],
)
def test_decide(
    refresh_token: str | None,
    refresh_expires_at: float | None,
    now: float,
    expected: RefreshDecision,
) -> None:
    assert (
        decide(
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
            now=now,
        )
        == expected
    )
