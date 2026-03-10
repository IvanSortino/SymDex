# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest

from symdex.core.parser import _get_language, parse_file


LANGUAGE_SAMPLES: dict[str, str] = {
    ".py": "def alpha():\n    return 1\nclass PyClass:\n    pass\n",
    ".js": "function alpha() { return 1; }\nclass JsClass {}\n",
    ".jsx": "function alpha() { return <div/>; }\nclass JsxClass extends React.Component {}\n",
    ".mjs": "function alpha() { return 1; }\nclass MjsClass {}\n",
    ".ts": "function alpha(): number { return 1; }\nclass TsClass {}\ninterface TsIface {}\n",
    ".tsx": "function alpha(){ return <div/>; }\nclass TsxClass extends React.Component {}\n",
    ".go": "package main\nfunc Alpha(){}\ntype GoType struct{}\n",
    ".rs": "fn alpha() {}\nstruct RsType;\ntrait RsTrait {}\n",
    ".java": "class JavaClass { void alpha(){} }\ninterface JavaIface {}\n",
    ".php": "<?php\nfunction alpha(){}\nclass PhpClass { public function beta(){} }\n",
    ".cs": "class CsClass { void Alpha(){} }\ninterface CsIface {}\n",
    ".c": "struct CType { int x; };\nint alpha(){ return 0; }\n",
    ".h": "class HeaderClass {};\n",
    ".cpp": "class CppClass {};\nint alpha(){ return 0; }\n",
    ".cc": "class CcClass {};\nint alpha(){ return 0; }\n",
    ".ex": "defmodule ExModule do\n  def alpha(), do: 1\nend\n",
    ".exs": "defmodule ExsModule do\n  defp alpha(), do: 1\nend\n",
    ".rb": "class RbClass\nend\ndef alpha\nend\n",
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
