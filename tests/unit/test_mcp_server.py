import anyio

from symdex.mcp.server import mcp


def test_server_registers_expected_tools():
    async def _list_tool_names():
        tools = await mcp.list_tools()
        return {tool.name for tool in tools}

    names = anyio.run(_list_tool_names)

    assert names == {
        "index_folder",
        "search_symbols",
        "get_symbol",
        "get_file_outline",
        "get_repo_outline",
        "search_text",
        "get_file_tree",
        "list_repos",
        "get_symbols",
        "index_repo",
        "invalidate_cache",
        "semantic_search",
        "get_callers",
        "get_callees",
        "search_routes",
        "gc_stale_indexes",
        "get_index_status",
        "get_repo_stats",
        "get_graph_diagram",
        "find_circular_deps",
    }
