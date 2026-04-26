"""Step 14 adoption synthesis public API.

The implementation is split across focused modules. This facade preserves the
original import path without calculating rankings, composite scores, trading
outputs, future returns, backtests, or valuation/fundamental judgments.
"""

from __future__ import annotations

from .adoption_compat import STEP14_ADOPTION_MATERIAL_NOTICE, STEP14_ADOPTION_TABLE_COLUMNS
from .adoption_guardrails import (
    STEP14_FORBIDDEN_LANGUAGE_TERMS,
    find_forbidden_step14_output_columns,
    reject_step14_forbidden_columns,
    validate_step14_adoption_language,
    validate_step14_adoption_table,
)
from .adoption_rules import STEP14_ALLOWED_BOUNDARY_PHRASES
from .adoption_states import ALLOWED_STEP14_ADOPTION_STATES, AdoptionState
from .adoption_table_builder import (
    build_adoption_synthesis_table,
    build_step14_adoption_bundle,
    synthesize_adoption_from_review_rows,
    synthesize_adoption_states,
)

__all__ = (
    "ALLOWED_STEP14_ADOPTION_STATES",
    "STEP14_ADOPTION_MATERIAL_NOTICE",
    "STEP14_ADOPTION_TABLE_COLUMNS",
    "STEP14_ALLOWED_BOUNDARY_PHRASES",
    "STEP14_FORBIDDEN_LANGUAGE_TERMS",
    "AdoptionState",
    "build_adoption_synthesis_table",
    "build_step14_adoption_bundle",
    "find_forbidden_step14_output_columns",
    "reject_step14_forbidden_columns",
    "synthesize_adoption_from_review_rows",
    "synthesize_adoption_states",
    "validate_step14_adoption_language",
    "validate_step14_adoption_table",
)
