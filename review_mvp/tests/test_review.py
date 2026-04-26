from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import review


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(__file__).resolve().parent / "workspace"
        self.temp_dir.mkdir(exist_ok=True)
        self.target = self.temp_dir / "sample_under_review.py"

    def tearDown(self) -> None:
        if self.target.exists():
            self.target.unlink()

    def _write_temp_file(self, body: str) -> Path:
        self.target.write_text(textwrap.dedent(body), encoding="utf-8")
        return self.target

    def test_detects_security_and_safety_findings(self) -> None:
        target = self._write_temp_file(
            """
            import subprocess

            password = "plain-text"

            def run(items=[]):
                print(f"debug password={password}")
                subprocess.run("echo hi", shell=True)
                return items[0]
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)
        rules = {finding.rule for finding in result.findings}

        self.assertIn("hardcoded-secret", rules)
        self.assertIn("sensitive-data-logging", rules)
        self.assertIn("subprocess-shell-true", rules)
        self.assertIn("mutable-default-argument", rules)
        self.assertIn("missing-bounds-check", rules)

    def test_markdown_render_groups_findings(self) -> None:
        target = self._write_temp_file(
            """
            token = "123"
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)
        rendered = review.render_markdown(result)

        self.assertIn("# Python 리뷰", rendered)
        self.assertIn("## 높음", rendered)
        self.assertIn("hardcoded-secret", rendered)

    def test_clean_file_passes(self) -> None:
        target = self._write_temp_file(
            """
            def first_item(items: list[str]) -> str | None:
                if items:
                    return items[0]
                return None
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)
        self.assertEqual([], result.findings)
        self.assertFalse(review.should_fail(result, "high"))

    def test_fail_fast_bounds_guard_suppresses_index_warning(self) -> None:
        target = self._write_temp_file(
            """
            def eighth_cell(cells):
                if len(cells) < 8:
                    return None
                return cells[0], cells[6], cells[7]
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("missing-bounds-check", {finding.rule for finding in result.findings})

    def test_non_exiting_length_check_still_reports_index_warning(self) -> None:
        target = self._write_temp_file(
            """
            def first_item(items):
                if len(items) < 1:
                    note = "too short"
                return items[0]
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("missing-bounds-check", {finding.rule for finding in result.findings})

    def test_test_file_noise_is_suppressed_but_security_still_reports(self) -> None:
        target = self.temp_dir / "test_generated_contract.py"
        target.write_text(
            textwrap.dedent(
                """
                token = "plain-text"

                def test_contract(rows):
                    assert rows[0] == "ok"
                """
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: target.unlink(missing_ok=True))

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)
        rules = {finding.rule for finding in result.findings}

        self.assertIn("hardcoded-secret", rules)
        self.assertNotIn("missing-bounds-check", rules)

    def test_fail_on_thresholds_follow_severity_order(self) -> None:
        result = review.ReviewResult(
            findings=[
                review.build_finding(
                    self.target,
                    1,
                    "mutable-default-argument",
                    name="run",
                )
            ],
            scanned_files=[str(self.target)],
        )

        self.assertFalse(review.should_fail(result, "high"))
        self.assertTrue(review.should_fail(result, "medium"))
        self.assertTrue(review.should_fail(result, "low"))

    def test_filter_findings_applies_severity_and_count_budget(self) -> None:
        result = review.ReviewResult(
            findings=[
                review.build_finding(self.target, 1, "hardcoded-secret", target="token"),
                review.build_finding(self.target, 2, "mutable-default-argument", name="run"),
                review.build_finding(self.target, 3, "debug-log"),
            ],
            scanned_files=[str(self.target)],
        )

        filtered = review.filter_findings(result, min_severity="medium", max_findings=1)

        self.assertEqual(["hardcoded-secret"], [finding.rule for finding in filtered.findings])
        self.assertEqual([str(self.target)], filtered.scanned_files)

    def test_detects_sensitive_attribute_and_subscript_logging(self) -> None:
        target = self._write_temp_file(
            """
            def run(user, config):
                print(user.password)
                print(config["token"])
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)
        rules = [finding.rule for finding in result.findings]
        self.assertEqual(2, rules.count("sensitive-data-logging"))

    def test_unreadable_file_becomes_finding(self) -> None:
        self.target.write_bytes(b"\x80not-utf8")

        result = review.run_review([self.target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertEqual(1, len(result.findings))
        self.assertEqual("file-decode-error", result.findings[0].rule)
        self.assertTrue(review.should_fail(result, "high"))

    def test_default_excludes_sample_dirs_but_explicit_file_can_be_scanned(self) -> None:
        samples_dir = self.temp_dir / "samples"
        self.addCleanup(lambda: shutil.rmtree(samples_dir, ignore_errors=True))
        samples_dir.mkdir(exist_ok=True)
        sample_file = samples_dir / "vulnerable.py"
        sample_file.write_text('token = "plain-text"\n', encoding="utf-8")

        directory_result = review.run_review([self.temp_dir], review.DEFAULT_EXCLUDE_DIRS)
        explicit_file_result = review.run_review([sample_file], review.DEFAULT_EXCLUDE_DIRS)

        self.assertEqual([], directory_result.findings)
        self.assertEqual(["hardcoded-secret"], [finding.rule for finding in explicit_file_result.findings])

    def test_default_excludes_worktree_dirs_but_explicit_file_can_be_scanned(self) -> None:
        worktrees_dir = self.temp_dir / "worktrees"
        self.addCleanup(lambda: shutil.rmtree(worktrees_dir, ignore_errors=True))
        nested_dir = worktrees_dir / "review_branch"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_file = nested_dir / "vulnerable.py"
        nested_file.write_text('token = "plain-text"\n', encoding="utf-8")

        directory_result = review.run_review([self.temp_dir], review.DEFAULT_EXCLUDE_DIRS)
        explicit_directory_result = review.run_review([nested_dir], review.DEFAULT_EXCLUDE_DIRS)
        explicit_file_result = review.run_review([nested_file], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn(str(nested_file), directory_result.scanned_files)
        self.assertEqual([], directory_result.findings)
        self.assertEqual(["hardcoded-secret"], [finding.rule for finding in explicit_directory_result.findings])
        self.assertEqual(["hardcoded-secret"], [finding.rule for finding in explicit_file_result.findings])

    def test_explicit_internal_api_allows_conversion_and_adapter_hooks(self) -> None:
        target = self._write_temp_file(
            """
            from dataclasses import dataclass
            from html.parser import HTMLParser

            @dataclass
            class Contract:
                value: str

                @classmethod
                def from_mapping(cls, values):
                    return cls(str(values.get("value", "")))

                def to_dict(self):
                    return {"value": self.value}

            class SourceAdapter:
                def build_search_url(self, query):
                    return f"https://example.test?q={query}"

                def fetch_search(self, query):
                    return self.build_search_url(query)

                def parse_response(self, payload):
                    return [payload]

            class AlertParser(HTMLParser):
                def handle_data(self, data):
                    self.last_data = data

            class CsvProvider:
                def load(self):
                    return []

            class StockScorer:
                def score(self, rows, context):
                    raise NotImplementedError()
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_allows_symbol_policy_leading_zero_hook(self) -> None:
        target = self._write_temp_file(
            """
            class SymbolPolicy:
                def is_valid(self, value):
                    return True

                def normalize(self, value):
                    return str(value)

                def leading_zero_loss_candidates(self, values):
                    return int(values.notna().sum())
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_allows_public_utility_hooks(self) -> None:
        target = self._write_temp_file(
            """
            class RequestCache:
                def get(self, key):
                    return None

                def store(self, key, value):
                    return None

                def cache_key(self, request):
                    return str(request)

            class PaperDedupeIndex:
                def add(self, paper):
                    return None

                def rebuild(self):
                    return None

                def find_duplicate_index(self, paper):
                    return None

            class SourceRateLimiter:
                def wait_before_request(self):
                    return None

                def mark_request_complete(self):
                    return None
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_allows_gui_callback_handlers(self) -> None:
        target = self._write_temp_file(
            """
            import tkinter as tk
            from tkinter import messagebox, ttk

            class Top5App:
                def __init__(self):
                    self.root = tk.Tk()
                    self.status_var = tk.StringVar()
                    self.run_button = ttk.Button(command=self.run_update)
                    ttk.Button(command=self.open_selected_chart)
                    self.root.after(500, self.run_update)

                def set_status(self, text):
                    self.status_var.set(text)
                    self.root.update_idletasks()

                def run_update(self):
                    self.set_status("running")
                    messagebox.showwarning("title", "body")

                def run_legacy_update(self):
                    self.run_button.state(["disabled"])
                    self.set_status("running")

                def run_evaluation(self):
                    self.run_button.state(["disabled"])

                def open_selected_chart(self):
                    self.set_status("opening")
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_plain_public_method(self) -> None:
        target = self._write_temp_file(
            """
            class Helper:
                def process(self):
                    return "internal"
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_plain_leading_zero_method(self) -> None:
        target = self._write_temp_file(
            """
            class Helper:
                def leading_zero_loss_candidates(self, values):
                    return int(values.notna().sum())
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_symbol_policy_random_public_method(self) -> None:
        target = self._write_temp_file(
            """
            class SymbolPolicy:
                def random_public_method(self):
                    return "internal"
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_plain_utility_names(self) -> None:
        target = self._write_temp_file(
            """
            class Helper:
                def get(self, key):
                    return None

            class RequestCache:
                def process(self):
                    return None
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_non_callback_gui_method(self) -> None:
        target = self._write_temp_file(
            """
            import tkinter as tk

            class Top5App:
                def __init__(self):
                    self.root = tk.Tk()

                def process(self):
                    return "internal"
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_explicit_internal_api_still_reports_gui_named_method_without_gui_context(self) -> None:
        target = self._write_temp_file(
            """
            class JobApp:
                def run_update(self):
                    return "internal"
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("explicit-internal-api", {finding.rule for finding in result.findings})

    def test_prefer_comprehension_reports_single_local_append_loop(self) -> None:
        target = self._write_temp_file(
            """
            def names_for(users):
                names = []
                for user in users:
                    names.append(user.name)
                return names
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("prefer-comprehension", {finding.rule for finding in result.findings})

    def test_prefer_comprehension_ignores_structured_accumulators(self) -> None:
        target = self._write_temp_file(
            """
            def render_lines(items):
                lines = []
                lines.append("header")
                for item in items:
                    lines.append(str(item))
                return "\\n".join(lines)

            class Collector:
                def collect(self, items):
                    for item in items:
                        self.items.append(item)
            """
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("prefer-comprehension", {finding.rule for finding in result.findings})

    def test_single_responsibility_ignores_long_linear_function(self) -> None:
        assignments = "\n".join(f"    value_{index} = {index}" for index in range(60))
        target = self._write_temp_file(
            "def build_values():\n"
            f"{assignments}\n"
            "    return value_59\n"
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertNotIn("single-responsibility", {finding.rule for finding in result.findings})

    def test_single_responsibility_reports_long_complex_function(self) -> None:
        padding = "\n".join("    total += 0" for _ in range(45))
        target = self._write_temp_file(
            "def classify_values(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        if item > 0:\n"
            "            total += item\n"
            "        if item % 2:\n"
            "            total += 1\n"
            "        if item % 3:\n"
            "            total += 1\n"
            "        if item % 5:\n"
            "            total += 1\n"
            "        if item % 7:\n"
            "            total += 1\n"
            "        if item % 11:\n"
            "            total += 1\n"
            "        if item % 13:\n"
            "            total += 1\n"
            f"{padding}\n"
            "    return total\n"
        )

        result = review.run_review([target], review.DEFAULT_EXCLUDE_DIRS)

        self.assertIn("single-responsibility", {finding.rule for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
