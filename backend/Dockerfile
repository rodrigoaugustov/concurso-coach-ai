# ---- Base Stage ----
FROM python:3.11-slim as base
# MUDANÇA: Usaremos /code como nosso diretório de trabalho padrão.
WORKDIR /code
RUN pip install --no-cache-dir uv

# ---- Builder Stage ----
FROM base as builder
COPY pyproject.toml .
RUN uv pip install --system -e .

# ---- Final Stage ----
FROM base as final
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# MUDANÇA: Copiamos nosso pacote 'app' para dentro do WORKDIR (/code).
# A estrutura final será /code/app/main.py
COPY ./app ./app

EXPOSE 8000

# MUDANÇA: O comando agora funciona perfeitamente, pois a partir de /code,
# o Python consegue encontrar o pacote 'app'.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]