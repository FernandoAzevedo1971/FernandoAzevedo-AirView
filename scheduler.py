"""
scheduler.py — Lógica de agendamento dos marcos de relatório.

Marcos contados a partir da DATA DE INÍCIO DA TERAPIA:
    D0  (no momento do cadastro / primeira coleta)
    D+3, D+7, D+14, D+21, D+30
"""
from datetime import date, datetime, timedelta

# Offsets em dias a partir da data de início da terapia
MILESTONE_OFFSETS = [0, 3, 7, 14, 21, 30]


def milestone_label(offset: int) -> str:
    return "D0" if offset == 0 else f"D+{offset}"


def initial_milestones() -> list:
    """
    Marcos iniciais no momento do cadastro (antes de conhecer a data de início).
    O D0 já fica 'disponivel' (precisa ser coletado para descobrir a data de início).
    Os demais ficam 'aguardando_inicio' até o D0 ser gerado.
    """
    milestones = []
    for offset in MILESTONE_OFFSETS:
        milestones.append({
            "label": milestone_label(offset),
            "offset_days": offset,
            "due_date": None,
            "status": "disponivel" if offset == 0 else "aguardando_inicio",
        })
    return milestones


def compute_due_dates(therapy_start: date) -> dict:
    """
    Dada a data de início da terapia, retorna {offset: due_date_iso}.
    """
    due = {}
    for offset in MILESTONE_OFFSETS:
        due[offset] = (therapy_start + timedelta(days=offset)).isoformat()
    return due


def milestone_display_status(milestone: dict, today: date = None) -> str:
    """
    Calcula o status de exibição de um marco para o painel:
      - 'gerado'      : já foi gerado com sucesso
      - 'erro'        : falhou na última tentativa
      - 'disponivel'  : a data de vencimento chegou e ainda não foi gerado
      - 'agendado'    : a data ainda não chegou
      - 'aguardando_inicio': ainda não sabemos a data de início (D0 não coletado)
    """
    today = today or date.today()
    status = milestone.get("status", "aguardando")

    if status == "gerado":
        return "gerado"
    if status == "erro":
        return "erro"
    if status == "aguardando_inicio":
        return "aguardando_inicio"

    due = milestone.get("due_date")
    if not due:
        # D0 sem data definida fica disponível imediatamente
        return "disponivel" if milestone.get("offset_days") == 0 else "aguardando_inicio"

    due_date = datetime.fromisoformat(due).date()
    if today >= due_date:
        return "disponivel"
    return "agendado"


def report_period(therapy_start: date, milestone_offset: int, today: date = None) -> tuple:
    """
    Define o período (start, end) do relatório de adesão para um marco.

    O relatório cobre da data de início da terapia até o dia do marco
    (ou hoje, se o marco já venceu há mais tempo — usa o que for menor para
    não pedir datas futuras).
    """
    today = today or date.today()
    end = therapy_start + timedelta(days=milestone_offset)
    if end > today:
        end = today
    # Para D0, garante ao menos 1 dia de período
    if end <= therapy_start:
        end = therapy_start + timedelta(days=1)
    return therapy_start, end
