from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap


ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATE_METADATA = ROOT / "scripts" / "release" / "validate_metadata.py"
VALIDATE_DIST = ROOT / "scripts" / "release" / "validate_dist.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_validate_metadata_accepts_current_pyproject():
    result = run_script(str(VALIDATE_METADATA), "--pyproject", str(ROOT / "pyproject.toml"))
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Validated package metadata" in result.stdout


def test_validate_metadata_rejects_mismatched_tag(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [project]
            name = "symdex"
            version = "1.2.3"
            description = "desc"
            readme = "README.md"
            requires-python = ">=3.11"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_script(
        str(VALIDATE_METADATA),
        "--pyproject",
        str(pyproject),
        "--tag",
        "v1.2.4",
    )
    assert result.returncode != 0
    assert "does not match pyproject version" in (result.stderr or result.stdout)


def test_validate_dist_accepts_one_matching_wheel_and_sdist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "symdex-0.1.9-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "symdex-0.1.9.tar.gz").write_text("", encoding="utf-8")

    result = run_script(
        str(VALIDATE_DIST),
        "--dist",
        str(dist),
        "--package",
        "symdex",
        "--version",
        "0.1.9",
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Validated distributions" in result.stdout


def test_validate_dist_rejects_extra_artifacts(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "symdex-0.1.9-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "symdex-0.1.9.tar.gz").write_text("", encoding="utf-8")
    (dist / "symdex-0.1.8-py3-none-any.whl").write_text("", encoding="utf-8")

    result = run_script(
        str(VALIDATE_DIST),
        "--dist",
        str(dist),
        "--package",
        "symdex",
        "--version",
        "0.1.9",
    )
    assert result.returncode != 0
    assert "Expected exactly one wheel and one sdist" in (result.stderr or result.stdout)
