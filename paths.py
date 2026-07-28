"""
paths.py — Caminhos de dados centralizados e configuráveis.

Permite apontar o banco e a pasta de relatórios para um volume persistente
na nuvem (ex.: Railway/Render) via a variável de ambiente APP_DATA_DIR.

Localmente, o padrão é a pasta atual (".") — nada muda.
Na nuvem, defina APP_DATA_DIR=/data (com um volume montado em /data).
"""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("APP_DATA_DIR", ".")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Banco SQLite
DB_PATH = DATA_DIR / "airview.db"

# Pasta de relatórios (PDF, PNG, laudos)
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
