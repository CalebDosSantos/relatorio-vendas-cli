"""Gera um CSV de vendas fictícias para exemplos e testes manuais.

O resultado é determinístico para a mesma semente. Simula sazonalidade
(Black Friday, Natal, volta às aulas), crescimento anual de volume,
reajuste anual de preços e promoções pontuais.

Uso:
    python scripts/gerar_vendas.py examples/vendas_2023_2025.csv \\
        --inicio 2023-01-01 --fim 2025-12-31 --linhas 6000
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# produto: (preço no primeiro ano, peso de popularidade)
PRODUCTS: dict[str, tuple[str, int]] = {
    "Camiseta": ("49.90", 30),
    "Calça Jeans": ("139.90", 14),
    "Tênis": ("249.90", 10),
    "Boné": ("39.90", 16),
    "Meia (par)": ("14.90", 24),
    "Jaqueta": ("299.90", 5),
    "Moletom": ("159.90", 8),
    "Bermuda": ("79.90", 12),
    "Vestido": ("189.90", 7),
    "Saia": ("99.90", 6),
    "Camisa Social": ("129.90", 9),
    "Cinto": ("59.90", 8),
    "Mochila": ("179.90", 5),
    "Óculos de Sol": ("149.90", 4),
    "Chinelo": ("29.90", 15),
}
MONTH_WEIGHT = {1: 1.1, 2: 1.2, 3: 0.9, 4: 0.8, 5: 1.0, 6: 0.9, 7: 1.0, 8: 0.9}
MONTH_WEIGHT |= {9: 0.8, 10: 1.0, 11: 1.6, 12: 1.9}
YEARLY_VOLUME_GROWTH = 1.15
YEARLY_PRICE_INCREASE = Decimal("1.05")
PROMO_CHANCE = 0.12
QUANTITIES = ([1, 2, 3, 4, 5, 6, 10], [45, 25, 12, 7, 5, 4, 2])


def generate(start: date, end: date, rows: int, seed: int) -> list[tuple[str, str, int, str]]:
    rng = random.Random(seed)
    names = list(PRODUCTS)
    popularity = [PRODUCTS[n][1] for n in names]
    days = [start + timedelta(d) for d in range((end - start).days + 1)]
    day_weights = [
        MONTH_WEIGHT[d.month] * YEARLY_VOLUME_GROWTH ** (d.year - start.year) for d in days
    ]

    sales = []
    for _ in range(rows):
        day = rng.choices(days, day_weights)[0]
        product = rng.choices(names, popularity)[0]
        price = Decimal(PRODUCTS[product][0]) * YEARLY_PRICE_INCREASE ** (day.year - start.year)
        if rng.random() < PROMO_CHANCE:
            price *= Decimal(1) - Decimal(rng.choice(["0.10", "0.15", "0.20"]))
        quantity = rng.choices(*QUANTITIES)[0]
        sales.append((day.isoformat(), product, quantity, f"{price.quantize(Decimal('0.01'))}"))
    sales.sort()
    return sales


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("saida", type=Path)
    parser.add_argument("--inicio", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--fim", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--linhas", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=2025)
    args = parser.parse_args()

    with args.saida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["data_venda", "produto", "quantidade", "preco_unitario"])
        writer.writerows(generate(args.inicio, args.fim, args.linhas, args.seed))


if __name__ == "__main__":
    main()
