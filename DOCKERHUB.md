# relatorio-vendas-cli

CLI em Python que lê um CSV de vendas e gera um relatório em **tabela de texto** ou **JSON**:

- total de vendas por produto (quantidade e faturamento);
- valor total de todas as vendas;
- produto mais vendido;
- filtro opcional por intervalo de datas.

Código-fonte, testes e documentação completa: https://github.com/CalebDosSantos/relatorio-vendas-cli

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

+----------+------------+-----------+
| Produto  | Quantidade |     Total |
+----------+------------+-----------+
| Calça    |          3 | R$ 299,70 |
| Tênis    |          1 | R$ 199,90 |
| Camiseta |          4 | R$ 199,60 |
| Boné     |          4 | R$ 119,60 |
+----------+------------+-----------+
| TOTAL    |         12 | R$ 818,80 |
+----------+------------+-----------+

Vendas processadas: 6
Valor total das vendas: R$ 818,80
Produto mais vendido: Camiseta (4 unidades)
```

## Formato do CSV

| Coluna | Obrigatória | Exemplo |
|---|---|---|
| `produto` | sim | `Camiseta` |
| `quantidade` | sim | `3` (inteiro > 0) |
| `preco_unitario` | sim | `49.9`, `49,90` ou `1.234,56` |
| `data_venda` ou `data` | só para filtrar por data | `2025-01-05` ou `05/01/2025` |

O delimitador (`,` ou `;`) e o encoding (UTF-8 ou Latin-1) são detectados automaticamente.

## Opções

| Opção | Descrição |
|---|---|
| `-f, --format {text,json}` | Formato de saída (padrão: `text`) |
| `--start` / `--end` | Intervalo de datas, inclusivo (`AAAA-MM-DD` ou `DD/MM/AAAA`) |
| `-o, --output ARQUIVO` | Grava o relatório em arquivo |
| `--encoding ENC` | Força o encoding do CSV |
| `--skip-invalid` | Ignora linhas inválidas com aviso, em vez de abortar |
| `-v` / `-q` | Mais logs / só erros |

O relatório vai para stdout e os logs para stderr. O código de saída do container é o mesmo da CLI: `0` sucesso, `1` erro de dados ou arquivo, `2` argumentos inválidos.

## Tags

| Tag | Descrição |
|---|---|
| `latest` | Última versão publicada |
| `1.0`, `1.0.0` | Versões fixas (semver) |

Plataformas: `linux/amd64` e `linux/arm64`. A imagem é baseada em `python:3.13-slim` e roda como usuário sem privilégios.
