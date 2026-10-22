# Manual de uso — vendas-cli

Este manual mostra tudo o que a CLI faz, com exemplos reais. Todos os comandos usam os arquivos de [`examples/`](../examples) e podem ser copiados e executados na raiz do repositório.

**Sumário**

1. [Instalação](#1-instalação)
2. [Primeiros passos](#2-primeiros-passos)
3. [Arquivo de entrada](#3-arquivo-de-entrada)
4. [Lendo o relatório](#4-lendo-o-relatório)
5. [Referência de opções](#5-referência-de-opções)
6. [Consultas: receitas prontas](#6-consultas-receitas-prontas)
7. [Saída JSON](#7-saída-json)
8. [Erros, avisos e códigos de saída](#8-erros-avisos-e-códigos-de-saída)
9. [Usando com Docker](#9-usando-com-docker)
10. [Dúvidas frequentes](#10-dúvidas-frequentes)

---

## 1. Instalação

**Com Python 3.10+:**

```bash
git clone https://github.com/CalebDosSantos/relatorio-vendas-cli.git
cd relatorio-vendas-cli
python -m venv .venv && source .venv/bin/activate
pip install .
vendas-cli --version
```

**Com Docker**, sem instalar Python, veja a [seção 9](#9-usando-com-docker).

## 2. Primeiros passos

A forma mais simples é passar só o arquivo:

```bash
vendas-cli examples/vendas_exemplo.csv
```

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

A partir daí, as opções se combinam livremente:

```bash
vendas-cli examples/vendas_2023_2025.csv --start 2025-01-01 --top 5 --group-by trimestre
vendas-cli examples/vendas_2023_2025.csv --format json -o relatorio.json
```

Para ver todas as opções: `vendas-cli --help`.

## 3. Arquivo de entrada

O arquivo é um CSV com uma linha de cabeçalho e uma venda por linha.

| Coluna | Obrigatória | Formato | Exemplos |
|---|---|---|---|
| `produto` | sim | texto não vazio | `Camiseta`, `Meia (par)` |
| `quantidade` | sim | inteiro maior que zero | `3` |
| `preco_unitario` | sim | decimal, zero ou positivo | `49.9`, `49,90`, `1.299,90` |
| `data_venda` ou `data` | não\* | data | `2025-01-05`, `05/01/2025` |

\* A data é necessária para usar `--start`, `--end` e `--group-by`.

A CLI aceita variações comuns sem configuração:

- **Delimitador** `,` ou `;`, detectado pelo cabeçalho.
- **Encoding** UTF-8 (com ou sem BOM) ou Latin-1. Se o arquivo não for UTF-8, ele é lido como Latin-1 e um aviso é exibido. Para forçar outro, use `--encoding`.
- **Cabeçalho** sem diferenciar maiúsculas e com espaços ao redor: `Produto`, ` QUANTIDADE ` e `Preco_Unitario` são aceitos.
- **Colunas extras** são ignoradas.
- **Linhas em branco** são ignoradas.

Exemplo no formato brasileiro ([`vendas_ponto_virgula.csv`](../examples/vendas_ponto_virgula.csv)):

```
Data;Produto;Quantidade;Preco_Unitario
03/02/2025;Camiseta;2;49,90
10/02/2025;Jaqueta;1;1.299,90
```

### Arquivos de exemplo

| Arquivo | Vendas | Para que serve |
|---|---|---|
| `vendas_exemplo.csv` | 4 | O exemplo do desafio, sem datas |
| `vendas_com_data.csv` | 8 | Exemplo pequeno com datas em 2025 |
| `vendas_2023_2025.csv` | 6.000 | Três anos de vendas, para explorar as consultas |
| `vendas_ponto_virgula.csv` | 10 | Formato brasileiro (`;`, `DD/MM/AAAA`, `1.299,90`) |
| `vendas_com_erros.csv` | 9 | 5 linhas inválidas, para ver erros e `--skip-invalid` |

O arquivo de três anos simula sazonalidade (picos em novembro e dezembro), crescimento de volume a cada ano, reajuste anual de preços e promoções. Ele é gerado por [`scripts/gerar_vendas.py`](../scripts/gerar_vendas.py), que pode criar arquivos de qualquer tamanho:

```bash
python scripts/gerar_vendas.py vendas.csv --inicio 2020-01-01 --fim 2025-12-31 --linhas 50000 --seed 7
```

## 4. Lendo o relatório

### Tabela de produtos

| Coluna | Significado |
|---|---|
| Produto | Nome como aparece no CSV |
| Vendas | Número de linhas do CSV daquele produto |
| Quantidade | Total de unidades vendidas |
| Preço médio | Faturamento ÷ quantidade (reflete promoções e reajustes) |
| Total | Faturamento: soma de `quantidade × preco_unitario` |
| Part. | Participação no faturamento total do relatório |

A linha **TOTAL** soma todos os produtos do relatório, inclusive os que ficaram em "Outros" (veja `--top`).

### Resumo

| Linha | Significado |
|---|---|
| Vendas processadas | Linhas consideradas, depois dos filtros |
| Itens vendidos | Soma das quantidades |
| Valor total das vendas | Faturamento total |
| Ticket médio | Faturamento ÷ vendas processadas |
| Produto mais vendido | Maior quantidade de unidades. Em empate, maior faturamento e depois ordem alfabética |

### Quebra por período

Aparece só com `--group-by`. Cada linha é um período com pelo menos uma venda.

| Coluna | Significado |
|---|---|
| Período | `2025-03-14` (dia), `2025-03` (mês), `2025-T1` (trimestre) ou `2025` (ano) |
| Vendas, Quantidade, Total | Como na tabela de produtos, só daquele período |
| Variação | Variação do faturamento em relação ao período anterior da lista. `-` no primeiro período |
| Mais vendido | Produto mais vendido naquele período |

## 5. Referência de opções

```
vendas-cli ARQUIVO [opções]
```

### Filtros

| Opção | Descrição |
|---|---|
| `--start DATA` | Considera vendas a partir desta data, inclusive |
| `--end DATA` | Considera vendas até esta data, inclusive |
| `-p NOME`, `--product NOME` | Considera só este produto. Repita para vários |

- As datas aceitam `AAAA-MM-DD` ou `DD/MM/AAAA`. Pode usar só `--start`, só `--end` ou os dois.
- Os nomes de produto não diferenciam maiúsculas: `-p "calça jeans"` encontra `Calça Jeans`. Acentos fazem diferença: `calca` não encontra `Calça`.
- Os filtros se combinam: primeiro o período, depois os produtos.

### Apresentação

| Opção | Valores | Padrão | Descrição |
|---|---|---|---|
| `--sort` | `faturamento`, `quantidade`, `produto` | `faturamento` | Ordem da tabela de produtos |
| `--top N` | inteiro ≥ 1 | todos | Mostra os N primeiros e soma o resto em "Outros (k)" |
| `--group-by` | `dia`, `mes`, `trimestre`, `ano` | — | Acrescenta a quebra por período |
| `-f`, `--format` | `text`, `json` | `text` | Formato de saída |

`--top` atua depois de `--sort`: `--sort quantidade --top 3` são os 3 produtos com mais unidades. Os totais e o produto mais vendido continuam considerando todos os produtos.

### Entrada e saída

| Opção | Descrição |
|---|---|
| `-o ARQUIVO`, `--output ARQUIVO` | Grava o relatório no arquivo (UTF-8), em vez de exibir |
| `--encoding ENC` | Força o encoding do CSV (`utf-8`, `latin-1`, `cp1252`...) |
| `--skip-invalid` | Ignora linhas inválidas com um aviso, em vez de parar no primeiro erro |

### Mensagens

| Opção | Descrição |
|---|---|
| `-v`, `--verbose` | Mostra também mensagens informativas (linhas lidas, efeito de cada filtro) |
| `-q`, `--quiet` | Mostra só erros |
| `--version` | Mostra a versão |
| `-h`, `--help` | Mostra a ajuda |

## 6. Consultas: receitas prontas

### Quais produtos vendem mais unidades?

```bash
vendas-cli examples/vendas_2023_2025.csv --sort quantidade --top 5
```

```
+-------------+--------+------------+-------------+-----------------+--------+
| Produto     | Vendas | Quantidade | Preço médio |           Total |  Part. |
+-------------+--------+------------+-------------+-----------------+--------+
| Camiseta    |   1052 |       2371 |    R$ 51,44 |   R$ 121.974,71 |   9,2% |
| Meia (par)  |    856 |       2032 |    R$ 15,43 |    R$ 31.360,46 |   2,4% |
| Boné        |    562 |       1331 |    R$ 41,18 |    R$ 54.815,60 |   4,1% |
| Calça Jeans |    505 |       1196 |   R$ 144,92 |   R$ 173.327,81 |  13,1% |
| Chinelo     |    500 |       1182 |    R$ 31,04 |    R$ 36.691,88 |   2,8% |
| Outros (10) |   2525 |       5750 |   R$ 157,36 |   R$ 904.827,93 |  68,4% |
+-------------+--------+------------+-------------+-----------------+--------+
| TOTAL       |   6000 |      13862 |             | R$ 1.322.998,39 | 100,0% |
+-------------+--------+------------+-------------+-----------------+--------+
```

Compare com o padrão (`--sort faturamento`): Meia (par) é o 2º em unidades, mas tem só 2,4% do faturamento.

### Como o faturamento evoluiu ano a ano?

```bash
vendas-cli examples/vendas_2023_2025.csv --group-by ano --top 3
```

```
Por ano:
+---------+--------+------------+---------------+----------+--------------+
| Período | Vendas | Quantidade |         Total | Variação | Mais vendido |
+---------+--------+------------+---------------+----------+--------------+
| 2023    |   1735 |       4007 | R$ 356.447,70 |        - | Camiseta     |
| 2024    |   2025 |       4729 | R$ 441.753,87 |   +23,9% | Camiseta     |
| 2025    |   2240 |       5126 | R$ 524.796,82 |   +18,8% | Camiseta     |
+---------+--------+------------+---------------+----------+--------------+
```

### Como foi o fim de ano (Black Friday e Natal)?

```bash
vendas-cli examples/vendas_2023_2025.csv --start 2025-11-01 --end 2025-12-31 --group-by mes --top 3
```

```
Por mês:
+---------+--------+------------+--------------+----------+--------------+
| Período | Vendas | Quantidade |        Total | Variação | Mais vendido |
+---------+--------+------------+--------------+----------+--------------+
| 2025-11 |    281 |        624 | R$ 61.404,50 |        - | Camiseta     |
| 2025-12 |    340 |        790 | R$ 81.332,13 |   +32,5% | Camiseta     |
+---------+--------+------------+--------------+----------+--------------+
```

### Como dois produtos se comportaram em cada trimestre?

```bash
vendas-cli examples/vendas_2023_2025.csv -p tênis -p "calça jeans" --start 2025-01-01 --group-by trimestre
```

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

### Como um produto vendeu dia a dia?

```bash
vendas-cli examples/vendas_2023_2025.csv -p camiseta --start 2025-12-20 --end 2025-12-24 --group-by dia
```

```
Por dia:
+------------+--------+------------+-----------+----------+--------------+
| Período    | Vendas | Quantidade |     Total | Variação | Mais vendido |
+------------+--------+------------+-----------+----------+--------------+
| 2025-12-20 |      5 |          9 | R$ 495,09 |        - | Camiseta     |
| 2025-12-21 |      1 |          1 |  R$ 55,01 |   -88,9% | Camiseta     |
| 2025-12-23 |      2 |          5 | R$ 242,05 |  +340,0% | Camiseta     |
| 2025-12-24 |      1 |          1 |  R$ 55,01 |   -77,3% | Camiseta     |
+------------+--------+------------+-----------+----------+--------------+
```

O dia 22 não aparece porque não teve venda de camiseta. Por isso a variação do dia 23 é calculada em relação ao dia 21.

### Qual é o ticket médio de um produto?

```bash
vendas-cli examples/vendas_2023_2025.csv -p jaqueta -q | grep "Ticket"
```

```
Ticket médio: R$ 694,02
```

### Exportar para outra ferramenta

```bash
# Arquivo JSON
vendas-cli examples/vendas_2023_2025.csv -f json --group-by mes -o relatorio.json

# Participação de cada produto, com jq
vendas-cli examples/vendas_2023_2025.csv -f json | jq -r '.vendas_por_produto[] | "\(.produto): \(.participacao)%"'

# Meses em que o faturamento caiu
vendas-cli examples/vendas_2023_2025.csv -f json --group-by mes \
  | jq -r '.por_periodo[] | select((.variacao_percentual // 0) < 0) | "\(.periodo) \(.variacao_percentual)%"'
```

## 7. Saída JSON

Com `--format json`, o relatório tem sempre as mesmas chaves. Valores monetários e percentuais são números com até 2 casas decimais.

```json
{
  "periodo": { "inicio": "2025-01-01", "fim": null },
  "filtros": { "produtos": ["camiseta"] },
  "quantidade_vendas": 406,
  "quantidade_itens": 884,
  "valor_total": 47457.34,
  "ticket_medio": 116.89,
  "produto_mais_vendido": { "...": "mesmo formato de um produto" },
  "vendas_por_produto": [
    {
      "produto": "Camiseta",
      "quantidade": 884,
      "quantidade_vendas": 406,
      "total": 47457.34,
      "preco_medio": 53.68,
      "participacao": 100.0
    }
  ],
  "outros": null,
  "agrupamento": "ano",
  "por_periodo": [
    {
      "periodo": "2025",
      "quantidade_vendas": 406,
      "quantidade_itens": 884,
      "valor_total": 47457.34,
      "variacao_percentual": null,
      "produto_mais_vendido": "Camiseta"
    }
  ]
}
```

| Chave | Tipo | Descrição |
|---|---|---|
| `periodo.inicio`, `periodo.fim` | texto ISO ou `null` | Valores de `--start` e `--end` |
| `filtros.produtos` | lista de texto | Nomes passados em `--product`, como foram digitados |
| `quantidade_vendas` | inteiro | Linhas consideradas |
| `quantidade_itens` | inteiro | Soma das quantidades |
| `valor_total` | número | Faturamento total |
| `ticket_medio` | número | `valor_total ÷ quantidade_vendas` |
| `produto_mais_vendido` | produto ou `null` | `null` quando não há vendas |
| `vendas_por_produto` | lista de produtos | Na ordem de `--sort`, limitada por `--top` |
| `outros` | produto ou `null` | Soma dos produtos fora do `--top` |
| `agrupamento` | texto ou `null` | Valor de `--group-by` |
| `por_periodo` | lista | Vazia sem `--group-by` |
| `por_periodo[].variacao_percentual` | número ou `null` | `null` no primeiro período ou quando o anterior faturou zero |

Cada **produto** tem `produto`, `quantidade`, `quantidade_vendas`, `total`, `preco_medio` e `participacao` (em %).

## 8. Erros, avisos e códigos de saída

O relatório vai para a **saída padrão** e as mensagens para a **saída de erro**. Assim, `vendas-cli ... -f json > arquivo.json` grava só o JSON.

| Código | Quando |
|---|---|
| `0` | Relatório gerado |
| `1` | Problema no arquivo ou nos dados (mensagem com `ERROR:`) |
| `2` | Opção inválida na linha de comando |

**Erros comuns**

| Mensagem | Causa | O que fazer |
|---|---|---|
| `arquivo não encontrado` | Caminho errado | Confira o caminho. No Docker, veja a [seção 9](#9-usando-com-docker) |
| `colunas obrigatórias ausentes: ...` | Cabeçalho sem `produto`, `quantidade` ou `preco_unitario` | Renomeie as colunas |
| `linha N: quantidade inválida 'dois'` | Valor malformado na linha N | Corrija a linha ou use `--skip-invalid` |
| `linha N: data inválida '2025-02-30'` | Data inexistente ou em outro formato | Use `AAAA-MM-DD` ou `DD/MM/AAAA` |
| `filtro por data solicitado, mas N venda(s) não possuem data` | `--start`/`--end` num CSV sem datas | Acrescente a coluna `data_venda` |
| `agrupamento por período solicitado, mas ...` | `--group-by` num CSV sem datas | Idem |
| `data inicial ... posterior à data final ...` | `--start` depois de `--end` | Inverta as datas |

Por padrão, a primeira linha inválida interrompe a leitura e informa o número da linha. Com `--skip-invalid`, cada linha inválida vira um aviso e o relatório é gerado com o restante:

```bash
vendas-cli examples/vendas_com_erros.csv --skip-invalid
```

```
WARNING: linha 3 ignorada: quantidade inválida 'dois' (esperado inteiro)
WARNING: linha 4 ignorada: produto vazio
WARNING: linha 6 ignorada: quantidade deve ser positiva, recebido 0
WARNING: linha 8 ignorada: data inválida '2025-02-30' (use AAAA-MM-DD ou DD/MM/AAAA)
WARNING: linha 9 ignorada: preço unitário negativo: -299.90
```

**Avisos** (o relatório é gerado mesmo assim):

- `arquivo ... não é UTF-8; lido como latin-1`: confira se os acentos saíram corretos. Se não, use `--encoding`.
- `produto não encontrado: ...`: um nome em `--product` não existe no arquivo, provavelmente por erro de digitação.

## 9. Usando com Docker

A imagem [`calebdev/relatorio-vendas-cli`](https://hub.docker.com/r/calebdev/relatorio-vendas-cli) tem a CLI instalada. Tudo o que vem depois do nome da imagem são as mesmas opções descritas neste manual.

```bash
docker pull calebdev/relatorio-vendas-cli
docker run --rm calebdev/relatorio-vendas-cli --help
```

**Exemplos embutidos.** A imagem traz os arquivos de exemplo em `/app/examples`:

```bash
docker run --rm calebdev/relatorio-vendas-cli /app/examples/vendas_2023_2025.csv --top 5 --group-by ano
```

**Seus arquivos.** O container só enxerga o que for montado. Monte a pasta atual em `/data` e passe o caminho relativo a ela:

```bash
docker run --rm -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv --group-by mes
```

**Gravar o relatório.** Use `-u` para que o arquivo criado pertença ao seu usuário:

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" calebdev/relatorio-vendas-cli vendas.csv -f json -o relatorio.json
```

**Atalho.** Para usar como se estivesse instalado, crie um alias (no `~/.bashrc` ou `~/.zshrc`):

```bash
alias vendas-cli='docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" calebdev/relatorio-vendas-cli'
vendas-cli vendas.csv --top 5
```

Com o alias, o arquivo precisa estar na pasta atual ou abaixo dela.

## 10. Dúvidas frequentes

**Por que o "mais vendido" não é o primeiro da tabela?**
A tabela é ordenada por faturamento, e o mais vendido é o de mais unidades. Use `--sort quantidade` para alinhar os dois.

**O `--top` muda os totais?**
Não. Os produtos de fora entram na linha "Outros", e o total, o ticket médio e o produto mais vendido consideram todos.

**Por que a variação compara com um período que não é o imediatamente anterior?**
Períodos sem vendas não aparecem. A variação é sempre em relação ao período anterior que aparece na tabela.

**Por que a variação aparece como `-`?**
É o primeiro período da lista, ou o anterior faturou zero (por exemplo, só brindes com preço 0), caso em que a variação seria infinita.

**Posso usar mais de um arquivo?**
Não diretamente. Junte os arquivos antes, mantendo um único cabeçalho: `(cat jan.csv; tail -n +2 fev.csv) > tri.csv`.

**Os valores têm erro de arredondamento?**
Não. Os cálculos usam `Decimal`, e o arredondamento (meio para cima) só acontece na exibição.
