"""Import helper for the standalone scripts under ``tools/``.

Those scripts are not part of the installed package, so they cannot be
imported by name. Tests load them straight from their path through this
single helper instead of each repeating the ``importlib`` plumbing.
"""

from __future__ import annotations

from importlib import util as importlib_util
from pathlib import Path
from types import ModuleType

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"


def load_tool_module(script_name: str) -> ModuleType:
    """Load ``tools/<script_name>.py`` as a module of its own.

    Args:
        script_name: The script's file stem, e.g. ``"lock"``.

    Returns:
        The executed module.
    """
    module_path = TOOLS_DIR / f"{script_name}.py"
    spec = importlib_util.spec_from_file_location(f"_tools_{script_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load a module spec for {module_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
