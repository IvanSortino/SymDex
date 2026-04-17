# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core.token_metrics import (
    build_search_roi_summary,
    count_token_metrics,
    format_search_roi_agent_hint,
    format_search_roi_summary,
)


def test_count_token_metrics_defaults_to_o200k_base():
    metrics = count_token_metrics("def foo():\n    return 1\n")
    assert metrics["tokenizer"] == "o200k_base"
    assert isinstance(metrics["approximate"], bool)
    assert metrics["token_count"] > 0


def test_build_search_roi_summary_reports_savings():
    summary = build_search_roi_summary(
        baseline_text="def foo():\n    return 1\n",
        result_text="def foo():\n    return 1\n",
        files_searched=1,
        lines_searched=2,
    )
    assert summary["tokenizer"] == "o200k_base"
    assert isinstance(summary["approximate"], bool)
    assert summary["estimated_tokens_without_symdex"] >= summary["estimated_tokens_with_symdex"]
    assert summary["estimated_tokens_saved"] == (
        summary["estimated_tokens_without_symdex"] - summary["estimated_tokens_with_symdex"]
    )


def test_format_search_roi_summary_is_one_line():
    summary = {
        "files_searched": 2,
        "lines_searched": 80,
        "tokenizer": "o200k_base",
        "approximate": True,
        "estimated_tokens_without_symdex": 1200,
        "estimated_tokens_with_symdex": 150,
        "estimated_tokens_saved": 1050,
    }

    text = format_search_roi_summary(summary)

    assert "\n" not in text
    assert text.startswith("SymDex token savings:")
    assert "~1,050 saved" in text


def test_format_search_roi_agent_hint_tells_agent_to_mention_savings():
    summary = {
        "files_searched": 1,
        "lines_searched": 20,
        "tokenizer": "o200k_base",
        "approximate": True,
        "estimated_tokens_without_symdex": 300,
        "estimated_tokens_with_symdex": 75,
        "estimated_tokens_saved": 225,
    }

    text = format_search_roi_agent_hint(summary)

    assert "mention" in text.lower()
    assert "SymDex saved ~225 tokens" in text
