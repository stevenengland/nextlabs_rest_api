"""Export-verification tests for the ``nextlabs_sdk.pdp`` facade."""

import importlib

import pytest

from nextlabs_sdk.pdp import __all__ as pdp_all


def _pdp_module() -> object:
    return importlib.import_module("nextlabs_sdk.pdp")


class TestPdpAllExports:
    """``__all__`` lists every public symbol and each is importable."""

    @pytest.mark.parametrize("symbol", pdp_all)
    def test_all_symbol_importable(self, symbol: str) -> None:
        mod = _pdp_module()
        obj = getattr(mod, symbol, None)
        assert obj is not None, (
            f"__all__ lists '{symbol}' but it is not importable "
            f"from nextlabs_sdk.pdp"
        )
