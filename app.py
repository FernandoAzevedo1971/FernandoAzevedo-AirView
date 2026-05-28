"""
app.py — Aplicação web (FastAPI) para gerenciar pacientes e relatórios AirView.

Funcionalidades:
  - Cadastrar pacientes manualmente pelo nome
  - Para cada paciente, agendar marcos de relatório: D0, D+3, D+7, D+14, D+21, D+30
    (contados a partir da data de início da terapia, extraída do 1º relatório)
  - Painel com lembrete dos relatórios "disponíveis" para gerar
  - Geração manual (botão) que dispara o pipeline em background
  - Visualização e download de PDF, PNG e laudo (GPT-4o)

Executar:
    uvicorn app:app --reload --port 8000
ou:
    python app.py
"""
import threading
import logging
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

import db
import scheduler
from report_pipeline import run_milestone
from utils import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger("airview.app")

app = FastAPI(title="AirView — Gestão de Relatórios de Adesão")

Path("static").mkdir(exist_ok=True)
Path("reports").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Rastreamento simples de jobs em andamento: {milestone_id: "gerando"}
_running_jobs = set()
_jobs_lock = threading.Lock()


@app.on_event("startup")
def startup():
    db.init_db()
    logger.info("Aplicação AirView iniciada")


# ==========================================================================
# Painel principal
# ==========================================================================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    patients = db.list_patients()
    today = date.today()

    # Enriquece cada paciente com seus marcos e status de exibição
    patient_views = []
    due_now = []  # relatórios disponíveis (lembrete)
    for p in patients:
        milestones = db.list_milestones(p["id"])
        ms_views = []
        for m in milestones:
            disp = scheduler.milestone_display_status(m, today)
            running = m["id"] in _running_jobs
            mv = {**m, "display": disp, "running": running}
            ms_views.append(mv)
            if disp == "disponivel" and not running:
                due_now.append({"patient": p, "milestone": mv})
        patient_views.append({**p, "milestones": ms_views})

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "patients": patient_views,
            "due_now": due_now,
            "today": today.strftime("%d/%m/%Y"),
        },
    )


# ==========================================================================
# Cadastro de paciente
# ==========================================================================
@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return templates.TemplateResponse(request, "add_patient.html", {})


@app.post("/add")
def add_patient(name: str = Form(...), notes: str = Form("")):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome do paciente é obrigatório")

    patient_id = db.add_patient(name, notes)
    # Cria os marcos iniciais (D0 disponível, demais aguardando início da terapia)
    db.create_milestones(patient_id, scheduler.initial_milestones())
    logger.info(f"Paciente cadastrado: {name} (id={patient_id})")
    return RedirectResponse(url=f"/patient/{patient_id}", status_code=303)


# ==========================================================================
# Detalhe do paciente
# ==========================================================================
@app.get("/patient/{patient_id}", response_class=HTMLResponse)
def patient_detail(request: Request, patient_id: int):
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    today = date.today()
    milestones = db.list_milestones(patient_id)
    ms_views = []
    for m in milestones:
        disp = scheduler.milestone_display_status(m, today)
        running = m["id"] in _running_jobs
        ms_views.append({**m, "display": disp, "running": running})

    therapy_start = None
    if patient["therapy_start_date"]:
        therapy_start = datetime.fromisoformat(patient["therapy_start_date"]).date().strftime("%d/%m/%Y")

    return templates.TemplateResponse(
        request,
        "patient_detail.html",
        {
            "patient": patient,
            "milestones": ms_views,
            "therapy_start": therapy_start,
        },
    )


@app.post("/patient/{patient_id}/delete")
def delete_patient(patient_id: int):
    db.delete_patient(patient_id)
    logger.info(f"Paciente removido: id={patient_id}")
    return RedirectResponse(url="/", status_code=303)


# ==========================================================================
# Geração de relatório (background)
# ==========================================================================
def _background_generate(milestone_id: int):
    """Roda o pipeline em uma thread e atualiza o banco ao final."""
    milestone = db.get_milestone(milestone_id)
    if not milestone:
        return
    patient = db.get_patient(milestone["patient_id"])
    if not patient:
        return

    therapy_start = None
    if patient["therapy_start_date"]:
        therapy_start = datetime.fromisoformat(patient["therapy_start_date"]).date()

    try:
        result = run_milestone(
            patient_id=patient["id"],
            patient_name=patient["name"],
            milestone_label=milestone["label"],
            milestone_offset=milestone["offset_days"],
            airview_url=patient["airview_url"],
            therapy_start=therapy_start,
        )

        if result.success:
            db.update_milestone(
                milestone_id,
                status="gerado",
                pdf_path=result.pdf_path,
                png_path=result.png_path,
                laudo_path=result.laudo_path,
                generated_at=datetime.now().isoformat(timespec="seconds"),
                error=None,
            )

            # Salva a URL resolvida do paciente, se ainda não tínhamos
            if result.resolved_url and not patient["airview_url"]:
                db.update_patient(patient["id"], airview_url=result.resolved_url)

            # Se descobrimos a data de início da terapia, calcula os vencimentos
            if result.therapy_start_date and not patient["therapy_start_date"]:
                ts = result.therapy_start_date
                db.update_patient(
                    patient["id"],
                    therapy_start_date=ts.isoformat(),
                    status="ativo",
                )
                due_dates = scheduler.compute_due_dates(ts)
                for m in db.list_milestones(patient["id"]):
                    offset = m["offset_days"]
                    new_due = due_dates.get(offset)
                    # Atualiza vencimento e libera os marcos que ainda aguardavam início
                    new_status = m["status"]
                    if m["status"] == "aguardando_inicio":
                        new_status = "agendado"
                    db.update_milestone(m["id"], due_date=new_due, status=new_status
                                        if m["status"] != "gerado" else "gerado")
            else:
                # Apenas marca o paciente como ativo
                if patient["status"] == "novo":
                    db.update_patient(patient["id"], status="ativo")
        else:
            db.update_milestone(milestone_id, status="erro", error=result.error)

    except Exception as e:
        logger.error(f"Erro no job do marco {milestone_id}: {e}", exc_info=True)
        db.update_milestone(milestone_id, status="erro", error=str(e))
    finally:
        with _jobs_lock:
            _running_jobs.discard(milestone_id)


@app.post("/patient/{patient_id}/generate/{milestone_id}")
def generate_report(patient_id: int, milestone_id: int):
    milestone = db.get_milestone(milestone_id)
    if not milestone or milestone["patient_id"] != patient_id:
        raise HTTPException(status_code=404, detail="Marco não encontrado")

    with _jobs_lock:
        if milestone_id in _running_jobs:
            return RedirectResponse(url=f"/patient/{patient_id}", status_code=303)
        _running_jobs.add(milestone_id)

    db.update_milestone(milestone_id, status="gerando", error=None)
    thread = threading.Thread(target=_background_generate, args=(milestone_id,), daemon=True)
    thread.start()
    logger.info(f"Geração iniciada: paciente={patient_id} marco={milestone_id}")

    return RedirectResponse(url=f"/patient/{patient_id}", status_code=303)


# ==========================================================================
# API de status (para polling do frontend)
# ==========================================================================
@app.get("/api/patient/{patient_id}/status")
def patient_status(patient_id: int):
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404)
    today = date.today()
    milestones = []
    for m in db.list_milestones(patient_id):
        disp = scheduler.milestone_display_status(m, today)
        milestones.append({
            "id": m["id"],
            "label": m["label"],
            "display": disp,
            "running": m["id"] in _running_jobs,
            "status": m["status"],
        })
    return JSONResponse({
        "patient_id": patient_id,
        "patient_status": patient["status"],
        "therapy_start_date": patient["therapy_start_date"],
        "milestones": milestones,
    })


# ==========================================================================
# Servir arquivos gerados (PDF, PNG, laudo)
# ==========================================================================
@app.get("/file")
def serve_file(path: str):
    """Serve um arquivo da pasta reports/ de forma segura."""
    p = Path(path).resolve()
    reports_dir = Path("reports").resolve()
    if reports_dir not in p.parents or not p.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(p)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
