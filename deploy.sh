#!/usr/bin/env bash

set -euo pipefail

APP_DIR="/srv/apps/pokemon-collection"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
VENV="${BACKEND_DIR}/.venv"
HEALTH_URL="http://127.0.0.1:8080/api/health"

cd "${APP_DIR}"

echo "==> Actualizando código desde GitHub"
git pull --ff-only

echo "==> Actualizando dependencias del backend"
"${VENV}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

echo "==> Instalando dependencias del frontend"
cd "${FRONTEND_DIR}"
npm ci

echo "==> Compilando frontend"
npm run build

echo "==> Restaurando contexto SELinux del frontend"
sudo restorecon -Rv "${FRONTEND_DIR}/dist"

echo "==> Reiniciando backend"
sudo systemctl restart pokemon-collection-backend

echo "==> Esperando backend..."
sleep 2

echo "==> Verificando aplicación"
if curl --fail --silent --show-error "${HEALTH_URL}"; then
    echo
    echo "==> Deploy completado correctamente."
else
    echo
    echo "==> ERROR: el health check falló."
    exit 1
fi
