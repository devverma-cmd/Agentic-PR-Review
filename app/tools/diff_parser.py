"""Utilities for parsing unified diffs and building position maps."""

from __future__ import annotations
import re
from app.models import ChangedFile


def build_position_map(diff_text: str) -> dict[tuple[str, int], int]:
    """
    Parse a unified diff and return a map of (filename, new_line_no) -> diff_position.

    GitHub's Review API requires `position` (the line's offset within the diff),
    not the raw line number. This function builds that mapping.
    """
    position_map: dict[tuple[str, int], int] = {}
    current_file: str | None = None
    position = 0
    new_line = 0

    for raw_line in diff_text.splitlines():
        # New file header
        if raw_line.startswith("diff --git"):
            position = 0
            current_file = None
            continue

        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue

        if current_file is None:
            continue

        # Hunk header: @@ -old_start,old_count +new_start,new_count @@
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            new_line = int(hunk_match.group(1)) - 1
            position += 1
            continue

        if raw_line.startswith("-"):
            position += 1
            continue  # removed line — no new_line advance

        if raw_line.startswith("+"):
            new_line += 1
            position += 1
            position_map[(current_file, new_line)] = position
            continue

        if raw_line.startswith(" "):
            new_line += 1
            position += 1
            position_map[(current_file, new_line)] = position

    return position_map


def filter_files(
    files: list[ChangedFile],
    max_files: int = 20,
    skip_extensions: tuple[str, ...] = (
        ".lock", ".sum", ".min.js", ".min.css",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
        ".pdf", ".zip", ".tar", ".gz",
    ),
) -> list[ChangedFile]:
    """Filter out binary/generated files and cap total count."""
    reviewable = [
        f for f in files
        if not any(f.filename.endswith(ext) for ext in skip_extensions)
        and f.patch is not None
        and f.status != "removed"
    ]
    return reviewable[:max_files]


def build_diff_context(files: list[ChangedFile], max_chars: int = 40_000) -> str:
    """Concatenate file patches into a single context string for the LLM."""
    parts = []
    total = 0
    for f in files:
        if f.patch is None:
            continue
        header = f"### {f.filename} ({f.language or 'unknown'})\n"
        chunk = header + f.patch + "\n"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n".join(parts)
