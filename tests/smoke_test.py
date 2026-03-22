from __future__ import annotations

import importlib.metadata
import os
import shutil
import subprocess
import sys


def main() -> int:
    version = importlib.metadata.version("symdex")
    expected_version = os.environ.get("SYMDEX_EXPECTED_VERSION")
    if expected_version and version != expected_version:
        raise SystemExit(
            f"Installed symdex version {version} does not match expected {expected_version}"
        )

    cli_path = shutil.which("symdex")
    if not cli_path:
        raise SystemExit("symdex console script is not on PATH")

    completed = subprocess.run(
        [cli_path, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"symdex --help failed with exit code {completed.returncode}:\n{completed.stderr}"
        )

    if "SymDex" not in completed.stdout:
        raise SystemExit("symdex --help output does not look like the SymDex CLI")

    print(f"Smoke test passed for symdex {version} via {cli_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
