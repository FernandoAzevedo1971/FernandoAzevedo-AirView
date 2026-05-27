"""
config.py — Seletores CSS/XPath resilientes e constantes de configuração
"""

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
LOGIN_SELECTORS = {
    "email_field": [
        'input[type="email"]',
        'input[name="username"]',
        'input[name="email"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="usuário" i]',
        'input[placeholder*="user" i]',
        '//input[@type="email"]',
        '//input[@name="username"]',
    ],
    "password_field": [
        'input[type="password"]',
        'input[name="password"]',
        'input[placeholder*="senha" i]',
        'input[placeholder*="password" i]',
        '//input[@type="password"]',
    ],
    "submit_button": [
        'button[type="submit"]',
        'button:has-text("Entrar")',
        'button:has-text("Login")',
        'button:has-text("Sign In")',
        'button:has-text("Acessar")',
        'input[type="submit"]',
        '//button[@type="submit"]',
    ],
}

# ---------------------------------------------------------------------------
# Lista de pacientes (/wireless)
# ---------------------------------------------------------------------------
PATIENT_LIST_SELECTORS = {
    "patient_row": [
        'tr[data-testid*="patient"]',
        'tr.patient-row',
        '[class*="PatientRow"]',
        '[class*="patient-list-item"]',
        '[class*="patientRow"]',
        'table tbody tr',
        '[role="row"]:not([role="columnheader"])',
        'tbody tr',
    ],
    "patient_name": [
        'td:first-child',
        'td:nth-child(1)',
        '[class*="patient-name"]',
        '[class*="patientName"]',
        '[data-field="name"]',
        '[data-column="name"]',
    ],
    "patient_link": [
        'a[href*="/patient/"]',
        'a[href*="/wireless/"]',
        'a[href*="/therapy/"]',
        'td a',
        'a',
    ],
}

# ---------------------------------------------------------------------------
# Relatório de adesão
# ---------------------------------------------------------------------------
REPORT_SELECTORS = {
    # Botão/menu para abrir painel de relatórios
    "reports_menu": [
        'button:has-text("Relatório")',
        'button:has-text("Relatórios")',
        'button:has-text("Report")',
        'button:has-text("Reports")',
        'a:has-text("Relatório")',
        'a:has-text("Report")',
        '[aria-label*="report" i]',
        '[aria-label*="relatório" i]',
        '[data-testid*="report"]',
        '[title*="Relatório" i]',
        '[title*="Report" i]',
    ],
    # Opção "Relatório de adesão ao tratamento"
    "adherence_report": [
        'text="Relatório de adesão ao tratamento"',
        'text="Compliance Report"',
        'li:has-text("adesão")',
        'li:has-text("Adesão")',
        'option:has-text("adesão")',
        'option:has-text("Adesão")',
        '[value*="adherence"]',
        '[value*="compliance"]',
        '[data-report-type*="adherence"]',
        '[data-report-type*="compliance"]',
        'a:has-text("adesão")',
        'button:has-text("adesão")',
        'text=/adesão ao tratamento/i',
        'text=/compliance/i',
    ],
    # Seleção do período de 14 dias
    "period_14_days": [
        'button:has-text("14")',
        'button:has-text("Últimos 14 dias")',
        'button:has-text("Last 14 days")',
        'button:has-text("14 days")',
        'input[value="14"]',
        'option[value="14"]',
        '[data-value="14"]',
        'label:has-text("14")',
    ],
    "date_start_input": [
        'input[name*="start" i]',
        'input[name*="from" i]',
        'input[name*="inicio" i]',
        'input[placeholder*="início" i]',
        'input[type="date"]:first-of-type',
    ],
    "date_end_input": [
        'input[name*="end" i]',
        'input[name*="to" i]',
        'input[name*="fim" i]',
        'input[placeholder*="fim" i]',
        'input[type="date"]:last-of-type',
    ],
    # Botão para gerar/baixar o relatório
    "generate_button": [
        'button:has-text("Gerar")',
        'button:has-text("Exportar")',
        'button:has-text("Download")',
        'button:has-text("Imprimir")',
        'button:has-text("Generate")',
        'button:has-text("Export")',
        'button:has-text("Print")',
        'button:has-text("OK")',
        'button:has-text("Confirmar")',
        'button[type="submit"]:visible',
        '[class*="generate" i]',
        '[class*="export" i]',
        '[class*="download" i]',
    ],
}

# ---------------------------------------------------------------------------
# Timeouts (milissegundos)
# ---------------------------------------------------------------------------
TIMEOUTS = {
    "page_load": 30_000,
    "element_visible": 15_000,
    "network_idle": 20_000,
    "download": 60_000,
    "between_patients": 2_000,
}

# ---------------------------------------------------------------------------
# Configurações gerais
# ---------------------------------------------------------------------------
BASE_URL = "https://airview.resmed.com"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
PDF_DPI = 300
