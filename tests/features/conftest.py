# tests/features/conftest.py
import os
import pytest
from symdex.mcp.tools import index_folder_tool


@pytest.fixture
def context():
    """Shared mutable state dict passed between BDD steps."""
    return {}


@pytest.fixture
def tmp_indexed(tmp_path, monkeypatch):
    """
    Index a temporary directory; redirect all DBs to tmp_path.
    Monkeypatches 3 sites for isolation.
    """
    def _mock_db_path(repo_name: str) -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"{repo_name}.db")

    def _mock_registry_path() -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "registry.db")

    monkeypatch.setattr("symdex.core.indexer.get_db_path", _mock_db_path)
    monkeypatch.setattr("symdex.mcp.tools.get_db_path", _mock_db_path)
    monkeypatch.setattr("symdex.core.storage.get_db_path", _mock_db_path)
    try:
        monkeypatch.setattr("tests.features.steps.mcp_steps.get_db_path", _mock_db_path)
    except AttributeError:
        pass
    try:
        monkeypatch.setattr("symdex.core.storage.get_registry_path", _mock_registry_path)
    except AttributeError:
        pass  # get_registry_path added in Task 3
    try:
        monkeypatch.setattr("symdex.cli.get_db_path", _mock_db_path)
    except AttributeError:
        pass
    try:
        monkeypatch.setattr("symdex.cli.get_registry_path", _mock_registry_path)
    except AttributeError:
        pass

    (tmp_path / "parse_module.py").write_text(
        'def parse_file(path: str) -> list:\n'
        '    """Parse a source file and return symbols."""\n'
        '    return []\n\n'
        'def parse_dir(path: str) -> dict:\n'
        '    """Parse all files in a directory."""\n'
        '    return {}\n'
    )
    (tmp_path / "utils.py").write_text(
        'class Helper:\n'
        '    """Utility helper class."""\n'
        '    def run(self) -> None:\n'
        '        pass\n'
    )

    result = index_folder_tool(path=str(tmp_path), name="testbdd")
    return {
        "path": str(tmp_path),
        "repo": "testbdd",
        "index_result": result,
    }
