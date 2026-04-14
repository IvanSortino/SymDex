# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest

from symdex.core.parser import _get_language, parse_file


LANGUAGE_SAMPLES: dict[str, str] = {
    ".bash": "function alpha() { echo ok; }\n",
    ".py": "def alpha():\n    return 1\nclass PyClass:\n    pass\n",
    ".js": "function alpha() { return 1; }\nclass JsClass {}\n",
    ".cjs": "function alpha() { return 1; }\nclass CjsClass {}\n",
    ".jsx": "function alpha() { return <div/>; }\nclass JsxClass extends React.Component {}\n",
    ".cjsx": "function alpha() { return <div/>; }\nclass CjsxClass extends React.Component {}\n",
    ".mjs": "function alpha() { return 1; }\nclass MjsClass {}\n",
    ".mjsx": "function alpha() { return <div/>; }\nclass MjsxClass extends React.Component {}\n",
    ".ts": "function alpha(): number { return 1; }\nclass TsClass {}\ninterface TsIface {}\n",
    ".cts": "function alpha(): number { return 1; }\nclass CtsClass {}\ninterface CtsIface {}\n",
    ".mts": "function alpha(): number { return 1; }\nclass MtsClass {}\ninterface MtsIface {}\n",
    ".tsx": "function alpha(){ return <div/>; }\nclass TsxClass extends React.Component {}\n",
    ".ctsx": "function alpha(){ return <div/>; }\nclass CtsxClass extends React.Component {}\n",
    ".mtsx": "function alpha(){ return <div/>; }\nclass MtsxClass extends React.Component {}\n",
    ".go": "package main\nfunc Alpha(){}\ntype GoType struct{}\n",
    ".rs": "fn alpha() {}\nstruct RsType;\ntrait RsTrait {}\n",
    ".java": "class JavaClass { void alpha(){} }\ninterface JavaIface {}\n",
    ".php": "<?php\nfunction alpha(){}\nclass PhpClass { public function beta(){} }\n",
    ".cs": "class CsClass { void Alpha(){} }\ninterface CsIface {}\n",
    ".c": "struct CType { int x; };\nint alpha(){ return 0; }\n",
    ".h": "class HeaderClass {};\n",
    ".hh": "class HhClass {};\nint alpha(){ return 0; }\n",
    ".cpp": "class CppClass {};\nint alpha(){ return 0; }\n",
    ".cc": "class CcClass {};\nint alpha(){ return 0; }\n",
    ".cxx": "class CxxClass {};\nint alpha(){ return 0; }\n",
    ".hpp": "class HppClass {};\nint alpha(){ return 0; }\n",
    ".hxx": "class HxxClass {};\nint alpha(){ return 0; }\n",
    ".html": '<main id="app"><section class="hero"><h1>Hello</h1></section></main>\n',
    ".htm": '<main id="app"><section class="hero"><h1>Hello</h1></section></main>\n',
    ".css": ".hero { color: red; }\n",
    ".less": ".hero { color: red; }\n",
    ".sass": ".hero { color: red; }\n",
    ".scss": "$primary: red;\n.hero { color: $primary; }\n",
    ".styl": ".hero { color: red; }\n",
    ".stylus": ".hero { color: red; }\n",
    ".sh": "alpha() { echo ok; }\n",
    ".zsh": "function alpha() { echo ok; }\n",
    ".svelte": "<script lang=\"ts\">\nfunction alpha(): number { return 1 }\n</script>\n<h1>Hello</h1>\n",
    ".ex": "defmodule ExModule do\n  def alpha(), do: 1\nend\n",
    ".exs": "defmodule ExsModule do\n  defp alpha(), do: 1\nend\n",
    ".rb": "class RbClass\nend\ndef alpha\nend\n",
    ".r": "my_func <- function(x, y = 10) {\n  return(x + y)\n}\nx <- 42\n",
}


@pytest.mark.parametrize("ext,source", sorted(LANGUAGE_SAMPLES.items()))
def test_parse_all_supported_languages_have_symbols(tmp_path, ext, source):
    """Contract test: every supported extension must parse and yield symbols."""
    file_path = tmp_path / f"sample{ext}"
    file_path.write_text(source, encoding="utf-8")

    lang_name, language = _get_language(ext)
    assert lang_name is not None, f"{ext} not mapped"
    assert language is not None, f"{ext} grammar failed to load"

    symbols = parse_file(str(file_path), str(tmp_path))
    assert symbols, f"{ext} parsed zero symbols"
