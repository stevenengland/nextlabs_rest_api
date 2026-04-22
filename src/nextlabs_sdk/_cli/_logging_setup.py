from __future__ import annotations

import logging
import os
import sys

from nextlabs_sdk._cli._body_limit import resolve_body_limit
from nextlabs_sdk._logging import set_effective_body_limit

_HANDLER_NAME = "nextlabs-cli-verbose"
_LOGGER_NAME = "nextlabs_sdk"
_BODY_LIMIT_ENV = "NEXTLABS_LOG_BODY_LIMIT"


def configure_cli_logging(verbose: int) -> None:
    """Attach a stderr handler to the SDK logger when verbose >= 2.

    Also resolves the effective body limit for the verbose HTTP trace
    from the ``verbose`` level and the ``NEXTLABS_LOG_BODY_LIMIT``
    environment variable, and publishes it to the SDK logging module.

    Idempotent: subsequent calls neither duplicate the handler nor
    lower the log level.
    """
    if verbose < 2:
        return
    set_effective_body_limit(
        resolve_body_limit(verbose, os.environ.get(_BODY_LIMIT_ENV))
    )
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
