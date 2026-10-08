from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

from mockito import when
import pytest

from tool_modules import load_tool_module

lock = load_tool_module("lock")

COMPILER_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "/usr/lib/piptools/resolver.py", line 677, in _do_resolve\n'
    "    resolver.resolve(\n"
    "pip._internal.exceptions.DistributionNotFound: ResolutionImpossible\n"
)

COMPILER_CRASH = (
    "Traceback (most recent call last):\n"
    '  File "/usr/lib/piptools/repositories/pypi.py", line 42, in find_best_match\n'
    "    return candidate.name\n"
    "AttributeError: 'NoneType' object has no attribute 'name'\n"
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


def test_compiler_crash_keeps_its_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _allow_any_python_minor()
    when(lock.subprocess).run(...).thenReturn(
        CompletedProcess(args=[], returncode=1, stderr=COMPILER_CRASH)
    )

    exit_code = lock.main(["--check"])

    assert exit_code != 0
    stderr = capsys.readouterr().err
    assert "Traceback" in stderr
    assert "piptools/repositories/pypi.py" in stderr
    assert "AttributeError" in stderr
    assert lock.COMPILER_FAILURE_HINT not in stderr


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


def test_stale_lock_reports_the_compiled_diff(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _allow_any_python_minor()
    committed = lock.CONSTRAINTS.read_text()
    requirement = next(line for line in committed.splitlines() if "==" in line)

    def write_compiled(output_file: Path) -> None:
        output_file.write_text(committed.replace(requirement, "example==2.0", 1))

    when(lock)._compile(...).thenAnswer(write_compiled)

    exit_code = lock.main(["--check"])

    stderr = capsys.readouterr().err
    assert exit_code == 1
    assert f"-{requirement}" in stderr
    assert "+example==2.0" in stderr
    assert "python tools/lock.py" in stderr


def test_lock_check_preserves_the_recipe_across_compiler_environments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _allow_any_python_minor()
    committed = lock.CONSTRAINTS.read_text()
    recipe = next(
        line.removeprefix("#    ")
        for line in committed.splitlines()
        if line.startswith("#    pip-compile")
    )
    environment_recipe = recipe.replace("--all-extras", "--all-extras --no-index")

    def run_compiler(
        arguments: list[str],
        **kwargs: object,
    ) -> CompletedProcess[str]:
        output_file = Path(
            next(
                argument.removeprefix("--output-file=")
                for argument in arguments
                if argument.startswith("--output-file=")
            )
        )
        environment = kwargs.get("env", {})
        assert isinstance(environment, dict)
        command = environment.get("CUSTOM_COMPILE_COMMAND", environment_recipe)
        assert isinstance(command, str)
        output_file.write_text(committed.replace(recipe, command))
        return CompletedProcess(args=arguments, returncode=0, stderr="")

    when(lock.subprocess).run(...).thenAnswer(run_compiler)

    exit_code = lock.main(["--check"])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
