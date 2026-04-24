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
}
MAX_FUNCTION_LINES = 50
BOUNDS_CHECK_LOOKBACK_LINES = 4
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
        if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
            expr = node.body[0].value
            if isinstance(expr, ast.Call) and self._call_name(expr.func).endswith(".append"):
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
        if line_span > MAX_FUNCTION_LINES:
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
        ]
        if index == 0:
            patterns.append(rf"if\s+{re.escape(variable)}\s*:")
        return any(re.search(pattern, context) for pattern in patterns)

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            root = self._call_name(node.value)
            return f"{root}.{node.attr}" if root else node.attr
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

    def _add(
        self,
        line: int,
        rule: str,
        **message_context: object,
    ) -> None:
        self.findings.append(build_finding(self.path, line, rule, **message_context))


def iter_python_files(paths: Iterable[Path], exclude_dirs: set[str]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from (
                child
                for child in path.rglob("*.py")
                if not any(part in exclude_dirs for part in child.parts)
            )
        elif path.suffix == ".py":
            yield path


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
