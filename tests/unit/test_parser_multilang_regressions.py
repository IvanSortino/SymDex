# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest

from symdex.core.parser import parse_file


@pytest.mark.parametrize(
    ("filename", "source", "expected"),
    [
        (
            "sample.py",
            "class A:\n"
            "    def m(self):\n"
            "        return 1\n\n"
            "def top():\n"
            "    return 2\n",
            {"A": "class", "m": "method", "top": "function"},
        ),
        (
            "sample.go",
            "package main\n"
            "type User struct{}\n"
            "func (u User) Method() {}\n"
            "func Top() {}\n",
            {"User": "class", "Method": "method", "Top": "function"},
        ),
        (
            "sample.kt",
            "enum class Role { ADMIN, USER }\n"
            "class User {\n"
            "  fun method(): Int = 1\n"
            "}\n"
            "fun top(): Int = 2\n",
            {"Role": "enum", "User": "class", "method": "method", "top": "function"},
        ),
        (
            "sample.java",
            "interface Api { void run(); }\n"
            "class User { void method() {} }\n",
            {"Api": "class", "run": "method", "User": "class", "method": "method"},
        ),
        (
            "sample.php",
            "<?php\n"
            "class User { public function method() {} }\n"
            "function top() {}\n",
            {"User": "class", "method": "method", "top": "function"},
        ),
        (
            "sample.cs",
            "interface IApi { void Run(); }\n"
            "class User { void Method() {} }\n",
            {"IApi": "class", "Run": "method", "User": "class", "Method": "method"},
        ),
        (
            "sample.c",
            "struct User { int id; };\n"
            "int top() { return 0; }\n",
            {"User": "class", "top": "function"},
        ),
        (
            "sample.h",
            "class HeaderUser { public: void method() {} };\n",
            {"HeaderUser": "class", "method": "method"},
        ),
        (
            "sample.cpp",
            "class User { public: void method() {} };\n"
            "int top() { return 0; }\n",
            {"User": "class", "method": "method", "top": "function"},
        ),
        (
            "sample.cc",
            "class User { public: void method() {} };\n"
            "int top() { return 0; }\n",
            {"User": "class", "method": "method", "top": "function"},
        ),
        (
            "sample.ex",
            "defmodule User do\n"
            "  def method(), do: 1\n"
            "  defp hidden(), do: 2\n"
            "end\n",
            {"User": "class", "method": "function", "hidden": "function"},
        ),
        (
            "sample.exs",
            "defmodule User do\n"
            "  def method(), do: 1\n"
            "end\n",
            {"User": "class", "method": "function"},
        ),
        (
            "sample.dart",
            "class User {\n"
            "  String method() => 'ok';\n"
            "}\n"
            "enum Role { admin, user }\n"
            "typedef UserFormatter = String Function(String value);\n"
            "String top() => 'ok';\n",
            {"User": "class", "method": "method", "Role": "enum", "UserFormatter": "type", "top": "function"},
        ),
        (
            "sample.swift",
            "enum Role {\n"
            "  case admin\n"
            "}\n"
            "class User {\n"
            "  func method() -> Int { return 1 }\n"
            "}\n"
            "func top() -> Int { return 2 }\n",
            {"Role": "enum", "User": "class", "method": "method", "top": "function"},
        ),
    ],
)
def test_supported_language_core_shapes(tmp_path, filename, source, expected):
    path = tmp_path / filename
    path.write_text(source, encoding="utf-8")

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    for name, kind in expected.items():
        assert by_name[name]["kind"] == kind


def test_javascript_class_method_and_function_expression_are_indexed(tmp_path):
    path = tmp_path / "sample.js"
    path.write_text(
        "class JsClass { methodOne() { return 1 } }\n"
        "const fnExpr = function namedExpr() { return 4 }\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["JsClass"]["kind"] == "class"
    assert by_name["methodOne"]["kind"] == "method"
    assert by_name["fnExpr"]["kind"] == "function"


def test_typescript_extended_symbols_are_indexed(tmp_path):
    path = tmp_path / "sample.ts"
    path.write_text(
        "interface TsIface { run(x: number): void }\n"
        "abstract class TsClass {\n"
        "  abstract build(): void\n"
        "  methodOne(): number { return 1 }\n"
        "}\n"
        "function topLevel(x: string): string { return x }\n"
        "const fnExpr = function namedExpr(): number { return 4 }\n"
        "export enum Role { Admin, User }\n"
        "export type UserId = string\n"
        "declare function boot(config: string): void\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["TsIface"]["kind"] == "class"
    assert by_name["run"]["kind"] == "method"
    assert by_name["TsClass"]["kind"] == "class"
    assert by_name["build"]["kind"] == "method"
    assert by_name["methodOne"]["kind"] == "method"
    assert by_name["topLevel"]["kind"] == "function"
    assert by_name["fnExpr"]["kind"] == "function"
    assert by_name["Role"]["kind"] == "enum"
    assert by_name["UserId"]["kind"] == "type"
    assert by_name["boot"]["kind"] == "function"


def test_python_class_methods_are_typed_as_methods(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(
        "class A:\n"
        "    def method_one(self):\n"
        "        return 1\n\n"
        "def top_level():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["A"]["kind"] == "class"
    assert by_name["method_one"]["kind"] == "method"
    assert by_name["top_level"]["kind"] == "function"


def test_rust_impl_and_trait_functions_are_typed_as_methods(tmp_path):
    path = tmp_path / "sample.rs"
    path.write_text(
        "impl User { fn method_one(&self) {} }\n"
        "fn top_level() {}\n"
        "trait X { fn trait_method(&self); }\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert sum(1 for symbol in symbols if symbol["name"] == "User" and symbol["kind"] == "class") == 1
    assert by_name["method_one"]["kind"] == "method"
    assert by_name["top_level"]["kind"] == "function"
    assert by_name["trait_method"]["kind"] == "method"


def test_cpp_class_methods_are_typed_as_methods(tmp_path):
    path = tmp_path / "sample.cpp"
    path.write_text(
        "class User { public: void methodOne() {} };\n"
        "int top_level(){ return 0; }\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["User"]["kind"] == "class"
    assert by_name["methodOne"]["kind"] == "method"
    assert by_name["top_level"]["kind"] == "function"


def test_ruby_top_level_defs_are_functions_and_class_defs_are_methods(tmp_path):
    path = tmp_path / "sample.rb"
    path.write_text(
        "class User\n"
        "  def method_one\n"
        "  end\n"
        "end\n"
        "def top_level\n"
        "end\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["User"]["kind"] == "class"
    assert by_name["method_one"]["kind"] == "method"
    assert by_name["top_level"]["kind"] == "function"


def test_vue_javascript_and_typescript_scripts_inherit_language_fixes(tmp_path):
    js_path = tmp_path / "component.vue"
    js_path.write_text(
        "<template><div/></template>\n"
        "<script>\n"
        "class JsComponent { methodOne() { return 1 } }\n"
        "const fnExpr = function namedExpr() { return 2 }\n"
        "</script>\n",
        encoding="utf-8",
    )
    ts_path = tmp_path / "component-ts.vue"
    ts_path.write_text(
        "<template><div/></template>\n"
        "<script lang=\"ts\">\n"
        "interface TsIface { run(): void }\n"
        "class TsComponent { methodOne(): number { return 1 } }\n"
        "</script>\n",
        encoding="utf-8",
    )

    js_symbols = {symbol["name"]: symbol for symbol in parse_file(str(js_path), str(tmp_path))}
    ts_symbols = {symbol["name"]: symbol for symbol in parse_file(str(ts_path), str(tmp_path))}

    assert js_symbols["JsComponent"]["kind"] == "class"
    assert js_symbols["methodOne"]["kind"] == "method"
    assert js_symbols["fnExpr"]["kind"] == "function"
    assert ts_symbols["TsIface"]["kind"] == "class"
    assert ts_symbols["run"]["kind"] == "method"
    assert ts_symbols["TsComponent"]["kind"] == "class"
    assert ts_symbols["methodOne"]["kind"] == "method"


def test_kotlin_lambda_assignment_is_indexed_as_function(tmp_path):
    path = tmp_path / "sample.kt"
    path.write_text(
        "class User {\n"
        "  fun method(): Int = 1\n"
        "}\n"
        "val formatter = { value: String -> value.trim() }\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["User"]["kind"] == "class"
    assert by_name["method"]["kind"] == "method"
    assert by_name["formatter"]["kind"] == "function"


def test_dart_functions_include_bodies_and_lambda_assignments(tmp_path):
    path = tmp_path / "sample.dart"
    source = (
        "class User {\n"
        "  String method() => service.fetchAll();\n"
        "}\n"
        "String top() {\n"
        "  return createUser();\n"
        "}\n"
        "final formatter = (String value) => value.trim();\n"
    )
    path.write_text(source, encoding="utf-8")

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["method"]["kind"] == "method"
    assert by_name["top"]["kind"] == "function"
    assert by_name["formatter"]["kind"] == "function"
    assert sum(1 for symbol in symbols if symbol["name"] == "method") == 1
    assert sum(1 for symbol in symbols if symbol["name"] == "top") == 1
    assert "service.fetchAll()" in source[by_name["method"]["start_byte"]:by_name["method"]["end_byte"]]
    assert "createUser()" in source[by_name["top"]["start_byte"]:by_name["top"]["end_byte"]]


def test_swift_protocols_methods_and_lambda_assignments_are_indexed(tmp_path):
    path = tmp_path / "sample.swift"
    path.write_text(
        "protocol UserApi {\n"
        "  func fetch(id: String) -> String\n"
        "}\n"
        "class User {\n"
        "  func method() -> Int { return 1 }\n"
        "}\n"
        "func top() -> Int { return 2 }\n"
        "let formatter = { (value: String) in value.trimmingCharacters(in: .whitespaces) }\n",
        encoding="utf-8",
    )

    symbols = parse_file(str(path), str(tmp_path))
    by_name = {symbol["name"]: symbol for symbol in symbols}

    assert by_name["UserApi"]["kind"] == "class"
    assert by_name["fetch"]["kind"] == "method"
    assert by_name["User"]["kind"] == "class"
    assert by_name["method"]["kind"] == "method"
    assert by_name["top"]["kind"] == "function"
    assert by_name["formatter"]["kind"] == "function"
