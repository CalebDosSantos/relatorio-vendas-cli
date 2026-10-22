"""Regras de negócio: filtragem e agregação das vendas."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from decimal import Decimal

from vendas_cli.exceptions import DateFilterError
from vendas_cli.models import (
    Granularity,
    PeriodSummary,
    ProductSummary,
    Sale,
    SalesReport,
    SortKey,
)

logger = logging.getLogger(__name__)

_SORT_KEYS: dict[SortKey, Callable[[ProductSummary], tuple[object, ...]]] = {
    SortKey.REVENUE: lambda s: (-s.revenue, s.product),
    SortKey.QUANTITY: lambda s: (-s.quantity, -s.revenue, s.product),
    SortKey.NAME: lambda s: (s.product.casefold(), s.product),
}


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

    _require_dates(items, "filtro por data")
    filtered = [
        sale
        for sale in items
        if sale.sale_date is not None
        and (start is None or sale.sale_date >= start)
        and (end is None or sale.sale_date <= end)
    ]
    logger.info("filtro de datas manteve %d de %d vendas", len(filtered), len(items))
    return filtered


def filter_by_products(sales: Iterable[Sale], products: Sequence[str]) -> list[Sale]:
    """Mantém as vendas dos produtos informados (sem diferenciar maiúsculas).

    Sem produtos, devolve todas as vendas. Nomes que não aparecem em nenhuma
    venda geram um aviso no log, para não passarem despercebidos.
    """
    items = list(sales)
    if not products:
        return items

    wanted = {name.strip().casefold() for name in products}
    filtered = [sale for sale in items if sale.product.casefold() in wanted]

    found = {sale.product.casefold() for sale in filtered}
    for name in sorted(wanted - found):
        logger.warning("produto não encontrado: %s", name)
    logger.info("filtro de produtos manteve %d de %d vendas", len(filtered), len(items))
    return filtered


def summarize_by_product(
    sales: Iterable[Sale], sort: SortKey = SortKey.REVENUE
) -> list[ProductSummary]:
    """Agrega quantidade, faturamento e número de vendas por produto."""
    quantities: dict[str, int] = {}
    revenues: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for sale in sales:
        quantities[sale.product] = quantities.get(sale.product, 0) + sale.quantity
        revenues[sale.product] = revenues.get(sale.product, Decimal(0)) + sale.total
        counts[sale.product] = counts.get(sale.product, 0) + 1

    summaries = [
        ProductSummary(name, quantities[name], revenues[name], counts[name]) for name in quantities
    ]
    summaries.sort(key=_SORT_KEYS[sort])
    return summaries


def best_seller(summaries: Sequence[ProductSummary]) -> ProductSummary | None:
    """Produto com maior quantidade vendida.

    Empates são resolvidos pelo maior faturamento e, depois, pela ordem
    alfabética, garantindo resultado determinístico.
    """
    if not summaries:
        return None
    return min(summaries, key=_SORT_KEYS[SortKey.QUANTITY])


def split_top(
    summaries: Sequence[ProductSummary], top: int | None
) -> tuple[list[ProductSummary], ProductSummary | None]:
    """Separa os ``top`` primeiros produtos e soma o restante em "Outros"."""
    if top is None or top >= len(summaries):
        return list(summaries), None
    if top < 1:
        raise ValueError(f"top deve ser positivo, recebido {top}")

    kept, rest = list(summaries[:top]), summaries[top:]
    others = ProductSummary(
        product=f"Outros ({len(rest)})",
        quantity=sum(s.quantity for s in rest),
        revenue=sum((s.revenue for s in rest), Decimal(0)),
        sales_count=sum(s.sales_count for s in rest),
    )
    return kept, others


def period_key(day: date, granularity: Granularity) -> str:
    """Rótulo ordenável do período: ``2025-01-05``, ``2025-01``, ``2025-T1``, ``2025``."""
    if granularity is Granularity.DAY:
        return day.isoformat()
    if granularity is Granularity.MONTH:
        return f"{day.year}-{day.month:02d}"
    if granularity is Granularity.QUARTER:
        return f"{day.year}-T{(day.month - 1) // 3 + 1}"
    return str(day.year)


def summarize_by_period(sales: Iterable[Sale], granularity: Granularity) -> list[PeriodSummary]:
    """Agrega as vendas por período, em ordem cronológica.

    A variação (``growth``) compara com o período anterior que teve vendas;
    períodos sem nenhuma venda não aparecem.
    """
    items = list(sales)
    _require_dates(items, "agrupamento por período")

    groups: dict[str, list[Sale]] = {}
    for sale in items:
        assert sale.sale_date is not None  # garantido por _require_dates
        groups.setdefault(period_key(sale.sale_date, granularity), []).append(sale)

    periods: list[PeriodSummary] = []
    previous: Decimal | None = None
    for key in sorted(groups):
        group = groups[key]
        summaries = summarize_by_product(group)
        revenue = sum((s.revenue for s in summaries), Decimal(0))
        top = best_seller(summaries)
        assert top is not None  # todo grupo tem ao menos uma venda
        periods.append(
            PeriodSummary(
                period=key,
                sales_count=len(group),
                quantity=sum(s.quantity for s in summaries),
                revenue=revenue,
                best_seller=top.product,
                growth=(revenue - previous) * 100 / previous if previous else None,
            )
        )
        previous = revenue
    return periods


def build_report(
    sales: Iterable[Sale],
    start: date | None = None,
    end: date | None = None,
    *,
    products: Sequence[str] = (),
    sort: SortKey = SortKey.REVENUE,
    top: int | None = None,
    group_by: Granularity | None = None,
) -> SalesReport:
    """Aplica os filtros e calcula todos os indicadores do relatório.

    Totais e produto mais vendido consideram todas as vendas filtradas,
    inclusive as que ficam em "Outros" por causa do ``top``.
    """
    selected = filter_by_products(filter_by_date(sales, start, end), products)
    summaries = summarize_by_product(selected, sort)
    kept, others = split_top(summaries, top)
    return SalesReport(
        products=tuple(kept),
        total_revenue=sum((s.revenue for s in summaries), Decimal(0)),
        total_quantity=sum(s.quantity for s in summaries),
        sales_count=len(selected),
        best_seller=best_seller(summaries),
        start=start,
        end=end,
        others=others,
        product_filter=tuple(products),
        group_by=group_by,
        periods=tuple(summarize_by_period(selected, group_by)) if group_by else (),
    )


def _require_dates(sales: Sequence[Sale], purpose: str) -> None:
    undated = sum(1 for sale in sales if sale.sale_date is None)
    if undated:
        raise DateFilterError(
            f"{purpose} solicitado, mas {undated} venda(s) não possuem data "
            "(o CSV precisa de uma coluna 'data_venda' ou 'data')"
        )
