import os
import subprocess  # noqa: S404
import sys


def call_black(directory) -> None:
    print("** BLACK **")
    cmd_path = "black"
    result_subprocess = None
    try:
        result_subprocess = subprocess.run(  # noqa: S607, S603
            [cmd_path, directory],
        )

    except FileNotFoundError:
        print("Black formatter not found. Please make sure it is installed.")

    if result_subprocess is not None and result_subprocess.returncode != 0:
        raise RuntimeError(
            f"Black formatter failed with return code {result_subprocess.returncode}",
        )

    print("Calling black completed successfully.")


def call_flake8(directory) -> None:
    print("** FLAKE8 **")
    cmd_path = "flake8"
    result_subprocess = None
    try:
        result_subprocess = subprocess.run([cmd_path, directory])  # noqa: S607, S603
    except FileNotFoundError:
        print("flake8 not found. Please make sure it is installed.")

    if result_subprocess is not None and result_subprocess.returncode != 0:
        raise RuntimeError(
            f"flake8 failed with return code {result_subprocess.returncode}",
        )

    print("Calling flake8 completed successfully.")


def call_pyright(directory: str) -> None:
    print("** PYRIGHT (Pylance) **")
    cmd_path = "pyright"
    result_subprocess = None
    try:
        result_subprocess = subprocess.run(  # noqa: S607, S603
            [cmd_path, "--warnings", directory],
        )

    except FileNotFoundError:
        print("Pyright not found. Please make sure it is installed.")

    if result_subprocess is not None and result_subprocess.returncode != 0:
        raise RuntimeError(
            f"Pyright failed with return code {result_subprocess.returncode}",
        )

    print("Calling Pyright completed successfully.")


def call_mypy(directory: str) -> None:
    print("** MYPY **")
    cmd_path = "mypy"
    result_subprocess = None
    env = {**os.environ, "MYPYPATH": "src"}
    try:
        result_subprocess = subprocess.run(  # noqa: S607, S603
            [
                cmd_path,
                directory,
                "--cache-dir=/dev/null",
            ],  # null on windows to disable cache
            check=True,
            env=env,
        )

    except FileNotFoundError:
        print("MyPy formatter not found. Please make sure it is installed.")

    if result_subprocess is not None and result_subprocess.returncode != 0:
        raise RuntimeError(
            f"MyPy failed with return code {result_subprocess.returncode}",
        )

    print("Calling MyPy completed successfully.")


if len(sys.argv) > 1:  # noqa: C901
    argument = sys.argv[1]
    if argument == "black":
        call_black(".")
    elif argument == "flake8":
        call_flake8(".")
    elif argument == "mypy":
        call_mypy(".")
    elif argument == "pyright":
        call_pyright(".")
    else:
        print(
            "Invalid argument. Please specify 'black', 'flake8', 'mypy', or 'pyright'."
        )
else:
    call_black(".")
    call_flake8(".")
    call_mypy(".")
    call_pyright(".")
