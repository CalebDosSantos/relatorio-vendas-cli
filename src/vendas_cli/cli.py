"""Interface de linha de comando (``vendas-cli``)."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from vendas_cli import __version__
from vendas_cli.core import build_report
from vendas_cli.exceptions import VendasError
from vendas_cli.output import OutputFormat, render
from vendas_cli.parser import parse_date, read_sales

logger = logging.getLogger("vendas_cli")

EXIT_OK = 0
EXIT_ERROR = 1


def _date_arg(value: str) -> date:
    try:
        return parse_date(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vendas-cli",
        description="Gera relatórios de vendas a partir de um arquivo CSV.",
        epilog="Colunas esperadas: produto, quantidade, preco_unitario [, data_venda | data].",
    )
    parser.add_argument("arquivo", type=Path, help="caminho do arquivo CSV de vendas")
    parser.add_argument(
        "-f",
        "--format",
        choices=[f.value for f in OutputFormat],
        default=OutputFormat.TEXT.value,
        help="formato de saída (padrão: text)",
    )
    parser.add_argument("--start", type=_date_arg, help="data inicial inclusiva (AAAA-MM-DD)")
    parser.add_argument("--end", type=_date_arg, help="data final inclusiva (AAAA-MM-DD)")
    parser.add_argument(
        "-o", "--output", type=Path, help="grava o relatório no arquivo em vez da saída padrão"
    )
    parser.add_argument(
        "--encoding", help="encoding do CSV (padrão: detecta UTF-8, com fallback para Latin-1)"
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="ignora linhas inválidas (com aviso) em vez de abortar",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="exibe logs detalhados")
    verbosity.add_argument("-q", "--quiet", action="store_true", help="exibe apenas erros")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.WARNING
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    configure_logging(args.verbose, args.quiet)

    try:
        sales = read_sales(args.arquivo, encoding=args.encoding, skip_invalid=args.skip_invalid)
        report = build_report(sales, start=args.start, end=args.end)
        content = render(report, OutputFormat(args.format))
        if args.output:
            args.output.write_text(content + "\n", encoding="utf-8")
            logger.info("relatório gravado em %s", args.output)
        else:
            print(content)
    except VendasError as exc:
        logger.error("%s", exc)
        return EXIT_ERROR
    except OSError as exc:
        logger.error("erro de E/S: %s", exc)
        return EXIT_ERROR
    return EXIT_OK
