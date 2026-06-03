"""Tests for the diff position map builder."""

import pytest
from app.tools.diff_parser import build_position_map, filter_files, build_diff_context
from app.models import ChangedFile

SAMPLE_DIFF = """\
diff --git a/app/main.py b/app/main.py
index abc1234..def5678 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,6 +10,10 @@ def old_function():
     x = 1
     y = 2
     return x + y
+
+def new_function():
+    password = "hardcoded_secret"
+    return password
"""


def test_build_position_map_basic():
    pos_map = build_position_map(SAMPLE_DIFF)
    # Added lines should be in the map
    assert ("app/main.py", 13) in pos_map or ("app/main.py", 14) in pos_map


def test_build_position_map_empty():
    assert build_position_map("") == {}


def test_filter_files_removes_lockfiles():
    files = [
        ChangedFile(filename="app/main.py", patch="+ some code"),
        ChangedFile(filename="package-lock.json", patch="+ locked"),
        ChangedFile(filename="poetry.lock", patch="+ locked"),
        ChangedFile(filename="image.png", patch=None),
    ]
    result = filter_files(files)
    assert len(result) == 1
    assert result[0].filename == "app/main.py"


def test_filter_files_respects_max():
    files = [
        ChangedFile(filename=f"file{i}.py", patch="+ code")
        for i in range(30)
    ]
    result = filter_files(files, max_files=5)
    assert len(result) == 5


def test_build_diff_context_truncates():
    files = [ChangedFile(filename="big.py", patch="x" * 50_000)]
    context = build_diff_context(files, max_chars=1000)
    assert len(context) <= 1100  # some overhead for header
