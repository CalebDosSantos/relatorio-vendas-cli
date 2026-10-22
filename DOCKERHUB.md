# relatorio-vendas-cli

CLI em Python que lê um CSV de vendas e gera um relatório em **tabela de texto** ou **JSON**:

- total de vendas por produto (quantidade, faturamento, preço médio e participação);
- valor total de todas as vendas e ticket médio;
- produto mais vendido;
- filtros por período e por produto;
- ranking dos N primeiros produtos;
- quebra por dia, mês, trimestre ou ano, com variação em relação ao período anterior.

Código-fonte, testes e documentação completa: https://github.com/CalebDosSantos/relatorio-vendas-cli

Manual de uso, com receitas de consultas e referência do JSON: https://github.com/CalebDosSantos/relatorio-vendas-cli/blob/main/docs/MANUAL.md

## Uso rápido

```bash
docker pull calebdev/relatorio-vendas-cli

# Ajuda
docker run --rm calebdev/relatorio-vendas-cli

# Seus arquivos: monte o diretório atual em /data
docker run --rm -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv --format text
docker run --rm -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv --format json --start 2025-01-01 --end 2025-03-31

# Gravar o relatório no host com o seu usuário
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv -f json -o relatorio.json
```

Para testar sem ter um CSV, a imagem traz exemplos em `/app/examples`:

```bash
docker run --rm calebdev/relatorio-vendas-cli /app/examples/vendas_com_data.csv --start 2025-01-01 --end 2025-03-31
```

```
RELATÓRIO DE VENDAS
Período: 01/01/2025 a 31/03/2025

+----------+--------+------------+-------------+-----------+--------+
| Produto  | Vendas | Quantidade | Preço médio |     Total |  Part. |
+----------+--------+------------+-------------+-----------+--------+
| Calça    |      2 |          3 |    R$ 99,90 | R$ 299,70 |  36,6% |
| Tênis    |      1 |          1 |   R$ 199,90 | R$ 199,90 |  24,4% |
| Camiseta |      2 |          4 |    R$ 49,90 | R$ 199,60 |  24,4% |
| Boné     |      1 |          4 |    R$ 29,90 | R$ 119,60 |  14,6% |
+----------+--------+------------+-------------+-----------+--------+
| TOTAL    |      6 |         12 |             | R$ 818,80 | 100,0% |
+----------+--------+------------+-------------+-----------+--------+

Vendas processadas: 6
Itens vendidos: 12
Valor total das vendas: R$ 818,80
Ticket médio: R$ 136,47
Produto mais vendido: Camiseta (4 unidades)
```

Outros exemplos embutidos:

| Arquivo | Conteúdo |
|---|---|
| `/app/examples/vendas_2023_2025.csv` | 6.000 vendas em 3 anos, com sazonalidade e crescimento anual |
| `/app/examples/vendas_ponto_virgula.csv` | Formato brasileiro: `;`, `DD/MM/AAAA` e `1.299,90` |
| `/app/examples/vendas_com_erros.csv` | Linhas inválidas, para testar `--skip-invalid` |
| `/app/examples/vendas_exemplo.csv` | O exemplo mínimo do desafio, sem datas |

## Consultas

```bash
# Top 5 por faturamento, resto em "Outros", com evolução ano a ano
docker run --rm calebdev/relatorio-vendas-cli /app/examples/vendas_2023_2025.csv --top 5 --group-by ano

# Dois produtos em 2025, trimestre a trimestre
docker run --rm calebdev/relatorio-vendas-cli /app/examples/vendas_2023_2025.csv \
  -p tênis -p "calça jeans" --start 2025-01-01 --group-by trimestre
```

## Formato do CSV

| Coluna | Obrigatória | Exemplo |
|---|---|---|
| `produto` | sim | `Camiseta` |
| `quantidade` | sim | `3` (inteiro > 0) |
| `preco_unitario` | sim | `49.9`, `49,90` ou `1.234,56` |
| `data_venda` ou `data` | só para `--start`, `--end` e `--group-by` | `2025-01-05` ou `05/01/2025` |

O delimitador (`,` ou `;`) e o encoding (UTF-8 ou Latin-1) são detectados automaticamente.

## Opções

| Opção | Descrição |
|---|---|
| `-f, --format {text,json}` | Formato de saída (padrão: `text`) |
| `--start` / `--end` | Intervalo de datas, inclusivo (`AAAA-MM-DD` ou `DD/MM/AAAA`) |
| `-p, --product NOME` | Só este produto; repita para vários (ignora maiúsculas) |
| `--sort {faturamento,quantidade,produto}` | Ordenação da tabela (padrão: `faturamento`) |
| `--top N` | Os N primeiros produtos; o resto somado em "Outros" |
| `--group-by {dia,mes,trimestre,ano}` | Quebra por período, com variação em relação ao anterior |
| `-o, --output ARQUIVO` | Grava o relatório em arquivo |
| `--encoding ENC` | Força o encoding do CSV |
| `--skip-invalid` | Ignora linhas inválidas com aviso, em vez de abortar |
| `-v` / `-q` | Mais logs / só erros |

O relatório vai para stdout e os logs para stderr. O código de saída do container é o mesmo da CLI: `0` sucesso, `1` erro de dados ou arquivo, `2` argumentos inválidos.

## Tags

| Tag | Descrição |
|---|---|
| `latest` | Última versão publicada |
| `1.1`, `1.1.0` | Versão atual: consultas por produto, ranking e período |
| `1.0`, `1.0.0` | Primeira versão |

Plataformas: `linux/amd64` e `linux/arm64`. A imagem é baseada em `python:3.13-slim` e roda como usuário sem privilégios.
