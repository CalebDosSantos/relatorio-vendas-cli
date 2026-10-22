from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tests.conftest import DATA_DIR, EXAMPLES_DIR, WriteCSV
from vendas_cli.exceptions import CSVFileError, CSVFormatError
from vendas_cli.models import Sale
from vendas_cli.parser import parse_date, parse_decimal, parse_quantity, read_sales


class TestParseDate:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2025-03-31", date(2025, 3, 31)),
            ("31/03/2025", date(2025, 3, 31)),
            (" 2025-01-01 ", date(2025, 1, 1)),
        ],
    )
    def test_valid_formats(self, value: str, expected: date) -> None:
        assert parse_date(value) == expected

    @pytest.mark.parametrize("value", ["2025-13-01", "ontem", "", "03-31-2025"])
    def test_invalid(self, value: str) -> None:
        with pytest.raises(ValueError, match="data inválida"):
            parse_date(value)


class TestParseNumbers:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("49.9", "49.9"), ("49,90", "49.90"), ("1.234,56", "1234.56"), (" 10 ", "10")],
    )
    def test_decimal(self, value: str, expected: str) -> None:
        assert parse_decimal(value) == Decimal(expected)

    @pytest.mark.parametrize("value", ["abc", "", "NaN", "Infinity"])
    def test_decimal_invalid(self, value: str) -> None:
        with pytest.raises(ValueError, match="valor numérico inválido"):
            parse_decimal(value)

    def test_quantity(self) -> None:
        assert parse_quantity(" 7 ") == 7

    @pytest.mark.parametrize("value", ["1.5", "x", ""])
    def test_quantity_invalid(self, value: str) -> None:
        with pytest.raises(ValueError, match="quantidade inválida"):
            parse_quantity(value)


class TestReadSales:
    def test_reads_sample_without_dates(self) -> None:
        sales = read_sales(EXAMPLES_DIR / "vendas_exemplo.csv")
        assert sales == [
            Sale("Camiseta", 3, Decimal("49.9")),
            Sale("Calça", 2, Decimal("99.9")),
            Sale("Camiseta", 1, Decimal("49.9")),
            Sale("Tênis", 1, Decimal("199.9")),
        ]

    def test_reads_dates(self) -> None:
        sales = read_sales(EXAMPLES_DIR / "vendas_com_data.csv")
        assert len(sales) == 8
        assert sales[0].sale_date == date(2025, 1, 5)

    def test_latin1_fallback(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            sales = read_sales(DATA_DIR / "latin1_sample.csv")
        assert [s.product for s in sales] == ["Camiseta", "Calça", "Camiseta", "Tênis"]
        assert "lido como latin-1" in caplog.text

    def test_explicit_encoding(self) -> None:
        sales = read_sales(DATA_DIR / "latin1_sample.csv", encoding="latin-1")
        assert sales[1].product == "Calça"

    def test_explicit_wrong_encoding(self) -> None:
        with pytest.raises(CSVFileError, match="não foi possível decodificar"):
            read_sales(DATA_DIR / "latin1_sample.csv", encoding="utf-8")

    def test_unknown_encoding(self) -> None:
        with pytest.raises(CSVFileError, match="encoding desconhecido"):
            read_sales(DATA_DIR / "latin1_sample.csv", encoding="nao-existe")

    def test_semicolon_and_header_normalization(self, write_csv: WriteCSV) -> None:
        path = write_csv("﻿ Produto ;QUANTIDADE;Preco_Unitario;Data\nBoné;2;29,90;10/02/2025\n")
        assert read_sales(path) == [Sale("Boné", 2, Decimal("29.90"), date(2025, 2, 10))]

    def test_blank_lines_are_ignored(self, write_csv: WriteCSV) -> None:
        path = write_csv("produto,quantidade,preco_unitario\n\nA,1,10\n,,\n")
        assert read_sales(path) == [Sale("A", 1, Decimal("10"))]

    def test_empty_date_cell_is_none(self, write_csv: WriteCSV) -> None:
        path = write_csv("produto,quantidade,preco_unitario,data\nA,1,10,\n")
        assert read_sales(path)[0].sale_date is None

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(CSVFileError, match="arquivo não encontrado"):
            read_sales(tmp_path / "nada.csv")

    def test_directory_is_not_a_file(self, tmp_path: Path) -> None:
        with pytest.raises(CSVFileError, match="arquivo não encontrado"):
            read_sales(tmp_path)

    def test_unreadable_file(self, write_csv: WriteCSV, monkeypatch: pytest.MonkeyPatch) -> None:
        path = write_csv("produto,quantidade,preco_unitario\n")

        def boom(self: Path) -> bytes:
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(Path, "read_bytes", boom)
        with pytest.raises(CSVFileError, match="Permission denied"):
            read_sales(path)

    def test_empty_file(self, write_csv: WriteCSV) -> None:
        with pytest.raises(CSVFileError, match="arquivo vazio"):
            read_sales(write_csv("  \n"))

    def test_missing_columns(self, write_csv: WriteCSV) -> None:
        with pytest.raises(CSVFormatError, match="ausentes: quantidade, preco_unitario"):
            read_sales(write_csv("produto,valor\nA,1\n"))

    def test_single_column_header(self, write_csv: WriteCSV) -> None:
        with pytest.raises(CSVFormatError, match="linha 1: colunas obrigatórias ausentes"):
            read_sales(write_csv("produto\nA\n"))

    def test_header_only_returns_empty(self, write_csv: WriteCSV) -> None:
        assert read_sales(write_csv("produto,quantidade,preco_unitario\n")) == []

    @pytest.mark.parametrize(
        ("row", "message"),
        [
            (",1,10", "produto vazio"),
            ("A,0,10", "quantidade deve ser positiva"),
            ("A,dois,10", "quantidade inválida"),
            ("A,1,-5", "preço unitário negativo"),
            ("A,1,abc", "valor numérico inválido"),
        ],
    )
    def test_invalid_row_reports_line(self, write_csv: WriteCSV, row: str, message: str) -> None:
        path = write_csv(f"produto,quantidade,preco_unitario\nOK,1,1\n{row}\n")
        with pytest.raises(CSVFormatError, match=f"linha 3: {message}") as exc_info:
            read_sales(path)
        assert exc_info.value.line == 3

    def test_skip_invalid(self, write_csv: WriteCSV, caplog: pytest.LogCaptureFixture) -> None:
        path = write_csv("produto,quantidade,preco_unitario\nA,1,10\nB,x,10\nC,2,5\n")
        with caplog.at_level(logging.WARNING):
            sales = read_sales(path, skip_invalid=True)
        assert [s.product for s in sales] == ["A", "C"]
        assert "linha 3 ignorada" in caplog.text

    def test_invalid_date_row(self, write_csv: WriteCSV) -> None:
        path = write_csv("produto,quantidade,preco_unitario,data_venda\nA,1,10,32/01/2025\n")
        with pytest.raises(CSVFormatError, match="linha 2: data inválida"):
            read_sales(path)
