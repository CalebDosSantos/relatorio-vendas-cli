from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.core import (
    best_seller,
    build_report,
    filter_by_date,
    filter_by_products,
    period_key,
    split_top,
    summarize_by_period,
    summarize_by_product,
)
from vendas_cli.exceptions import DateFilterError
from vendas_cli.models import Granularity, PeriodSummary, ProductSummary, Sale, SortKey


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
        assert result["Camiseta"] == ProductSummary("Camiseta", 4, Decimal("199.60"), 2)
        assert result["Calça"] == ProductSummary("Calça", 2, Decimal("199.80"), 1)
        assert result["Tênis"] == ProductSummary("Tênis", 1, Decimal("199.90"), 1)

    def test_order_by_revenue_desc(self, dated_sales: list[Sale]) -> None:
        names = [s.product for s in summarize_by_product(dated_sales)]
        assert names == ["Tênis", "Calça", "Camiseta"]

    @pytest.mark.parametrize(
        ("sort", "expected"),
        [
            (SortKey.REVENUE, ["Tênis", "Calça", "Camiseta"]),
            (SortKey.QUANTITY, ["Camiseta", "Calça", "Tênis"]),
            (SortKey.NAME, ["Calça", "Camiseta", "Tênis"]),
        ],
    )
    def test_sort_keys(self, dated_sales: list[Sale], sort: SortKey, expected: list[str]) -> None:
        assert [s.product for s in summarize_by_product(dated_sales, sort)] == expected

    def test_sort_by_name_ignores_case(self) -> None:
        sales = [Sale("bermuda", 1, Decimal(1)), Sale("Boné", 1, Decimal(1))]
        names = [s.product for s in summarize_by_product(sales, SortKey.NAME)]
        assert names == ["bermuda", "Boné"]

    def test_empty(self) -> None:
        assert summarize_by_product([]) == []

    def test_average_price(self) -> None:
        assert ProductSummary("A", 4, Decimal("10.00")).average_price == Decimal("2.5")
        assert ProductSummary("A", 0, Decimal(0)).average_price == Decimal(0)


class TestFilterByProducts:
    def test_no_products_returns_all(self, dated_sales: list[Sale]) -> None:
        assert filter_by_products(dated_sales, []) == dated_sales

    def test_case_and_whitespace_insensitive(self, dated_sales: list[Sale]) -> None:
        result = filter_by_products(dated_sales, [" CAMISETA ", "tênis"])
        assert [s.product for s in result] == ["Camiseta", "Camiseta", "Tênis"]

    def test_unknown_product_warns(
        self, dated_sales: list[Sale], caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            result = filter_by_products(dated_sales, ["Calça", "Gravata"])
        assert len(result) == 1
        assert "produto não encontrado: gravata" in caplog.text
        assert "calça" not in caplog.text


class TestSplitTop:
    def test_without_top(self, dated_sales: list[Sale]) -> None:
        summaries = summarize_by_product(dated_sales)
        assert split_top(summaries, None) == (summaries, None)
        assert split_top(summaries, 3) == (summaries, None)

    def test_groups_the_rest_as_others(self, dated_sales: list[Sale]) -> None:
        summaries = summarize_by_product(dated_sales)
        kept, others = split_top(summaries, 1)
        assert [s.product for s in kept] == ["Tênis"]
        assert others == ProductSummary("Outros (2)", 6, Decimal("399.40"), 3)

    def test_invalid_top(self, dated_sales: list[Sale]) -> None:
        with pytest.raises(ValueError, match="positivo"):
            split_top(summarize_by_product(dated_sales), 0)


class TestPeriods:
    @pytest.mark.parametrize(
        ("granularity", "expected"),
        [
            (Granularity.DAY, "2025-11-28"),
            (Granularity.MONTH, "2025-11"),
            (Granularity.QUARTER, "2025-T4"),
            (Granularity.YEAR, "2025"),
        ],
    )
    def test_period_key(self, granularity: Granularity, expected: str) -> None:
        assert period_key(date(2025, 11, 28), granularity) == expected

    @pytest.mark.parametrize(("month", "quarter"), [(1, 1), (3, 1), (4, 2), (9, 3), (12, 4)])
    def test_quarter_boundaries(self, month: int, quarter: int) -> None:
        assert period_key(date(2025, month, 1), Granularity.QUARTER) == f"2025-T{quarter}"

    def test_monthly_summary(self, dated_sales: list[Sale]) -> None:
        assert summarize_by_period(dated_sales, Granularity.MONTH) == [
            PeriodSummary("2025-01", 2, 5, Decimal("349.50"), "Camiseta", None),
            PeriodSummary(
                "2025-02",
                1,
                1,
                Decimal("49.90"),
                "Camiseta",
                (Decimal("49.90") - Decimal("349.50")) * 100 / Decimal("349.50"),
            ),
            PeriodSummary(
                "2025-04",
                1,
                1,
                Decimal("199.90"),
                "Tênis",
                (Decimal("199.90") - Decimal("49.90")) * 100 / Decimal("49.90"),
            ),
        ]

    def test_growth_after_zero_revenue_is_none(self) -> None:
        sales = [
            Sale("Brinde", 1, Decimal(0), date(2024, 5, 1)),
            Sale("A", 1, Decimal(10), date(2025, 5, 1)),
        ]
        periods = summarize_by_period(sales, Granularity.YEAR)
        assert [p.growth for p in periods] == [None, None]

    def test_requires_dates(self) -> None:
        with pytest.raises(DateFilterError, match="agrupamento por período"):
            summarize_by_period([Sale("A", 1, Decimal(1))], Granularity.MONTH)

    def test_empty(self) -> None:
        assert summarize_by_period([], Granularity.YEAR) == []


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
        assert report.average_ticket == Decimal(0)
        assert report.share(Decimal(10)) == Decimal(0)
        assert report.others is None and report.periods == ()

    def test_metrics(self, dated_sales: list[Sale]) -> None:
        report = build_report(dated_sales)
        assert report.average_ticket == Decimal("149.825")
        assert report.share(Decimal("599.30")) == Decimal(100)

    def test_all_options(self, dated_sales: list[Sale]) -> None:
        report = build_report(
            dated_sales,
            end=date(2025, 3, 31),
            products=["camiseta", "calça"],
            sort=SortKey.QUANTITY,
            top=1,
            group_by=Granularity.QUARTER,
        )
        assert [p.product for p in report.products] == ["Camiseta"]
        assert report.others == ProductSummary("Outros (1)", 2, Decimal("199.80"), 1)
        # totais e mais vendido consideram também o que ficou em "Outros"
        assert report.total_revenue == Decimal("399.40")
        assert report.sales_count == 3
        assert report.best_seller is not None and report.best_seller.product == "Camiseta"
        assert report.product_filter == ("camiseta", "calça")
        assert report.group_by is Granularity.QUARTER
        assert [p.period for p in report.periods] == ["2025-T1"]

    def test_best_seller_ignores_sort_and_top(self, dated_sales: list[Sale]) -> None:
        report = build_report(dated_sales, sort=SortKey.NAME, top=1)
        assert [p.product for p in report.products] == ["Calça"]
        assert report.best_seller is not None and report.best_seller.product == "Camiseta"

    def test_group_by_requires_dates(self) -> None:
        with pytest.raises(DateFilterError, match="agrupamento"):
            build_report([Sale("A", 1, Decimal(1))], group_by=Granularity.YEAR)
