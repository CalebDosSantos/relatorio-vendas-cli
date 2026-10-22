"""Formatação do relatório em texto (tabela) ou JSON."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

from vendas_cli.models import Granularity, PeriodSummary, ProductSummary, SalesReport

CENTS = Decimal("0.01")
TENTHS = Decimal("0.1")

PERIOD_TITLES: dict[Granularity, str] = {
    Granularity.DAY: "Por dia",
    Granularity.MONTH: "Por mês",
    Granularity.QUARTER: "Por trimestre",
    Granularity.YEAR: "Por ano",
}


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


def format_money(value: Decimal) -> str:
    """Formata no padrão brasileiro: ``R$ 1.234,56``."""
    quantized = value.quantize(CENTS, rounding=ROUND_HALF_UP)
    us_style = f"{quantized:,.2f}"
    return "R$ " + us_style.replace(",", "_").replace(".", ",").replace("_", ".")


def format_percent(value: Decimal | None, signed: bool = False) -> str:
    """Formata com uma casa decimal: ``12,5%`` (ou ``+12,5%`` com ``signed``)."""
    if value is None:
        return "-"
    quantized = value.quantize(TENTHS, rounding=ROUND_HALF_UP)
    text = f"{quantized:+.1f}" if signed else f"{quantized:.1f}"
    return text.replace(".", ",") + "%"


def render(report: SalesReport, fmt: OutputFormat) -> str:
    renderers: dict[OutputFormat, Callable[[SalesReport], str]] = {
        OutputFormat.TEXT: render_text,
        OutputFormat.JSON: render_json,
    }
    return renderers[fmt](report)


def render_text(report: SalesReport) -> str:
    lines = ["RELATÓRIO DE VENDAS", f"Período: {_period_label(report)}"]
    if report.product_filter:
        lines.append(f"Produtos: {', '.join(report.product_filter)}")
    lines.append("")

    if not report.products:
        lines.append("Nenhuma venda encontrada.")
        return "\n".join(lines)

    lines.extend(_product_table(report))

    best = report.best_seller
    assert best is not None  # há produtos, logo há um mais vendido
    lines += [
        "",
        f"Vendas processadas: {report.sales_count}",
        f"Itens vendidos: {report.total_quantity}",
        f"Valor total das vendas: {format_money(report.total_revenue)}",
        f"Ticket médio: {format_money(report.average_ticket)}",
        f"Produto mais vendido: {best.product} ({best.quantity} unidades)",
    ]

    if report.group_by is not None:
        lines += ["", f"{PERIOD_TITLES[report.group_by]}:", *_period_table(report.periods)]
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
        "filtros": {"produtos": list(report.product_filter)},
        "quantidade_vendas": report.sales_count,
        "quantidade_itens": report.total_quantity,
        "valor_total": _round2(report.total_revenue),
        "ticket_medio": _round2(report.average_ticket),
        "produto_mais_vendido": _product_to_dict(report.best_seller, report)
        if report.best_seller
        else None,
        "vendas_por_produto": [_product_to_dict(p, report) for p in report.products],
        "outros": _product_to_dict(report.others, report) if report.others else None,
        "agrupamento": report.group_by.value if report.group_by else None,
        "por_periodo": [_period_to_dict(p) for p in report.periods],
    }


def _product_to_dict(summary: ProductSummary, report: SalesReport) -> dict[str, Any]:
    return {
        "produto": summary.product,
        "quantidade": summary.quantity,
        "quantidade_vendas": summary.sales_count,
        "total": _round2(summary.revenue),
        "preco_medio": _round2(summary.average_price),
        "participacao": _round2(report.share(summary.revenue)),
    }


def _period_to_dict(period: PeriodSummary) -> dict[str, Any]:
    return {
        "periodo": period.period,
        "quantidade_vendas": period.sales_count,
        "quantidade_itens": period.quantity,
        "valor_total": _round2(period.revenue),
        "variacao_percentual": _round2(period.growth) if period.growth is not None else None,
        "produto_mais_vendido": period.best_seller,
    }


def _round2(value: Decimal) -> float:
    return float(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def _period_label(report: SalesReport) -> str:
    if report.start is None and report.end is None:
        return "todas as datas"
    start = report.start.strftime("%d/%m/%Y") if report.start else "início"
    end = report.end.strftime("%d/%m/%Y") if report.end else "fim"
    return f"{start} a {end}"


def _product_table(report: SalesReport) -> list[str]:
    def row(p: ProductSummary) -> list[str]:
        return [
            p.product,
            str(p.sales_count),
            str(p.quantity),
            format_money(p.average_price),
            format_money(p.revenue),
            format_percent(report.share(p.revenue)),
        ]

    rows = [row(p) for p in report.products]
    if report.others is not None:
        rows.append(row(report.others))
    footer = [
        "TOTAL",
        str(report.sales_count),
        str(report.total_quantity),
        "",
        format_money(report.total_revenue),
        format_percent(Decimal(100)),
    ]
    header = ["Produto", "Vendas", "Quantidade", "Preço médio", "Total", "Part."]
    return _table(header, rows, footer, right_align={1, 2, 3, 4, 5})


def _period_table(periods: Sequence[PeriodSummary]) -> list[str]:
    rows = [
        [
            p.period,
            str(p.sales_count),
            str(p.quantity),
            format_money(p.revenue),
            format_percent(p.growth, signed=True),
            p.best_seller,
        ]
        for p in periods
    ]
    header = ["Período", "Vendas", "Quantidade", "Total", "Variação", "Mais vendido"]
    return _table(header, rows, None, right_align={1, 2, 3, 4})


def _table(
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
    footer: Sequence[str] | None,
    right_align: set[int],
) -> list[str]:
    all_rows = [header, *rows] + ([footer] if footer else [])
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(header))]

    def fmt_row(cells: Sequence[str]) -> str:
        parts = [
            cell.rjust(widths[i]) if i in right_align else cell.ljust(widths[i])
            for i, cell in enumerate(cells)
        ]
        return "| " + " | ".join(parts) + " |"

    separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    lines = [separator, fmt_row(header), separator, *(fmt_row(r) for r in rows), separator]
    if footer:
        lines += [fmt_row(footer), separator]
    return lines
