"""Public PDP REST API surface (client, request/response models, enums).

Re-exports the curated PDP API from the internal ``_pdp`` package.
"""

__all__: list[str] = [
    # Clients
    "AsyncPdpClient",
    "PdpClient",
    # Enums/Types
    "ContentType",
    "Decision",
    "ResourceDimension",
    # Models
    "Action",
    "ActionPermission",
    "Application",
    "Environment",
    "EvalRequest",
    "EvalResponse",
    "EvalResult",
    "Obligation",
    "ObligationAttribute",
    "PermissionsRequest",
    "PermissionsResponse",
    "PolicyRef",
    "Resource",
    "Status",
    "Subject",
    # Payload
    "LoadedPayload",
    "PayloadFormat",
    "load_eval_payload",
    "load_permissions_payload",
]

from nextlabs_sdk._pdp import Action as Action
from nextlabs_sdk._pdp import ActionPermission as ActionPermission
from nextlabs_sdk._pdp import Application as Application
from nextlabs_sdk._pdp import AsyncPdpClient as AsyncPdpClient
from nextlabs_sdk._pdp import ContentType as ContentType
from nextlabs_sdk._pdp import Decision as Decision
from nextlabs_sdk._pdp import Environment as Environment
from nextlabs_sdk._pdp import EvalRequest as EvalRequest
from nextlabs_sdk._pdp import EvalResponse as EvalResponse
from nextlabs_sdk._pdp import EvalResult as EvalResult
from nextlabs_sdk._pdp import LoadedPayload as LoadedPayload
from nextlabs_sdk._pdp import Obligation as Obligation
from nextlabs_sdk._pdp import ObligationAttribute as ObligationAttribute
from nextlabs_sdk._pdp import PayloadFormat as PayloadFormat
from nextlabs_sdk._pdp import PdpClient as PdpClient
from nextlabs_sdk._pdp import PermissionsRequest as PermissionsRequest
from nextlabs_sdk._pdp import PermissionsResponse as PermissionsResponse
from nextlabs_sdk._pdp import PolicyRef as PolicyRef
from nextlabs_sdk._pdp import Resource as Resource
from nextlabs_sdk._pdp import ResourceDimension as ResourceDimension
from nextlabs_sdk._pdp import Status as Status
from nextlabs_sdk._pdp import Subject as Subject
from nextlabs_sdk._pdp import load_eval_payload as load_eval_payload
from nextlabs_sdk._pdp import load_permissions_payload as load_permissions_payload
