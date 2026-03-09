# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest
from symdex.core.storage import get_connection


def test_routes_table_exists(tmp_path):
    db = str(tmp_path / "test.db")
    conn = get_connection(db)
    # If table doesn't exist this raises OperationalError
    conn.execute("SELECT * FROM routes LIMIT 0")
    conn.close()


from symdex.core.route_extractor import extract_routes, RouteInfo


FLASK_SOURCE = b'''
from flask import Flask
app = Flask(__name__)

@app.route("/users", methods=["GET", "POST"])
def list_users():
    pass

@app.get("/users/<int:id>")
def get_user(id):
    pass

@app.delete("/users/<int:id>")
def delete_user(id):
    pass
'''

FASTAPI_SOURCE = b'''
from fastapi import FastAPI
app = FastAPI()
router = APIRouter()

@app.get("/items")
async def list_items():
    pass

@router.post("/items")
async def create_item():
    pass
'''

DJANGO_SOURCE = b'''
from django.urls import path, re_path
from . import views

urlpatterns = [
    path("users/", views.list_users),
    path("users/<int:pk>/", views.get_user, name="user-detail"),
    re_path(r"^orders/(?P<id>[0-9]+)/$", views.get_order),
]
'''

EXPRESS_SOURCE = b'''
const express = require("express");
const router = express.Router();
const app = express();

app.get("/products", listProducts);
router.post("/products", createProduct);
app.delete("/products/:id", deleteProduct);
'''


def test_flask_route_detected():
    routes = extract_routes(FLASK_SOURCE, "app.py", "python")
    paths = [r.path for r in routes]
    assert "/users" in paths


def test_flask_route_method():
    routes = extract_routes(FLASK_SOURCE, "app.py", "python")
    r = next(r for r in routes if r.path == "/users" and r.method == "GET")
    assert r.handler == "list_users"


def test_flask_shorthand_get():
    routes = extract_routes(FLASK_SOURCE, "app.py", "python")
    paths = [r.path for r in routes]
    assert "/users/<int:id>" in paths


def test_flask_shorthand_delete():
    routes = extract_routes(FLASK_SOURCE, "app.py", "python")
    methods = {r.method for r in routes if r.path == "/users/<int:id>"}
    assert "DELETE" in methods


def test_fastapi_router():
    routes = extract_routes(FASTAPI_SOURCE, "main.py", "python")
    paths = [r.path for r in routes]
    assert "/items" in paths


def test_fastapi_post():
    routes = extract_routes(FASTAPI_SOURCE, "main.py", "python")
    posts = [r for r in routes if r.method == "POST"]
    assert len(posts) >= 1


def test_django_path():
    routes = extract_routes(DJANGO_SOURCE, "urls.py", "python")
    paths = [r.path for r in routes]
    assert "users/" in paths


def test_express_get():
    routes = extract_routes(EXPRESS_SOURCE, "routes.js", "javascript")
    methods = {r.method for r in routes if r.path == "/products"}
    assert "GET" in methods


def test_express_post():
    routes = extract_routes(EXPRESS_SOURCE, "routes.js", "javascript")
    posts = [r for r in routes if r.method == "POST"]
    assert len(posts) == 1


def test_express_delete():
    routes = extract_routes(EXPRESS_SOURCE, "routes.js", "javascript")
    deletes = [r for r in routes if r.method == "DELETE"]
    assert len(deletes) == 1


def test_route_info_has_bytes():
    routes = extract_routes(FLASK_SOURCE, "app.py", "python")
    for r in routes:
        assert r.start_byte >= 0
        assert r.end_byte > r.start_byte


def test_empty_source_returns_empty():
    assert extract_routes(b"", "empty.py", "python") == []


def test_unsupported_lang_returns_empty():
    assert extract_routes(b"some content", "file.rs", "rust") == []
