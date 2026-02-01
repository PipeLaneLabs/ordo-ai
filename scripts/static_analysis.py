import subprocess
import sys


def run_command(command: list[str]) -> tuple[str, str, int]:
    """Runs a command and prints its output."""
    print(f"--- Running command: {' '.join(command)} ---")  # noqa: T201
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
        )
        if result.stdout:
            print(result.stdout)  # noqa: T201
        if result.stderr:
            print(result.stderr, file=sys.stderr)  # noqa: T201
        print(f"--- Exit code: {result.returncode} ---")  # noqa: T201
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        print(
            f"Error: Command '{command[0]}' not found. Make sure it is installed and in your PATH.",
            file=sys.stderr,
        )
        return "", f"Command not found: {command[0]}", 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)  # noqa: T201
        return "", str(e), 1


def main() -> None:
    """Runs all static analysis tools."""
    print("Starting static analysis...")  # noqa: T201

    commands = [
        ["poetry", "run", "black", "--check", "src", "tests"],
        ["poetry", "run", "ruff", "check", "src", "tests"],
        ["poetry", "run", "mypy", "src", "tests"],
        ["poetry", "run", "radon", "cc", "src", "tests", "-s", "-a"],
    ]

    for command in commands:
        run_command(command)

    print("Static analysis finished.")  # noqa: T201


if __name__ == "__main__":
    main()
