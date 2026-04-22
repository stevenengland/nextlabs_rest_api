from __future__ import annotations

from nextlabs_sdk._logging import _DEFAULT_BODY_LIMIT


def resolve_body_limit(verbose: int, env_value: str | None) -> int | None:
    """Return the effective log body limit.

    Precedence: ``NEXTLABS_LOG_BODY_LIMIT`` (when valid) beats the verbose
    level. ``0`` means unlimited. Invalid or negative env values fall back
    to the verbose-level default.
    """
    override_found, override = _parse_env_override(env_value)
    if override_found:
        return override
    if verbose >= 3:
        return None
    return _DEFAULT_BODY_LIMIT


def _parse_env_override(env_value: str | None) -> tuple[bool, int | None]:
    if env_value is None or env_value == "":
        return (False, None)
    try:
        parsed = int(env_value)
    except ValueError:
        return (False, None)
    if parsed == 0:
        return (True, None)
    if parsed > 0:
        return (True, parsed)
    return (False, None)
