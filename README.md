# nextlabs-sdk

A typed Python SDK wrapping the NextLabs CloudAz Console API and PDP REST API

## Installation

```bash
pip install nextlabs-sdk
```

## Quick Start

```python
from nextlabs_sdk import CloudAzClient

client = CloudAzClient(
    base_url="https://cloudaz.example.com",
    username="admin",
    password="secret",
    client_id="ControlCenterOIDCClient",
)

tags = client.tags.list("COMPONENT_TAG")
```

## Development

See [docs/development.md](docs/development.md) for the full development guide.

## License

MIT — see [LICENSE](LICENSE) for details.
