from __future__ import annotations

import argparse
import pathlib
import re
import tomllib


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED_PROJECT_FIELDS = (
    "name",
    "version",
    "description",
    "readme",
    "requires-python",
)


def load_project(pyproject_path: pathlib.Path) -> dict[str, object]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise SystemExit(f"{pyproject_path} is missing a [project] table")
    return project


def validate_project(project: dict[str, object], tag: str | None = None) -> tuple[str, str]:
    missing = [field for field in REQUIRED_PROJECT_FIELDS if not project.get(field)]
    if missing:
        raise SystemExit(f"Missing required project metadata: {', '.join(missing)}")

    version = str(project["version"])
    if not SEMVER_RE.fullmatch(version):
        raise SystemExit(
            f"Version must use strict X.Y.Z semantics for releases, got: {version}"
        )

    expected_tag = f"v{version}"
    if tag and tag != expected_tag:
        raise SystemExit(
            f"Git tag {tag!r} does not match pyproject version {version!r}; expected {expected_tag!r}"
        )

    return version, expected_tag


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release metadata in pyproject.toml.")
    parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    parser.add_argument("--tag", help="Optional git tag to validate against the version")
    parser.add_argument(
        "--github-output",
        help="Optional path to GITHUB_OUTPUT for writing version and tag outputs",
    )
    args = parser.parse_args()

    pyproject_path = pathlib.Path(args.pyproject)
    project = load_project(pyproject_path)
    version, tag = validate_project(project, tag=args.tag)

    if args.github_output:
      output_path = pathlib.Path(args.github_output)
      with output_path.open("a", encoding="utf-8") as fh:
          fh.write(f"version={version}\n")
          fh.write(f"tag={tag}\n")

    print(
        f"Validated package metadata: name={project['name']}, version={version}, release_tag={tag}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
