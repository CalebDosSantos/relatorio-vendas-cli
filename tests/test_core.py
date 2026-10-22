from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.core import best_seller, build_report, filter_by_date, summarize_by_product
from vendas_cli.exceptions import DateFilterError
from vendas_cli.models import ProductSummary, Sale


class TestFilterByDate:
    def test_no_bounds_returns_all(self, dated_sales: list[Sale]) -> None:
        assert filter_by_date(dated_sales) == dated_sales

    def test_no_bounds_accepts_undated(self) -> None:
        sales = [Sale("A", 1, Decimal(1))]
        assert filter_by_date(sales) == sales

    def test_inclusive_range(self, dated_sales: list[Sale]) -> None:
        result = filter_by_date(dated_sales, date(2025, 1, 18), date(2025, 2, 2))
        assert [s.sale_date for s in result] == [date(2025, 1, 18), date(2025, 2, 2)]

    def test_only_start(self, dated_sales: list[Sale]) -> None:
        assert len(filter_by_date(dated_sales, start=date(2025, 2, 1))) == 2

    def test_only_end(self, dated_sales: list[Sale]) -> None:
        assert len(filter_by_date(dated_sales, end=date(2025, 1, 31))) == 2

    def test_start_after_end(self, dated_sales: list[Sale]) -> None:
        with pytest.raises(DateFilterError, match="posterior"):
            filter_by_date(dated_sales, date(2025, 3, 1), date(2025, 1, 1))

    def test_undated_sales_with_filter(self) -> None:
        with pytest.raises(DateFilterError, match="1 venda"):
            filter_by_date([Sale("A", 1, Decimal(1))], start=date(2025, 1, 1))


class TestSummaries:
    def test_aggregation_values(self, dated_sales: list[Sale]) -> None:
        result = {s.product: s for s in summarize_by_product(dated_sales)}
        assert result["Camiseta"] == ProductSummary("Camiseta", 4, Decimal("199.60"))
        assert result["Calça"] == ProductSummary("Calça", 2, Decimal("199.80"))
        assert result["Tênis"] == ProductSummary("Tênis", 1, Decimal("199.90"))

    def test_order_by_revenue_desc(self, dated_sales: list[Sale]) -> None:
        names = [s.product for s in summarize_by_product(dated_sales)]
        assert names == ["Tênis", "Calça", "Camiseta"]

    def test_empty(self) -> None:
        assert summarize_by_product([]) == []


class TestBestSeller:
    def test_by_quantity(self, dated_sales: list[Sale]) -> None:
        result = best_seller(summarize_by_product(dated_sales))
        assert result is not None and result.product == "Camiseta"

    def test_tie_broken_by_revenue_then_name(self) -> None:
        summaries = [
            ProductSummary("B", 5, Decimal(10)),
            ProductSummary("A", 5, Decimal(10)),
            ProductSummary("C", 5, Decimal(50)),
        ]
        assert best_seller(summaries) == summaries[2]
        assert best_seller(summaries[:2]) == summaries[1]

    def test_empty(self) -> None:
        assert best_seller([]) is None


class TestBuildReport:
    def test_full_report(self, dated_sales: list[Sale]) -> None:
        report = build_report(dated_sales)
        assert report.total_revenue == Decimal("599.30")
        assert report.total_quantity == 7
        assert report.sales_count == 4
        assert report.best_seller is not None and report.best_seller.product == "Camiseta"
        assert report.start is None and report.end is None

    def test_filtered_report(self, dated_sales: list[Sale]) -> None:
        report = build_report(dated_sales, date(2025, 1, 1), date(2025, 1, 31))
        assert report.total_revenue == Decimal("349.50")
        assert report.sales_count == 2
        assert (report.start, report.end) == (date(2025, 1, 1), date(2025, 1, 31))

    def test_empty_report(self) -> None:
        report = build_report([])
        assert report.products == ()
        assert report.total_revenue == Decimal(0)
        assert report.best_seller is None
