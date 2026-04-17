from __future__ import annotations

import argparse
import pathlib
import subprocess


ALLOWED_MARKDOWN = {
    "README.md",
    "skills/symdex-code-search/SKILL.md",
}


def tracked_markdown_files(repo_root: pathlib.Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", "*.md"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Unable to list tracked Markdown files")

    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def disallowed_markdown_files(repo_root: pathlib.Path) -> list[str]:
    return [
        path
        for path in tracked_markdown_files(repo_root)
        if path not in ALLOWED_MARKDOWN
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if tracked private Markdown files are present."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root to check")
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    disallowed = disallowed_markdown_files(repo_root)
    if disallowed:
        formatted = "\n".join(f"  - {path}" for path in disallowed)
        raise SystemExit(
            "Tracked Markdown files are not allowed outside the public allowlist:\n"
            f"{formatted}"
        )

    print("No disallowed Markdown files tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
