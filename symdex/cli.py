# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import json
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from symdex.core.indexer import index_folder as _index_folder, invalidate as _invalidate
from symdex.core.watcher import watch as _watch_repo
from symdex.core.storage import (
    get_connection,
    get_db_path,
    get_registry_json_path,
    get_registry_path,  # noqa: F401 — imported for monkeypatching
    get_stale_repos,
    query_file_symbols,
    query_repos,
    query_routes,
    remove_repo,
    search_text_in_index,
    upsert_repo,
)
from symdex.core.token_metrics import build_search_roi_summary_from_rows, format_search_roi_summary
from symdex.core.updates import get_update_notice
from symdex.search.symbol_search import search_symbols as _search_symbols
from symdex.search.semantic import search_semantic as _search_semantic

app = typer.Typer(name="symdex", help="SymDex - universal code indexer")
console = Console()
err_console = Console(stderr=True)
_UPDATE_NOTICE_EMITTED = False


def _apply_state_dir_override(state_dir: Optional[str]) -> None:
    if state_dir:
        os.environ["SYMDEX_STATE_DIR"] = state_dir


@app.callback()
def main(
    state_dir: Optional[str] = typer.Option(
        None,
        "--state-dir",
        help="State directory for SymDex indexes and registry (for example .symdex)",
    ),
) -> None:
    _apply_state_dir_override(state_dir)


def _format_language_breakdown(languages: dict[str, int]) -> str:
    if not languages:
        return "none"
    parts = [f"{name}: {count}" for name, count in sorted(languages.items())]
    return ", ".join(parts)


def _print_code_summary(summary: dict) -> None:
    table = Table(title="Code Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files", str(summary.get("file_count", 0)))
    table.add_row("Lines of Code", str(summary.get("lines_of_code", 0)))
    table.add_row("Symbols", str(summary.get("symbol_count", 0)))
    table.add_row("Functions", str(summary.get("functions", 0)))
    table.add_row("Classes", str(summary.get("classes", 0)))
    table.add_row("Methods", str(summary.get("methods", 0)))
    table.add_row("Constants", str(summary.get("constants", 0)))
    table.add_row("Variables", str(summary.get("variables", 0)))
    table.add_row("Routes", str(summary.get("routes", 0)))
    table.add_row("Languages", _format_language_breakdown(summary.get("language_distribution", {})))
    table.add_row("Skipped", str(summary.get("skipped", 0)))
    table.add_row("Errors", str(summary.get("errored", 0)))
    console.print(table)


def _repo_root(repo: str) -> str | None:
    for entry in query_repos():
        if entry["name"] == repo:
            return entry["root_path"]
    return None


def _print_search_roi(summary: dict) -> None:
    console.print()
    console.print("[bold]ROI[/bold]")
    console.print(f"Lines searched: [cyan]{summary['lines_searched']}[/cyan]")
    console.print(
        f"Without SymDex: ~[red]{summary['estimated_tokens_without_symdex']}[/red] tokens"
    )
    console.print(
        f"With SymDex: ~[green]{summary['estimated_tokens_with_symdex']}[/green] tokens"
    )
    console.print(f"Saved: ~[green]{summary['estimated_tokens_saved']}[/green] tokens")
    console.print("[italic]You're in good hands.[/italic]")


def _stdout_is_terminal() -> bool:
    isatty = getattr(sys.stdout, "isatty", None)
    return bool(callable(isatty) and isatty())


def _maybe_print_update_notice(argv: list[str] | None = None, json_output: bool = False) -> None:
    global _UPDATE_NOTICE_EMITTED
    if _UPDATE_NOTICE_EMITTED or json_output or not _stdout_is_terminal():
        return

    notice = get_update_notice(argv)
    if notice is None:
        return

    _UPDATE_NOTICE_EMITTED = True
    console.print(
        f"[bold yellow]Update available:[/bold yellow] SymDex "
        f"{notice['latest_version']} (you have {notice['installed_version']})"
    )
    console.print(f"pip: [cyan]{notice['pip_command']}[/cyan]")
    console.print(f"uv tool: [cyan]{notice['uv_tool_command']}[/cyan]")
    console.print(f"uvx: [cyan]{notice['uvx_command']}[/cyan]")
    console.print("[dim]Fewer tokens. More signal. Stay current.[/dim]")
    console.print()


def _search_roi_summary(repo: str, rows: list[dict], result_kind: str) -> dict | None:
    root = _repo_root(repo)
    if not root or not rows:
        return None
    conn = get_connection(get_db_path(repo))
    try:
        return build_search_roi_summary_from_rows(
            conn,
            repo=repo,
            rows=rows,
            repo_root=root,
            result_kind=result_kind,
        )
    finally:
        conn.close()


def _attach_roi_payload(payload: dict, roi: dict | None) -> dict:
    if roi is not None:
        payload["roi"] = roi
        payload["roi_summary"] = format_search_roi_summary(roi)
    return payload


@app.command()
def index(
    path: str = typer.Argument(..., help="Directory to index"),
    repo: str = typer.Option(
        None,
        "--repo",
        "--name",
        "-r",
        "-n",
        help="Repo name (omit to auto-generate from git branch and path hash)",
    ),
) -> None:
    """Index a folder and register it."""
    _maybe_print_update_notice(sys.argv[1:])
    if not os.path.isdir(path):
        err_console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(code=1)
    result = _index_folder(path, repo=repo, progress_callback=lambda msg: console.print(f"[dim]{msg}[/dim]"))
    upsert_repo(result.repo, root_path=os.path.abspath(path), db_path=result.db_path)
    table = Table(title="Index Result")
    table.add_column("Repo", style="cyan")
    table.add_column("Indexed", style="green")
    table.add_column("Skipped", style="yellow")
    table.add_column("DB Path")
    table.add_row(result.repo, str(result.indexed_count), str(result.skipped_count), result.db_path)
    console.print(table)
    console.print()
    _print_code_summary(result.summary)
    console.print(f"[dim]Registry DB:[/dim] {get_registry_path()}")
    console.print(f"[dim]Registry JSON:[/dim] {get_registry_json_path()}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Symbol name to search for"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repo name (omit to search all repos)"),
    kind: str = typer.Option(None, "--kind", "-k", help="Symbol kind filter"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Find functions/classes by name (omit --repo to search all indexed repos)."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    if repo:
        conn = get_connection(get_db_path(repo))
        try:
            symbols = _search_symbols(conn, repo=repo, query=query, kind=kind, limit=limit)
        finally:
            conn.close()
    else:
        from symdex.graph.registry import search_across_repos
        symbols = search_across_repos(query=query, kind=kind, limit=limit)
    if not symbols:
        err_console.print(f"[red]Error:[/red] No symbols found matching: {query}")
        raise typer.Exit(code=1)
    if json_output:
        payload = {"symbols": symbols}
        if repo:
            roi = _search_roi_summary(repo, symbols, "symbol")
            _attach_roi_payload(payload, roi)
        typer.echo(json.dumps(payload))
        return
    table = Table(title=f"Symbols matching '{query}'")
    table.add_column("Repo", style="blue")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("File")
    table.add_column("Start", style="dim")
    for s in symbols:
        table.add_row(s.get("repo", repo or ""), s["name"], s["kind"], s["file"], str(s["start_byte"]))
    console.print(table)
    if repo:
        roi = _search_roi_summary(repo, symbols, "symbol")
        if roi is not None:
            _print_search_roi(roi)


@app.command()
def find(
    name: str = typer.Argument(..., help="Exact symbol name"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repo name"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Exact symbol name lookup by symbol name."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    if not repo:
        err_console.print("[red]Error:[/red] --repo is required")
        raise typer.Exit(code=1)
    conn = get_connection(get_db_path(repo))
    try:
        symbols = _search_symbols(conn, repo=repo, query=name, limit=1)
    finally:
        conn.close()
    if not symbols:
        err_console.print(f"[red]Error:[/red] Symbol not found: {name}")
        raise typer.Exit(code=1)
    if json_output:
        payload = {"symbols": symbols}
        roi = _search_roi_summary(repo, symbols, "symbol")
        _attach_roi_payload(payload, roi)
        typer.echo(json.dumps(payload))
        return
    s = symbols[0]
    table = Table(title=f"Symbol: {name}")
    table.add_column("Field")
    table.add_column("Value")
    for k, v in s.items():
        table.add_row(k, str(v) if v is not None else "")
    console.print(table)
    roi = _search_roi_summary(repo, symbols, "symbol")
    if roi is not None:
        _print_search_roi(roi)


@app.command()
def outline(
    file: str = typer.Argument(..., help="Relative file path within repo"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repo name"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List all symbols in a file."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    conn = get_connection(get_db_path(repo))
    try:
        symbols = query_file_symbols(conn, repo=repo, file=file)
    finally:
        conn.close()
    if not symbols:
        err_console.print(f"[red]Error:[/red] No symbols found in: {file}")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps({"symbols": symbols}))
        return
    table = Table(title=f"Outline: {file}")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Start", style="dim")
    table.add_column("End", style="dim")
    for s in symbols:
        table.add_row(s["name"], s["kind"], str(s["start_byte"]), str(s["end_byte"]))
    console.print(table)


@app.command()
def text(
    query: str = typer.Argument(..., help="Text to search for"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repo name"),
    pattern: str = typer.Option(None, "--pattern", "-p", help="File glob pattern"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Text search across indexed files."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    if not repo:
        err_console.print("[red]Error:[/red] --repo is required")
        raise typer.Exit(code=1)
    all_repos = query_repos()
    repo_info = next((r for r in all_repos if r["name"] == repo), None)
    if repo_info is None:
        err_console.print(f"[red]Error:[/red] Repo not indexed: {repo}")
        raise typer.Exit(code=1)
    conn = get_connection(get_db_path(repo))
    try:
        matches = search_text_in_index(conn, repo=repo, query=query, repo_root=repo_info["root_path"], file_pattern=pattern)
    finally:
        conn.close()
    if not matches:
        err_console.print(f"[red]Error:[/red] No matches found for: {query}")
        raise typer.Exit(code=1)
    if json_output:
        payload = {"matches": matches}
        roi = _search_roi_summary(repo, matches, "text")
        _attach_roi_payload(payload, roi)
        typer.echo(json.dumps(payload))
        return
    table = Table(title=f"Text matches for '{query}'")
    table.add_column("File")
    table.add_column("Line", style="dim")
    table.add_column("Text")
    for m in matches:
        table.add_row(m["file"], str(m["line"]), m["text"])
    console.print(table)
    roi = _search_roi_summary(repo, matches, "text")
    if roi is not None:
        _print_search_roi(roi)


@app.command()
def semantic(
    query: str = typer.Argument(..., help="Natural language query"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repo name"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Semantic similarity search by meaning."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    from symdex.search.semantic import search_semantic
    if not repo:
        err_console.print("[red]Error:[/red] --repo is required")
        raise typer.Exit(code=1)
    conn = get_connection(get_db_path(repo))
    try:
        try:
            results = _search_semantic(
                conn,
                query=query,
                repo=repo,
                limit=limit,
                progress_callback=lambda msg: console.print(f"[dim]{msg}[/dim]"),
            )
        except Exception as exc:
            err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
            raise typer.Exit(code=1)
    finally:
        conn.close()
    if not results:
        err_console.print(f"[red]Error:[/red] No semantic matches found for: {query}")
        raise typer.Exit(code=1)
    if json_output:
        payload = {"symbols": results}
        roi = _search_roi_summary(repo, results, "symbol")
        _attach_roi_payload(payload, roi)
        typer.echo(json.dumps(payload))
        return
    table = Table(title=f"Semantic matches for '{query}'")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("File")
    for s in results:
        table.add_row(s["name"], s["kind"], str(s["score"]), s["file"])
    console.print(table)
    roi = _search_roi_summary(repo, results, "symbol")
    if roi is not None:
        _print_search_roi(roi)


@app.command()
def callers(
    name: str = typer.Argument(..., help="Function name to find callers of"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repo name"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show all functions that call the named function."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    from symdex.graph.call_graph import get_callers as _get_callers
    conn = get_connection(get_db_path(repo))
    try:
        results = _get_callers(conn, name=name, repo=repo)
    finally:
        conn.close()
    if not results:
        err_console.print(f"[red]Error:[/red] No callers found for: {name}")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps({"callers": results}))
        return
    table = Table(title=f"Callers of '{name}'")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("File")
    for s in results:
        table.add_row(s["name"], s["kind"], s["file"])
    console.print(table)


@app.command()
def callees(
    name: str = typer.Argument(..., help="Function name to find callees of"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repo name"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show all functions called by the named function."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    from symdex.graph.call_graph import get_callees as _get_callees
    conn = get_connection(get_db_path(repo))
    try:
        results = _get_callees(conn, name=name, repo=repo)
    finally:
        conn.close()
    if not results:
        err_console.print(f"[red]Error:[/red] No callees found for: {name}")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps({"callees": results}))
        return
    table = Table(title=f"Callees of '{name}'")
    table.add_column("Name", style="cyan")
    table.add_column("File")
    for s in results:
        table.add_row(s["name"], s.get("file") or "")
    console.print(table)


@app.command()
def repos(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List all indexed repositories."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    all_repos = query_repos()
    if not all_repos:
        err_console.print("[red]Error:[/red] No repos indexed yet.")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps({
            "repos": all_repos,
            "registry_db": get_registry_path(),
            "registry_json": get_registry_json_path(),
        }))
        return
    table = Table(title="Indexed Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Root Path")
    table.add_column("Last Indexed", style="dim")
    for r in all_repos:
        table.add_row(r["name"], r["root_path"], str(r.get("last_indexed", "")))
    console.print(table)
    console.print(f"[dim]Registry DB:[/dim] {get_registry_path()}")
    console.print(f"[dim]Registry JSON:[/dim] {get_registry_json_path()}")


@app.command()
def invalidate(
    repo: str = typer.Option(..., "--repo", "-r", help="Repo name"),
    file: str = typer.Option(None, "--file", "-f", help="Specific file to invalidate"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Force re-index of a repo or specific file."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    count = _invalidate(repo, file=file)
    if json_output:
        typer.echo(json.dumps({"invalidated": count}))
        return
    console.print(f"Invalidated [green]{count}[/green] record(s) for repo '[cyan]{repo}[/cyan]'")


@app.command()
def routes(
    repo: str = typer.Argument(..., help="Repo name to query routes for."),
    method: Optional[str] = typer.Option(None, "--method", "-m", help="Filter by HTTP method (GET, POST, ...)."),
    path_contains: Optional[str] = typer.Option(None, "--path", "-p", help="Filter routes whose path contains this string."),
) -> None:
    """List HTTP routes indexed for a repo."""
    _maybe_print_update_notice(sys.argv[1:])
    db_path = get_db_path(repo)
    conn = get_connection(db_path)
    try:
        rows = query_routes(conn, repo=repo, method=method, path_contains=path_contains)
    finally:
        conn.close()

    if not rows:
        console.print(f"[yellow]No routes indexed for repo '{repo}'.[/yellow]")
        return

    table = Table(title=f"Routes — {repo}", show_header=True, header_style="bold")
    table.add_column("Method", style="cyan", width=8)
    table.add_column("Path")
    table.add_column("Handler")
    table.add_column("File")
    for r in rows:
        table.add_row(r["method"], r["path"], r.get("handler") or "", r["file"])
    console.print(table)


@app.command()
def serve(
    port: int = typer.Option(None, "--port", "-p", help="HTTP port (omit for stdio mode)"),
) -> None:
    """Start the MCP server."""
    _maybe_print_update_notice(sys.argv[1:])
    from symdex.mcp.server import mcp
    if port:
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run()


@app.command()
def watch(
    path: str = typer.Argument(..., help="Path to the directory to watch."),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "--name",
        "-r",
        "-n",
        help="Repo name (omit to auto-generate from git branch and path hash)",
    ),
    interval: float = typer.Option(5.0, "--interval", "-i", help="Seconds between re-index cycles."),
) -> None:
    """Watch a directory and keep its index up to date automatically."""
    _maybe_print_update_notice(sys.argv[1:])
    console.print(f"[bold]Watching[/bold] {path} (interval={interval}s) — Ctrl+C to stop")
    try:
        _watch_repo(path, repo=repo, interval=interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch stopped.[/yellow]")


@app.command()
def gc(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Remove stale index databases for repos whose directories no longer exist."""
    _maybe_print_update_notice(sys.argv[1:], json_output=json_output)
    stale = get_stale_repos()
    removed = []
    for entry in stale:
        remove_repo(entry["name"])
        removed.append(entry["name"])
    if json_output:
        typer.echo(json.dumps({"removed": removed, "count": len(removed)}))
        return
    if not removed:
        console.print("Registry is clean — nothing to remove.")
        return
    for name in removed:
        console.print(f"Removed stale index: [cyan]{name}[/cyan]")
    console.print(f"[green]{len(removed)}[/green] stale index(es) removed.")


if __name__ == "__main__":
    app()
