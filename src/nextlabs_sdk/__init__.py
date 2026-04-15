"""nextlabs-sdk."""

from importlib.metadata import PackageNotFoundError, version

from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth as CloudAzAuth
from nextlabs_sdk._auth._pdp_auth import PdpAuth as PdpAuth
from nextlabs_sdk._config import HttpConfig as HttpConfig
from nextlabs_sdk._config import RetryConfig as RetryConfig
from nextlabs_sdk._http_transport import (
    create_async_http_client as create_async_http_client,
)
from nextlabs_sdk._http_transport import (
    create_http_client as create_http_client,
)
from nextlabs_sdk._pagination import AsyncPaginator as AsyncPaginator
from nextlabs_sdk._pagination import PageResult as PageResult
from nextlabs_sdk._pagination import SyncPaginator as SyncPaginator

try:
    __version__ = version("nextlabs-sdk")
except PackageNotFoundError:
    __version__ = "0.0.0"
