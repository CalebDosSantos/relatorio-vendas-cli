from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from tests.conftest import EXAMPLES_DIR, WriteCSV
from vendas_cli import __version__
from vendas_cli.cli import EXIT_ERROR, EXIT_OK, main

SAMPLE = str(EXAMPLES_DIR / "vendas_exemplo.csv")
DATED = str(EXAMPLES_DIR / "vendas_com_data.csv")
MULTI_YEAR = str(EXAMPLES_DIR / "vendas_2023_2025.csv")
SEMICOLON = str(EXAMPLES_DIR / "vendas_ponto_virgula.csv")
WITH_ERRORS = str(EXAMPLES_DIR / "vendas_com_erros.csv")


def test_text_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "--format", "text"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Valor total das vendas: R$ 599,30" in out
    assert "Produto mais vendido: Camiseta (4 unidades)" in out


def test_default_format_is_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE]) == EXIT_OK
    assert capsys.readouterr().out.startswith("RELATÓRIO DE VENDAS")


def test_json_with_date_range(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([DATED, "--format", "json", "--start", "2025-01-01", "--end", "2025-03-31"])
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["periodo"] == {"inicio": "2025-01-01", "fim": "2025-03-31"}
    assert data["quantidade_vendas"] == 6
    assert data["valor_total"] == 818.8
    # Camiseta e Boné empatam em 4 unidades; desempate pelo faturamento.
    assert data["produto_mais_vendido"]["produto"] == "Camiseta"


def test_brazilian_date_argument(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([DATED, "-f", "json", "--start", "01/04/2025"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["quantidade_vendas"] == 2


def test_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "relatorio.json"
    assert main([SAMPLE, "-f", "json", "-o", str(target)]) == EXIT_OK
    assert capsys.readouterr().out == ""
    assert json.loads(target.read_text(encoding="utf-8"))["valor_total"] == 599.3


def test_output_file_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "nao" / "existe.txt"
    assert main([SAMPLE, "-o", str(target)]) == EXIT_ERROR
    assert "ERROR: erro de E/S" in capsys.readouterr().err


def test_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "x.csv")]) == EXIT_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR: arquivo não encontrado" in captured.err


def test_date_filter_without_date_column(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "--start", "2025-01-01"]) == EXIT_ERROR
    assert "não possuem data" in capsys.readouterr().err


def test_invalid_row_and_skip(write_csv: WriteCSV, capsys: pytest.CaptureFixture[str]) -> None:
    path = str(write_csv("produto,quantidade,preco_unitario\nA,1,10\nB,x,1\n"))
    assert main([path]) == EXIT_ERROR
    assert "linha 3" in capsys.readouterr().err

    assert main([path, "--skip-invalid", "-f", "json"]) == EXIT_OK
    captured = capsys.readouterr()
    assert json.loads(captured.out)["valor_total"] == 10.0
    assert "WARNING: linha 3 ignorada" in captured.err


def test_quiet_hides_warnings(write_csv: WriteCSV, capsys: pytest.CaptureFixture[str]) -> None:
    path = str(write_csv("produto,quantidade,preco_unitario\nB,x,1\n"))
    assert main([path, "--skip-invalid", "-q"]) == EXIT_OK
    assert capsys.readouterr().err == ""


def test_verbose_shows_info(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "-v"]) == EXIT_OK
    assert "INFO: 4 vendas lidas" in capsys.readouterr().err


def test_product_filter_and_sort(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [DATED, "-f", "json", "-p", "camiseta", "--product", "BONÉ", "--sort", "produto"]
    assert main(argv) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["filtros"]["produtos"] == ["camiseta", "BONÉ"]
    assert [p["produto"] for p in data["vendas_por_produto"]] == ["Boné", "Camiseta"]
    assert data["quantidade_itens"] == 13


def test_unknown_product_warns(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([DATED, "-p", "Gravata"]) == EXIT_OK
    captured = capsys.readouterr()
    assert "Nenhuma venda encontrada." in captured.out
    assert "WARNING: produto não encontrado: gravata" in captured.err


def test_top_and_group_by(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([DATED, "-f", "json", "--top", "2", "--group-by", "trimestre"]) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert len(data["vendas_por_produto"]) == 2
    assert data["outros"]["produto"] == "Outros (2)"
    assert [p["periodo"] for p in data["por_periodo"]] == ["2025-T1", "2025-T2"]


def test_group_by_without_dates(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "--group-by", "mes"]) == EXIT_ERROR
    assert "agrupamento por período" in capsys.readouterr().err


def test_multi_year_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([MULTI_YEAR, "-f", "json", "--group-by", "ano"]) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["quantidade_vendas"] == 6000
    years = data["por_periodo"]
    assert [p["periodo"] for p in years] == ["2023", "2024", "2025"]
    assert all(p["variacao_percentual"] > 0 for p in years[1:])


def test_semicolon_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SEMICOLON, "-f", "json", "--start", "01/03/2025"]) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["quantidade_vendas"] == 5
    assert data["valor_total"] == 2120.92


def test_errors_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([WITH_ERRORS]) == EXIT_ERROR
    assert "linha 3: quantidade inválida" in capsys.readouterr().err

    assert main([WITH_ERRORS, "--skip-invalid", "-f", "json"]) == EXIT_OK
    captured = capsys.readouterr()
    assert json.loads(captured.out)["quantidade_vendas"] == 4
    assert captured.err.count("WARNING: linha") == 5


@pytest.mark.parametrize(
    "argv",
    [
        [SAMPLE, "--format", "xml"],
        [SAMPLE, "--start", "2025-99-01"],
        [SAMPLE, "-v", "-q"],
        [SAMPLE, "--top", "0"],
        [SAMPLE, "--top", "dois"],
        [SAMPLE, "--sort", "preco"],
        [SAMPLE, "--group-by", "semana"],
        [],
    ],
)
def test_usage_errors_exit_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_python_dash_m(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["vendas_cli", SAMPLE, "-f", "json"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("vendas_cli", run_name="__main__")
    assert exc_info.value.code == EXIT_OK
    assert json.loads(capsys.readouterr().out)["quantidade_itens"] == 7
