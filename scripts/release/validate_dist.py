from __future__ import annotations

import argparse
import pathlib
import re


def validate_dist(dist_dir: pathlib.Path, package: str, version: str) -> tuple[pathlib.Path, pathlib.Path]:
    if not dist_dir.is_dir():
        raise SystemExit(f"Distribution directory does not exist: {dist_dir}")

    files = sorted(path for path in dist_dir.iterdir() if path.is_file())
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]

    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(
            "Expected exactly one wheel and one sdist in "
            f"{dist_dir}, found wheels={len(wheels)} sdists={len(sdists)}"
        )

    wheel = wheels[0]
    sdist = sdists[0]

    wheel_re = re.compile(rf"^{re.escape(package)}-{re.escape(version)}-.*\.whl$")
    sdist_re = re.compile(rf"^{re.escape(package)}-{re.escape(version)}\.tar\.gz$")

    if not wheel_re.fullmatch(wheel.name):
        raise SystemExit(
            f"Wheel filename {wheel.name!r} does not match expected package/version {package} {version}"
        )

    if not sdist_re.fullmatch(sdist.name):
        raise SystemExit(
            f"Sdist filename {sdist.name!r} does not match expected package/version {package} {version}"
        )

    extra = [
        path.name
        for path in files
        if path not in {wheel, sdist}
    ]
    if extra:
        raise SystemExit(f"Unexpected extra files in {dist_dir}: {', '.join(extra)}")

    return wheel, sdist


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate built distribution files.")
    parser.add_argument("--dist", required=True, help="Path to dist directory")
    parser.add_argument("--package", required=True, help="Expected package name")
    parser.add_argument("--version", required=True, help="Expected package version")
    args = parser.parse_args()

    dist_dir = pathlib.Path(args.dist)
    wheel, sdist = validate_dist(dist_dir, args.package, args.version)
    print(f"Validated distributions: wheel={wheel.name} sdist={sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
