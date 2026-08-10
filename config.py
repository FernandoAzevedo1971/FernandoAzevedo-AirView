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
# Relatório de adesão — fluxo confirmado na tela real (/patients/{id}/charts):
#   1) botão "Criar relatório" abre um modal
#   2) <select> "Tipo de relatório" → opção com "adesão" + "terapia"
#      (relatório combinado: traz uso/adesão E dados de terapia como
#      pressão/vazamento/IAH — a opção só "adesão" não teria esses últimos)
#   3) radio "Período de tempo fixo" já vem selecionado por padrão, com
#      um campo numérico de dias + um campo de data final (dd/mm/aaaa)
#   4) botão "Continuar" gera e baixa o PDF diretamente (confirmado: sem
#      etapa extra no meio)
# ---------------------------------------------------------------------------
REPORT_SELECTORS = {
    # Botão que abre o modal "Criar relatório"
    "reports_menu": [
        'button:has-text("Criar relatório")',
        'button:has-text("Criar relatorio")',
        'button:has-text("Create report")',
        'button:has-text("Relatório")',
        'a:has-text("Criar relatório")',
        '[aria-label*="relatório" i]',
        '[aria-label*="report" i]',
    ],
    # Texto que confirma que o modal abriu
    "report_modal_marker": [
        'text="Tipo de relatório"',
        'text=/Tipo de relat/i',
    ],
    # Palavras-chave (não seletores CSS) usadas para achar a opção certa
    # dentro do <select> "Tipo de relatório" — ver _selecionar_tipo_relatorio()
    "adherence_report_keywords_priority": [
        ["adesao", "terapia"],   # combinado — preferido (mais dados)
        ["adesao"],               # só adesão — fallback
        ["compliance", "therapy"],
        ["compliance"],
    ],
    # Radio "Período de tempo fixo" (já vem marcado por padrão, mas
    # garantimos a seleção caso não venha)
    "fixed_period_radio": [
        'text="Período de tempo fixo"',
        'label:has-text("Período de tempo fixo")',
        'text="Fixed time period"',
    ],
    # Campo numérico de quantidade de dias
    "period_days_input": [
        'input[type="number"]',
        'input[type="text"][maxlength="3"]',
    ],
    # Campo de data final do período (formato dd/mm/aaaa na tela)
    "period_end_date_input": [
        'input[type="date"]',
        'input[placeholder*="dd/mm" i]',
        'input[placeholder*="data" i]',
    ],
    # Botão que confirma e gera/baixa o PDF.
    # IMPORTANTE: confirmado por print real que o botão "Continuar" existe
    # e é clicável na tela — mas nenhum seletor 'button:has-text(...)'
    # o encontrou, sugerindo que NÃO é uma tag <button> (pode ser <input
    # type=submit>, <a>, <div role="button">, etc). Por isso a lista
    # prioriza seletores de TEXTO puro (funcionam em qualquer tag),
    # antes dos específicos de <button>.
    "generate_button": [
        'text="Continuar"',
        'text=/^Continuar$/i',
        '[role="button"]:has-text("Continuar")',
        'a:has-text("Continuar")',
        'input[type="submit"][value="Continuar" i]',
        'input[type="button"][value="Continuar" i]',
        'button:has-text("Continuar")',
        'button:has-text("Continue")',
        'text="Continue"',
        'button:has-text("Gerar")',
        'button:has-text("Confirmar")',
        'button:has-text("Download")',
        'button[type="submit"]:visible',
    ],
}

# ---------------------------------------------------------------------------
# Busca de paciente por nome
# ---------------------------------------------------------------------------
SEARCH_SELECTORS = {
    # Campo de busca de pacientes — confirmado na tela real de /wireless
    "search_input": [
        '#q',
        'input[name="q"]',
        'input[type="search"]',
        'input[placeholder*="Pesquisar" i]',
        'input[placeholder*="Buscar" i]',
        'input[placeholder*="Search" i]',
        'input[placeholder*="paciente" i]',
        'input[placeholder*="patient" i]',
        'input[name*="search" i]',
        '[role="searchbox"]',
    ],
    # Botão para submeter a busca — confirmado: #searchItems
    "search_button": [
        '#searchItems',
        'button[name="search"]',
        'input[type="submit"][name="search"]',
        'button[type="submit"]',
        'button:has-text("Pesquisar")',
        'button:has-text("Buscar")',
        'button:has-text("Search")',
    ],
    # Links de paciente — confirmado: /patients/{uuid}/charts
    "search_result": [
        'a[href*="/patients/"][href*="/charts"]',
        'a[href*="/patient/"]',
        'a[href*="/wireless/"]',
        '[class*="search-result"] a',
        'table tbody tr a',
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
