"""Tests for comment formatting utilities."""

import pytest
from app.models import Finding
from app.utils.formatters import (
    format_inline_body,
    format_summary_comment,
    rank_findings,
    deduplicate_findings,
)


def make_finding(**kwargs) -> Finding:
    defaults = dict(
        file="app/main.py",
        line=10,
        severity="medium",
        category="bug",
        title="Test finding",
        description="Something is wrong here.",
        suggestion="Fix it like this.",
        confidence=0.9,
    )
    return Finding(**{**defaults, **kwargs})


def test_format_inline_body_contains_title():
    f = make_finding(title="Null dereference", severity="critical")
    body = format_inline_body(f)
    assert "Null dereference" in body
    assert "🔴" in body
    assert "BUG" in body


def test_format_summary_counts():
    findings = [
        make_finding(severity="critical"),
        make_finding(severity="high"),
        make_finding(severity="high"),
        make_finding(severity="low"),
    ]
    summary = format_summary_comment(findings, "owner/repo", 42)
    assert "Critical | 1" in summary
    assert "High     | 2" in summary
    assert "Low      | 1" in summary


def test_rank_findings_order():
    findings = [
        make_finding(severity="low"),
        make_finding(severity="critical"),
        make_finding(severity="medium"),
    ]
    ranked = rank_findings(findings)
    assert ranked[0].severity == "critical"
    assert ranked[-1].severity == "low"


def test_deduplicate_removes_same_location():
    findings = [
        make_finding(file="a.py", line=5, category="bug"),
        make_finding(file="a.py", line=5, category="bug"),   # duplicate
        make_finding(file="a.py", line=6, category="bug"),   # different line
    ]
    unique = deduplicate_findings(findings)
    assert len(unique) == 2


def test_deduplicate_keeps_different_categories():
    findings = [
        make_finding(file="a.py", line=5, category="bug"),
        make_finding(file="a.py", line=5, category="security"),  # same loc, diff category
    ]
    unique = deduplicate_findings(findings)
    assert len(unique) == 2
