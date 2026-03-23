# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core import updates


def test_is_newer_uses_semver_ordering():
    assert updates._is_newer("0.1.16", "0.1.15") is True
    assert updates._is_newer("0.1.15", "0.1.15") is False
    assert updates._is_newer("0.1.14", "0.1.15") is False


def test_should_check_for_updates_skips_json(monkeypatch):
    monkeypatch.delenv("SYMDEX_DISABLE_UPDATE_CHECK", raising=False)
    assert updates.should_check_for_updates(["repos"]) is True
    assert updates.should_check_for_updates(["repos", "--json"]) is False


def test_get_update_notice_returns_commands(monkeypatch):
    monkeypatch.delenv("SYMDEX_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(updates, "get_installed_version", lambda: "0.1.15")
    monkeypatch.setattr(updates, "_get_latest_version", lambda installed: "0.1.16")

    notice = updates.get_update_notice(["repos"])

    assert notice is not None
    assert notice["latest_version"] == "0.1.16"
    assert notice["pip_command"] == "py -m pip install -U symdex"
    assert notice["uv_tool_command"] == "uv tool upgrade symdex"
    assert notice["uvx_command"].startswith("uvx symdex@latest repos")
