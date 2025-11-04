# ---- Base Stage ----
FROM python:3.11-slim as base
# Usando /code como diretório de trabalho padrão
WORKDIR /code

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# ---- Builder Stage ----
FROM base as builder
COPY pyproject.toml uv.lock* ./
# Instalar dependências em ambiente virtual
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r pyproject.toml

# ---- Final Stage ----
FROM base as final

# Copiar ambiente virtual do builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código da aplicação
COPY ./app ./app

# Expor porta (Railway usará a variável PORT)
EXPOSE 8000

# Comando para produção - Railway definirá PORT automaticamente
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}