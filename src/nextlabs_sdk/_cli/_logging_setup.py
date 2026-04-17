from __future__ import annotations

import logging
import sys

_HANDLER_NAME = "nextlabs-cli-verbose"
_LOGGER_NAME = "nextlabs_sdk"


def configure_cli_logging(verbose: int) -> None:
    """Attach a stderr handler to the SDK logger when verbose >= 2.

    Idempotent: subsequent calls neither duplicate the handler nor
    lower the log level.
    """
    if verbose < 2:
        return
    sdk_logger = logging.getLogger(_LOGGER_NAME)
    for existing in sdk_logger.handlers:
        if getattr(existing, "name", None) == _HANDLER_NAME:
            return
    stream = logging.StreamHandler(sys.stderr)
    stream.name = _HANDLER_NAME
    stream.setLevel(logging.DEBUG)
    stream.setFormatter(logging.Formatter("%(message)s"))
    sdk_logger.addHandler(stream)
    sdk_logger.setLevel(logging.DEBUG)
