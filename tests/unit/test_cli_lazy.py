# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os

import symdex.cli as cli


def test_start_lazy_embedding_watch_uses_absolute_path_and_state_dir(monkeypatch):
    calls = []

    class _FakeProcess:
        pid = 1234

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return _FakeProcess()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    pid = cli._start_lazy_embedding_watch(
        ".",
        "lazy_repo",
        state_dir=".symdex",
        interval=7.5,
        idle_timeout=60.0,
    )

    command, kwargs = calls[0]
    assert pid == 1234
    assert command[4] == os.path.abspath(".")
    assert command[-2:] == ["--state-dir", os.path.abspath(".symdex")]
    assert kwargs["cwd"] == os.path.abspath(".")
