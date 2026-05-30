"""Export-verification tests for the ``nextlabs_sdk.cloudaz`` facade."""

import importlib

import pytest

from nextlabs_sdk.cloudaz import __all__ as cloudaz_all


def _cloudaz_module() -> object:
    return importlib.import_module("nextlabs_sdk.cloudaz")


class TestCloudazModelImports:
    """AC1: Core model classes are importable from the public facade."""

    @pytest.mark.parametrize(
        "symbol",
        ["Policy", "PolicyLite", "Component", "ComponentLite"],
    )
    def test_model_importable(self, symbol: str) -> None:
        mod = _cloudaz_module()
        obj = getattr(mod, symbol, None)
        assert obj is not None, f"{symbol} not found in nextlabs_sdk.cloudaz"


class TestCloudazServiceImports:
    """AC2: Service classes (sync, async, search) are importable."""

    @pytest.mark.parametrize(
        "symbol",
        [
            "PolicyService",
            "AsyncPolicyService",
            "PolicySearchService",
            "AsyncPolicySearchService",
            "ComponentService",
            "AsyncComponentService",
            "ComponentSearchService",
            "AsyncComponentSearchService",
            "TagService",
            "AsyncTagService",
        ],
    )
    def test_service_importable(self, symbol: str) -> None:
        mod = _cloudaz_module()
        obj = getattr(mod, symbol, None)
        assert obj is not None, f"{symbol} not found in nextlabs_sdk.cloudaz"


class TestCloudazAllExports:
    """AC4: ``__all__`` lists every public symbol and each is importable."""

    @pytest.mark.parametrize("symbol", cloudaz_all)
    def test_all_symbol_importable(self, symbol: str) -> None:
        mod = _cloudaz_module()
        obj = getattr(mod, symbol, None)
        assert obj is not None, (
            f"__all__ lists '{symbol}' but it is not importable "
            f"from nextlabs_sdk.cloudaz"
        )
