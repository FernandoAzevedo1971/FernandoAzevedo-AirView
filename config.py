"""
config.py — Seletores CSS/XPath resilientes e constantes de configuração
"""

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
# O AirView usa Okta (signin.resmed.com) com login em DUAS ETAPAS:
#   1) informa o usuário → clica em "Avançar" (idp-discovery)
#   2) a tela de senha aparece → informa a senha → clica em "Entrar"
# Os IDs abaixo foram confirmados inspecionando a tela real.
LOGIN_SELECTORS = {
    "email_field": [
        '#idp-discovery-username',           # confirmado na tela real
        'input[name="identifier"]',          # Okta (outras versões)
        '#okta-signin-username',
        'input[autocomplete="username"]',
        'input[type="email"]',
        'input[name="username"]',
        'input[name="email"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="usuário" i]',
        'input[placeholder*="usuario" i]',
        'input[placeholder*="user" i]',
    ],
    # Botão da 1ª etapa (avançar para a tela de senha)
    "next_button": [
        '#idp-discovery-submit',             # confirmado na tela real
        '#okta-signin-submit',
        'input[type="submit"][value*="Next" i]',
        'input[type="submit"][value*="Avançar" i]',
        'input[type="submit"][value*="Continuar" i]',
        'button:has-text("Avançar")',
        'button:has-text("Próximo")',
        'button:has-text("Continuar")',
        'button:has-text("Next")',
        'input[type="submit"]',
        'button[type="submit"]',
    ],
    "password_field": [
        '#okta-signin-password',
        'input[name="credentials.passcode"]',  # Okta
        'input[type="password"]',
        'input[name="password"]',
        'input[autocomplete="current-password"]',
        'input[placeholder*="senha" i]',
        'input[placeholder*="password" i]',
    ],
    # Botão da 2ª etapa (confirmar a senha e entrar)
    "submit_button": [
        '#okta-signin-submit',
        'input[type="submit"][value*="Verify" i]',
        'input[type="submit"][value*="Sign" i]',
        'input[type="submit"][value*="Entrar" i]',
        'button:has-text("Verificar")',
        'button:has-text("Entrar")',
        'button:has-text("Acessar")',
        'button:has-text("Verify")',
        'button:has-text("Sign In")',
        'input[type="submit"]',
        'button[type="submit"]',
    ],
    # Mensagens de erro / desafios de segurança (diagnóstico)
    "error_message": [
        '.okta-form-infobox-error',
        '[data-se="callout"]',
        '[role="alert"]',
    ],
    # Indício de que a sessão já está autenticada
    "logged_in_marker": [
        'a[href="/logout"]',
        'a[href*="/logout"]',
        'a[href="/wireless"]',
        'a[href="/myprofile"]',
    ],
}

# Banner de cookies (OneTrust) — precisa ser dispensado antes de clicar
# em qualquer coisa, senão ele intercepta os cliques.
COOKIE_BANNER_SELECTORS = [
    '#onetrust-accept-btn-handler',
    '#accept-recommended-btn-handler',
    'button:has-text("Aceitar cookies")',
    'button:has-text("Aceitar todos")',
    'button:has-text("Accept")',
    '.onetrust-close-btn-handler',
]

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
    # Cabeçalho da coluna de data para clicar e ordenar decrescente
    "date_column_header": [
        'th:has-text("Data de cadastro")',
        'th:has-text("Cadastro")',
        'th:has-text("Data de início")',
        'th:has-text("Início")',
        'th:has-text("Setup Date")',
        'th:has-text("Enrollment")',
        'th:has-text("Date")',
        'th:has-text("Data")',
        '[role="columnheader"]:has-text("Data")',
        '[role="columnheader"]:has-text("Date")',
        '[role="columnheader"]:has-text("Cadastro")',
        '[data-field*="date" i]',
        '[data-field*="registration" i]',
        '[data-field*="enrollment" i]',
        '[data-column*="date" i]',
        '[aria-label*="data" i]',
        '[aria-label*="date" i]',
    ],
    # Célula de data de cadastro dentro de cada linha
    "registration_date": [
        '[data-field*="registration" i]',
        '[data-field*="setupDate" i]',
        '[data-field*="enrollmentDate" i]',
        '[data-column*="date" i]',
        'td[class*="date" i]',
        'td[class*="cadastro" i]',
        'td[class*="registration" i]',
        'td[aria-label*="data" i]',
        'td[aria-label*="date" i]',
        # Fallback: última coluna (muitas vezes contém a data)
        'td:last-child',
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
# Busca de paciente por nome
# ---------------------------------------------------------------------------
SEARCH_SELECTORS = {
    # Campo de busca de pacientes
    "search_input": [
        'input[type="search"]',
        'input[placeholder*="Pesquisar" i]',
        'input[placeholder*="Buscar" i]',
        'input[placeholder*="Search" i]',
        'input[placeholder*="paciente" i]',
        'input[placeholder*="patient" i]',
        'input[name*="search" i]',
        'input[aria-label*="search" i]',
        'input[aria-label*="buscar" i]',
        '[role="searchbox"]',
    ],
    # Botão para submeter a busca (quando não basta Enter)
    "search_button": [
        'button[type="submit"]',
        'button:has-text("Pesquisar")',
        'button:has-text("Buscar")',
        'button:has-text("Search")',
        '[aria-label*="search" i] button',
        'button[class*="search" i]',
    ],
    # Resultado da busca (link/linha clicável)
    "search_result": [
        'a[href*="/patient/"]',
        'a[href*="/wireless/"]',
        'a[href*="/therapy/"]',
        '[class*="search-result"] a',
        '[class*="searchResult"] a',
        'table tbody tr a',
        'table tbody tr',
        '[role="row"]:not([role="columnheader"])',
        'li[class*="result"]',
    ],
}

# ---------------------------------------------------------------------------
# Padrões de texto para extrair a DATA DE INÍCIO DA TERAPIA do PDF
# ---------------------------------------------------------------------------
THERAPY_START_LABELS = [
    "Data de início da terapia",
    "Início da terapia",
    "Data de início",
    "Therapy start date",
    "Therapy start",
    "Start date",
    "Início do tratamento",
    "Data de início do tratamento",
    "First use",
    "Primeiro uso",
]

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
