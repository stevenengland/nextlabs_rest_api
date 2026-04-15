from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0


@dataclass(frozen=True)
class HttpConfig:
    timeout: float = 30.0
    verify_ssl: bool = True
    retry: RetryConfig = field(default_factory=RetryConfig)
