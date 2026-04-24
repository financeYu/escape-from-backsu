"""Backward-compatible accessors for the application CLI."""

from app.cli import build_parser, main, run_daily_scan, run_single_stock

__all__ = ["run_single_stock", "run_daily_scan", "build_parser", "main"]
