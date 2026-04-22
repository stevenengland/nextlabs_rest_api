"""Orchestrator: read payload source, decode, classify, validate."""

from __future__ import annotations

from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from nextlabs_sdk._pdp._payload._detect import detect_text_format
from nextlabs_sdk._pdp._payload._format import LoadedPayload, PayloadFormat
from nextlabs_sdk._pdp._payload._parse import parse_text
from nextlabs_sdk._pdp._payload._shape import is_raw_xacml, require_raw_xacml
from nextlabs_sdk._pdp._request_models import EvalRequest, PermissionsRequest
from nextlabs_sdk.exceptions import PdpPayloadError

_Model = TypeVar("_Model", bound=BaseModel)

PayloadSource = Path | str | bytes


def load_eval_payload(
    source: PayloadSource,
    *,
    payload_format: PayloadFormat = PayloadFormat.AUTO,
) -> LoadedPayload:
    """Load a payload and validate structured entries against ``EvalRequest``."""
    return _load(source, payload_format, EvalRequest)


def load_permissions_payload(
    source: PayloadSource,
    *,
    payload_format: PayloadFormat = PayloadFormat.AUTO,
) -> LoadedPayload:
    """Load a payload and validate structured entries against ``PermissionsRequest``."""
    return _load(source, payload_format, PermissionsRequest)


def _load(
    source: PayloadSource,
    payload_format: PayloadFormat,
    model_cls: Type[_Model],
) -> LoadedPayload:
    text = _read_source(source)
    text_format, force_raw_xacml = _resolve_text_format(text, payload_format)
    parsed = parse_text(text, text_format)
    if force_raw_xacml:
        return LoadedPayload.raw_xacml(require_raw_xacml(parsed))
    if is_raw_xacml(parsed):
        return LoadedPayload.raw_xacml(parsed)
    validated = _validate_structured(parsed, model_cls)
    assert isinstance(validated, (EvalRequest, PermissionsRequest))
    return LoadedPayload.structured(validated)


def _resolve_text_format(
    text: str,
    payload_format: PayloadFormat,
) -> tuple[PayloadFormat, bool]:
    if payload_format is PayloadFormat.JSON:
        return PayloadFormat.JSON, False
    if payload_format is PayloadFormat.YAML:
        return PayloadFormat.YAML, False
    if payload_format is PayloadFormat.XACML_JSON:
        return PayloadFormat.JSON, True
    return detect_text_format(text), False


def _read_source(source: PayloadSource) -> str:
    if isinstance(source, Path):
        return _read_path(source)
    if isinstance(source, bytes):
        return _decode_bytes(source)
    return source


def _read_path(path: Path) -> str:
    if not path.is_file():
        raise PdpPayloadError(f"Payload file not found: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PdpPayloadError(
            f"Payload file is not valid UTF-8: {path}: {exc}",
        ) from None
    except OSError as exc:
        raise PdpPayloadError(f"Could not read payload file {path}: {exc}") from None


def _decode_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PdpPayloadError(f"Payload bytes are not valid UTF-8: {exc}") from None


def _validate_structured(
    parsed: dict[str, object],
    model_cls: Type[_Model],
) -> _Model:
    try:
        return model_cls.model_validate(parsed)
    except ValidationError as exc:
        raise PdpPayloadError(_format_validation_error(exc)) from None


def _format_validation_error(exc: ValidationError) -> str:
    errors = exc.errors()
    lines = [_format_one_error(err) for err in errors]
    joined = "; ".join(lines) if lines else str(exc)
    return f"Invalid structured payload: {joined}"


def _format_one_error(err: object) -> str:
    if not isinstance(err, dict):
        return str(err)
    loc_parts = err.get("loc", ())
    if not isinstance(loc_parts, tuple):
        loc_parts = ()
    loc = ".".join(str(part) for part in loc_parts)
    msg = err.get("msg", "invalid")
    return f"{loc}: {msg}" if loc else str(msg)
