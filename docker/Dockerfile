# syntax=docker/dockerfile:1
# Imagem da API. Build a partir da raiz do projeto:
#   docker build -f docker/Dockerfile -t casos-teste-api .
# Python 3.12+ é obrigatório: o código usa a sintaxe de genéricos do 3.12.

# O mysqlclient é compilado aqui, para o compilador não ir para a imagem final.
FROM python:3.13-slim AS dependencias

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=false \
    DIRETORIO_ESCOPOS=/app/uploads/escopos

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=dependencias /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY sistema-core/ sistema-core/
COPY api/ api/
# O código fica do root (só leitura para a aplicação); o usuário app escreve só
# em /app (banco SQLite quando não há MYSQL_HOST) e nos uploads.
RUN mkdir -p "$DIRETORIO_ESCOPOS" && chown app:app /app && chown -R app:app /app/uploads

USER app
EXPOSE 8000

# Timeout alto porque a geração de casos espera a resposta completa da IA,
# que leva minutos num escopo grande; com o padrão (30 s) o worker seria morto.
CMD ["gunicorn", "--chdir", "api", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "300"]
