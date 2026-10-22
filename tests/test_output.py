from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.core import build_report
from vendas_cli.models import Sale
from vendas_cli.output import OutputFormat, format_money, render, render_json, render_text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), "R$ 0,00"),
        (Decimal("49.9"), "R$ 49,90"),
        (Decimal("1234567.891"), "R$ 1.234.567,89"),
        (Decimal("0.005"), "R$ 0,01"),
    ],
)
def test_format_money(value: Decimal, expected: str) -> None:
    assert format_money(value) == expected


def test_render_text(dated_sales: list[Sale]) -> None:
    text = render_text(build_report(dated_sales))
    assert text.splitlines() == [
        "RELATÓRIO DE VENDAS",
        "Período: todas as datas",
        "",
        "+----------+------------+-----------+",
        "| Produto  | Quantidade |     Total |",
        "+----------+------------+-----------+",
        "| Tênis    |          1 | R$ 199,90 |",
        "| Calça    |          2 | R$ 199,80 |",
        "| Camiseta |          4 | R$ 199,60 |",
        "+----------+------------+-----------+",
        "| TOTAL    |          7 | R$ 599,30 |",
        "+----------+------------+-----------+",
        "",
        "Vendas processadas: 4",
        "Valor total das vendas: R$ 599,30",
        "Produto mais vendido: Camiseta (4 unidades)",
    ]


@pytest.mark.parametrize(
    ("start", "end", "label"),
    [
        (date(2025, 1, 1), date(2025, 3, 31), "01/01/2025 a 31/03/2025"),
        (date(2025, 1, 1), None, "01/01/2025 a fim"),
        (None, date(2025, 3, 31), "início a 31/03/2025"),
    ],
)
def test_render_text_period(
    dated_sales: list[Sale], start: date | None, end: date | None, label: str
) -> None:
    assert f"Período: {label}" in render_text(build_report(dated_sales, start, end))


def test_render_text_empty() -> None:
    assert render_text(build_report([])).endswith("Nenhuma venda encontrada.")


def test_render_json(dated_sales: list[Sale]) -> None:
    data = json.loads(render_json(build_report(dated_sales, end=date(2025, 12, 31))))
    assert data == {
        "periodo": {"inicio": None, "fim": "2025-12-31"},
        "quantidade_vendas": 4,
        "quantidade_itens": 7,
        "valor_total": 599.3,
        "produto_mais_vendido": {"produto": "Camiseta", "quantidade": 4, "total": 199.6},
        "vendas_por_produto": [
            {"produto": "Tênis", "quantidade": 1, "total": 199.9},
            {"produto": "Calça", "quantidade": 2, "total": 199.8},
            {"produto": "Camiseta", "quantidade": 4, "total": 199.6},
        ],
    }


def test_render_json_keeps_unicode(dated_sales: list[Sale]) -> None:
    assert "Calça" in render_json(build_report(dated_sales))


def test_render_json_empty() -> None:
    data = json.loads(render_json(build_report([])))
    assert data["produto_mais_vendido"] is None
    assert data["vendas_por_produto"] == []


def test_render_dispatch(dated_sales: list[Sale]) -> None:
    report = build_report(dated_sales)
    assert render(report, OutputFormat.TEXT) == render_text(report)
    assert render(report, OutputFormat.JSON) == render_json(report)
