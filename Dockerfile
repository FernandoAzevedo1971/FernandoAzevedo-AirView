# Imagem oficial do Playwright — já inclui Python, Playwright e o Chromium
# com todas as dependências de sistema. A tag deve casar com a versão do
# playwright em requirements.txt (1.44.0).
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto
COPY . .

# Porta (Railway/Render injetam via $PORT) e pasta de dados persistente.
# Monte um volume do host em /data para preservar banco e relatórios.
ENV PORT=8000
ENV APP_DATA_DIR=/data

EXPOSE 8000

# host 0.0.0.0 para aceitar conexões externas; porta vinda de $PORT
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
