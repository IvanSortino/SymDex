# tests/features/steps/mcp_steps.py
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from symdex.mcp.tools import (
    index_folder_tool,
    search_symbols_tool,
    get_symbol_tool,
    get_file_outline_tool,
    get_repo_outline_tool,
    invalidate_cache_tool,
    list_repos_tool,
)
from symdex.core.storage import get_connection, get_db_path, query_file_symbols

scenarios("../mcp_tools.feature")


# ── Background ────────────────────────────────────────────────────────────────

@given("a temporary directory with Python source files has been indexed")
def background_indexed(tmp_indexed):
    assert tmp_indexed["index_result"] is not None


# ── index_folder ──────────────────────────────────────────────────────────────

@when("I call index_folder with the temporary directory path")
def call_index_folder(tmp_indexed, context):
    context["response"] = index_folder_tool(path=tmp_indexed["path"], name="testbdd_scan")


@then('the response contains "indexed" count greater than 0')
def check_indexed_count(context):
    assert context["response"]["indexed"] > 0


@then('the response contains a "repo" name')
def check_repo_name(context):
    assert "repo" in context["response"]
    assert context["response"]["repo"]


@then('the response contains a "db_path"')
def check_db_path(context):
    assert "db_path" in context["response"]


# ── search_symbols — found ─────────────────────────────────────────────────────

@when('I call search_symbols with query "parse_file"')
def call_search_symbols_found(tmp_indexed, context):
    context["response"] = search_symbols_tool(query="parse_file", repo=tmp_indexed["repo"])


@then('the response contains a "symbols" list')
def check_symbols_list(context):
    assert "symbols" in context["response"]
    assert isinstance(context["response"]["symbols"], list)


@then('the response contains a non-empty "symbols" list')
def check_nonempty_symbols_list(context):
    assert "symbols" in context["response"]
    assert isinstance(context["response"]["symbols"], list)
    assert len(context["response"]["symbols"]) > 0


@then('the first symbol has fields "name", "file", "kind", "start_byte", "end_byte"')
def check_symbol_fields(context):
    sym = context["response"]["symbols"][0]
    for field in ("name", "file", "kind", "start_byte", "end_byte"):
        assert field in sym, f"Missing field: {field}"


# ── search_symbols — not found ─────────────────────────────────────────────────

@when('I call search_symbols with query "nonexistent_xyz_abc_symbol"')
def call_search_symbols_missing(tmp_indexed, context):
    context["response"] = search_symbols_tool(
        query="nonexistent_xyz_abc_symbol", repo=tmp_indexed["repo"]
    )


@then(parsers.parse("the response is an error envelope with code {code:d}"))
def check_error_envelope(context, code):
    assert "error" in context["response"], f"Expected error envelope, got: {context['response']}"
    assert context["response"]["error"]["code"] == code


@then(parsers.parse('the error key is "{key}"'))
def check_error_key(context, key):
    assert context["response"]["error"]["key"] == key


# ── get_symbol ─────────────────────────────────────────────────────────────────

@given("I have a symbol with a known start_byte and end_byte")
def known_symbol(tmp_indexed, context):
    conn = get_connection(get_db_path(tmp_indexed["repo"]))
    try:
        syms = query_file_symbols(conn, tmp_indexed["repo"], "parse_module.py")
    finally:
        conn.close()
    assert syms, "No symbols indexed for parse_module.py"
    context["symbol"] = syms[0]


@when("I call get_symbol with those byte offsets")
def call_get_symbol(tmp_indexed, context):
    sym = context["symbol"]
    context["response"] = get_symbol_tool(
        repo=tmp_indexed["repo"],
        file=sym["file"],
        start_byte=sym["start_byte"],
        end_byte=sym["end_byte"],
    )


@then('the response contains a non-empty "source" string')
def check_source(context):
    assert "source" in context["response"], f"Got: {context['response']}"
    assert len(context["response"]["source"]) > 0


# ── get_file_outline ───────────────────────────────────────────────────────────

@when("I call get_file_outline with a known indexed file")
def call_get_file_outline(tmp_indexed, context):
    context["response"] = get_file_outline_tool(
        repo=tmp_indexed["repo"], file="parse_module.py"
    )


# ── get_repo_outline ───────────────────────────────────────────────────────────

@when("I call get_repo_outline for an indexed repo")
def call_get_repo_outline(tmp_indexed, context):
    context["response"] = get_repo_outline_tool(repo=tmp_indexed["repo"])


@then('the response contains "tree" as a string')
def check_tree(context):
    assert "tree" in context["response"]
    assert isinstance(context["response"]["tree"], str)


@then('the response contains "stats" with "files" greater than 0')
def check_stats(context):
    assert context["response"]["stats"]["files"] > 0


# ── list_repos ─────────────────────────────────────────────────────────────────

@when("I call list_repos")
def call_list_repos(context):
    context["response"] = list_repos_tool()


@then('the response contains a "repos" list with at least one entry')
def check_repos_list(context):
    assert "repos" in context["response"]
    assert len(context["response"]["repos"]) >= 1


# ── invalidate_cache ───────────────────────────────────────────────────────────

@when("I call invalidate_cache for a specific indexed file")
def call_invalidate_cache(tmp_indexed, context):
    context["response"] = invalidate_cache_tool(
        repo=tmp_indexed["repo"], file="parse_module.py"
    )


@then('the response contains "invalidated" count greater than 0')
def check_invalidated(context):
    assert context["response"]["invalidated"] > 0


# ── search_symbols — empty query ───────────────────────────────────────────────

@when("I call search_symbols without providing a query")
def call_search_symbols_no_query(tmp_indexed, context):
    context["response"] = search_symbols_tool(query="", repo=tmp_indexed["repo"])
