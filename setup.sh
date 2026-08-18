#!/usr/bin/env bash
# Instalacao do robo de sincronizacao AirView -> MONITORAMENTO_CPAP_FAPS.
#
# No Windows (uso normal), rode pelo Git Bash:  ./setup.sh
# Depois de terminar, registre o botao do painel com um duplo-clique em
# registrar_protocolo.bat — so entao o link "Sincronizar com AirView"
# funciona neste computador.
set -e

echo "=== Instalando dependencias Python ==="
pip install -r requirements.txt

echo "=== Instalando o Chromium do Playwright ==="
# --with-deps so se aplica a Linux; no Windows/macOS o comando simples basta.
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    python -m playwright install chromium --with-deps
else
    python -m playwright install chromium
fi

echo "=== Criando pastas necessarias ==="
mkdir -p reports logs

echo "=== Configurando credenciais ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "ATENCAO: edite o arquivo .env antes de executar. Obrigatorios:"
    echo "  AIRVIEW_USER        seu login do AirView"
    echo "  AIRVIEW_PASS        sua senha do AirView"
    echo "  NEXTJS_API_URL      https://monitoramento-cpap-ares.vercel.app"
    echo "  AIRVIEW_SYNC_SECRET a mesma string cadastrada na Vercel"
    echo ""
    echo "OPENAI_API_KEY e opcional: a extracao dos dados do PDF passou a"
    echo "ser por regex (pdf_data_extractor.py), sem IA e sem custo."
else
    echo ".env ja existe — mantendo a configuracao atual."
fi

echo ""
echo "=== Setup concluido ==="
echo "Registrar o botao do painel:  duplo-clique em registrar_protocolo.bat"
echo "Rodar a sincronizacao:        duplo-clique em executar_sync.bat"
echo "                              (ou 'python -m sync_runner')"
