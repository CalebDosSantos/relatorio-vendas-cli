"""Permite executar a CLI com ``python -m vendas_cli``."""

import sys

from vendas_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
