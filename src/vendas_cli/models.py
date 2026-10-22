"""Modelos de dados imutáveis usados entre as camadas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


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
