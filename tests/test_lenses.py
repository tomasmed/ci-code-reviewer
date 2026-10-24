"""Tests for review lenses and sub-agent turn orchestration."""

from pathlib import Path

from ci_code_reviewer.config import ReviewerConfig
from ci_code_reviewer.harness.native import NativeReviewHarness
from ci_code_reviewer.lenses import (
    ReviewLensConfig,
    diff_matches_lens,
    discover_in_repo_lenses,
    extract_touched_files,
    get_default_lenses,
    load_lens_context,
    parse_lens_markdown,
)
from ci_code_reviewer.models import Recommendation


def test_default_lenses_present() -> None:
    lenses = get_default_lenses()
    names = [lens.name for lens in lenses]
    assert "architecture_adrs" in names
    assert "security_owasp" in names
    assert "test_integrity" in names


def test_extract_touched_files_from_diff() -> None:
    diff = """--- a/src/db/queries.py
+++ b/src/db/queries.py
@@ -1 +1 @@
-old
+new
--- a/tests/test_db.py
+++ b/tests/test_db.py
@@ -1 +1 @@
-old_test
+new_test
"""
    touched = extract_touched_files(diff)
    assert "src/db/queries.py" in touched
    assert "tests/test_db.py" in touched


def test_diff_matches_lens_file_patterns() -> None:
    sql_lens = ReviewLensConfig(
        name="data_access",
        prompt="Audit database access",
        file_patterns=["src/db/**", "**/sql/**"],
    )

    # Matches DB path
    assert diff_matches_lens(sql_lens, ["src/db/users.py"]) is True
    # Does not match unrelated frontend path
    assert diff_matches_lens(sql_lens, ["src/components/Header.tsx"]) is False
    # Empty patterns apply to all files
    all_lens = ReviewLensConfig(name="general", prompt="General audit")
    assert diff_matches_lens(all_lens, ["src/any/file.py"]) is True


def test_parse_lens_markdown() -> None:
    raw_md = """---
name: custom_sp_lens
description: Enforce stored-procedure rules
file_patterns:
  - "src/db/**"
blocking: true
---
You are a Database Architecture sub-agent.
Ensure all database access is SP-driven.
"""
    lens = parse_lens_markdown("fallback_name", raw_md)
    assert lens is not None
    assert lens.name == "custom_sp_lens"
    assert lens.description == "Enforce stored-procedure rules"
    assert "src/db/**" in lens.file_patterns
    assert lens.blocking is True
    assert "SP-driven" in lens.prompt


def test_discover_in_repo_lenses(tmp_path: Path) -> None:
    lens_dir = tmp_path / ".ci-reviewer" / "lenses"
    lens_dir.mkdir(parents=True)
    custom_lens_file = lens_dir / "sp-rules.md"
    custom_lens_file.write_text(
        """---
name: sp_driven_rules
blocking: true
---
Ensure no inline SQL queries.
"""
    )
    discovered = discover_in_repo_lenses(tmp_path)
    assert len(discovered) == 1
    assert discovered[0].name == "sp_driven_rules"
    assert discovered[0].blocking is True


def test_load_lens_context(tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "0001-test.md").write_text("# Decision 1\nWe use stored procedures.")

    lens = ReviewLensConfig(
        name="adrs",
        prompt="Audit ADRs",
        context_files=["docs/adr/*.md"],
    )
    context = load_lens_context(lens, tmp_path)
    assert "Decision 1" in context
    assert "We use stored procedures" in context


def test_native_harness_multi_lens_turn_execution() -> None:
    config = ReviewerConfig(
        lenses=[
            ReviewLensConfig(
                name="data_access",
                prompt="Audit DB queries",
                file_patterns=["src/db/**"],
                blocking=True,
            ),
            ReviewLensConfig(
                name="test_integrity",
                prompt="Audit tests",
                file_patterns=["tests/**"],
                blocking=False,
            ),
        ]
    )

    diff = """--- a/src/db/repo.py
+++ b/src/db/repo.py
@@ -1 +1 @@
+SELECT * FROM users;
"""
    harness = NativeReviewHarness()
    # Runs offline fallback turn execution
    assessment = harness.review(diff, "Global context", config)
    assert assessment.recommendation in [Recommendation.APPROVE, Recommendation.COMMENT]
    assert "data_access" in assessment.lens_summaries
    # Test integrity lens was not triggered because diff didn't touch tests/
    assert "test_integrity" not in assessment.lens_summaries
