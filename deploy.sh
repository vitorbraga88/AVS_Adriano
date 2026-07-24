#!/usr/bin/env bash
# Deploy seguro do AVS Admin para servidor-203.
#
# NUNCA sincroniza dados vivos: database/ (SQLite) e relatorios/ (PDFs) e .env
# ficam SÓ no servidor. Sem estes excludes, o rsync sobrescreve o banco de
# produção com o seed versionado — apagando ordens e clientes reais.
#
# Uso:  ./deploy.sh [host]
set -euo pipefail

HOST="${1:-servidor-203.tail43f430.ts.net}"
DEST="/var/www/avs-admin"
SRC="$(cd "$(dirname "$0")" && pwd)/"

rsync -avz --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.venv' \
  --exclude='.env' \
  --exclude='database/' \
  --exclude='relatorios/' \
  --exclude='_*.py' \
  --exclude='_*.json' \
  "$SRC" "$HOST:$DEST/"

ssh "$HOST" "cd $DEST && ./.venv/bin/pip install -q -r requirements.txt && sudo systemctl restart avs-admin && sleep 3 && systemctl is-active avs-admin"
echo "deploy concluído em $HOST"
