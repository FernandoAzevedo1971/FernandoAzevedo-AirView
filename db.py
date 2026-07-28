"""
db.py — Camada de persistência em SQLite para a aplicação web AirView.

Tabelas:
  - patients:   pacientes cadastrados manualmente
  - milestones: marcos de relatório (D0, D+3, D+7, D+14, D+21, D+30) por paciente
"""
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

from paths import DB_PATH

logger = logging.getLogger("airview.db")


@contextmanager
def get_conn():
    """Context manager que abre uma conexão SQLite com row_factory de dicionário."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Cria as tabelas se não existirem."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL,
                airview_url         TEXT,
                therapy_start_date  TEXT,
                status              TEXT NOT NULL DEFAULT 'novo',
                notes               TEXT,
                created_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS milestones (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id    INTEGER NOT NULL,
                label         TEXT NOT NULL,          -- D0, D+3, ...
                offset_days   INTEGER NOT NULL,       -- 0, 3, 7, 14, 21, 30
                due_date      TEXT,                   -- ISO; nulo até saber a data de início
                status        TEXT NOT NULL DEFAULT 'aguardando',
                pdf_path      TEXT,
                png_path      TEXT,
                laudo_path    TEXT,
                generated_at  TEXT,
                error         TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
            );
            """
        )
    logger.info(f"Banco inicializado: {DB_PATH.resolve()}")


# --------------------------------------------------------------------------
# Pacientes
# --------------------------------------------------------------------------
def add_patient(name: str, notes: str = "") -> int:
    """Cadastra um paciente e retorna seu id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO patients (name, status, notes, created_at) VALUES (?, 'novo', ?, ?)",
            (name.strip(), notes.strip(), datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def get_patient(patient_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        return dict(row) if row else None


def list_patients() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM patients ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_patient(patient_id: int, **fields):
    """Atualiza campos arbitrários do paciente."""
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [patient_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE patients SET {cols} WHERE id = ?", values)


def delete_patient(patient_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))


# --------------------------------------------------------------------------
# Marcos (milestones)
# --------------------------------------------------------------------------
def create_milestones(patient_id: int, milestones: list):
    """
    Cria os marcos de um paciente.
    `milestones` é uma lista de dicts: {label, offset_days, due_date, status}
    """
    with get_conn() as conn:
        for m in milestones:
            conn.execute(
                """INSERT INTO milestones
                   (patient_id, label, offset_days, due_date, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (patient_id, m["label"], m["offset_days"],
                 m.get("due_date"), m.get("status", "aguardando")),
            )


def list_milestones(patient_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM milestones WHERE patient_id = ? ORDER BY offset_days",
            (patient_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_milestone(milestone_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
        return dict(row) if row else None


def update_milestone(milestone_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [milestone_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE milestones SET {cols} WHERE id = ?", values)


def all_milestones_with_patient() -> list:
    """Retorna todos os marcos com dados do paciente (para o painel)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT m.*, p.name AS patient_name, p.status AS patient_status
               FROM milestones m
               JOIN patients p ON p.id = m.patient_id
               ORDER BY m.due_date IS NULL, m.due_date""",
        ).fetchall()
        return [dict(r) for r in rows]
