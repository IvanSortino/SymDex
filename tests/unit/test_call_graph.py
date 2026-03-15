# tests/unit/test_call_graph.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os
import sqlite3
import tempfile

import pytest

from symdex.core.storage import get_connection
from symdex.graph.call_graph import find_circular_deps


class TestFindCircularDepsNoEdges:
    """Test find_circular_deps with no edges at all."""

    def test_find_circular_deps_no_cycles_empty_graph(self, tmp_path):
        """Build a DB with symbols but no edges. Should return no cycles."""
        db_path = tmp_path / "test.db"
        conn = get_connection(str(db_path))

        try:
            # Insert 3 symbols with no edges between them
            for name in ["file_a.py", "file_b.py", "file_c.py"]:
                conn.execute(
                    "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("test_repo", name, name, "function", 0, 100),
                )
            conn.commit()

            result = find_circular_deps("test_repo", str(db_path))

            assert result["count"] == 0
            assert result["cycles"] == []
        finally:
            conn.close()


class TestFindCircularDepsAcyclic:
    """Test find_circular_deps with acyclic dependencies."""

    def test_find_circular_deps_no_cycles_acyclic_chain(self, tmp_path):
        """Build A->B->C acyclic chain. Should detect no cycles."""
        db_path = tmp_path / "test.db"
        conn = get_connection(str(db_path))

        try:
            # Insert 3 symbols: A, B, C
            symbols = [
                ("a.py", "func_a", "function"),
                ("b.py", "func_b", "function"),
                ("c.py", "func_c", "function"),
            ]
            sym_ids = {}
            for file, name, kind in symbols:
                cursor = conn.execute(
                    "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("test_repo", file, name, kind, 0, 100),
                )
                sym_ids[file] = cursor.lastrowid

            # Create edges: A->B, B->C (acyclic)
            conn.execute(
                "INSERT INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_ids["a.py"], "func_b", "b.py"),
            )
            conn.execute(
                "INSERT INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_ids["b.py"], "func_c", "c.py"),
            )
            conn.commit()

            result = find_circular_deps("test_repo", str(db_path))

            assert result["count"] == 0
            assert result["cycles"] == []
        finally:
            conn.close()


class TestFindCircularDeps3Cycle:
    """Test find_circular_deps with a 3-node cycle."""

    def test_find_circular_deps_detects_3_node_cycle(self, tmp_path):
        """Build a 3-node cycle: A->B->C->A. Should detect the cycle."""
        db_path = tmp_path / "test.db"
        conn = get_connection(str(db_path))

        try:
            # Insert 3 symbols: A, B, C
            symbols = [
                ("a.py", "func_a", "function"),
                ("b.py", "func_b", "function"),
                ("c.py", "func_c", "function"),
            ]
            sym_ids = {}
            for file, name, kind in symbols:
                cursor = conn.execute(
                    "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("test_repo", file, name, kind, 0, 100),
                )
                sym_ids[file] = cursor.lastrowid

            # Create cycle: A->B, B->C, C->A
            conn.execute(
                "INSERT INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_ids["a.py"], "func_b", "b.py"),
            )
            conn.execute(
                "INSERT INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_ids["b.py"], "func_c", "c.py"),
            )
            conn.execute(
                "INSERT INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_ids["c.py"], "func_a", "a.py"),
            )
            conn.commit()

            result = find_circular_deps("test_repo", str(db_path))

            # Should detect at least one cycle with count >= 1
            assert result["count"] >= 1
            assert len(result["cycles"]) >= 1

            # The cycle should contain all three files
            files_in_cycles = set()
            for cycle in result["cycles"]:
                files_in_cycles.update(cycle[:-1])  # Exclude the closing node

            assert "a.py" in files_in_cycles
            assert "b.py" in files_in_cycles
            assert "c.py" in files_in_cycles
        finally:
            conn.close()
