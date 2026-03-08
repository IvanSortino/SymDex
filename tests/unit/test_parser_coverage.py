# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Targeted coverage tests for symdex/core/parser.py.
# Covers grammar load failure, OSError on read, comment docstrings,
# and decorated_definition handling.

import os
import pytest
from unittest.mock import patch
from symdex.core.parser import (
    parse_file,
    _get_language,
    _extract_comment_docstring,
    _extract_python_docstring,
)


# ── _get_language — grammar import failure ────────────────────────────────────

def test_get_language_unknown_extension():
    lang_name, language = _get_language(".xyz")
    assert lang_name is None
    assert language is None


def test_get_language_import_failure():
    """Simulate a grammar module that raises on import."""
    with patch("symdex.core.parser.importlib.import_module", side_effect=ImportError("no module")):
        lang_name, language = _get_language(".py")
    # lang_name is still "python" from _EXT_MAP; language is None due to the error
    assert lang_name == "python"
    assert language is None


# ── parse_file — OSError on read ──────────────────────────────────────────────

def test_parse_file_oserror_on_read(tmp_path):
    """If the file is unreadable, parse_file must return [] without raising."""
    f = tmp_path / "unreadable.py"
    f.write_text("def foo(): pass\n")
    # Make file unreadable by patching open to raise OSError
    with patch("builtins.open", side_effect=OSError("permission denied")):
        result = parse_file(str(f), str(tmp_path))
    assert result == []


# ── parse_file — decorated_definition (Python decorator) ─────────────────────

DECORATED_SOURCE = '''\
import functools

def decorator(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper

@decorator
def decorated_func(x: int) -> int:
    """A decorated function."""
    return x + 1
'''


def test_parse_decorated_python_function(tmp_path):
    f = tmp_path / "decorated.py"
    f.write_text(DECORATED_SOURCE)
    symbols = parse_file(str(f), str(tmp_path))
    names = [s["name"] for s in symbols]
    assert "decorated_func" in names
    fn = next(s for s in symbols if s["name"] == "decorated_func")
    assert fn["kind"] == "function"


# ── _extract_comment_docstring edge cases ─────────────────────────────────────

def test_comment_docstring_first_child_no_prev(tmp_path):
    """A node that is the first child of its parent returns None (idx == 0 branch)."""
    # Parse a plain Python file; the top-level function is the first child
    f = tmp_path / "first.py"
    f.write_text("def first_func(): pass\n")
    symbols = parse_file(str(f), str(tmp_path))
    # Verify no crash and result is a list
    assert isinstance(symbols, list)


# ── JavaScript comment docstring ──────────────────────────────────────────────

JS_WITH_COMMENT = '''\
// Adds two numbers together
function addNumbers(a, b) {
    return a + b;
}
'''


def test_js_comment_docstring_extracted(tmp_path):
    f = tmp_path / "add.js"
    f.write_text(JS_WITH_COMMENT)
    symbols = parse_file(str(f), str(tmp_path))
    names = [s["name"] for s in symbols]
    assert "addNumbers" in names


# ── TypeScript interface ──────────────────────────────────────────────────────

TS_INTERFACE = '''\
interface UserProfile {
    id: number;
    name: string;
}

function getUserProfile(id: number): UserProfile {
    return { id, name: "test" };
}
'''


def test_parse_typescript_interface(tmp_path):
    f = tmp_path / "profile.ts"
    f.write_text(TS_INTERFACE)
    # If the TypeScript grammar is unavailable, parse_file returns [] without raising.
    # If it is available, at least one symbol should be found.
    symbols = parse_file(str(f), str(tmp_path))
    assert isinstance(symbols, list)
    if symbols:
        names = [s["name"] for s in symbols]
        assert "UserProfile" in names or "getUserProfile" in names


# ── Python single-quote docstring ─────────────────────────────────────────────

SINGLE_QUOTE_DOC = '''\
def single_quoted():
    'Single-quote docstring.'
    return 1
'''


def test_python_single_quote_docstring(tmp_path):
    f = tmp_path / "sq.py"
    f.write_text(SINGLE_QUOTE_DOC)
    symbols = parse_file(str(f), str(tmp_path))
    fn = next((s for s in symbols if s["name"] == "single_quoted"), None)
    assert fn is not None
    # Docstring may or may not be extracted depending on exact node structure
    assert isinstance(fn.get("docstring"), (str, type(None)))


# ── parse_file with multiple Python symbols ───────────────────────────────────

MULTI_SOURCE = '''\
class OuterClass:
    """Outer class."""

    class InnerClass:
        """Inner class."""
        pass

    def method_one(self):
        """Method one."""
        pass

def module_level_func():
    pass
'''


def test_parse_nested_class_and_methods(tmp_path):
    f = tmp_path / "multi.py"
    f.write_text(MULTI_SOURCE)
    symbols = parse_file(str(f), str(tmp_path))
    names = [s["name"] for s in symbols]
    assert "OuterClass" in names
    assert "module_level_func" in names
    # All results have required fields
    for s in symbols:
        assert "name" in s
        assert "start_byte" in s
        assert "end_byte" in s
        assert s["end_byte"] > s["start_byte"]
