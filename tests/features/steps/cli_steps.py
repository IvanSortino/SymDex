# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import json
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from typer.testing import CliRunner
from symdex.cli import app

scenarios("../cli.feature")

# Default CliRunner already mixes stderr into result.output (Click 8.x StreamMixer behaviour)
runner = CliRunner()


@given("a temporary directory with Python source files has been indexed")
def step_indexed(tmp_indexed):
    """Background step — tmp_indexed fixture handles indexing."""
    pass


@when('I run "symdex index" on the temporary directory')
def step_run_index(context, tmp_indexed):
    result = runner.invoke(app, ["index", tmp_indexed["path"]])
    context["result"] = result


@when(parsers.parse('I run "symdex search" with query "{query}"'))
def step_run_search(context, tmp_indexed, query):
    result = runner.invoke(app, ["search", query, "--repo", tmp_indexed["repo"]])
    context["result"] = result


@when(parsers.parse('I run "symdex search" with query "{query}" and flag "--json"'))
def step_run_search_json(context, tmp_indexed, query):
    result = runner.invoke(app, ["search", query, "--repo", tmp_indexed["repo"], "--json"])
    context["result"] = result


@when('I run "symdex repos"')
def step_run_repos(context, tmp_indexed):
    result = runner.invoke(app, ["repos"])
    context["result"] = result


@when('I run "symdex outline" on an indexed file')
def step_run_outline(context, tmp_indexed):
    result = runner.invoke(app, ["outline", "parse_module.py", "--repo", tmp_indexed["repo"]])
    context["result"] = result


@when(parsers.parse('I run "symdex text" with query "{query}"'))
def step_run_text(context, tmp_indexed, query):
    result = runner.invoke(app, ["text", query, "--repo", tmp_indexed["repo"]])
    context["result"] = result


@when('I run "symdex invalidate" for the indexed repo')
def step_run_invalidate(context, tmp_indexed):
    result = runner.invoke(app, ["invalidate", "--repo", tmp_indexed["repo"]])
    context["result"] = result


@then("the command exits with code 0")
def step_exit_0(context):
    result = context["result"]
    assert result.exit_code == 0, (
        f"exit code {result.exit_code}\noutput: {result.output}"
    )


@then("the command exits with code 1")
def step_exit_1(context):
    result = context["result"]
    assert result.exit_code == 1, (
        f"exit code {result.exit_code}\noutput: {result.output}"
    )


@then("the output contains indexing statistics")
def step_output_has_indexing_stats(context):
    output = context["result"].output
    assert any(c.isdigit() for c in output), f"No digit in output: {output}"


@then("the output contains at least one symbol row")
def step_output_has_symbol_row(context):
    output = context["result"].output
    assert len(output.strip()) > 0, "Output is empty"
    assert any(kw in output for kw in ["parse_file", "MyClass", "function", "class", "method"]), (
        f"No symbol keyword in output: {output}"
    )


@then('the output contains "Error"')
def step_output_has_error(context):
    output = context["result"].output
    assert "Error" in output, f"'Error' not found in output: {output}"


@then("the output contains at least one repo name")
def step_output_has_repo_name(context):
    assert "testbdd" in context["result"].output, (
        f"Repo name 'testbdd' not found in output: {context['result'].output}"
    )


@then('the output is valid JSON containing a "symbols" key')
def step_output_is_json_with_symbols(context):
    try:
        data = json.loads(context["result"].output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {e}\nOutput: {context['result'].output}")
    assert "symbols" in data, f"No 'symbols' key in JSON: {data}"


@then("the output contains at least one result row")
def step_output_has_result_row(context):
    output = context["result"].output
    assert len(output.strip()) > 0, "Output is empty"


@then("the output contains the invalidated count")
def step_output_has_invalidated_count(context):
    output = context["result"].output
    assert any(c.isdigit() for c in output), f"No digit in output: {output}"
