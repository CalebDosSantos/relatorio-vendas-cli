from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from vendas_cli.models import Sale

DATA_DIR = Path(__file__).parent
EXAMPLES_DIR = DATA_DIR.parent / "examples"

WriteCSV = Callable[..., Path]


@pytest.fixture
def write_csv(tmp_path: Path) -> WriteCSV:
    def _write(content: str, name: str = "vendas.csv", encoding: str = "utf-8") -> Path:
        path = tmp_path / name
        path.write_text(content, encoding=encoding)
        return path

    return _write


@pytest.fixture
def dated_sales() -> list[Sale]:
    return [
        Sale("Camiseta", 3, Decimal("49.90"), date(2025, 1, 5)),
        Sale("Calça", 2, Decimal("99.90"), date(2025, 1, 18)),
        Sale("Camiseta", 1, Decimal("49.90"), date(2025, 2, 2)),
        Sale("Tênis", 1, Decimal("199.90"), date(2025, 4, 8)),
    ]
