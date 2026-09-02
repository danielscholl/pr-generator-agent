"""Pre-flight shaping of git diffs before they are sent to a model.

Two concerns live here: dropping content that costs tokens without
improving the generated text (lock files, minified bundles, huge single-file
rewrites), and estimating the input size so a runaway diff is refused
before it is billed.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Rough characters-per-token ratio for code and diffs across current models.
_CHARS_PER_TOKEN = 3.5

# Default ceiling on estimated input tokens. Override with --max-input-tokens
# or AIPR_MAX_INPUT_TOKENS; 0 disables the check.
DEFAULT_MAX_INPUT_TOKENS = 100_000

# Per-file line ceiling; anything longer is cut with a marker so one generated
# file cannot crowd out the rest of the change.
DEFAULT_MAX_FILE_LINES = 1500

# Files whose diffs are noise for a commit message or PR description. The
# model still sees them by name in the file summary and in the omission note.
NOISE_PATTERNS = [
    r"(^|/)(package-lock|yarn|pnpm-lock|bun)\.(json|lock|lockb|yaml)$",
    r"(^|/)(poetry|uv|Pipfile|Cargo|composer|Gemfile|flake|pubspec|packages)\.lock$",
    r"(^|/)go\.sum$",
    r"(^|/)mix\.lock$",
    r"\.min\.(js|css)$",
    r"\.(map|pb|pbtxt|onnx|parquet|pyc|whl|jar|zip|gz|tar|tgz)$",
    r"\.(png|jpe?g|gif|ico|webp|pdf|woff2?|ttf|eot)$",
    r"^(dist|build|vendor|node_modules|\.venv)/",
    r"(^|/)__pycache__/",
    r"\.ipynb$",
]
_NOISE_RE = re.compile("|".join(f"(?:{p})" for p in NOISE_PATTERNS), re.IGNORECASE)

_HEADER_PREFIX = "diff --git "
_HEADER_TOKEN_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|(\S+)')


def _header_path(line: str) -> Optional[str]:
    """Return the destination path from a ``diff --git`` header line.

    Handles git's quoting of paths with spaces or non-ASCII characters and
    the ``diff.noprefix`` / ``diff.mnemonicPrefix`` configurations, where the
    ``a/`` and ``b/`` prefixes are absent or different.
    """
    tokens = [q or bare for q, bare in _HEADER_TOKEN_RE.findall(line[len(_HEADER_PREFIX) :])]
    if len(tokens) < 2:
        return None
    src, dst = tokens[0], tokens[-1]
    if len(src) > 2 and len(dst) > 2 and src[1] == "/" and dst[1] == "/":
        return dst[2:]
    return dst


@dataclass
class FilteredDiff:
    """A diff after noise removal, with a record of what was dropped."""

    text: str
    omitted: List[str] = field(default_factory=list)
    truncated: List[str] = field(default_factory=list)
    original_chars: int = 0

    @property
    def notes(self) -> str:
        """Human-readable summary of what was removed, or an empty string."""
        parts = []
        if self.omitted:
            parts.append("omitted generated/lock files: " + ", ".join(self.omitted))
        if self.truncated:
            parts.append("truncated oversized files: " + ", ".join(self.truncated))
        return "; ".join(parts)


def estimate_tokens(text: str) -> int:
    """Estimate the token count of ``text`` for budgeting purposes.

    A character ratio is used rather than a tokenizer call so the check is
    free and provider-agnostic; it is deliberately a little pessimistic.
    """
    return int(len(text) / _CHARS_PER_TOKEN) + 1


def _split_files(diff: str) -> List[Tuple[Optional[str], List[str]]]:
    """Split a unified diff into (path, lines) sections.

    Text before the first ``diff --git`` header is kept with path ``None``.
    """
    sections: List[Tuple[Optional[str], List[str]]] = []
    current_path: Optional[str] = None
    current: List[str] = []
    for line in diff.splitlines():
        if line.startswith(_HEADER_PREFIX):
            if current:
                sections.append((current_path, current))
            current_path = _header_path(line)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append((current_path, current))
    return sections


def filter_diff(diff: str, max_file_lines: int = DEFAULT_MAX_FILE_LINES) -> FilteredDiff:
    """Drop noise files and cut oversized files from a unified diff.

    Args:
        diff: Raw unified diff text from git.
        max_file_lines: Per-file line ceiling; 0 disables truncation.

    Returns:
        A ``FilteredDiff`` whose ``text`` replaces each removed file with a
        one-line marker so the model still knows the file changed.
    """
    result = FilteredDiff(text="", original_chars=len(diff))
    kept: List[str] = []
    for path, lines in _split_files(diff):
        if path is not None and _NOISE_RE.search(path):
            result.omitted.append(path)
            kept.append(lines[0])
            kept.append(f"[{len(lines) - 1} diff lines omitted: generated or lock file]")
            continue
        if path is not None and max_file_lines and len(lines) > max_file_lines:
            result.truncated.append(path)
            kept.extend(lines[:max_file_lines])
            kept.append(f"[{len(lines) - max_file_lines} more diff lines truncated]")
            continue
        kept.extend(lines)
    result.text = "\n".join(kept)
    return result


def resolve_max_input_tokens(flag_value: Optional[int]) -> int:
    """Pick the input-token ceiling from the CLI flag, then the environment."""
    if flag_value is not None:
        return flag_value
    env_value = os.getenv("AIPR_MAX_INPUT_TOKENS")
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            raise ValueError(f"AIPR_MAX_INPUT_TOKENS must be an integer, got {env_value!r}")
    return DEFAULT_MAX_INPUT_TOKENS


def check_input_budget(text: str, max_tokens: int) -> int:
    """Return the estimated token count, or raise if it exceeds ``max_tokens``.

    Raises:
        ValueError: When the estimate is over the ceiling. The message tells
            the user how to shrink the input or raise the cap, and nothing has
            been sent to a provider yet.
    """
    estimate = estimate_tokens(text)
    if max_tokens and estimate > max_tokens:
        raise ValueError(
            f"Diff is about {estimate:,} tokens, over the {max_tokens:,} token limit. "
            "Nothing was sent. Stage fewer files, split the change, or raise the cap "
            "with --max-input-tokens N (0 disables) or AIPR_MAX_INPUT_TOKENS."
        )
    return estimate
