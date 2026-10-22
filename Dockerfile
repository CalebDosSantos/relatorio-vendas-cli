# syntax=docker/dockerfile:1

# --- build: gera o wheel do projeto ---
FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /dist .

# --- runtime: só o pacote instalado, sem ferramentas de build ---
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl \
    && useradd --create-home --uid 1000 app
COPY examples /app/examples

USER app
# Monte o diretório com os CSVs aqui: -v "$PWD:/data"
WORKDIR /data
ENTRYPOINT ["vendas-cli"]
CMD ["--help"]
