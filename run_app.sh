#!/usr/bin/env bash
set -e

echo "=== Iniciando aplicação web AirView ==="
echo "Acesse no navegador: http://localhost:8000"
echo ""

# Garante que as pastas existem
mkdir -p reports logs static templates

# Sobe o servidor FastAPI
uvicorn app:app --host 0.0.0.0 --port 8000
