"""Step 7 technical indicator calculation layer."""

__all__ = [
    "IndicatorConfig",
    "IndicatorPaths",
    "IndicatorResult",
    "IndicatorWindows",
    "calculate_technical_indicators",
    "load_indicator_config",
    "run_indicator_pipeline_from_config",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(name)
    from . import technical

    return getattr(technical, name)
