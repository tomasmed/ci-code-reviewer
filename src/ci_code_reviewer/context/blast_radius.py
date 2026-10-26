"""Workspace blast radius analysis and downstream reference scanner."""

import fnmatch
import os
import re
from pathlib import Path

# Common symbol declaration patterns across Python, TypeScript/JavaScript, Go, etc.
SYMBOL_PATTERNS = [
    re.compile(r"^[+-]\s*(?:export\s+)?(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^[+-]\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^[+-]\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(
        r"^[+-]\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\("
    ),
]

# Common noise or generic symbols to exclude from search
IGNORE_SYMBOLS = {
    "__init__",
    "__str__",
    "__repr__",
    "main",
    "test",
    "run",
    "setUp",
    "tearDown",
    # Common HTTP methods frequently exported in route handlers (e.g. Next.js App Router)
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "handler",
    "default",
}

DEFAULT_SCAN_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".cs",
}

DEFAULT_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".cursor",
}


def extract_modified_symbols(diff_text: str) -> list[str]:
    """Scan unified diff added/removed lines for modified function or class declarations."""
    discovered: list[str] = []
    seen: set[str] = set()

    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if not (line.startswith("+") or line.startswith("-")):
            continue

        for pattern in SYMBOL_PATTERNS:
            match = pattern.search(line)
            if match:
                symbol = match.group(1).strip()
                if symbol not in seen and symbol not in IGNORE_SYMBOLS and len(symbol) > 2:
                    seen.add(symbol)
                    discovered.append(symbol)
                break

    return discovered


def _should_ignore_path(path_str: str, ignore_patterns: list[str]) -> bool:
    normalized = path_str.replace("\\", "/")
    for pattern in ignore_patterns:
        norm_pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, norm_pattern):
            return True
        if fnmatch.fnmatch(Path(normalized).name, norm_pattern):
            return True
    return False


def find_downstream_references(
    symbols: list[str],
    workspace_root: Path,
    exclude_files: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
    max_refs_per_symbol: int = 10,
) -> dict[str, list[str]]:
    """Scan workspace files for calls or imports of the specified symbols.

    Excludes files modified in the diff itself and ignored directories.
    """
    if not symbols or not workspace_root.is_dir():
        return {}

    exclude_set = {f.replace("\\", "/").lstrip("./") for f in (exclude_files or [])}
    ignores = list(ignore_patterns or [])

    # Precompile regex for symbols
    compiled_symbols = {symbol: re.compile(rf"\b{re.escape(symbol)}\b") for symbol in symbols}

    references: dict[str, list[str]] = {s: [] for s in symbols}

    for root_dir, dirs, files in os.walk(workspace_root):
        # Prune ignored directory trees
        dirs[:] = [d for d in dirs if d not in DEFAULT_SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            file_path = Path(root_dir) / filename
            if file_path.suffix not in DEFAULT_SCAN_EXTENSIONS:
                continue

            try:
                rel_path = file_path.relative_to(workspace_root).as_posix()
            except ValueError:
                continue

            if rel_path in exclude_set:
                continue

            if _should_ignore_path(rel_path, ignores):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for symbol, regex in compiled_symbols.items():
                if len(references[symbol]) >= max_refs_per_symbol:
                    continue

                for line_idx, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        snippet = line.strip()
                        references[symbol].append(f"{rel_path}:{line_idx}: {snippet}")
                        if len(references[symbol]) >= max_refs_per_symbol:
                            break

    # Return only symbols that have references
    return {s: refs for s, refs in references.items() if refs}


def format_blast_radius_context(references: dict[str, list[str]]) -> str:
    """Format downstream callers and blast radius into Markdown context for lens turns."""
    if not references:
        return ""

    lines = [
        "### ⚠️ Downstream Workspace References & Blast Radius",
        "The following modified symbols are referenced across unchanged files in the repository:",
    ]

    for symbol, refs in sorted(references.items()):
        lines.append(f"- **`{symbol}`**:")
        for ref in refs:
            lines.append(f"  - `{ref}`")

    return "\n".join(lines)
