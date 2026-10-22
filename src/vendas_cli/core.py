"""Regras de negócio: filtragem e agregação das vendas."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal

from vendas_cli.exceptions import DateFilterError
from vendas_cli.models import ProductSummary, Sale, SalesReport

logger = logging.getLogger(__name__)


def filter_by_date(
    sales: Iterable[Sale],
    start: date | None = None,
    end: date | None = None,
) -> list[Sale]:
    """Mantém as vendas com data em ``[start, end]`` (limites inclusivos).

    Sem limites, devolve todas as vendas. Com algum limite, todas as vendas
    precisam ter data; caso contrário o filtro seria ambíguo.
    """
    items = list(sales)
    if start is None and end is None:
        return items
    if start is not None and end is not None and start > end:
        raise DateFilterError(f"data inicial {start} posterior à data final {end}")

    undated = sum(1 for sale in items if sale.sale_date is None)
    if undated:
        raise DateFilterError(
            f"filtro por data solicitado, mas {undated} venda(s) não possuem data "
            "(o CSV precisa de uma coluna 'data_venda' ou 'data')"
        )

    filtered = [
        sale
        for sale in items
        if sale.sale_date is not None
        and (start is None or sale.sale_date >= start)
        and (end is None or sale.sale_date <= end)
    ]
    logger.info("filtro de datas manteve %d de %d vendas", len(filtered), len(items))
    return filtered


def summarize_by_product(sales: Iterable[Sale]) -> list[ProductSummary]:
    """Agrega quantidade e faturamento por produto, ordenado por faturamento."""
    quantities: dict[str, int] = {}
    revenues: dict[str, Decimal] = {}
    for sale in sales:
        quantities[sale.product] = quantities.get(sale.product, 0) + sale.quantity
        revenues[sale.product] = revenues.get(sale.product, Decimal(0)) + sale.total

    summaries = [ProductSummary(name, quantities[name], revenues[name]) for name in quantities]
    summaries.sort(key=lambda s: (-s.revenue, s.product))
    return summaries


def best_seller(summaries: Sequence[ProductSummary]) -> ProductSummary | None:
    """Produto com maior quantidade vendida.

    Empates são resolvidos pelo maior faturamento e, depois, pela ordem
    alfabética, garantindo resultado determinístico.
    """
    if not summaries:
        return None
    return min(summaries, key=lambda s: (-s.quantity, -s.revenue, s.product))


def build_report(
    sales: Iterable[Sale],
    start: date | None = None,
    end: date | None = None,
) -> SalesReport:
    """Aplica o filtro de datas e calcula todos os indicadores do relatório."""
    selected = filter_by_date(sales, start, end)
    summaries = summarize_by_product(selected)
    return SalesReport(
        products=tuple(summaries),
        total_revenue=sum((s.revenue for s in summaries), Decimal(0)),
        total_quantity=sum(s.quantity for s in summaries),
        sales_count=len(selected),
        best_seller=best_seller(summaries),
        start=start,
        end=end,
    )
