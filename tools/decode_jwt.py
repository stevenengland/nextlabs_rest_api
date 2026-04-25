"""Decode a JWT locally without verifying its signature.

Reads a token from a CLI argument, a file, stdin, or the clipboard-style
``-`` marker, then prints the decoded header and payload as pretty JSON.
Signature verification is intentionally skipped — this is a debugging
aid, not a security tool.

Examples::

    python tools/decode_jwt.py eyJhbGciOi...
    python tools/decode_jwt.py --file token.txt
    echo "$TOKEN" | python tools/decode_jwt.py -
    python tools/decode_jwt.py --raw eyJhbGciOi...   # no pretty-printing
    python tools/decode_jwt.py --claim exp eyJhbGciOi...
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

JsonDict = dict[str, object]


TIMESTAMP_CLAIMS = {"exp", "iat", "nbf", "auth_time", "updated_at"}


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def decode_jwt(token: str) -> tuple[JsonDict, JsonDict, bytes]:
    """Return ``(header, payload, signature_bytes)`` for a JWT.

    Raises ``ValueError`` if the token is malformed.
    """
    token = token.strip()
    non_ascii = sorted({ch for ch in token if ord(ch) > 127})
    if non_ascii:
        preview = ", ".join(f"{ch!r} (U+{ord(ch):04X})" for ch in non_ascii)
        raise ValueError(
            "Token contains non-ASCII characters — it was likely truncated "
            f"or elided during copy/paste (found: {preview})."
        )
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected 3 dot-separated segments, got {len(parts)}.")
    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
        signature = _b64url_decode(parts[2]) if parts[2] else b""
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JWT encoding: {exc}") from exc
    return header, payload, signature


def _annotate_timestamps(payload: JsonDict) -> JsonDict:
    annotated = dict(payload)
    for key in TIMESTAMP_CLAIMS & payload.keys():
        value = payload[key]
        if isinstance(value, (int, float)):
            iso = datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
            annotated[f"{key}_iso"] = iso
    return annotated


def _read_token(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()
    if args.token == "-" or args.token is None and not sys.stdin.isatty():
        return sys.stdin.read().strip()
    if args.token:
        return args.token
    raise SystemExit("No token provided. Pass a token, --file PATH, or pipe via stdin.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a JWT locally without verifying its signature."
    )
    parser.add_argument("token", nargs="?", help="JWT string, or '-' to read stdin.")
    parser.add_argument("--file", "-f", help="Read the token from a file.")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Do not add ISO timestamps for exp/iat/nbf claims.",
    )
    parser.add_argument(
        "--claim",
        "-c",
        help="Print only the value of a single payload claim.",
    )
    parser.add_argument(
        "--part",
        choices=("header", "payload", "all"),
        default="all",
        help="Which section to print (default: all).",
    )
    args = parser.parse_args(argv)

    token = _read_token(args)
    try:
        header, payload, signature = decode_jwt(token)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.claim:
        if args.claim not in payload:
            print(f"error: claim '{args.claim}' not in payload", file=sys.stderr)
            return 1
        value = payload[args.claim]
        print(value if isinstance(value, str) else json.dumps(value, indent=2))
        return 0

    payload_out = payload if args.raw else _annotate_timestamps(payload)

    def dump(label: str, obj: JsonDict) -> None:
        print(f"--- {label} ---")
        print(json.dumps(obj, indent=2, sort_keys=True, default=str))

    if args.part in ("header", "all"):
        dump("header", header)
    if args.part in ("payload", "all"):
        dump("payload", payload_out)
    if args.part == "all":
        print(f"--- signature ({len(signature)} bytes, not verified) ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
