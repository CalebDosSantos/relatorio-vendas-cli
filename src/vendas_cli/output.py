"""Formatação do relatório em texto (tabela) ou JSON."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

from vendas_cli.models import ProductSummary, SalesReport

CENTS = Decimal("0.01")


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


def format_money(value: Decimal) -> str:
    """Formata no padrão brasileiro: ``R$ 1.234,56``."""
    quantized = value.quantize(CENTS, rounding=ROUND_HALF_UP)
    us_style = f"{quantized:,.2f}"
    return "R$ " + us_style.replace(",", "_").replace(".", ",").replace("_", ".")


def render(report: SalesReport, fmt: OutputFormat) -> str:
    renderers: dict[OutputFormat, Callable[[SalesReport], str]] = {
        OutputFormat.TEXT: render_text,
        OutputFormat.JSON: render_json,
    }
    return renderers[fmt](report)


def render_text(report: SalesReport) -> str:
    lines = ["RELATÓRIO DE VENDAS", f"Período: {_period_label(report)}", ""]

    if not report.products:
        lines.append("Nenhuma venda encontrada.")
        return "\n".join(lines)

    rows = [[p.product, str(p.quantity), format_money(p.revenue)] for p in report.products]
    footer = ["TOTAL", str(report.total_quantity), format_money(report.total_revenue)]
    lines.extend(_table(["Produto", "Quantidade", "Total"], rows, footer, right_align={1, 2}))

    best = report.best_seller
    assert best is not None  # há produtos, logo há um mais vendido
    lines += [
        "",
        f"Vendas processadas: {report.sales_count}",
        f"Valor total das vendas: {format_money(report.total_revenue)}",
        f"Produto mais vendido: {best.product} ({best.quantity} unidades)",
    ]
    return "\n".join(lines)


def render_json(report: SalesReport) -> str:
    payload = report_to_dict(report)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def report_to_dict(report: SalesReport) -> dict[str, Any]:
    return {
        "periodo": {
            "inicio": report.start.isoformat() if report.start else None,
            "fim": report.end.isoformat() if report.end else None,
        },
        "quantidade_vendas": report.sales_count,
        "quantidade_itens": report.total_quantity,
        "valor_total": _money_number(report.total_revenue),
        "produto_mais_vendido": _product_to_dict(report.best_seller)
        if report.best_seller
        else None,
        "vendas_por_produto": [_product_to_dict(p) for p in report.products],
    }


def _product_to_dict(summary: ProductSummary) -> dict[str, Any]:
    return {
        "produto": summary.product,
        "quantidade": summary.quantity,
        "total": _money_number(summary.revenue),
    }


def _money_number(value: Decimal) -> float:
    return float(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def _period_label(report: SalesReport) -> str:
    if report.start is None and report.end is None:
        return "todas as datas"
    start = report.start.strftime("%d/%m/%Y") if report.start else "início"
    end = report.end.strftime("%d/%m/%Y") if report.end else "fim"
    return f"{start} a {end}"


def _table(
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
    footer: Sequence[str],
    right_align: set[int],
) -> list[str]:
    widths = [max(len(r[i]) for r in [header, *rows, footer]) for i in range(len(header))]

    def fmt_row(cells: Sequence[str]) -> str:
        parts = [
            cell.rjust(widths[i]) if i in right_align else cell.ljust(widths[i])
            for i, cell in enumerate(cells)
        ]
        return "| " + " | ".join(parts) + " |"

    separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    return [
        separator,
        fmt_row(header),
        separator,
        *(fmt_row(r) for r in rows),
        separator,
        fmt_row(footer),
        separator,
    ]
