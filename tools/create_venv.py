import subprocess  # noqa: S404
import sys


def main() -> None:
    """Install project dependencies for CI environments."""
    commands = [
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            "requirements/dev.txt",
            "-c",
            "requirements/constraints.txt",
        ],
        [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
    ]

    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)  # noqa: S603
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            sys.exit(result.returncode)

    print("Dependency installation completed successfully.")


if __name__ == "__main__":
    main()
