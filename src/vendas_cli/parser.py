"""Leitura e validação do arquivo CSV de vendas."""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Iterator, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from vendas_cli.exceptions import CSVFileError, CSVFormatError
from vendas_cli.models import Sale

logger = logging.getLogger(__name__)

COL_PRODUCT = "produto"
COL_QUANTITY = "quantidade"
COL_UNIT_PRICE = "preco_unitario"
REQUIRED_COLUMNS: tuple[str, ...] = (COL_PRODUCT, COL_QUANTITY, COL_UNIT_PRICE)
# A coluna de data é opcional; a primeira encontrada é usada.
DATE_COLUMNS: tuple[str, ...] = ("data_venda", "data")
DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y")
# Tentadas em ordem quando o encoding não é informado.
FALLBACK_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "latin-1")
SUPPORTED_DELIMITERS = ",;"


def parse_date(value: str) -> date:
    """Converte ``AAAA-MM-DD`` ou ``DD/MM/AAAA`` em ``date``."""
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida {value!r} (use AAAA-MM-DD ou DD/MM/AAAA)")


def parse_decimal(value: str) -> Decimal:
    """Aceita ``1234.56``, ``1234,56`` e ``1.234,56``."""
    text = value.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"valor numérico inválido {value!r}") from None
    if not number.is_finite():
        raise ValueError(f"valor numérico inválido {value!r}")
    return number


def parse_quantity(value: str) -> int:
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"quantidade inválida {value!r} (esperado inteiro)") from None


def read_sales(
    path: str | Path,
    *,
    encoding: str | None = None,
    skip_invalid: bool = False,
) -> list[Sale]:
    """Lê o CSV em ``path`` e devolve as vendas.

    Com ``skip_invalid=True`` linhas malformadas são registradas no log e
    ignoradas; caso contrário a primeira linha inválida interrompe a leitura.
    """
    file_path = Path(path)
    text = _read_text(file_path, encoding)
    if not text.strip():
        raise CSVFileError(f"arquivo vazio: {file_path}")

    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=_sniff_dialect(text))
    date_column = _validate_header(reader.fieldnames)

    sales: list[Sale] = []
    skipped = 0
    for line, row in _iter_rows(reader):
        try:
            sales.append(_row_to_sale(row, date_column))
        except ValueError as exc:
            if not skip_invalid:
                raise CSVFormatError(str(exc), line=line) from exc
            skipped += 1
            logger.warning("linha %d ignorada: %s", line, exc)

    logger.info("%d vendas lidas de %s (%d linhas ignoradas)", len(sales), file_path, skipped)
    return sales


def _read_text(path: Path, encoding: str | None) -> str:
    if not path.is_file():
        raise CSVFileError(f"arquivo não encontrado: {path}")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CSVFileError(f"não foi possível ler {path}: {exc.strerror}") from exc

    candidates = (encoding,) if encoding else FALLBACK_ENCODINGS
    for candidate in candidates:
        try:
            text = raw.decode(candidate)
        except UnicodeDecodeError:
            logger.debug("encoding %s falhou para %s", candidate, path)
            continue
        except LookupError as exc:
            raise CSVFileError(f"encoding desconhecido: {candidate}") from exc
        if candidate != candidates[0]:
            logger.warning("arquivo %s não é UTF-8; lido como %s", path, candidate)
        return text
    raise CSVFileError(f"não foi possível decodificar {path} com encoding {encoding}")


def _sniff_dialect(text: str) -> type[csv.Dialect]:
    first_line = text.lstrip("﻿").splitlines()[0]
    try:
        return csv.Sniffer().sniff(first_line, delimiters=SUPPORTED_DELIMITERS)
    except csv.Error:
        return csv.excel


def _validate_header(fieldnames: Sequence[str] | None) -> str | None:
    normalized = {_normalize(name) for name in fieldnames or [] if name}
    missing = [col for col in REQUIRED_COLUMNS if col not in normalized]
    if missing:
        raise CSVFormatError(f"colunas obrigatórias ausentes: {', '.join(missing)}", line=1)
    return next((col for col in DATE_COLUMNS if col in normalized), None)


def _iter_rows(reader: csv.DictReader[str]) -> Iterator[tuple[int, dict[str, str]]]:
    for raw_row in reader:
        row = {_normalize(k): (v or "") for k, v in raw_row.items() if isinstance(k, str)}
        if not any(value.strip() for value in row.values()):
            continue
        yield reader.line_num, row


def _row_to_sale(row: Mapping[str, str], date_column: str | None) -> Sale:
    product = row[COL_PRODUCT].strip()
    if not product:
        raise ValueError("produto vazio")
    quantity = parse_quantity(row[COL_QUANTITY])
    if quantity <= 0:
        raise ValueError(f"quantidade deve ser positiva, recebido {quantity}")
    unit_price = parse_decimal(row[COL_UNIT_PRICE])
    if unit_price < 0:
        raise ValueError(f"preço unitário negativo: {unit_price}")
    sale_date = None
    if date_column is not None and row[date_column].strip():
        sale_date = parse_date(row[date_column])
    return Sale(product=product, quantity=quantity, unit_price=unit_price, sale_date=sale_date)


def _normalize(name: str) -> str:
    return name.strip().lstrip("﻿").lower()
