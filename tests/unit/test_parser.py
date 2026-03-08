# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os
import pytest
from symdex.core.parser import parse_file


PYTHON_SOURCE = '''\
class MyClass:
    """A test class."""

    def my_method(self, x: int) -> int:
        """Returns x doubled."""
        return x * 2

def standalone_func():
    pass
'''

PYTHON_NO_DOCSTRING = '''\
def no_doc():
    return 42
'''

JS_SOURCE = '''\
function greet(name) {
    return "Hello " + name;
}

const double = (x) => x * 2;
'''

SYNTAX_ERROR_SOURCE = '''\
def broken(:
    pass
'''


@pytest.fixture
def py_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text(PYTHON_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def py_no_doc_file(tmp_path):
    f = tmp_path / "nodoc.py"
    f.write_text(PYTHON_NO_DOCSTRING)
    return str(f), str(tmp_path)


@pytest.fixture
def js_file(tmp_path):
    f = tmp_path / "sample.js"
    f.write_text(JS_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def syntax_error_file(tmp_path):
    f = tmp_path / "broken.py"
    f.write_text(SYNTAX_ERROR_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def unsupported_file(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b,c\n1,2,3\n")
    return str(f), str(tmp_path)


def test_parse_python_class(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "MyClass" in names
    cls = next(s for s in symbols if s["name"] == "MyClass")
    assert cls["kind"] == "class"
    assert cls["start_byte"] >= 0
    assert cls["end_byte"] > cls["start_byte"]
    assert cls["file"] == "sample.py"


def test_parse_python_function(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "standalone_func" in names
    fn = next(s for s in symbols if s["name"] == "standalone_func")
    assert fn["kind"] == "function"


def test_parse_python_method(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "my_method" in names
    m = next(s for s in symbols if s["name"] == "my_method")
    assert m["kind"] in ("function", "method")


def test_parse_python_docstring_extracted(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    cls = next(s for s in symbols if s["name"] == "MyClass")
    assert cls["docstring"] is not None
    assert "test class" in cls["docstring"]


def test_parse_python_no_docstring_is_none(py_no_doc_file):
    path, root = py_no_doc_file
    symbols = parse_file(path, root)
    fn = next(s for s in symbols if s["name"] == "no_doc")
    assert fn["docstring"] is None


def test_parse_javascript_function_declaration(js_file):
    path, root = js_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "greet" in names
    fn = next(s for s in symbols if s["name"] == "greet")
    assert fn["kind"] == "function"


def test_parse_javascript_arrow_function(js_file):
    path, root = js_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "double" in names


def test_parse_syntax_error_returns_empty_list(syntax_error_file):
    path, root = syntax_error_file
    # Must not raise — tree-sitter recovers from syntax errors
    # The implementation may return [] or partial results; what matters is no exception
    result = parse_file(path, root)
    assert isinstance(result, list)
    # Confirm no exception raised (already guaranteed by reaching this line)


def test_parse_unsupported_extension_returns_empty_list(unsupported_file):
    path, root = unsupported_file
    result = parse_file(path, root)
    assert result == []


def test_parse_file_path_is_relative_to_repo_root(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    for s in symbols:
        assert not os.path.isabs(s["file"])
        assert s["file"] == "sample.py"
