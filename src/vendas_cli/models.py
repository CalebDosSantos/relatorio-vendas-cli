"""Modelos de dados imutáveis usados entre as camadas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class SortKey(str, Enum):
    """Critério de ordenação da tabela de produtos."""

    REVENUE = "faturamento"
    QUANTITY = "quantidade"
    NAME = "produto"


class Granularity(str, Enum):
    """Granularidade do agrupamento por período."""

    DAY = "dia"
    MONTH = "mes"
    QUARTER = "trimestre"
    YEAR = "ano"


@dataclass(frozen=True, slots=True)
class Sale:
    """Uma linha de venda do CSV."""

    product: str
    quantity: int
    unit_price: Decimal
    sale_date: date | None = None

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass(frozen=True, slots=True)
class ProductSummary:
    """Totais agregados de um produto."""

    product: str
    quantity: int
    revenue: Decimal
    sales_count: int = 0

    @property
    def average_price(self) -> Decimal:
        """Preço médio por unidade, ponderado pela quantidade."""
        return self.revenue / self.quantity if self.quantity else Decimal(0)


@dataclass(frozen=True, slots=True)
class PeriodSummary:
    """Totais de um período (dia, mês, trimestre ou ano)."""

    period: str
    sales_count: int
    quantity: int
    revenue: Decimal
    best_seller: str
    growth: Decimal | None = None
    """Variação percentual do faturamento em relação ao período anterior."""


@dataclass(frozen=True, slots=True)
class SalesReport:
    """Resultado consolidado do processamento."""

    products: tuple[ProductSummary, ...]
    total_revenue: Decimal
    total_quantity: int
    sales_count: int
    best_seller: ProductSummary | None
    start: date | None = None
    end: date | None = None
    others: ProductSummary | None = None
    """Soma dos produtos que ficaram fora do ``--top``."""
    product_filter: tuple[str, ...] = ()
    group_by: Granularity | None = None
    periods: tuple[PeriodSummary, ...] = ()

    @property
    def average_ticket(self) -> Decimal:
        """Faturamento médio por venda (linha do CSV)."""
        return self.total_revenue / self.sales_count if self.sales_count else Decimal(0)

    def share(self, revenue: Decimal) -> Decimal:
        """Participação percentual de ``revenue`` no faturamento total."""
        return revenue * 100 / self.total_revenue if self.total_revenue else Decimal(0)
