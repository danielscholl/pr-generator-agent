"""Tests for pre-flight diff filtering and input budgeting."""

from unittest.mock import patch

import pytest

from aipr.gitdiff import (
    DEFAULT_MAX_INPUT_TOKENS,
    check_input_budget,
    estimate_tokens,
    filter_diff,
    resolve_max_input_tokens,
)


def _file(path, body_lines):
    return "\n".join(
        [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}"] + body_lines
    )


class TestFilterDiff:
    """Noise removal and per-file truncation."""

    def test_lock_files_are_replaced_with_marker(self):
        """Lock files are replaced with marker."""
        diff = _file("uv.lock", ["+a", "+b"]) + "\n" + _file("aipr/main.py", ["+real"])
        result = filter_diff(diff)
        assert result.omitted == ["uv.lock"]
        assert "+a" not in result.text
        assert "diff --git a/uv.lock b/uv.lock" in result.text
        assert "omitted: generated or lock file" in result.text
        assert "+real" in result.text
        assert "uv.lock" in result.notes

    @pytest.mark.parametrize(
        "path",
        [
            "package-lock.json",
            "web/yarn.lock",
            "pnpm-lock.yaml",
            "poetry.lock",
            "Cargo.lock",
            "go.sum",
            "static/app.min.js",
            "dist/bundle.js",
            "node_modules/x/index.js",
            "assets/logo.png",
            "notebooks/a.ipynb",
        ],
    )
    def test_noise_patterns(self, path):
        """Noise patterns."""
        assert filter_diff(_file(path, ["+x"])).omitted == [path]

    @pytest.mark.parametrize(
        "path",
        [
            "aipr/main.py",
            "src/lock.py",
            "docs/build.md",
            "Makefile",
            "docs/build/index.md",
            "pkg/build/build.go",
            "cmd/dist/main.go",
            "lib/vendor/foo.rb",
            "tests/__snapshots__/a.snap",
            "assets/icon.svg",
        ],
    )
    def test_source_files_are_kept(self, path):
        """Source files are kept."""
        result = filter_diff(_file(path, ["+x"]))
        assert result.omitted == []
        assert "+x" in result.text

    def test_oversized_file_is_truncated(self):
        """Oversized file is truncated."""
        big = _file("data/generated.py", [f"+line {i}" for i in range(50)])
        result = filter_diff(big, max_file_lines=10)
        assert result.truncated == ["data/generated.py"]
        assert "+line 3" in result.text
        assert "+line 49" not in result.text
        assert "more diff lines truncated" in result.text

    def test_truncation_can_be_disabled(self):
        """Truncation can be disabled."""
        big = _file("x.py", [f"+line {i}" for i in range(50)])
        assert filter_diff(big, max_file_lines=0).truncated == []

    def test_preamble_and_empty_diff_survive(self):
        """Preamble and empty diff survive."""
        assert filter_diff("").text == ""
        assert filter_diff("junk header\n").text == "junk header"

    def test_quoted_and_unprefixed_headers_still_split(self):
        """Quoted paths and diff.noprefix headers are section boundaries."""
        diff = "\n".join(
            [
                "diff --git a/uv.lock b/uv.lock",
                "+lock",
                'diff --git "a/caf\\303\\251 x.py" "b/caf\\303\\251 x.py"',
                "+real code",
                "diff --git plain.py plain.py",
                "+also real",
            ]
        )
        result = filter_diff(diff)
        assert result.omitted == ["uv.lock"]
        assert "+real code" in result.text
        assert "+also real" in result.text
        assert "+lock" not in result.text

    def test_renames_and_binary_files_are_kept(self):
        """Rename-only and binary sections pass through untouched."""
        diff = "\n".join(
            [
                "diff --git a/old.py b/new.py",
                "similarity index 100%",
                "rename from old.py",
                "rename to new.py",
                "diff --git a/blob.bin b/blob.bin",
                "Binary files a/blob.bin and b/blob.bin differ",
            ]
        )
        result = filter_diff(diff)
        assert result.omitted == [] and result.truncated == []
        assert result.text == diff

    def test_notes_empty_when_nothing_removed(self):
        """Notes empty when nothing removed."""
        assert filter_diff(_file("a.py", ["+x"])).notes == ""


class TestBudget:
    """Token estimation and the input ceiling."""

    def test_estimate_is_monotonic(self):
        """Estimate is monotonic."""
        assert estimate_tokens("") == 1
        assert estimate_tokens("x" * 350) > estimate_tokens("x" * 35)

    def test_over_budget_raises_before_any_call(self):
        """Over budget raises before any call."""
        with pytest.raises(ValueError, match="Nothing was sent"):
            check_input_budget("x" * 10_000, 100)

    def test_zero_disables_check(self):
        """Zero disables check."""
        assert check_input_budget("x" * 10_000, 0) > 100

    def test_under_budget_returns_estimate(self):
        """Under budget returns estimate."""
        assert check_input_budget("x" * 35, 100) == 11

    def test_resolve_prefers_flag_then_env_then_default(self):
        """Resolve prefers flag then env then default."""
        assert resolve_max_input_tokens(5) == 5
        with patch.dict("os.environ", {"AIPR_MAX_INPUT_TOKENS": "77"}):
            assert resolve_max_input_tokens(None) == 77
            assert resolve_max_input_tokens(0) == 0
        with patch.dict("os.environ", {}, clear=True):
            assert resolve_max_input_tokens(None) == DEFAULT_MAX_INPUT_TOKENS

    def test_resolve_rejects_bad_env(self):
        """Resolve rejects bad env."""
        with patch.dict("os.environ", {"AIPR_MAX_INPUT_TOKENS": "lots"}):
            with pytest.raises(ValueError, match="AIPR_MAX_INPUT_TOKENS"):
                resolve_max_input_tokens(None)
