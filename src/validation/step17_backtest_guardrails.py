"""Step 17 conservative backtest validation guardrails.

This module validates Step 17 backtest structures and generated report text.
It does not run a backtest, compute returns, create trading signals, redefine
ranking/scoring formulas, or perform valuation/fundamental scoring.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

import pandas as pd

from src.scores.schema import find_valuation_fundamental_columns


STEP17_EVALUATION_ONLY_NOTICE = "evaluation-only"

STEP17_REQUIRED_REPORT_NOTICES: tuple[str, ...] = (
    "evaluation-only",
    "not a trading recommendation",
    "does not redefine score or ranking formulas",
    "technical-only upstream ranking context",
    "valuation/fundamental scoring remains gated until step 18",
)

STEP17_REQUIRED_LIMITATION_FLAGS: tuple[str, ...] = (
    "survivorship_bias",
    "corporate_action_adjustment_uncertainty",
    "missing_execution_or_exit_price",
    "transaction_cost_and_slippage",
    "no_valuation_fundamental_data",
    "no_return_feedback_to_scores",
)

STEP17_ALLOWED_BACKTEST_EVALUATION_COLUMNS = frozenset(
    {
        "realized_holding_return",
        "backtest_period_return",
        "evaluation_return",
        "evaluation_start_date",
        "evaluation_end_date",
        "execution_date",
        "exit_date",
        "transaction_cost_bps",
        "slippage_bps",
        "limitation_flags",
    }
)

STEP17_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "future_return",
        "forward_return",
        "expected_return",
        "target_return",
        "next_return",
        "next_period_return",
        "realized_return",
        "realized_pnl",
        "alpha",
        "alpha_signal",
        "signal",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "target_price",
        "valuation_score",
        "fundamental_score",
        "per",
        "pbr",
        "roe",
        "eps",
        "bps",
        "market_cap",
        "cheap",
        "undervalued",
        "bargain",
    }
)

STEP17_FORBIDDEN_PREFIXES = (
    "future_return",
    "forward_return",
    "expected_return",
    "target_return",
    "next_return",
    "next_period_return",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "hold_",
    "recommendation_",
    "target_price",
    "valuation_",
    "fundamental_",
    "financial_",
    "per_",
    "pbr_",
    "roe_",
    "eps_",
    "bps_",
    "market_cap_",
)

STEP17_FORBIDDEN_SUFFIXES = (
    "_future_return",
    "_forward_return",
    "_expected_return",
    "_target_return",
    "_next_return",
    "_next_period_return",
    "_alpha",
    "_signal",
    "_buy",
    "_sell",
    "_hold",
    "_recommendation",
    "_target_price",
    "_valuation_score",
    "_fundamental_score",
    "_per",
    "_pbr",
    "_roe",
    "_eps",
    "_bps",
    "_market_cap",
)

STEP17_FORBIDDEN_COLUMN_SUBSTRINGS = (
    "future_return",
    "forward_return",
    "expected_return",
    "target_return",
    "next_day_return",
    "next_month_return",
    "next_period_return",
    "label_return",
    "target_price",
    "valuation_score",
    "fundamental_score",
    "market_cap",
)

STEP17_FORBIDDEN_COLUMN_TOKENS = frozenset(
    {
        "alpha",
        "signal",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "cheap",
        "undervalued",
        "bargain",
    }
)

STEP17_UPSTREAM_CONTEXT_KEYWORDS = frozenset(
    {
        "step 13",
        "step13",
        "review_status",
        "technical selection",
        "step 14",
        "step14",
        "adoption_state",
        "adoption synthesis",
        "step 15",
        "step15",
        "ranking",
        "rank",
        "step 16",
        "step16",
        "detail report",
        "score update",
        "upstream",
    }
)

STEP17_UPSTREAM_MUTATION_FIELDS = frozenset(
    {
        "review_status",
        "source_review_status",
        "adoption_state",
        "step15_usage",
        "rank",
        "technical_composite_score",
        "final_composite_score",
        "score_value",
        "normalized_score",
        "score_formula",
        "ranking_formula",
        "formula_change",
        "report_notice",
        "boundary_notice",
    }
)

STEP17_FORBIDDEN_REPORT_LANGUAGE_PATTERNS: Mapping[str, str] = {
    "alpha proven": r"\balpha\s+(?:is\s+)?proven\b|\bproven\s+alpha\b",
    "backtest proves": r"\bbacktest(?:ed)?\s+proves?\b|\bbacktest-proven\b",
    "profitable strategy": r"\bprofitable\s+strategy\b|\bprofitability\s+proven\b",
    "market beating": r"\bmarket[-\s]?beating\b|\boutperform(?:s|ed|ing)?\s+the\s+market\b",
    "buy recommendation": r"\bbuy\s+(?:signal|recommendation|call)\b",
    "sell recommendation": r"\bsell\s+(?:signal|recommendation|call)\b",
    "hold recommendation": r"\bhold\s+(?:signal|recommendation|call)\b",
    "trading signal": r"\btrading\s+signal\b",
    "trading recommendation": r"\btrading\s+recommendation\b",
    "investment recommendation": r"\binvestment\s+recommendation\b",
    "undervalued": r"\bundervalued\b",
    "cheap": r"\bcheap\b",
    "bargain": r"\bbargain\b",
    "target price": r"\btarget[_\s-]?price\b|\bprice\s+target\b",
    "valuation score": r"\bvaluation[_\s-]?score\b",
    "fundamental score": r"\bfundamental[_\s-]?score\b",
    "valuation ratio claim": r"\bper\s+ratio\b|\bp/e\b|\bpbr\b|\broe\b",
    "score formula improvement": (
        r"\bscore\s+formula\s+improvement\b|"
        r"\bimprov(?:e|es|ed|ing)\s+score\s+formula\b"
    ),
    "ranking formula improvement": (
        r"\branking\s+formula\s+improvement\b|"
        r"\bimprov(?:e|es|ed|ing)\s+ranking\s+formula\b"
    ),
    "automatic adoption": (
        r"\bautomatic\s+adoption\b|"
        r"\bauto[-\s]?adoption\b|"
        r"\badopt(?:ed|ion)?\s+automatically\b|"
        r"\badopt(?:ed|ion)?\s+based\s+on\s+backtest\b"
    ),
    "backtest as score source": (
        r"\bbacktest\s+(?:is|as|becomes)\s+(?:the\s+)?score\s+(?:definition\s+)?source\b|"
        r"\bsource\s+for\s+score\s+definitions?\b"
    ),
    "backtest as ranking source": (
        r"\bbacktest\s+(?:is|as|becomes)\s+(?:the\s+)?ranking\s+source\b|"
        r"\bsource\s+for\s+ranking\b"
    ),
    "backtest as adoption source": (
        r"\bbacktest\s+(?:is|as|becomes)\s+(?:the\s+)?adoption\s+source\b|"
        r"\bsource\s+for\s+adoption\b"
    ),
    "backtest updates upstream score": (
        r"\bbacktest\s+result\s+(?:updates?|changes?|redefines?)\s+score\b|"
        r"\breturns?\s+(?:update|change|redefine)\s+upstream\s+scores?\b"
    ),
}

STEP17_LIMITATION_PHRASES: Mapping[str, tuple[str, ...]] = {
    "survivorship_bias": (
        "survivorship bias",
        "pit constituent membership",
        "point-in-time constituent membership",
    ),
    "corporate_action_adjustment_uncertainty": (
        "corporate action",
        "adjusted price uncertainty",
        "adjusted price",
    ),
    "missing_execution_or_exit_price": (
        "missing execution",
        "missing exit price",
        "execution or exit price",
    ),
    "transaction_cost_and_slippage": (
        "transaction cost",
        "slippage",
    ),
    "no_valuation_fundamental_data": (
        "no valuation/fundamental data",
        "no valuation data",
        "no fundamental data",
    ),
    "no_return_feedback_to_scores": (
        "no return feedback",
        "no return feedback into upstream scores",
        "does not feed returns",
        "does not feed back returns",
    ),
}


@dataclass(frozen=True)
class Step17BacktestValidationResult:
    """Validation result for Step 17 backtest guardrail checks."""

    context: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()
    forbidden_language: tuple[str, ...] = ()
    missing_notices: tuple[str, ...] = ()
    missing_limitation_flags: tuple[str, ...] = ()
    evaluation_fields: tuple[str, ...] = ()
    upstream_mutation_fields: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether validation passed."""

        return not self.errors

    @property
    def valid(self) -> bool:
        """Alias for callers that prefer shorter result names."""

        return self.is_valid

    def raise_for_errors(self) -> None:
        """Raise a compact ValueError when validation failed."""

        if self.errors:
            raise ValueError(f"{self.context} failed Step 17 validation: {'; '.join(self.errors)}")


def validate_step17_backtest_input(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "Step 17 backtest input",
    raise_on_error: bool = True,
) -> Step17BacktestValidationResult:
    """Validate Step 17 input structures without accepting result labels."""

    return _validate_structured_step17_data(
        data,
        context=context,
        allow_backtest_evaluation_columns=False,
        require_limitation_flags=False,
        raise_on_error=raise_on_error,
    )


def validate_step17_backtest_output(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "Step 17 backtest output",
    require_limitation_flags: bool = True,
    raise_on_error: bool = True,
) -> Step17BacktestValidationResult:
    """Validate Step 17 output structures with evaluation columns allowed."""

    return _validate_structured_step17_data(
        data,
        context=context,
        allow_backtest_evaluation_columns=True,
        require_limitation_flags=require_limitation_flags,
        raise_on_error=raise_on_error,
    )


def validate_step17_backtest_report(
    report: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "Step 17 backtest report",
    require_notice: bool = True,
    require_limitation_flags: bool = True,
    raise_on_error: bool = True,
) -> Step17BacktestValidationResult:
    """Validate Step 17 report text and structured generated-output boundary."""

    if isinstance(report, str):
        columns: tuple[str, ...] = ()
        report_text = report
        structured_result = Step17BacktestValidationResult(context=context)
    else:
        frame = _coerce_frame(report)
        columns = _column_names(frame)
        report_text = _extract_report_text(frame)
        structured_result = _validate_structured_step17_data(
            frame,
            context=context,
            allow_backtest_evaluation_columns=True,
            require_limitation_flags=False,
            raise_on_error=False,
        )

    errors = list(structured_result.errors)
    warnings = list(structured_result.warnings)

    forbidden_language = find_step17_forbidden_report_language(report_text)
    if forbidden_language:
        errors.append(f"contains forbidden report language: {', '.join(forbidden_language)}")

    missing_notices = (
        find_missing_step17_report_notices(report_text) if require_notice else []
    )
    if missing_notices:
        errors.append(f"missing required notices: {', '.join(missing_notices)}")

    missing_limitations = (
        find_missing_step17_limitation_flags(report)
        if require_limitation_flags
        else []
    )
    if missing_limitations:
        errors.append(f"missing limitation disclosures: {', '.join(missing_limitations)}")

    result = Step17BacktestValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_fields=structured_result.forbidden_fields,
        forbidden_language=tuple(forbidden_language),
        missing_notices=tuple(missing_notices),
        missing_limitation_flags=tuple(missing_limitations),
        evaluation_fields=structured_result.evaluation_fields,
        upstream_mutation_fields=structured_result.upstream_mutation_fields,
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def validate_step17_report_boundary(
    input_data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    report: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "Step 17 report boundary",
    raise_on_error: bool = True,
) -> Step17BacktestValidationResult:
    """Validate the frozen-input to evaluation-report one-way boundary."""

    input_result = validate_step17_backtest_input(
        input_data,
        context=f"{context} input",
        raise_on_error=False,
    )
    report_result = validate_step17_backtest_report(
        report,
        context=f"{context} report",
        raise_on_error=False,
    )
    errors = [*input_result.errors, *report_result.errors]
    warnings = [*input_result.warnings, *report_result.warnings]

    result = Step17BacktestValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(dict.fromkeys(warnings)),
        forbidden_fields=tuple(
            sorted(set(input_result.forbidden_fields).union(report_result.forbidden_fields))
        ),
        forbidden_language=report_result.forbidden_language,
        missing_notices=report_result.missing_notices,
        missing_limitation_flags=report_result.missing_limitation_flags,
        evaluation_fields=tuple(
            sorted(set(input_result.evaluation_fields).union(report_result.evaluation_fields))
        ),
        upstream_mutation_fields=tuple(
            sorted(
                set(input_result.upstream_mutation_fields).union(
                    report_result.upstream_mutation_fields
                )
            )
        ),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def validate_step17_no_feedback_loop(
    candidate_update: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    target_context: str,
    context: str = "Step 17 no-feedback boundary",
    raise_on_error: bool = True,
) -> Step17BacktestValidationResult:
    """Reject using Step 17 backtest results as upstream score/rank/adoption updates."""

    frame = _coerce_frame(candidate_update)
    columns = _column_names(frame)
    report_text = _extract_report_text(frame)
    target = target_context.lower()
    target_is_upstream = any(token in target for token in STEP17_UPSTREAM_CONTEXT_KEYWORDS)
    evaluation_fields = find_step17_evaluation_fields(columns)
    mutation_fields = find_step17_upstream_mutation_fields(columns)
    errors: list[str] = []

    if target_is_upstream and (evaluation_fields or mutation_fields or "backtest" in report_text.lower()):
        errors.append(
            f"Step 17 evaluation output cannot update upstream context: {target_context}"
        )

    forbidden_language = find_step17_forbidden_report_language(report_text)
    if forbidden_language:
        errors.append(f"contains forbidden feedback language: {', '.join(forbidden_language)}")

    result = Step17BacktestValidationResult(
        context=context,
        errors=tuple(errors),
        forbidden_language=tuple(forbidden_language),
        evaluation_fields=tuple(evaluation_fields),
        upstream_mutation_fields=tuple(mutation_fields),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def find_step17_forbidden_fields(
    columns: pd.DataFrame | Iterable[str],
    *,
    allow_backtest_evaluation_columns: bool = False,
) -> list[str]:
    """Return fields that cross Step 17 evaluation-only boundaries."""

    column_names = _column_names(columns)
    forbidden: set[str] = set(find_valuation_fundamental_columns(column_names))
    for column in column_names:
        normalized = column.lower()
        if normalized in STEP17_ALLOWED_BACKTEST_EVALUATION_COLUMNS:
            if not allow_backtest_evaluation_columns:
                forbidden.add(column)
            continue

        tokens = set(_split_tokens(normalized))
        if (
            normalized in STEP17_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP17_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP17_FORBIDDEN_SUFFIXES)
            or any(term in normalized for term in STEP17_FORBIDDEN_COLUMN_SUBSTRINGS)
            or bool(tokens.intersection(STEP17_FORBIDDEN_COLUMN_TOKENS))
        ):
            forbidden.add(column)

    return sorted(forbidden)


def find_step17_evaluation_fields(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return Step 17 backtest evaluation fields present in a structure."""

    return sorted(
        column
        for column in _column_names(columns)
        if column.lower() in STEP17_ALLOWED_BACKTEST_EVALUATION_COLUMNS
    )


def find_step17_upstream_mutation_fields(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return fields that belong to upstream score/rank/adoption/report contexts."""

    return sorted(
        column
        for column in _column_names(columns)
        if column.lower() in STEP17_UPSTREAM_MUTATION_FIELDS
    )


def find_step17_forbidden_report_language(text: str) -> list[str]:
    """Return Step 17 report phrases that imply performance proof or adoption."""

    lowered = text.lower()
    forbidden: list[str] = []
    for label, pattern in STEP17_FORBIDDEN_REPORT_LANGUAGE_PATTERNS.items():
        if _contains_forbidden_report_pattern(lowered, pattern, label):
            forbidden.append(label)
    return sorted(forbidden)


def find_missing_step17_report_notices(text: str) -> list[str]:
    """Return required Step 17 report boundary notices missing from text."""

    lowered = text.lower()
    return [notice for notice in STEP17_REQUIRED_REPORT_NOTICES if notice not in lowered]


def find_missing_step17_limitation_flags(
    report: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    required_flags: Iterable[str] = STEP17_REQUIRED_LIMITATION_FLAGS,
) -> list[str]:
    """Return required conservative limitation disclosures missing from report."""

    if isinstance(report, str):
        report_text = report
        explicit_flags: set[str] = set()
    else:
        frame = _coerce_frame(report)
        report_text = _extract_report_text(frame)
        explicit_flags = _extract_explicit_limitation_flags(frame)

    lowered = report_text.lower()
    missing: list[str] = []
    for flag in required_flags:
        normalized_flag = flag.lower()
        if normalized_flag in explicit_flags:
            continue
        phrases = STEP17_LIMITATION_PHRASES.get(normalized_flag, (normalized_flag,))
        if not any(phrase in lowered for phrase in phrases):
            missing.append(flag)
    return missing


def _validate_structured_step17_data(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str,
    allow_backtest_evaluation_columns: bool,
    require_limitation_flags: bool,
    raise_on_error: bool,
) -> Step17BacktestValidationResult:
    frame = _coerce_frame(data)
    columns = _column_names(frame)
    errors: list[str] = []
    warnings: list[str] = []

    forbidden = find_step17_forbidden_fields(
        columns,
        allow_backtest_evaluation_columns=allow_backtest_evaluation_columns,
    )
    if forbidden:
        errors.append(f"contains forbidden Step 17 fields: {', '.join(forbidden)}")

    evaluation_fields = find_step17_evaluation_fields(columns)
    if evaluation_fields and not allow_backtest_evaluation_columns:
        errors.append(
            "Step 17 evaluation fields are allowed only in backtest output context: "
            f"{', '.join(evaluation_fields)}"
        )

    mutation_fields = find_step17_upstream_mutation_fields(columns)
    if mutation_fields:
        warnings.append(
            "Upstream score/rank/adoption fields must remain read-only context, not updates."
        )

    missing_limitations = (
        find_missing_step17_limitation_flags(frame) if require_limitation_flags else []
    )
    if missing_limitations:
        errors.append(f"missing limitation disclosures: {', '.join(missing_limitations)}")

    result = Step17BacktestValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_fields=tuple(forbidden),
        missing_limitation_flags=tuple(missing_limitations),
        evaluation_fields=tuple(evaluation_fields),
        upstream_mutation_fields=tuple(mutation_fields),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def _coerce_frame(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, Mapping):
        return pd.DataFrame([dict(data)])
    return pd.DataFrame(list(data))


def _column_names(columns: pd.DataFrame | Iterable[str]) -> tuple[str, ...]:
    if isinstance(columns, pd.DataFrame):
        return tuple(str(column) for column in columns.columns)
    return tuple(str(column) for column in columns)


def _extract_report_text(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    parts: list[str] = []
    for record in frame.to_dict(orient="records"):
        _collect_report_text(record, parts)
    return "\n".join(parts)


def _collect_report_text(value: object, parts: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            parts.append(str(key))
            _collect_report_text(child, parts)
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            _collect_report_text(child, parts)
        return
    if isinstance(value, str):
        parts.append(value)


def _extract_explicit_limitation_flags(frame: pd.DataFrame) -> set[str]:
    flags: set[str] = set()
    for record in frame.to_dict(orient="records"):
        _collect_limitation_flags(record, flags, inside_limitation_flags=False)
    return flags


def _collect_limitation_flags(
    value: object,
    flags: set[str],
    *,
    inside_limitation_flags: bool,
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            child_is_flag = inside_limitation_flags or key_text == "limitation_flags"
            if inside_limitation_flags and bool(child):
                flags.add(key_text)
            _collect_limitation_flags(
                child,
                flags,
                inside_limitation_flags=child_is_flag,
            )
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            _collect_limitation_flags(
                child,
                flags,
                inside_limitation_flags=inside_limitation_flags,
            )
        return
    if inside_limitation_flags and isinstance(value, str):
        flags.add(value.lower())


def _contains_forbidden_report_pattern(lowered: str, pattern: str, label: str) -> bool:
    for match in re.finditer(pattern, lowered):
        if _is_allowed_negated_report_match(lowered, match, label):
            continue
        return True
    return False


def _is_allowed_negated_report_match(lowered: str, match: re.Match[str], label: str) -> bool:
    if label not in {"trading recommendation", "investment recommendation"}:
        return False
    prefix = lowered[max(0, match.start() - 16) : match.start()]
    return "not a " in prefix or "not an " in prefix or "not " in prefix or "non-" in prefix


def _split_tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", value) if token)


__all__ = (
    "STEP17_ALLOWED_BACKTEST_EVALUATION_COLUMNS",
    "STEP17_EVALUATION_ONLY_NOTICE",
    "STEP17_REQUIRED_LIMITATION_FLAGS",
    "STEP17_REQUIRED_REPORT_NOTICES",
    "Step17BacktestValidationResult",
    "find_missing_step17_limitation_flags",
    "find_missing_step17_report_notices",
    "find_step17_evaluation_fields",
    "find_step17_forbidden_fields",
    "find_step17_forbidden_report_language",
    "find_step17_upstream_mutation_fields",
    "validate_step17_backtest_input",
    "validate_step17_backtest_output",
    "validate_step17_backtest_report",
    "validate_step17_no_feedback_loop",
    "validate_step17_report_boundary",
)
