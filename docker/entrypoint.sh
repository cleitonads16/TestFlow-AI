#!/bin/sh
# Aplica as migrations antes de subir a API, para o banco estar sempre no
# esquema do código da imagem. Só depois executa o comando do container.
set -e

python api/manage.py migrate --noinput

exec "$@"
