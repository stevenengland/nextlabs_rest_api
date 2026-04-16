from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SystemConfig(BaseModel):
    """Reporter system configuration as key-value pairs."""

    model_config = ConfigDict(frozen=True)

    settings: dict[str, str]

    @classmethod
    def from_response(cls, response_data: dict[str, str]) -> SystemConfig:
        """Create a SystemConfig from the raw API response."""
        return cls(settings=response_data)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Retrieve a configuration value by key."""
        return self.settings.get(key, default)
