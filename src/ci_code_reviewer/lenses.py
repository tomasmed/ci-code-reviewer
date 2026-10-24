"""Review lenses and sub-agent turn orchestration."""

import fnmatch
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ReviewLensConfig(BaseModel):
    """Configuration for a focused review lens (sub-agent turn)."""

    name: str = Field(
        description="Unique identifier for the review lens (e.g. 'adrs', 'data_access', 'security')."
    )
    description: str = Field(
        default="", description="Human-readable description of what this lens audits."
    )
    prompt: str = Field(description="Sub-agent prompt instructions for this review lens turn.")
    context_files: list[str] = Field(
        default_factory=list,
        description="File globs to read and inject as context for this lens (e.g. ['docs/adr/*.md']).",
    )
    file_patterns: list[str] = Field(
        default_factory=list,
        description="File globs in the diff that activate this lens (e.g. ['src/db/**', 'migrations/**']). If empty, runs on all diffs.",
    )
    blocking: bool = Field(
        default=True,
        description="Whether critical findings from this lens trigger REQUEST_CHANGES.",
    )
    enabled: bool = Field(default=True, description="Whether this lens is enabled.")


def get_default_lenses() -> list[ReviewLensConfig]:
    """Return the standard built-in review lenses."""
    return [
        ReviewLensConfig(
            name="architecture_adrs",
            description="Evaluates changes against in-repo ADRs and module boundaries.",
            prompt=(
                "You are an expert Software Architect sub-agent.\n"
                "Evaluate the git diff strictly through the lens of architectural integrity and in-repo ADRs.\n"
                "1. Cross-reference the changes with any provided Architecture Decision Records (ADRs).\n"
                "2. Verify module boundary separation (e.g., UI layer not calling database directly, domain models free of framework dependencies).\n"
                "3. Flag prohibited new external dependencies or architectural drift as critical blockers."
            ),
            context_files=[
                "docs/adr/*.md",
                "docs/architecture/*.md",
                "AGENTS.md",
            ],
            blocking=True,
            enabled=True,
        ),
        ReviewLensConfig(
            name="security_owasp",
            description="Audits diff for OWASP vulnerabilities, secret leaks, and insecure data handling.",
            prompt=(
                "You are an expert Application Security (AppSec) sub-agent.\n"
                "Audit the git diff strictly for security flaws:\n"
                "1. Check for hardcoded credentials, API keys, tokens, or private secrets.\n"
                "2. Look for injection risks (SQL, shell/command, XSS, SSRF).\n"
                "3. Ensure all user inputs and external webhook payloads are strictly validated.\n"
                "Flag any security vulnerabilities as critical blockers."
            ),
            blocking=True,
            enabled=True,
        ),
        ReviewLensConfig(
            name="test_integrity",
            description="Scrutinizes test modifications and enforces anti-lazy-assert discipline.",
            prompt=(
                "You are an expert QA and Test Integrity sub-agent.\n"
                "Audit the test code and test assertions in this git diff:\n"
                "1. Anti-Lazy-Assert: Flag hollow assertions (e.g. 'assert True', trivial identity checks, empty test stubs).\n"
                "2. Over-Mocking: Flag tests that mock everything and test no real logic.\n"
                "3. Missing Coverage: If business logic is modified or added without corresponding tests, flag it."
            ),
            file_patterns=["tests/**", "test/**", "**/*test*.py", "**/*spec*"],
            blocking=False,
            enabled=True,
        ),
    ]


def extract_touched_files(diff_text: str) -> list[str]:
    """Parse unified git diff to extract modified/added file paths."""
    files: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path and path != "/dev/null":
                files.add(path)
        elif line.startswith("--- a/") and not files:
            path = line[6:].strip()
            if path and path != "/dev/null":
                files.add(path)
    return sorted(files)


def diff_matches_lens(lens: ReviewLensConfig, touched_files: list[str]) -> bool:
    """Determine whether the touched files trigger this specific lens."""
    if not lens.enabled:
        return False
    if not lens.file_patterns:
        # If no patterns specified, lens applies to all diffs
        return True
    if not touched_files:
        return True

    for file_path in touched_files:
        normalized_path = file_path.replace("\\", "/")
        for pattern in lens.file_patterns:
            normalized_pattern = pattern.replace("\\", "/")
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True
            # Also check basename
            if fnmatch.fnmatch(Path(normalized_path).name, normalized_pattern):
                return True
    return False


def load_lens_context(lens: ReviewLensConfig, repo_root: Path | None = None) -> str:
    """Read in-repo context files specified in the lens configuration."""
    if not lens.context_files:
        return ""

    root = repo_root or Path.cwd()
    collected_texts: list[str] = []

    for pattern in lens.context_files:
        # Resolve pattern relative to repo_root
        matching_files = list(root.glob(pattern))
        for p in matching_files:
            if p.is_file():
                try:
                    rel_path = p.relative_to(root)
                    content = p.read_text(encoding="utf-8", errors="replace")
                    collected_texts.append(f"### File: {rel_path}\n```\n{content}\n```")
                except Exception:
                    continue

    if not collected_texts:
        return ""
    return "\n\n".join(collected_texts)


def discover_in_repo_lenses(repo_root: Path | None = None) -> list[ReviewLensConfig]:
    """Discover custom lens definitions from markdown files in .ci-reviewer/lenses/ or .reviewer/lenses/."""
    root = repo_root or Path.cwd()
    search_dirs = [
        root / ".ci-reviewer" / "lenses",
        root / ".reviewer" / "lenses",
        root / ".github" / "reviewer-lenses",
    ]

    discovered: list[ReviewLensConfig] = []
    for lens_dir in search_dirs:
        if not lens_dir.is_dir():
            continue
        for md_file in lens_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                lens = parse_lens_markdown(md_file.stem, content)
                if lens:
                    discovered.append(lens)
            except Exception:
                continue
    return discovered


def parse_lens_markdown(file_stem: str, raw_markdown: str) -> ReviewLensConfig | None:
    """Parse a markdown file with optional YAML frontmatter into a ReviewLensConfig."""
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_markdown, re.DOTALL)
    metadata: dict[str, Any] = {}
    body = raw_markdown

    if frontmatter_match:
        try:
            metadata = yaml.safe_load(frontmatter_match.group(1)) or {}
            body = frontmatter_match.group(2).strip()
        except Exception:
            pass

    name = metadata.get("name", file_stem)
    description = metadata.get("description", f"In-repo review lens: {name}")
    prompt = body.strip() or metadata.get("prompt", "")

    if not prompt:
        return None

    return ReviewLensConfig(
        name=name,
        description=description,
        prompt=prompt,
        context_files=metadata.get("context_files", []),
        file_patterns=metadata.get("file_patterns", []),
        blocking=metadata.get("blocking", True),
        enabled=metadata.get("enabled", True),
    )
