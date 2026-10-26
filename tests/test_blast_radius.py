"""Tests for workspace blast radius analysis and downstream reference scanning."""

from pathlib import Path

from ci_code_reviewer.context.blast_radius import (
    extract_modified_symbols,
    find_downstream_references,
    format_blast_radius_context,
)


def test_extract_modified_symbols_python() -> None:
    diff_text = """
--- a/src/utils/helpers.py
+++ b/src/utils/helpers.py
@@ -5,3 +5,3 @@
-def calculate_discount(price: float, rate: float) -> float:
+def calculate_discount(price: float, rate: float, cap: float = 100.0) -> float:
     return price * rate
@@ -20,2 +20,4 @@
+class PaymentProcessor:
+    def process_transaction(self, amount: float) -> bool:
+        return True
"""
    symbols = extract_modified_symbols(diff_text)
    assert "calculate_discount" in symbols
    assert "PaymentProcessor" in symbols
    assert "process_transaction" in symbols


def test_extract_modified_symbols_typescript() -> None:
    diff_text = """
--- a/src/auth.ts
+++ b/src/auth.ts
@@ -1,4 +1,4 @@
-export function verifyJwt(token: string): boolean {
+export async function verifyJwt(token: string, audience: string): Promise<boolean> {
     return true;
 }
+export class AuthService {
"""
    symbols = extract_modified_symbols(diff_text)
    assert "verifyJwt" in symbols
    assert "AuthService" in symbols


def test_extract_modified_symbols_ignores_http_verbs_and_noise() -> None:
    diff_text = """
--- a/src/routes.ts
+++ b/src/routes.ts
@@ -1,6 +1,8 @@
+export async function POST(request: Request) {
+    return new Response("ok");
+}
+export async function GET(request: Request) {
+    return new Response("ok");
+}
+export async function handleUserUpdate(id: string) {
+    return id;
+}
"""
    symbols = extract_modified_symbols(diff_text)
    assert "POST" not in symbols
    assert "GET" not in symbols
    assert "handleUserUpdate" in symbols


def test_find_downstream_references(tmp_path: Path) -> None:
    # Setup simulated workspace
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    caller_file = src_dir / "billing.py"
    caller_file.write_text(
        "import math\n\ndef run_billing():\n    total = calculate_discount(100.0, 0.1)\n    return total\n",
        encoding="utf-8",
    )

    other_file = src_dir / "user.py"
    other_file.write_text("class User:\n    pass\n", encoding="utf-8")

    symbols = ["calculate_discount"]
    # Exclude the diff source file itself
    modified_files = ["src/utils/helpers.py"]

    refs = find_downstream_references(
        symbols=symbols,
        workspace_root=tmp_path,
        exclude_files=modified_files,
        ignore_patterns=["**/tests/**"],
    )

    assert "calculate_discount" in refs
    assert len(refs["calculate_discount"]) == 1
    ref_entry = refs["calculate_discount"][0]
    assert "billing.py" in ref_entry
    assert "calculate_discount(100.0, 0.1)" in ref_entry


def test_format_blast_radius_context() -> None:
    refs = {"calculate_discount": ["src/billing.py:4: total = calculate_discount(100.0, 0.1)"]}
    context = format_blast_radius_context(refs)
    assert "Downstream Workspace References & Blast Radius" in context
    assert "calculate_discount" in context
    assert "src/billing.py:4" in context

    empty_context = format_blast_radius_context({})
    assert empty_context == ""
