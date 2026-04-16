import subprocess  # noqa: S404
import sys


def main() -> None:
    """Build the Python package (sdist + wheel)."""
    print("** BUILD **")

    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "install", "build"],
        check=True,
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "build"],
        check=False,
    )

    if result.returncode != 0:
        print(f"Build failed with return code {result.returncode}")
        sys.exit(result.returncode)

    print("Build completed successfully.")


if __name__ == "__main__":
    main()
