# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from unittest.mock import patch

from symdex.core.indexer import _ROUTE_LANG_MAP, index_folder
from symdex.core.route_extractor import extract_routes
from symdex.core.storage import get_connection, query_routes


def test_route_language_map_includes_extended_web_languages():
    assert _ROUTE_LANG_MAP[".py"] == "python"
    assert _ROUTE_LANG_MAP[".cjs"] == "javascript"
    assert _ROUTE_LANG_MAP[".cjsx"] == "javascript"
    assert _ROUTE_LANG_MAP[".mjsx"] == "javascript"
    assert _ROUTE_LANG_MAP[".mts"] == "typescript"
    assert _ROUTE_LANG_MAP[".cts"] == "typescript"
    assert _ROUTE_LANG_MAP[".mtsx"] == "typescript"
    assert _ROUTE_LANG_MAP[".ctsx"] == "typescript"
    assert _ROUTE_LANG_MAP[".go"] == "go"
    assert _ROUTE_LANG_MAP[".java"] == "java"
    assert _ROUTE_LANG_MAP[".kt"] == "kotlin"
    assert _ROUTE_LANG_MAP[".cs"] == "csharp"
    assert _ROUTE_LANG_MAP[".rb"] == "ruby"
    assert _ROUTE_LANG_MAP[".ex"] == "elixir"
    assert _ROUTE_LANG_MAP[".rs"] == "rust"


def test_python_api_route_detected():
    source = (
        b'@router.api_route("/users", methods=["GET", "POST"])\n'
        b"async def users_handler():\n"
        b"    return []\n"
    )
    routes = extract_routes(source, "api.py", "python")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "users_handler") in methods_paths
    assert ("POST", "/users", "users_handler") in methods_paths


def test_express_route_chain_detected():
    source = (
        b'router.route("/users")\n'
        b"  .get(listUsers)\n"
        b"  .post(async (req, res) => {\n"
        b"    res.json({ ok: true });\n"
        b"  });\n"
    )
    routes = extract_routes(source, "routes.ts", "typescript")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "listUsers") in methods_paths
    assert ("POST", "/users", "<inline>") in methods_paths


def test_go_routes_detected():
    source = (
        b'router.GET("/users", listUsers)\n'
        b'r.Get("/orders/{id}", getOrder)\n'
        b'http.HandleFunc("/health", healthHandler)\n'
    )
    routes = extract_routes(source, "main.go", "go")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "listUsers") in methods_paths
    assert ("GET", "/orders/{id}", "getOrder") in methods_paths
    assert ("ANY", "/health", "healthHandler") in methods_paths


def test_java_spring_routes_detected():
    source = (
        b'@GetMapping("/users")\n'
        b"public List<User> listUsers() { return users; }\n"
        b'@RequestMapping(value = "/orders", method = RequestMethod.POST)\n'
        b"public Order createOrder() { return order; }\n"
    )
    routes = extract_routes(source, "UsersController.java", "java")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "listUsers") in methods_paths
    assert ("POST", "/orders", "createOrder") in methods_paths


def test_kotlin_spring_routes_detected():
    source = (
        b'@GetMapping("/users")\n'
        b'fun listUsers(): String = "ok"\n'
        b'@RequestMapping(value = "/orders", method = RequestMethod.POST)\n'
        b'fun createOrder(): String = "ok"\n'
    )
    routes = extract_routes(source, "UsersController.kt", "kotlin")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "listUsers") in methods_paths
    assert ("POST", "/orders", "createOrder") in methods_paths


def test_csharp_attribute_routes_detected():
    source = (
        b'[HttpGet("/users")]\n'
        b"public IActionResult ListUsers() => Ok();\n"
        b'[Route("/orders")]\n'
        b"[HttpPost]\n"
        b"public IActionResult CreateOrder() => Ok();\n"
    )
    routes = extract_routes(source, "UsersController.cs", "csharp")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "ListUsers") in methods_paths
    assert ("POST", "/orders", "CreateOrder") in methods_paths


def test_ruby_rails_and_sinatra_routes_detected():
    source = (
        b'get "/users", to: "users#index"\n'
        b'post "/sessions" do\n'
        b"  json ok: true\n"
        b"end\n"
    )
    routes = extract_routes(source, "routes.rb", "ruby")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "users#index") in methods_paths
    assert ("POST", "/sessions", "<inline>") in methods_paths


def test_elixir_phoenix_routes_detected():
    source = b'get "/users", UserController, :index\npost "/users", UserController, :create\n'
    routes = extract_routes(source, "router.ex", "elixir")
    methods_paths = {(route.method, route.path, route.handler) for route in routes}
    assert ("GET", "/users", "UserController.index") in methods_paths
    assert ("POST", "/users", "UserController.create") in methods_paths


def test_rust_actix_routes_detected():
    source = (
        b'#[get("/users")]\n'
        b"async fn list_users() -> impl Responder { HttpResponse::Ok() }\n"
    )
    routes = extract_routes(source, "routes.rs", "rust")
    assert len(routes) == 1
    assert routes[0].method == "GET"
    assert routes[0].path == "/users"
    assert routes[0].handler == "list_users"


def test_index_folder_extracts_go_routes(tmp_path):
    repo_dir = tmp_path / "go_app"
    repo_dir.mkdir()
    (repo_dir / "main.go").write_text(
        "package main\n"
        "func setup(router *gin.Engine) {\n"
        '    router.GET("/users", listUsers)\n'
        "}\n",
        encoding="utf-8",
    )

    db_path_store = {}

    def fake_db_path(repo):
        path = str(tmp_path / f"{repo}.db")
        db_path_store[repo] = path
        return path

    with (
        patch("symdex.core.indexer.get_db_path", fake_db_path),
        patch("symdex.core.storage.get_db_path", fake_db_path),
        patch("symdex.search.semantic.embed_text", return_value=[0.0] * 384),
    ):
        index_folder(str(repo_dir), name="go_routes_test")

    conn = get_connection(db_path_store["go_routes_test"])
    routes = query_routes(conn, repo="go_routes_test")
    conn.close()

    assert any(route["method"] == "GET" and route["path"] == "/users" for route in routes)
