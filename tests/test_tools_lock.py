from __future__ import annotations

from importlib import util as importlib_util
from pathlib import Path
from subprocess import CompletedProcess
from types import ModuleType

from mockito import when
import pytest


def _load_lock() -> ModuleType:
    repo_root = Path(__file__).resolve().parent.parent
    module_path = repo_root / "tools" / "lock.py"
    spec = importlib_util.spec_from_file_location("_tools_lock", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lock = _load_lock()

COMPILER_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "/usr/lib/piptools/resolver.py", line 677, in _do_resolve\n'
    "    resolver.resolve(\n"
    "pip._internal.exceptions.DistributionNotFound: ResolutionImpossible\n"
)


def _allow_any_python_minor() -> None:
    when(lock)._guard_python_minor().thenReturn(None)


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param([], id="regenerate"),
        pytest.param(["--check"], id="check"),
    ],
)
def test_compiler_failure_reports_repair_instead_of_traceback(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _allow_any_python_minor()
    when(lock.subprocess).run(...).thenReturn(
        CompletedProcess(args=[], returncode=2, stderr=COMPILER_TRACEBACK)
    )

    exit_code = lock.main(argv)

    assert exit_code != 0
    stderr = capsys.readouterr().err
    assert "ResolutionImpossible" in stderr
    assert "requirements/constraints.txt" in stderr
    assert "python tools/lock.py" in stderr
    assert "Traceback" not in stderr
    assert 'File "' not in stderr


def test_compiler_output_survives_a_successful_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _allow_any_python_minor()
    when(lock.subprocess).run(...).thenReturn(
        CompletedProcess(args=[], returncode=0, stderr="dropping extra 'cli'\n")
    )

    assert lock.main(["--check"]) == 0
    assert "dropping extra 'cli'" in capsys.readouterr().err


def test_unexpected_compiler_error_stays_visible() -> None:
    _allow_any_python_minor()
    when(lock.subprocess).run(...).thenRaise(FileNotFoundError("no interpreter"))

    with pytest.raises(FileNotFoundError):
        lock.main(["--check"])


def test_valid_lock_passes_the_check(capsys: pytest.CaptureFixture[str]) -> None:
    _allow_any_python_minor()
    when(lock)._compile(...).thenReturn(None)

    exit_code = lock.main(["--check"])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
