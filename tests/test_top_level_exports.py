"""Verify top-level ``nextlabs_sdk`` re-exports match ``__all__``."""

import nextlabs_sdk


class TestTopLevelExports:
    """Every symbol listed in ``__all__`` must be importable from the package."""

    def test_all_symbols_are_accessible(self) -> None:
        for name in nextlabs_sdk.__all__:
            attr = getattr(nextlabs_sdk, name, None)
            assert attr is not None, f"{name!r} listed in __all__ but not importable"

    def test_backward_compat_cloudaz_client_import(self) -> None:
        assert hasattr(nextlabs_sdk, "CloudAzClient")
        assert nextlabs_sdk.CloudAzClient is not None
