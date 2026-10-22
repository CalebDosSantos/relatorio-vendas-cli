"""Exceções de domínio da aplicação."""

from __future__ import annotations


class VendasError(Exception):
    """Erro base: tudo que a CLI deve reportar ao usuário sem stack trace."""


class CSVFileError(VendasError):
    """O arquivo não pode ser lido (inexistente, vazio, encoding, etc.)."""


class CSVFormatError(VendasError):
    """O conteúdo do CSV é inválido (colunas ausentes, valores malformados)."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(f"linha {line}: {message}" if line is not None else message)


class DateFilterError(VendasError):
    """O filtro de datas não pode ser aplicado."""
