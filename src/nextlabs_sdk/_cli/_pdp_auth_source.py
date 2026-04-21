from __future__ import annotations

from enum import Enum


class PdpAuthSource(str, Enum):
    """Which OAuth token endpoint the PDP CLI commands should target.

    - ``CLOUDAZ``: authenticate at ``/cas/token`` on the CloudAz host
      (``--base-url``).
    - ``PDP``: authenticate at ``/dpc/oauth`` on the PDP host
      (``--pdp-url``).
    """

    CLOUDAZ = "cloudaz"
    PDP = "pdp"
