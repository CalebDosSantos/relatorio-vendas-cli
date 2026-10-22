from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.core import build_report
from vendas_cli.models import Granularity, Sale
from vendas_cli.output import (
    OutputFormat,
    format_money,
    format_percent,
    render,
    render_json,
    render_text,
)


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


@pytest.mark.parametrize(
    ("value", "signed", "expected"),
    [
        (Decimal("33.3555"), False, "33,4%"),
        (Decimal("100"), False, "100,0%"),
        (Decimal("12.25"), True, "+12,3%"),
        (Decimal("-85.7210"), True, "-85,7%"),
        (Decimal("0"), True, "+0,0%"),
        (None, True, "-"),
    ],
)
def test_format_percent(value: Decimal | None, signed: bool, expected: str) -> None:
    assert format_percent(value, signed=signed) == expected


def test_render_text(dated_sales: list[Sale]) -> None:
    text = render_text(build_report(dated_sales))
    assert text.splitlines() == [
        "RELATÓRIO DE VENDAS",
        "Período: todas as datas",
        "",
        "+----------+--------+------------+-------------+-----------+--------+",
        "| Produto  | Vendas | Quantidade | Preço médio |     Total |  Part. |",
        "+----------+--------+------------+-------------+-----------+--------+",
        "| Tênis    |      1 |          1 |   R$ 199,90 | R$ 199,90 |  33,4% |",
        "| Calça    |      1 |          2 |    R$ 99,90 | R$ 199,80 |  33,3% |",
        "| Camiseta |      2 |          4 |    R$ 49,90 | R$ 199,60 |  33,3% |",
        "+----------+--------+------------+-------------+-----------+--------+",
        "| TOTAL    |      4 |          7 |             | R$ 599,30 | 100,0% |",
        "+----------+--------+------------+-------------+-----------+--------+",
        "",
        "Vendas processadas: 4",
        "Itens vendidos: 7",
        "Valor total das vendas: R$ 599,30",
        "Ticket médio: R$ 149,83",
        "Produto mais vendido: Camiseta (4 unidades)",
    ]


def test_render_text_with_queries(dated_sales: list[Sale]) -> None:
    report = build_report(
        dated_sales, products=["camiseta", "tênis", "calça"], top=1, group_by=Granularity.MONTH
    )
    lines = render_text(report).splitlines()
    assert lines[2] == "Produtos: camiseta, tênis, calça"
    assert "| Outros (2) |      3 |          6 |    R$ 66,57 | R$ 399,40 |  66,6% |" in lines
    assert lines[-8:] == [
        "Por mês:",
        "+---------+--------+------------+-----------+----------+--------------+",
        "| Período | Vendas | Quantidade |     Total | Variação | Mais vendido |",
        "+---------+--------+------------+-----------+----------+--------------+",
        "| 2025-01 |      2 |          5 | R$ 349,50 |        - | Camiseta     |",
        "| 2025-02 |      1 |          1 |  R$ 49,90 |   -85,7% | Camiseta     |",
        "| 2025-04 |      1 |          1 | R$ 199,90 |  +300,6% | Tênis        |",
        "+---------+--------+------------+-----------+----------+--------------+",
    ]


@pytest.mark.parametrize(
    ("granularity", "title"),
    [
        (Granularity.DAY, "Por dia:"),
        (Granularity.MONTH, "Por mês:"),
        (Granularity.QUARTER, "Por trimestre:"),
        (Granularity.YEAR, "Por ano:"),
    ],
)
def test_render_text_period_titles(
    dated_sales: list[Sale], granularity: Granularity, title: str
) -> None:
    assert title in render_text(build_report(dated_sales, group_by=granularity)).splitlines()


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


def test_render_text_empty_after_product_filter(dated_sales: list[Sale]) -> None:
    lines = render_text(build_report(dated_sales, products=["Gravata"])).splitlines()
    assert lines[2:] == ["Produtos: Gravata", "", "Nenhuma venda encontrada."]


def test_render_json(dated_sales: list[Sale]) -> None:
    data = json.loads(render_json(build_report(dated_sales, end=date(2025, 12, 31))))
    camiseta = {
        "produto": "Camiseta",
        "quantidade": 4,
        "quantidade_vendas": 2,
        "total": 199.6,
        "preco_medio": 49.9,
        "participacao": 33.31,
    }
    assert data == {
        "periodo": {"inicio": None, "fim": "2025-12-31"},
        "filtros": {"produtos": []},
        "quantidade_vendas": 4,
        "quantidade_itens": 7,
        "valor_total": 599.3,
        "ticket_medio": 149.83,
        "produto_mais_vendido": camiseta,
        "vendas_por_produto": [
            {
                "produto": "Tênis",
                "quantidade": 1,
                "quantidade_vendas": 1,
                "total": 199.9,
                "preco_medio": 199.9,
                "participacao": 33.36,
            },
            {
                "produto": "Calça",
                "quantidade": 2,
                "quantidade_vendas": 1,
                "total": 199.8,
                "preco_medio": 99.9,
                "participacao": 33.34,
            },
            camiseta,
        ],
        "outros": None,
        "agrupamento": None,
        "por_periodo": [],
    }


def test_render_json_with_queries(dated_sales: list[Sale]) -> None:
    report = build_report(
        dated_sales, products=["Tênis", "Calça"], top=1, group_by=Granularity.YEAR
    )
    data = json.loads(render_json(report))
    assert data["filtros"] == {"produtos": ["Tênis", "Calça"]}
    assert [p["produto"] for p in data["vendas_por_produto"]] == ["Tênis"]
    assert data["outros"] == {
        "produto": "Outros (1)",
        "quantidade": 2,
        "quantidade_vendas": 1,
        "total": 199.8,
        "preco_medio": 99.9,
        "participacao": 49.99,
    }
    assert data["agrupamento"] == "ano"
    assert data["por_periodo"] == [
        {
            "periodo": "2025",
            "quantidade_vendas": 2,
            "quantidade_itens": 3,
            "valor_total": 399.7,
            "variacao_percentual": None,
            "produto_mais_vendido": "Calça",
        }
    ]


def test_render_json_growth(dated_sales: list[Sale]) -> None:
    data = json.loads(render_json(build_report(dated_sales, group_by=Granularity.MONTH)))
    assert [p["variacao_percentual"] for p in data["por_periodo"]] == [None, -85.72, 300.6]


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
