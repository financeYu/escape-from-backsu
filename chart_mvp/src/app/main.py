"""Application main entry point."""

from __future__ import annotations

import sys

from app.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    """Run the stock analysis CLI."""

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

