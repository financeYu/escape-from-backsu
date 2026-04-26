from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
import re
import sys
from typing import Iterable


SENSITIVE_NAME_PATTERN = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)

DEBUG_STRING_PATTERN = re.compile(r"(debug|tmp|todo|fixme)", re.IGNORECASE)

LOG_CALLS = {
    "print",
    "logging.debug",
    "logging.info",
    "logging.warning",
    "logging.error",
    "logger.debug",
    "logger.info",
    "logger.warning",
    "logger.error",
}

SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_LEVELS = (SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW)
SEVERITY_ORDER = {severity: index for index, severity in enumerate(SEVERITY_LEVELS)}
SEVERITY_LABELS = {
    SEVERITY_HIGH: "높음",
    SEVERITY_MEDIUM: "보통",
    SEVERITY_LOW: "낮음",
}
DEFAULT_EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "samples",
    "worktrees",
}
MAX_FUNCTION_LINES = 50
MAX_LINEAR_FUNCTION_LINES = 120
SINGLE_RESPONSIBILITY_COMPLEXITY = 8
BOUNDS_CHECK_LOOKBACK_LINES = 16
DYNAMIC_EXECUTION_CALLS = {"eval", "exec"}
EXTERNAL_INPUT_CALLS = {"input"}
SUBPROCESS_SHELL_CALLS = {"subprocess.run", "subprocess.Popen"}
REQUEST_CALLS = {"requests.get", "requests.post", "requests.put", "requests.delete"}
DEFAULT_PATHS = (".",)
OUTPUT_FORMATS = ("text", "markdown", "json")
DEFAULT_OUTPUT_FORMAT = "text"
FAIL_ON_CHOICES = ("none", "low", "medium", "high")
DEFAULT_FAIL_ON = "high"
FAIL_ON_SEVERITY = {
    "low": SEVERITY_LOW,
    "medium": SEVERITY_MEDIUM,
    "high": SEVERITY_HIGH,
}
MIN_SEVERITY_CHOICES = ("low", "medium", "high")
DEFAULT_MIN_SEVERITY = "low"
DEFAULT_MAX_FINDINGS = 0
NOISY_TEST_RULES = {
    "missing-bounds-check",
    "prefer-comprehension",
    "single-responsibility",
    "explicit-internal-api",
}
PUBLIC_CONVERSION_METHODS = {
    "as_dict",
    "from_dict",
    "from_json",
    "from_mapping",
    "from_toml_file",
    "to_dict",
    "to_json",
    "to_mapping",
    "to_record",
    "to_summary_dict",
}
PUBLIC_CONVERSION_SUFFIXES = (
    "_dict",
    "_frame",
    "_json",
    "_mapping",
    "_record",
    "_toml_file",
)
PUBLIC_HOOK_METHODS_BY_CLASS_SUFFIX = {
    "Provider": {"load"},
    "Scorer": {"score"},
    "Policy": {"is_valid", "normalize"},
    "Spec": {"is_valid", "normalize", "validate_size"},
}
SYMBOL_POLICY_HOOK_METHODS = {"leading_zero_loss_candidates"}
PUBLIC_UTILITY_METHODS_BY_CLASS_SUFFIX = {
    "Cache": {"cache_key", "get", "store"},
    "DedupeIndex": {"add", "find_duplicate_index", "rebuild"},
    "Deduper": {"add", "find_duplicate_index", "rebuild"},
    "RateLimiter": {"mark_request_complete", "wait_before_request"},
    "Throttle": {"mark_request_complete", "wait_before_request"},
}
PUBLIC_HOOK_PREFIXES_BY_CLASS_SUFFIX = {
    "Adapter": ("build_", "fetch_", "parse_", "request_", "validate_"),
    "Parser": ("handle_", "parse_"),
}
FRAMEWORK_OVERRIDE_METHODS_BY_BASE = {
    "HTMLParser": {"handle_data", "handle_endtag", "handle_starttag"},
}
PUBLIC_RESULT_METHODS = {"raise_for_errors"}
GUI_CONTAINER_CLASS_SUFFIXES = ("App", "Dialog", "Frame", "Panel", "View", "Viewer", "Window")
GUI_HANDLER_METHOD_PREFIXES = ("run_", "open_selected_")
GUI_HANDLER_METHODS = {"set_status"}
GUI_METHOD_SURFACE_ATTRS = {
    "after",
    "bind",
    "selection",
    "set_status",
    "state",
    "status_var",
    "update_idletasks",
}
GUI_METHOD_SURFACE_NAMES = {"filedialog", "messagebox"}


@dataclass(frozen=True)
class RuleDefinition:
    severity: str
    category: str
    message_template: str

    def _format_message(self, **context: object) -> str:
        return self.message_template.format(**context)


RULE_DEFINITIONS = {
    "missing-bounds-check": RuleDefinition(
        SEVERITY_MEDIUM,
        "safety",
        "`{variable}[{index}]` 인덱스 접근 전에 범위 확인이 보이지 않습니다.",
    ),
    "prefer-comprehension": RuleDefinition(
        SEVERITY_LOW,
        "style",
        "단순 `append()` 반복문입니다. 가독성이 좋아진다면 comprehension 또는 고차 함수를 우선 검토하세요.",
    ),
    "bare-except": RuleDefinition(
        SEVERITY_MEDIUM,
        "quality",
        "bare `except:`는 예상치 못한 오류를 숨길 수 있습니다. 구체적인 예외를 지정하세요.",
    ),
    "single-responsibility": RuleDefinition(
        SEVERITY_LOW,
        "quality",
        "함수 `{name}`가 {line_span}줄입니다. 단일 책임 원칙을 벗어나지 않는지 확인하세요.",
    ),
    "mutable-default-argument": RuleDefinition(
        SEVERITY_MEDIUM,
        "safety",
        "함수 `{name}`가 mutable default argument를 사용합니다.",
    ),
    "explicit-internal-api": RuleDefinition(
        SEVERITY_LOW,
        "style",
        "`{name}`는 내부 구현처럼 보입니다. 공개 API가 아니라면 `_` 접두어를 고려하세요.",
    ),
    "hardcoded-secret": RuleDefinition(
        SEVERITY_HIGH,
        "security",
        "`{target}`에 하드코딩된 비밀값이 포함된 것으로 보입니다. 환경변수나 비밀 관리 도구를 사용하세요.",
    ),
    "unsafe-dynamic-execution": RuleDefinition(
        SEVERITY_HIGH,
        "safety",
        "`{call}` 사용은 피하거나 엄격히 제한된 환경에서만 사용해야 합니다.",
    ),
    "debug-log": RuleDefinition(
        SEVERITY_LOW,
        "quality",
        "디버그성 print/log가 보입니다. 운영 코드에 필요하지 않다면 제거하세요.",
    ),
    "sensitive-data-logging": RuleDefinition(
        SEVERITY_HIGH,
        "security",
        "민감한 정보가 출력되거나 로그에 기록되는 것으로 보입니다.",
    ),
    "raw-input-validation": RuleDefinition(
        SEVERITY_MEDIUM,
        "safety",
        "외부 입력을 직접 읽고 있습니다. 사용 전에 검증과 정제가 필요합니다.",
    ),
    "subprocess-shell-true": RuleDefinition(
        SEVERITY_HIGH,
        "security",
        "`subprocess`에서 `shell=True` 사용이 보입니다. 입력이 완전히 신뢰되고 적절히 이스케이프된 경우가 아니라면 피하세요.",
    ),
    "tls-verification-disabled": RuleDefinition(
        SEVERITY_HIGH,
        "security",
        "TLS 인증서 검증이 비활성화되어 있습니다.",
    ),
    "syntax-error": RuleDefinition(
        SEVERITY_HIGH,
        "quality",
        "파일을 구문 분석할 수 없습니다: {detail}",
    ),
    "file-decode-error": RuleDefinition(
        SEVERITY_HIGH,
        "quality",
        "파일을 UTF-8로 읽을 수 없습니다: {detail}",
    ),
    "file-read-error": RuleDefinition(
        SEVERITY_HIGH,
        "quality",
        "파일을 읽는 중 오류가 발생했습니다: {detail}",
    ),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    severity: str
    category: str
    rule: str
    message: str


def build_finding(path: Path, line: int, rule: str, **message_context: object) -> Finding:
    definition = RULE_DEFINITIONS[rule]
    return Finding(
        path=str(path),
        line=line,
        severity=definition.severity,
        category=definition.category,
        rule=rule,
        message=definition._format_message(**message_context),
    )


@dataclass(frozen=True)
class ReviewResult:
    findings: list[Finding]
    scanned_files: list[str]

    @property
    def high_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_LOW)


class PythonReviewVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_lines: list[str]) -> None:
        self.path = path
        self.source_lines = source_lines
        self.findings: list[Finding] = []
        self.parents: dict[ast.AST, ast.AST] = {}

    def visit(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            self.parents[child] = node
        super().visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_hardcoded_secret(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._check_hardcoded_secret(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        full_name = self._call_name(node.func)
        self._check_dynamic_execution(node, full_name)
        self._check_logging(node, full_name)
        self._check_external_input(node, full_name)
        self._check_subprocess_usage(node, full_name)
        self._check_requests_usage(node, full_name)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        index = node.slice
        if isinstance(index, ast.Constant) and isinstance(index.value, int):
            if isinstance(node.value, ast.Name) and not self._has_nearby_bounds_check(
                node.value.id, node.lineno, index.value
            ):
                self._add(
                    node.lineno,
                    "missing-bounds-check",
                    variable=node.value.id,
                    index=index.value,
                )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        if self._is_prefer_comprehension_candidate(node):
            self._add(
                node.lineno,
                "prefer-comprehension",
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(
                node.lineno,
                "bare-except",
            )
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        line_span = (node.end_lineno or node.lineno) - node.lineno + 1
        if self._is_single_responsibility_candidate(node, line_span):
            self._add(
                node.lineno,
                "single-responsibility",
                name=node.name,
                line_span=line_span,
            )

        if self._has_mutable_default_argument(node):
            self._add(
                node.lineno,
                "mutable-default-argument",
                name=node.name,
            )

        if (
            not node.name.startswith("_")
            and not node.name.startswith("visit_")
            and node.name != "visit"
            and not node.name.startswith("test_")
            and not self._has_property_decorator(node)
            and not self._is_testcase_method(node)
            and self._is_nested_or_method(node)
            and not self._is_intended_public_api(node)
        ):
            self._add(
                node.lineno,
                "explicit-internal-api",
                name=node.name,
            )

        self.generic_visit(node)

    def _check_hardcoded_secret(self, target: ast.expr, value: ast.expr, line: int) -> None:
        if not isinstance(target, ast.Name):
            return
        if not SENSITIVE_NAME_PATTERN.search(target.id):
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            self._add(
                line,
                "hardcoded-secret",
                target=target.id,
            )

    def _check_dynamic_execution(self, node: ast.Call, full_name: str) -> None:
        if full_name in DYNAMIC_EXECUTION_CALLS:
            self._add(
                node.lineno,
                "unsafe-dynamic-execution",
                call=full_name,
            )

    def _check_logging(self, node: ast.Call, full_name: str) -> None:
        if full_name not in LOG_CALLS:
            return
        if self._is_debug_log(node):
            self._add(
                node.lineno,
                "debug-log",
            )
        for arg in node.args:
            if self._contains_sensitive_reference(arg):
                self._add(
                    node.lineno,
                    "sensitive-data-logging",
                )

    def _check_external_input(self, node: ast.Call, full_name: str) -> None:
        if full_name in EXTERNAL_INPUT_CALLS:
            self._add(
                node.lineno,
                "raw-input-validation",
            )

    def _check_subprocess_usage(self, node: ast.Call, full_name: str) -> None:
        if full_name in SUBPROCESS_SHELL_CALLS and self._has_shell_true(node):
            self._add(
                node.lineno,
                "subprocess-shell-true",
            )

    def _check_requests_usage(self, node: ast.Call, full_name: str) -> None:
        if full_name in REQUEST_CALLS:
            if self._has_keyword_bool(node, "verify", False):
                self._add(
                    node.lineno,
                    "tls-verification-disabled",
                )

    def _contains_sensitive_reference(self, node: ast.AST) -> bool:
        return any(self._is_sensitive_reference(child) for child in ast.walk(node))

    def _is_sensitive_reference(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return bool(SENSITIVE_NAME_PATTERN.search(node.id))
        if isinstance(node, ast.Attribute):
            return bool(SENSITIVE_NAME_PATTERN.search(node.attr))
        if isinstance(node, ast.Subscript):
            return self._subscript_key_is_sensitive(node.slice)
        return False

    def _subscript_key_is_sensitive(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return bool(SENSITIVE_NAME_PATTERN.search(node.value))
        return False

    def _has_nearby_bounds_check(self, variable: str, line_no: int, index: int) -> bool:
        window_start = max(0, line_no - BOUNDS_CHECK_LOOKBACK_LINES)
        context = "\n".join(self.source_lines[window_start:line_no])
        patterns = [
            rf"len\(\s*{re.escape(variable)}\s*\)\s*>\s*{index}",
            rf"len\(\s*{re.escape(variable)}\s*\)\s*>=\s*{index + 1}",
            rf"if\s+{re.escape(variable)}\s+and",
            rf"assert\s+{re.escape(variable)}\s*,",
            rf"assert\s+len\(\s*{re.escape(variable)}\s*\)\s*>\s*{index}",
            rf"assert\s+len\(\s*{re.escape(variable)}\s*\)\s*>=\s*{index + 1}",
        ]
        if index == 0:
            patterns.append(rf"if\s+{re.escape(variable)}\s*:")
            patterns.append(rf"assert\s+{re.escape(variable)}\s*$")
        if any(re.search(pattern, context) for pattern in patterns):
            return True
        return self._has_fail_fast_bounds_guard(variable, line_no, index)

    def _has_fail_fast_bounds_guard(self, variable: str, line_no: int, index: int) -> bool:
        start = max(0, line_no - BOUNDS_CHECK_LOOKBACK_LINES - 1)
        stop = min(line_no - 1, len(self.source_lines))
        for line_index in range(start, stop):
            line = self.source_lines[line_index]
            match = re.match(r"^(\s*)if\s+(.+):\s*$", line)
            if not match:
                continue
            if not self._condition_proves_min_length(match.group(2), variable, index):
                continue
            if self._guard_body_exits(line_index, len(match.group(1)), stop):
                return True
        return False

    def _condition_proves_min_length(self, condition: str, variable: str, index: int) -> bool:
        escaped = re.escape(variable)
        less_than = re.search(rf"len\(\s*{escaped}\s*\)\s*<\s*(\d+)", condition)
        if less_than and int(less_than.group(1)) > index:
            return True

        less_than_or_equal = re.search(rf"len\(\s*{escaped}\s*\)\s*<=\s*(\d+)", condition)
        if less_than_or_equal and int(less_than_or_equal.group(1)) >= index:
            return True

        equals_zero = re.search(rf"len\(\s*{escaped}\s*\)\s*==\s*0", condition)
        if equals_zero and index == 0:
            return True

        return bool(index == 0 and re.search(rf"not\s+{escaped}\b", condition))

    def _guard_body_exits(self, guard_line_index: int, guard_indent: int, stop: int) -> bool:
        for line in self.source_lines[guard_line_index + 1 : stop]:
            stripped = line.strip()
            if not stripped:
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= guard_indent:
                return False
            if stripped.startswith(("return", "continue", "raise", "break")):
                return True
        return False

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            root = self._call_name(node.value)
            return f"{root}.{node.attr}" if root else node.attr
        if isinstance(node, ast.Subscript):
            return self._call_name(node.value)
        return ""

    def _has_shell_true(self, node: ast.Call) -> bool:
        return self._has_keyword_bool(node, "shell", True)

    def _has_keyword_bool(self, node: ast.Call, keyword: str, expected: bool) -> bool:
        for item in node.keywords:
            if item.arg == keyword and isinstance(item.value, ast.Constant) and item.value.value is expected:
                return True
        return False

    def _is_debug_log(self, node: ast.Call) -> bool:
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if DEBUG_STRING_PATTERN.search(arg.value):
                    return True
        return False

    def _has_mutable_default_argument(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        mutable_nodes = (ast.List, ast.Dict, ast.Set)
        defaults = list(node.args.defaults) + list(node.args.kw_defaults)
        return any(isinstance(default, mutable_nodes) for default in defaults if default is not None)

    def _is_single_responsibility_candidate(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        line_span: int,
    ) -> bool:
        if line_span <= MAX_FUNCTION_LINES:
            return False
        if line_span >= MAX_LINEAR_FUNCTION_LINES:
            return True
        return self._function_complexity(node) >= SINGLE_RESPONSIBILITY_COMPLEXITY

    def _function_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        score = 1
        for child in self._iter_scope_nodes(node.body):
            if isinstance(
                child,
                (
                    ast.ExceptHandler,
                    ast.For,
                    ast.AsyncFor,
                    ast.If,
                    ast.Match,
                    ast.Try,
                    ast.While,
                    ast.With,
                    ast.AsyncWith,
                ),
            ):
                score += 1
            elif isinstance(child, ast.BoolOp):
                score += max(0, len(child.values) - 1)
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                score += len(child.generators)
        return score

    def _is_prefer_comprehension_candidate(self, node: ast.For) -> bool:
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Expr):
            return False
        expr = node.body[0].value
        if not isinstance(expr, ast.Call):
            return False
        target_name = self._append_target_name(expr)
        if target_name is None:
            return False
        scope = self._enclosing_scope(node)
        if scope is None:
            return False
        if not self._has_prior_empty_list_assignment(scope, target_name, node.lineno):
            return False
        return self._append_count_in_scope(scope, target_name) == 1

    def _append_target_name(self, node: ast.Call) -> str | None:
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "append":
            return None
        if isinstance(node.func.value, ast.Name):
            return node.func.value.id
        return None

    def _enclosing_scope(self, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.Module | None:
        current = node
        while current in self.parents:
            parent = self.parents[current]
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                return parent
            current = parent
        return None

    def _has_prior_empty_list_assignment(
        self,
        scope: ast.FunctionDef | ast.AsyncFunctionDef | ast.Module,
        target_name: str,
        line_no: int,
    ) -> bool:
        for node in self._iter_scope_nodes(scope.body):
            if getattr(node, "lineno", line_no + 1) >= line_no:
                continue
            if self._is_empty_list_assignment_to(node, target_name):
                return True
        return False

    def _append_count_in_scope(
        self,
        scope: ast.FunctionDef | ast.AsyncFunctionDef | ast.Module,
        target_name: str,
    ) -> int:
        count = 0
        for node in self._iter_scope_nodes(scope.body):
            if isinstance(node, ast.Call) and self._append_target_name(node) == target_name:
                count += 1
        return count

    def _is_empty_list_assignment_to(self, node: ast.AST, target_name: str) -> bool:
        if isinstance(node, ast.Assign):
            return self._is_empty_list_expr(node.value) and any(
                isinstance(target, ast.Name) and target.id == target_name
                for target in node.targets
            )
        if isinstance(node, ast.AnnAssign):
            return (
                isinstance(node.target, ast.Name)
                and node.target.id == target_name
                and node.value is not None
                and self._is_empty_list_expr(node.value)
            )
        return False

    def _is_empty_list_expr(self, node: ast.AST) -> bool:
        if isinstance(node, ast.List) and not node.elts:
            return True
        return isinstance(node, ast.Call) and self._call_name(node.func) == "list" and not node.args and not node.keywords

    def _iter_scope_nodes(self, body: list[ast.stmt]) -> Iterable[ast.AST]:
        stack: list[ast.AST] = list(reversed(body))
        while stack:
            node = stack.pop()
            yield node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.extend(reversed(list(ast.iter_child_nodes(node))))

    def _is_nested_or_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        parent = self.parents.get(node)
        return isinstance(parent, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))

    def _has_property_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "property":
                return True
        return False

    def _is_testcase_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        parent = self.parents.get(node)
        if not isinstance(parent, ast.ClassDef):
            return False
        return any(
            isinstance(base, ast.Attribute) and base.attr == "TestCase"
            or isinstance(base, ast.Name) and base.id == "TestCase"
            for base in parent.bases
        )

    def _is_intended_public_api(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        parent = self.parents.get(node)
        if not isinstance(parent, ast.ClassDef):
            return False
        if self._is_conversion_method(node, parent):
            return True
        if self._is_framework_override(node, parent):
            return True
        if self._is_named_public_hook(node, parent):
            return True
        if self._is_gui_handler_method(node, parent):
            return True
        return self._is_abstract_hook(node, parent)

    def _is_conversion_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        if node.name in PUBLIC_CONVERSION_METHODS:
            return True
        if node.name.startswith("to_") and node.name.endswith(PUBLIC_CONVERSION_SUFFIXES):
            return True
        return node.name.startswith("from_") and self._is_dataclass_like_class(parent)

    def _is_dataclass_like_class(self, node: ast.ClassDef) -> bool:
        if any(self._decorator_name(decorator).endswith("dataclass") for decorator in node.decorator_list):
            return True
        return node.name.endswith(
            (
                "Breakdown",
                "Config",
                "Contract",
                "Notice",
                "Record",
                "Report",
                "Result",
                "Summary",
            )
        )

    def _is_framework_override(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        base_names = self._class_base_names(parent)
        return any(
            node.name in methods
            for base_name, methods in FRAMEWORK_OVERRIDE_METHODS_BY_BASE.items()
            if base_name in base_names
        )

    def _is_named_public_hook(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        if node.name in PUBLIC_RESULT_METHODS and parent.name.endswith(("Result", "Report", "Summary")):
            return True
        if self._is_symbol_policy_hook(node, parent):
            return True
        if self._is_public_utility_method(node, parent):
            return True
        for suffix, method_names in PUBLIC_HOOK_METHODS_BY_CLASS_SUFFIX.items():
            if parent.name.endswith(suffix) and node.name in method_names:
                return True
        for suffix, prefixes in PUBLIC_HOOK_PREFIXES_BY_CLASS_SUFFIX.items():
            if parent.name.endswith(suffix) and node.name.startswith(prefixes):
                return True
        return False

    def _is_symbol_policy_hook(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        return parent.name.endswith("SymbolPolicy") and node.name in SYMBOL_POLICY_HOOK_METHODS

    def _is_public_utility_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        return any(
            parent.name.endswith(suffix) and node.name in method_names
            for suffix, method_names in PUBLIC_UTILITY_METHODS_BY_CLASS_SUFFIX.items()
        )

    def _is_gui_handler_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        if not parent.name.endswith(GUI_CONTAINER_CLASS_SUFFIXES):
            return False
        if not self._module_imports_tkinter(parent):
            return False
        if node.name in GUI_HANDLER_METHODS:
            return self._method_uses_gui_surface(node)
        if not node.name.startswith(GUI_HANDLER_METHOD_PREFIXES):
            return False
        return self._method_uses_gui_surface(node) or self._class_registers_gui_callback(parent, node.name)

    def _module_imports_tkinter(self, node: ast.AST) -> bool:
        module = self._module_for(node)
        if module is None:
            return False
        for statement in module.body:
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    if alias.name == "tkinter" or alias.name.startswith("tkinter."):
                        return True
            elif isinstance(statement, ast.ImportFrom) and statement.module:
                if statement.module == "tkinter" or statement.module.startswith("tkinter."):
                    return True
        return False

    def _method_uses_gui_surface(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr in GUI_METHOD_SURFACE_ATTRS:
                return True
            if isinstance(child, ast.Name) and child.id in GUI_METHOD_SURFACE_NAMES:
                return True
        return False

    def _class_registers_gui_callback(self, parent: ast.ClassDef, method_name: str) -> bool:
        for child in ast.walk(parent):
            if isinstance(child, ast.keyword) and child.arg == "command":
                if self._is_self_method_reference(child.value, method_name):
                    return True
            elif isinstance(child, ast.Call) and self._call_name(child.func).endswith((".after", ".bind")):
                if any(self._is_gui_callback_arg(argument, method_name) for argument in child.args):
                    return True
        return False

    def _is_gui_callback_arg(self, node: ast.AST, method_name: str) -> bool:
        if self._is_self_method_reference(node, method_name):
            return True
        if isinstance(node, ast.Lambda):
            return any(self._is_self_method_reference(child, method_name) for child in ast.walk(node.body))
        return False

    def _is_self_method_reference(self, node: ast.AST, method_name: str) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == method_name
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        )

    def _module_for(self, node: ast.AST) -> ast.Module | None:
        current = node
        while current in self.parents:
            current = self.parents[current]
        return current if isinstance(current, ast.Module) else None

    def _is_abstract_hook(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.ClassDef,
    ) -> bool:
        base_names = self._class_base_names(parent)
        if {"ABC", "Protocol"} & base_names:
            return True
        if len(node.body) != 1:
            return False
        only_statement = node.body[0]
        if isinstance(only_statement, ast.Pass):
            return True
        if isinstance(only_statement, ast.Expr):
            value = only_statement.value
            return isinstance(value, ast.Constant) and value.value is Ellipsis
        if isinstance(only_statement, ast.Raise) and isinstance(only_statement.exc, ast.Call):
            return self._call_name(only_statement.exc.func) == "NotImplementedError"
        return False

    def _class_base_names(self, node: ast.ClassDef) -> set[str]:
        names = set()
        for base in node.bases:
            name = self._call_name(base)
            if name:
                names.add(name.rsplit(".", 1)[-1])
        return names

    def _decorator_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Call):
            return self._call_name(node.func)
        return self._call_name(node)

    def _add(
        self,
        line: int,
        rule: str,
        **message_context: object,
    ) -> None:
        if rule in NOISY_TEST_RULES and _is_test_path(self.path):
            return
        self.findings.append(build_finding(self.path, line, rule, **message_context))


def iter_python_files(paths: Iterable[Path], exclude_dirs: set[str]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from (
                child
                for child in path.rglob("*.py")
                if not any(part in exclude_dirs for part in child.relative_to(path).parts)
            )
        elif path.suffix == ".py":
            yield path


def _is_test_path(path: Path) -> bool:
    return path.name.lower().startswith("test_")


def review_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    visitor = PythonReviewVisitor(path, source.splitlines())
    visitor.visit(tree)
    return sorted(
        visitor.findings,
        key=lambda finding: (
            SEVERITY_ORDER[finding.severity],
            finding.path,
            finding.line,
            finding.rule,
        ),
    )


def run_review(paths: Iterable[Path], exclude_dirs: set[str]) -> ReviewResult:
    files = sorted(set(iter_python_files(paths, exclude_dirs)))
    scanned_files = [str(path) for path in files]
    findings: list[Finding] = []

    for file_path in files:
        try:
            findings.extend(review_file(file_path))
        except SyntaxError as error:
            findings.append(build_finding(file_path, error.lineno or 1, "syntax-error", detail=error.msg))
        except UnicodeDecodeError as error:
            findings.append(build_finding(file_path, 1, "file-decode-error", detail=error.reason))
        except OSError as error:
            findings.append(build_finding(file_path, 1, "file-read-error", detail=error.strerror or str(error)))

    findings.sort(
        key=lambda finding: (
            SEVERITY_ORDER[finding.severity],
            finding.path,
            finding.line,
            finding.rule,
        )
    )
    return ReviewResult(findings=findings, scanned_files=scanned_files)


def to_display_path(path: str) -> str:
    resolved = Path(path)
    cwd = Path.cwd()
    if resolved.is_absolute():
        try:
            return str(resolved.relative_to(cwd))
        except ValueError:
            return str(resolved)
    return path


def render_text(result: ReviewResult) -> str:
    if not result.scanned_files:
        return "검사할 Python 파일이 없습니다."

    if not result.findings:
        return "리뷰 결과 이상이 없습니다. 검사한 Python 파일이 현재 규칙을 통과했습니다."

    finding_lines = [
        f"[{SEVERITY_LABELS[finding.severity]}] {to_display_path(finding.path)}:{finding.line} "
        f"{finding.rule} - {finding.message}"
        for finding in result.findings
    ]
    lines = ["Python 리뷰 결과", "==================", *finding_lines, ""]
    lines.extend(render_summary_lines(result))
    return "\n".join(lines)


def render_markdown(result: ReviewResult) -> str:
    if not result.scanned_files:
        return "# Python 리뷰\n\n검사할 Python 파일이 없습니다."

    if not result.findings:
        return "# Python 리뷰\n\n리뷰 결과 이상이 없습니다. 검사한 Python 파일이 현재 규칙을 통과했습니다."

    lines = ["# Python 리뷰", ""]
    current_severity = None
    for finding in result.findings:
        if finding.severity != current_severity:
            current_severity = finding.severity
            lines.extend([f"## {SEVERITY_LABELS[current_severity]}", ""])
        lines.append(
            f"- `{to_display_path(finding.path)}:{finding.line}` `{finding.rule}`: {finding.message}"
        )

    lines.extend(["", "## 요약", ""])
    lines.extend([f"- {line}" for line in render_summary_lines(result)])
    return "\n".join(lines)


def render_json(result: ReviewResult) -> str:
    payload = {
        "scanned_files": [to_display_path(path) for path in result.scanned_files],
        "summary": {
            "total_findings": len(result.findings),
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
            "categories": dict(Counter(finding.category for finding in result.findings)),
        },
        "findings": [
            {
                **asdict(finding),
                "path": to_display_path(finding.path),
            }
            for finding in result.findings
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def filter_findings(
    result: ReviewResult,
    *,
    min_severity: str = DEFAULT_MIN_SEVERITY,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> ReviewResult:
    threshold = SEVERITY_ORDER[FAIL_ON_SEVERITY[min_severity]]
    findings = [
        finding
        for finding in result.findings
        if SEVERITY_ORDER[finding.severity] <= threshold
    ]
    if max_findings > 0:
        findings = findings[:max_findings]
    return ReviewResult(findings=findings, scanned_files=result.scanned_files)


def render_summary_lines(result: ReviewResult) -> list[str]:
    category_counts = Counter(finding.category for finding in result.findings)
    category_text = ", ".join(
        f"{category} {count}" for category, count in sorted(category_counts.items())
    )
    return [
        f"검사한 파일 수: {len(result.scanned_files)}",
        f"전체 이슈 수: {len(result.findings)}",
        f"높음 심각도: {result.high_count}",
        f"보통 심각도: {result.medium_count}",
        f"낮음 심각도: {result.low_count}",
        f"카테고리별: {category_text or '없음'}",
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="보안, 안전성, 스타일, 일반 품질 기준에 맞춘 Python 코드 리뷰 도구입니다."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=list(DEFAULT_PATHS),
        help="리뷰할 Python 파일 또는 디렉터리입니다. 기본값은 현재 디렉터리입니다.",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=DEFAULT_OUTPUT_FORMAT,
        help="리뷰 결과 출력 형식입니다.",
    )
    parser.add_argument(
        "--fail-on",
        choices=FAIL_ON_CHOICES,
        default=DEFAULT_FAIL_ON,
        help="지정한 심각도 이상의 이슈가 있으면 종료 코드를 1로 반환합니다.",
    )
    parser.add_argument(
        "--min-severity",
        choices=MIN_SEVERITY_CHOICES,
        default=DEFAULT_MIN_SEVERITY,
        help="출력과 실패 판정에 포함할 최소 심각도입니다.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=DEFAULT_MAX_FINDINGS,
        help="출력할 최대 finding 수입니다. 0이면 제한하지 않습니다.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="제외할 디렉터리 이름입니다. 여러 번 지정할 수 있습니다.",
    )
    return parser


def should_fail(result: ReviewResult, fail_on: str) -> bool:
    if fail_on == "none":
        return False
    threshold = SEVERITY_ORDER[FAIL_ON_SEVERITY[fail_on]]
    return any(SEVERITY_ORDER[finding.severity] <= threshold for finding in result.findings)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    targets = [Path(raw).resolve() for raw in args.paths]
    exclude_dirs = DEFAULT_EXCLUDE_DIRS | set(args.exclude_dir)
    result = run_review(targets, exclude_dirs)
    result = filter_findings(
        result,
        min_severity=args.min_severity,
        max_findings=max(0, args.max_findings),
    )

    if args.format == "json":
        output = render_json(result)
    elif args.format == "markdown":
        output = render_markdown(result)
    else:
        output = render_text(result)

    print(output)
    return 1 if should_fail(result, args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
