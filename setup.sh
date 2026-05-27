#!/usr/bin/env bash
set -e

echo "=== Instalando dependências Python ==="
pip install -r requirements.txt

echo "=== Instalando browser Chromium para Playwright ==="
python -m playwright install chromium --with-deps

echo "=== Criando pastas necessárias ==="
mkdir -p reports logs

echo "=== Configurando credenciais ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "ATENÇÃO: Edite o arquivo .env com suas credenciais antes de executar:"
    echo "  AIRVIEW_USER, AIRVIEW_PASS e ANTHROPIC_API_KEY"
else
    echo ".env já existe — mantendo configuração atual."
fi

echo ""
echo "=== Setup concluído! ==="
echo "Para executar: python airview_automation.py"
