"""Command-line interface argument parsing for RC-Gestor.

Provides safe CLI flags that don't change default behavior unless explicitly set.
"""

from __future__ import annotations

import argparse
from typing import Final, NamedTuple


class AppArgs(NamedTuple):
    """Parsed application arguments."""

    no_splash: bool = False
    safe_mode: bool = False
    debug: bool = False


def parse_args(argv: list[str] | None = None) -> AppArgs:
    """Parse command-line arguments.

    Args:
        argv: Arguments to parse (defaults to sys.argv[1:])

    Returns:
        Parsed arguments as AppArgs
    """
    parser = argparse.ArgumentParser(
        prog="RC-Gestor-Clientes",
        description="Sistema de Gestão de Clientes - Regularize Consultoria",
        add_help=True,
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Pular tela de splash (útil para debug e CI)",
    )

    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Iniciar com tema padrão e desativar extensões opcionais",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativar modo debug com logs detalhados",
    )

    args = parser.parse_args(argv)

    return AppArgs(
        no_splash=args.no_splash,
        safe_mode=args.safe_mode,
        debug=args.debug,
    )


# Global singleton for parsed args (lazy-loaded)
_parsed_args: AppArgs | None = None


def get_args() -> AppArgs:
    """Get parsed command-line arguments (singleton).

    Returns:
        Parsed arguments, parsing on first call
    """
    global _parsed_args
    if _parsed_args is None:
        _parsed_args = parse_args()
    return _parsed_args


__all__: Final = ["AppArgs", "parse_args", "get_args"]
