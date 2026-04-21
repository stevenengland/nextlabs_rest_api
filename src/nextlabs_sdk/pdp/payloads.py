"""Public API for loading PDP request payloads from YAML / JSON / raw XACML files.

Example::

    from pathlib import Path

    from nextlabs_sdk.pdp.payloads import load_eval_payload

    loaded = load_eval_payload(Path("request.json"))
    if loaded.kind == "structured":
        response = client.evaluate(loaded.request)
    else:
        response = client.evaluate_raw(loaded.body)
"""

from nextlabs_sdk._pdp._payload._format import (
    LoadedPayload as LoadedPayload,
)
from nextlabs_sdk._pdp._payload._format import (
    PayloadFormat as PayloadFormat,
)
from nextlabs_sdk._pdp._payload._loader import (
    load_eval_payload as load_eval_payload,
)
from nextlabs_sdk._pdp._payload._loader import (
    load_permissions_payload as load_permissions_payload,
)
