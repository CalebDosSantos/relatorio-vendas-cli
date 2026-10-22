# vendas-cli

[![CI](https://github.com/CalebDosSantos/relatorio-vendas-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/CalebDosSantos/relatorio-vendas-cli/actions/workflows/ci.yml)

CLI em Python que lê um CSV de vendas e gera um relatório em **tabela de texto** ou **JSON**, com:

- total de vendas por produto (quantidade, faturamento, preço médio e participação);
- valor total de todas as vendas e ticket médio;
- produto mais vendido;
- filtro opcional por intervalo de datas (`--start` / `--end`).

E consultas mais elaboradas:

- filtro por um ou mais produtos (`--product`);
- ordenação e ranking dos N primeiros, com o resto somado em "Outros" (`--sort`, `--top`);
- quebra por dia, mês, trimestre ou ano, com variação em relação ao período anterior (`--group-by`).

Usa só a biblioteca padrão em tempo de execução (`csv`, `argparse`, `logging`, `decimal`, ...).

**[Manual de uso completo](docs/MANUAL.md)**: todas as opções, receitas de consultas, formato do JSON e solução de erros.

## Requisitos

- Python 3.10 ou superior

## Instalação

```bash
git clone https://github.com/CalebDosSantos/relatorio-vendas-cli.git
cd relatorio-vendas-cli
python -m venv .venv && source .venv/bin/activate
pip install .            # só a CLI
pip install -e '.[dev]'  # para desenvolvimento (pytest, cobertura, mypy, ruff)
```

## Uso

```bash
vendas-cli examples/vendas_exemplo.csv --format text
vendas-cli examples/vendas_com_data.csv --format json --start 2025-01-01 --end 2025-03-31
```

Saída em texto:

```
RELATÓRIO DE VENDAS
Período: todas as datas

+----------+--------+------------+-------------+-----------+--------+
| Produto  | Vendas | Quantidade | Preço médio |     Total |  Part. |
+----------+--------+------------+-------------+-----------+--------+
| Tênis    |      1 |          1 |   R$ 199,90 | R$ 199,90 |  33,4% |
| Calça    |      1 |          2 |    R$ 99,90 | R$ 199,80 |  33,3% |
| Camiseta |      2 |          4 |    R$ 49,90 | R$ 199,60 |  33,3% |
+----------+--------+------------+-------------+-----------+--------+
| TOTAL    |      4 |          7 |             | R$ 599,30 | 100,0% |
+----------+--------+------------+-------------+-----------+--------+

Vendas processadas: 4
Itens vendidos: 7
Valor total das vendas: R$ 599,30
Ticket médio: R$ 149,83
Produto mais vendido: Camiseta (4 unidades)
```

"Vendas" é o número de linhas do CSV; "Quantidade", o de unidades. "Part." é a participação no faturamento total.

Saída em JSON (valores monetários e percentuais como números com 2 casas):

```bash
vendas-cli examples/vendas_com_data.csv -f json --end 2025-03-31 --top 1 --group-by trimestre
```

```json
{
  "periodo": { "inicio": null, "fim": "2025-03-31" },
  "filtros": { "produtos": [] },
  "quantidade_vendas": 6,
  "quantidade_itens": 12,
  "valor_total": 818.8,
  "ticket_medio": 136.47,
  "produto_mais_vendido": { "produto": "Camiseta", "quantidade": 4, "quantidade_vendas": 2, "total": 199.6, "preco_medio": 49.9, "participacao": 24.38 },
  "vendas_por_produto": [
    { "produto": "Calça", "quantidade": 3, "quantidade_vendas": 2, "total": 299.7, "preco_medio": 99.9, "participacao": 36.6 }
  ],
  "outros": { "produto": "Outros (3)", "quantidade": 9, "quantidade_vendas": 4, "total": 519.1, "preco_medio": 57.68, "participacao": 63.4 },
  "agrupamento": "trimestre",
  "por_periodo": [
    { "periodo": "2025-T1", "quantidade_vendas": 6, "quantidade_itens": 12, "valor_total": 818.8, "variacao_percentual": null, "produto_mais_vendido": "Camiseta" }
  ]
}
```

### Consultas

```bash
# Os 5 produtos de maior faturamento, o resto somado em "Outros", com evolução anual
vendas-cli examples/vendas_2023_2025.csv --top 5 --group-by ano

# Ranking por unidades vendidas
vendas-cli examples/vendas_2023_2025.csv --sort quantidade --top 3

# Só dois produtos em 2025, trimestre a trimestre (nomes sem diferenciar maiúsculas)
vendas-cli examples/vendas_2023_2025.csv -p tênis -p "calça jeans" --start 2025-01-01 --group-by trimestre
```

Trecho da saída do último comando:

```
Por trimestre:
+---------+--------+------------+--------------+----------+--------------+
| Período | Vendas | Quantidade |        Total | Variação | Mais vendido |
+---------+--------+------------+--------------+----------+--------------+
| 2025-T1 |     81 |        212 | R$ 41.443,00 |        - | Calça Jeans  |
| 2025-T2 |     70 |        171 | R$ 33.495,68 |   -19,2% | Calça Jeans  |
| 2025-T3 |     57 |        147 | R$ 29.830,66 |   -10,9% | Calça Jeans  |
| 2025-T4 |    117 |        226 | R$ 44.321,83 |   +48,6% | Calça Jeans  |
+---------+--------+------------+--------------+----------+--------------+
```

Os filtros se combinam: primeiro período (`--start`/`--end`), depois produtos (`--product`). Ordenação, `--top` e `--group-by` atuam sobre o resultado filtrado.

### Com Docker

Sem instalar Python, dá para usar a aplicação por um container. A imagem está publicada no Docker Hub em [`calebdev/relatorio-vendas-cli`](https://hub.docker.com/r/calebdev/relatorio-vendas-cli), para amd64 e arm64:

```bash
docker pull calebdev/relatorio-vendas-cli

# Sem argumentos, mostra a ajuda
docker run --rm calebdev/relatorio-vendas-cli

# CSVs de exemplo embutidos na imagem
docker run --rm calebdev/relatorio-vendas-cli /app/examples/vendas_com_data.csv -f json --start 2025-01-01 --end 2025-03-31

# Seus próprios arquivos: monte o diretório atual em /data
docker run --rm -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv --format text

# Gravando o relatório no host com o seu usuário (evita arquivo com dono errado)
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv -f json -o relatorio.json
```

Para fixar uma versão, use a tag correspondente (ex.: `calebdev/relatorio-vendas-cli:1.1.0`). Para construir a imagem a partir do código:

```bash
docker build -t relatorio-vendas-cli .
docker run --rm -v "$PWD:/data" relatorio-vendas-cli vendas.csv
```

Novas versões são publicadas automaticamente pelo GitHub Actions ao criar uma tag `vX.Y.Z`.

A imagem é multi-stage, baseada em `python:3.13-slim`, e roda como usuário sem privilégios. O comando `vendas-cli` é o `ENTRYPOINT`, então tudo após o nome da imagem são argumentos da CLI. O código de saída do container é o mesmo da CLI.

### Opções

| Opção | Descrição |
|---|---|
| `arquivo` | Caminho do CSV (obrigatório) |
| `-f, --format {text,json}` | Formato de saída (padrão: `text`) |
| `--start AAAA-MM-DD` | Data inicial, inclusiva (também aceita `DD/MM/AAAA`) |
| `--end AAAA-MM-DD` | Data final, inclusiva |
| `-p, --product NOME` | Considera só este produto; repita para vários (ignora maiúsculas) |
| `--sort {faturamento,quantidade,produto}` | Ordenação da tabela de produtos (padrão: `faturamento`) |
| `--top N` | Mostra os N primeiros produtos e soma o resto em "Outros" |
| `--group-by {dia,mes,trimestre,ano}` | Quebra por período, com variação em relação ao anterior |
| `-o, --output ARQUIVO` | Grava o relatório em arquivo em vez da saída padrão |
| `--encoding ENC` | Força o encoding do CSV (padrão: tenta UTF-8 e cai para Latin-1) |
| `--skip-invalid` | Ignora linhas inválidas com aviso, em vez de abortar |
| `-v, --verbose` / `-q, --quiet` | Mais logs / só erros |
| `--version` | Mostra a versão |

Também dá para rodar com `python -m vendas_cli ...`.

**Códigos de saída:** `0` sucesso · `1` erro de dados ou de arquivo · `2` erro de uso (argumentos inválidos).

Logs e erros vão para **stderr**; o relatório vai para **stdout**. Assim, `vendas-cli x.csv -f json | jq` funciona sem ruído.

## Formato do CSV

| Coluna | Obrigatória | Exemplo |
|---|---|---|
| `produto` | sim | `Camiseta` |
| `quantidade` | sim | `3` (inteiro > 0) |
| `preco_unitario` | sim | `49.9`, `49,90` ou `1.234,56` |
| `data_venda` ou `data` | só para `--start`, `--end` e `--group-by` | `2025-01-05` ou `05/01/2025` |

- Delimitador `,` ou `;` (detectado automaticamente).
- Cabeçalhos sem diferenciar maiúsculas/minúsculas; espaços e BOM são ignorados.
- O arquivo de exemplo enviado com o desafio está em Latin-1. A CLI detecta isso e avisa no log.

### Arquivos de exemplo

| Arquivo | Conteúdo |
|---|---|
| `vendas_exemplo.csv` | O exemplo do desafio (4 vendas, sem datas) |
| `vendas_com_data.csv` | 8 vendas em 2025, com empate no produto mais vendido do 1º trimestre |
| `vendas_2023_2025.csv` | 6.000 vendas em 3 anos, com sazonalidade, crescimento anual, reajuste de preços e promoções |
| `vendas_ponto_virgula.csv` | Formato brasileiro: `;`, datas `DD/MM/AAAA` e valores `1.299,90` |
| `vendas_com_erros.csv` | 5 linhas inválidas, para testar a mensagem de erro e o `--skip-invalid` |

O arquivo de 3 anos é gerado por `scripts/gerar_vendas.py`, de forma determinística (semente fixa). Para gerar outro período ou tamanho:

```bash
python scripts/gerar_vendas.py vendas.csv --inicio 2020-01-01 --fim 2025-12-31 --linhas 50000
```

## Decisões de projeto

- **`Decimal` para dinheiro**, para não acumular erro de ponto flutuante. Arredondamento `ROUND_HALF_UP` só na apresentação.
- **Produto mais vendido = maior quantidade de unidades.** Em empate, ganha o maior faturamento e depois a ordem alfabética, para o resultado ser sempre o mesmo. O exemplo com datas tem esse empate (Camiseta e Boné com 4 unidades no 1º trimestre).
- **Filtro de data sem coluna de data é erro, não aviso.** Filtrar um arquivo sem datas devolveria um relatório enganoso, então a CLI recusa com uma mensagem clara.
- **Falha rápida por padrão.** Uma linha inválida aborta com o número da linha. Com `--skip-invalid`, a linha é registrada no log e ignorada.
- **Tabela de produtos ordenada por faturamento** (decrescente), a menos que `--sort` diga outra coisa.
- **`--top` não muda os totais.** O resto entra numa linha "Outros", então a tabela sempre fecha com o total. O produto mais vendido também considera todos os produtos, não só os exibidos.
- **Variação compara com o período anterior que teve vendas.** Períodos sem nenhuma venda não aparecem na quebra. Se o período anterior faturou zero, a variação fica vazia (`-` / `null`), em vez de infinita.
- **Produto inexistente em `--product` gera aviso, não erro**, para que um nome digitado errado não passe despercebido.

## Estrutura

```
src/vendas_cli/
├── cli.py         # argparse, logging, códigos de saída
├── parser.py      # leitura/validação do CSV (encoding, delimitador, tipos)
├── core.py        # filtros, agregações, ranking e quebra por período
├── output.py      # renderização em tabela de texto e JSON
├── models.py      # dataclasses imutáveis e enums (Sale, SalesReport, SortKey, ...)
└── exceptions.py  # hierarquia de erros de domínio
tests/             # pytest, um arquivo por módulo
examples/          # CSVs de exemplo
scripts/           # gerador de dados de exemplo
```

O fluxo é linear: `parser` → `core` → `output`, e `cli` orquestra. Só `cli` conhece argparse e stdout, então as outras camadas são testadas de forma isolada.

## Testes e qualidade

```bash
pytest                 # roda os testes com cobertura (configurado em pytest.ini)
mypy src               # tipagem estrita
ruff check src tests   # lint
```

A cobertura atual é de 100% (linhas e branches). O mínimo exigido é 90% (`fail_under` no `pyproject.toml`). O GitHub Actions roda tudo isso em Python 3.10 a 3.13.
