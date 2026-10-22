# vendas-cli

[![CI](https://github.com/CalebDosSantos/relatorio-vendas-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/CalebDosSantos/relatorio-vendas-cli/actions/workflows/ci.yml)

CLI em Python que lê um CSV de vendas e gera um relatório em **tabela de texto** ou **JSON**, com:

- total de vendas por produto (quantidade e faturamento);
- valor total de todas as vendas;
- produto mais vendido;
- filtro opcional por intervalo de datas (`--start` / `--end`).

Usa só a biblioteca padrão em tempo de execução (`csv`, `argparse`, `logging`, `decimal`, ...).

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

+----------+------------+-----------+
| Produto  | Quantidade |     Total |
+----------+------------+-----------+
| Tênis    |          1 | R$ 199,90 |
| Calça    |          2 | R$ 199,80 |
| Camiseta |          4 | R$ 199,60 |
+----------+------------+-----------+
| TOTAL    |          7 | R$ 599,30 |
+----------+------------+-----------+

Vendas processadas: 4
Valor total das vendas: R$ 599,30
Produto mais vendido: Camiseta (4 unidades)
```

Saída em JSON (valores monetários como números com 2 casas):

```json
{
  "periodo": { "inicio": "2025-01-01", "fim": "2025-03-31" },
  "quantidade_vendas": 6,
  "quantidade_itens": 12,
  "valor_total": 818.8,
  "produto_mais_vendido": { "produto": "Camiseta", "quantidade": 4, "total": 199.6 },
  "vendas_por_produto": [
    { "produto": "Calça", "quantidade": 3, "total": 299.7 },
    ...
  ]
}
```

### Com Docker

Sem instalar Python, dá para usar a aplicação por um container:

```bash
docker build -t relatorio-vendas-cli .

# Sem argumentos, mostra a ajuda
docker run --rm relatorio-vendas-cli

# CSVs de exemplo embutidos na imagem
docker run --rm relatorio-vendas-cli /app/examples/vendas_com_data.csv -f json --start 2025-01-01 --end 2025-03-31

# Seus próprios arquivos: monte o diretório atual em /data
docker run --rm -v "$PWD:/data" relatorio-vendas-cli vendas.csv --format text

# Gravando o relatório no host com o seu usuário (evita arquivo com dono errado)
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" relatorio-vendas-cli vendas.csv -f json -o relatorio.json
```

A imagem é multi-stage, baseada em `python:3.13-slim`, e roda como usuário sem privilégios. O comando `vendas-cli` é o `ENTRYPOINT`, então tudo após o nome da imagem são argumentos da CLI. O código de saída do container é o mesmo da CLI.

### Opções

| Opção | Descrição |
|---|---|
| `arquivo` | Caminho do CSV (obrigatório) |
| `-f, --format {text,json}` | Formato de saída (padrão: `text`) |
| `--start AAAA-MM-DD` | Data inicial, inclusiva (também aceita `DD/MM/AAAA`) |
| `--end AAAA-MM-DD` | Data final, inclusiva |
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
| `data_venda` ou `data` | só para filtrar por data | `2025-01-05` ou `05/01/2025` |

- Delimitador `,` ou `;` (detectado automaticamente).
- Cabeçalhos sem diferenciar maiúsculas/minúsculas; espaços e BOM são ignorados.
- O arquivo de exemplo enviado com o desafio está em Latin-1. A CLI detecta isso e avisa no log.

## Decisões de projeto

- **`Decimal` para dinheiro**, para não acumular erro de ponto flutuante. Arredondamento `ROUND_HALF_UP` só na apresentação.
- **Produto mais vendido = maior quantidade de unidades.** Em empate, ganha o maior faturamento e depois a ordem alfabética, para o resultado ser sempre o mesmo. O exemplo com datas tem esse empate (Camiseta e Boné com 4 unidades no 1º trimestre).
- **Filtro de data sem coluna de data é erro, não aviso.** Filtrar um arquivo sem datas devolveria um relatório enganoso, então a CLI recusa com uma mensagem clara.
- **Falha rápida por padrão.** Uma linha inválida aborta com o número da linha. Com `--skip-invalid`, a linha é registrada no log e ignorada.
- **Tabela de produtos ordenada por faturamento** (decrescente).

## Estrutura

```
src/vendas_cli/
├── cli.py         # argparse, logging, códigos de saída
├── parser.py      # leitura/validação do CSV (encoding, delimitador, tipos)
├── core.py        # filtro por data e agregações
├── output.py      # renderização em tabela de texto e JSON
├── models.py      # dataclasses imutáveis (Sale, ProductSummary, SalesReport)
└── exceptions.py  # hierarquia de erros de domínio
tests/             # pytest, um arquivo por módulo
examples/          # CSVs de exemplo
```

O fluxo é linear: `parser` → `core` → `output`, e `cli` orquestra. Só `cli` conhece argparse e stdout, então as outras camadas são testadas de forma isolada.

## Testes e qualidade

```bash
pytest                 # roda os testes com cobertura (configurado em pytest.ini)
mypy src               # tipagem estrita
ruff check src tests   # lint
```

A cobertura atual é de 100% (linhas e branches). O mínimo exigido é 90% (`fail_under` no `pyproject.toml`). O GitHub Actions roda tudo isso em Python 3.10 a 3.13.
