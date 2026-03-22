# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core.token_metrics import build_search_roi_summary, count_token_metrics


def test_count_token_metrics_defaults_to_o200k_base():
    metrics = count_token_metrics("def foo():\n    return 1\n")
    assert metrics["tokenizer"] == "o200k_base"
    assert metrics["approximate"] is True
    assert metrics["token_count"] > 0


def test_build_search_roi_summary_reports_savings():
    summary = build_search_roi_summary(
        baseline_text="def foo():\n    return 1\n",
        result_text="def foo():\n    return 1\n",
        files_searched=1,
        lines_searched=2,
    )
    assert summary["tokenizer"] == "o200k_base"
    assert summary["approximate"] is True
    assert summary["estimated_tokens_without_symdex"] >= summary["estimated_tokens_with_symdex"]
    assert summary["estimated_tokens_saved"] == (
        summary["estimated_tokens_without_symdex"] - summary["estimated_tokens_with_symdex"]
    )
