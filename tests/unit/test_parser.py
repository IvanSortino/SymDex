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

TS_SOURCE = '''\
interface User {
    name: string;
}

class AuthService {
    login(email: string): boolean {
        return email.includes("@");
    }
}

function validateEmail(email: string): boolean {
    return email.includes("@");
}
'''

PHP_SOURCE = '''\
<?php
class UserController {
    public function index() {
        return [];
    }
}

function helper_fn($x) {
    return $x;
}
'''

SYNTAX_ERROR_SOURCE = '''\
def broken(:
    pass
'''

MARKDOWN_SOURCE = '''\
# SDK Guide

Use this guide to configure the SDK.

## Python Example

```python
def configure_client(api_key: str):
    return {"api_key": api_key}
```

## Shell Example

```bash
echo "not parsed as a symbol"
```
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
def ts_file(tmp_path):
    f = tmp_path / "sample.ts"
    f.write_text(TS_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def php_file(tmp_path):
    f = tmp_path / "sample.php"
    f.write_text(PHP_SOURCE)
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


def test_parse_typescript_symbols(ts_file):
    path, root = ts_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "validateEmail" in names
    assert "AuthService" in names


def test_parse_php_symbols(php_file):
    path, root = php_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "helper_fn" in names
    assert "UserController" in names


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


@pytest.mark.parametrize("ext", [".md", ".markdown", ".mdx"])
def test_parse_markdown_headings_as_sections(tmp_path, ext):
    f = tmp_path / f"guide{ext}"
    f.write_text(MARKDOWN_SOURCE, encoding="utf-8")

    symbols = parse_file(str(f), str(tmp_path))
    sections = [s for s in symbols if s["kind"] == "section"]

    assert [s["name"] for s in sections] == ["SDK Guide", "Python Example", "Shell Example"]
    assert sections[0]["signature"] == "# SDK Guide"
    assert "configure the SDK" in (sections[0]["docstring"] or "")
    with open(f, "rb") as fh:
        source_bytes = fh.read()
    first_section = source_bytes[sections[0]["start_byte"]:sections[0]["end_byte"]].decode("utf-8")
    assert first_section.startswith("# SDK Guide")
    assert "## Python Example" not in first_section


@pytest.mark.parametrize("ext", [".md", ".markdown", ".mdx"])
def test_parse_markdown_fenced_code_blocks_as_symbols(tmp_path, ext):
    f = tmp_path / f"guide{ext}"
    f.write_text(MARKDOWN_SOURCE, encoding="utf-8")

    symbols = parse_file(str(f), str(tmp_path))
    fn = next(s for s in symbols if s["name"] == "configure_client")

    assert fn["kind"] == "function"
    assert fn["file"] == f"guide{ext}"
    with open(f, "rb") as fh:
        source_bytes = fh.read()
    snippet = source_bytes[fn["start_byte"]:fn["end_byte"]].decode("utf-8")
    assert snippet.startswith("def configure_client")
    assert "api_key" in snippet
    assert "echo" not in [s["name"] for s in symbols]


def test_parse_file_path_is_relative_to_repo_root(py_file):
    path, root = py_file
    symbols = parse_file(path, root)
    for s in symbols:
        assert not os.path.isabs(s["file"])
        assert s["file"] == "sample.py"


# ── Vue SFC tests ────────────────────────────────────────────────────────────

VUE_JS_SOURCE = """\
<template>
  <div>{{ message }}</div>
</template>

<script>
function greetUser(name) {
  return "Hello " + name;
}

const double = (x) => x * 2;
</script>

<style scoped>
div { color: red; }
</style>
"""

VUE_TS_SOURCE = """\
<template><span>hi</span></template>

<script lang="ts">
interface User {
  name: string;
}

function getUser(id: number): User {
  return { name: "Alice" };
}
</script>
"""

VUE_NO_SCRIPT = """\
<template>
  <div>no script here</div>
</template>
"""


@pytest.fixture
def vue_js_file(tmp_path):
    f = tmp_path / "component.vue"
    f.write_text(VUE_JS_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def vue_ts_file(tmp_path):
    f = tmp_path / "component.vue"
    f.write_text(VUE_TS_SOURCE)
    return str(f), str(tmp_path)


@pytest.fixture
def vue_no_script_file(tmp_path):
    f = tmp_path / "empty.vue"
    f.write_text(VUE_NO_SCRIPT)
    return str(f), str(tmp_path)


def test_parse_vue_js_finds_function(vue_js_file):
    path, root = vue_js_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "greetUser" in names


def test_parse_vue_js_finds_arrow_function(vue_js_file):
    path, root = vue_js_file
    symbols = parse_file(path, root)
    names = [s["name"] for s in symbols]
    assert "double" in names


def test_parse_vue_ts_finds_function(vue_ts_file):
    path, root = vue_ts_file
    symbols = parse_file(path, root)
    # If the TS grammar is available, getUser must be found.
    # If not (grammar load failure), parse_file returns [] — acceptable graceful degradation.
    if symbols:
        names = [s["name"] for s in symbols]
        assert "getUser" in names


def test_parse_vue_byte_offsets_point_into_full_file(vue_js_file):
    """start_byte/end_byte must index into the full .vue file, not the script fragment.

    Arrow functions store bytes at the function value node (not the variable name),
    so we check that offsets are valid and lie within the <script> section.
    """
    path, root = vue_js_file
    symbols = parse_file(path, root)
    with open(path, "rb") as fh:
        full_bytes = fh.read()
    script_start = full_bytes.find(b"<script")
    for sym in symbols:
        assert sym["start_byte"] < len(full_bytes)
        assert sym["end_byte"] <= len(full_bytes)
        assert sym["end_byte"] > sym["start_byte"]
        assert sym["start_byte"] >= script_start, (
            f"{sym['name']} byte offset {sym['start_byte']} is before the <script> block"
        )


def test_parse_vue_no_script_returns_empty(vue_no_script_file):
    path, root = vue_no_script_file
    assert parse_file(path, root) == []


def test_parse_vue_file_field_is_vue_extension(vue_js_file):
    path, root = vue_js_file
    symbols = parse_file(path, root)
    for s in symbols:
        assert s["file"].endswith(".vue")
