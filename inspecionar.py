#!/usr/bin/env python3
"""
inspecionar.py — Ferramenta de diagnóstico da interface do AirView.

Faz login, abre a página /wireless e imprime a estrutura real da página
(campos de busca, botões, links, tabelas). Serve para calibrar os
seletores em config.py contra a interface real, sem adivinhação.

Uso:
    python inspecionar.py

Gera também:
    logs/inspecao_wireless.png   — screenshot da página inteira
    logs/inspecao_wireless.html  — HTML completo (para análise detalhada)
"""
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from browser import AirViewBrowser
from login import perform_login
from config import BASE_URL, TIMEOUTS

logger = logging.getLogger("airview.inspecionar")

LIMITE_ITENS = 40       # máximo de elementos listados por categoria
LIMITE_TEXTO = 60       # caracteres por texto exibido


def _resumir(texto: str, limite: int = LIMITE_TEXTO) -> str:
    if not texto:
        return ""
    texto = " ".join(texto.split())
    return texto[:limite] + ("…" if len(texto) > limite else "")


async def _listar_inputs(page):
    print("\n" + "=" * 70)
    print("  CAMPOS DE ENTRADA (input / textarea)")
    print("=" * 70)
    elementos = await page.locator("input, textarea").all()
    if not elementos:
        print("  (nenhum encontrado)")
        return
    for i, el in enumerate(elementos[:LIMITE_ITENS], 1):
        attrs = {}
        for attr in ("type", "name", "id", "placeholder", "aria-label", "role", "class"):
            try:
                v = await el.get_attribute(attr)
            except Exception:
                v = None
            if v:
                attrs[attr] = _resumir(v, 45)
        try:
            visivel = await el.is_visible()
        except Exception:
            visivel = "?"
        print(f"  [{i:02d}] visivel={visivel} {attrs}")
    if len(elementos) > LIMITE_ITENS:
        print(f"  ... (+{len(elementos) - LIMITE_ITENS} outros)")


async def _listar_botoes(page):
    print("\n" + "=" * 70)
    print("  BOTÕES")
    print("=" * 70)
    elementos = await page.locator("button, [role='button'], input[type='submit']").all()
    if not elementos:
        print("  (nenhum encontrado)")
        return
    for i, el in enumerate(elementos[:LIMITE_ITENS], 1):
        try:
            texto = _resumir(await el.inner_text())
        except Exception:
            texto = ""
        attrs = {}
        for attr in ("type", "aria-label", "title", "id", "class"):
            try:
                v = await el.get_attribute(attr)
            except Exception:
                v = None
            if v:
                attrs[attr] = _resumir(v, 40)
        try:
            visivel = await el.is_visible()
        except Exception:
            visivel = "?"
        print(f"  [{i:02d}] visivel={visivel} texto={texto!r} {attrs}")
    if len(elementos) > LIMITE_ITENS:
        print(f"  ... (+{len(elementos) - LIMITE_ITENS} outros)")


async def _listar_links(page):
    print("\n" + "=" * 70)
    print("  LINKS (primeiros com href)")
    print("=" * 70)
    elementos = await page.locator("a[href]").all()
    if not elementos:
        print("  (nenhum encontrado)")
        return
    for i, el in enumerate(elementos[:LIMITE_ITENS], 1):
        try:
            href = await el.get_attribute("href")
        except Exception:
            href = None
        try:
            texto = _resumir(await el.inner_text(), 40)
        except Exception:
            texto = ""
        print(f"  [{i:02d}] texto={texto!r} href={_resumir(href or '', 70)!r}")
    if len(elementos) > LIMITE_ITENS:
        print(f"  ... (+{len(elementos) - LIMITE_ITENS} outros)")


async def _listar_tabelas(page):
    print("\n" + "=" * 70)
    print("  TABELAS / LINHAS DE DADOS")
    print("=" * 70)
    for seletor in ("table", "[role='table']", "[role='grid']"):
        tabelas = await page.locator(seletor).all()
        if tabelas:
            print(f"  Seletor {seletor!r}: {len(tabelas)} encontrada(s)")

    cabecalhos = await page.locator("th, [role='columnheader']").all()
    if cabecalhos:
        print("\n  Cabeçalhos de coluna:")
        for i, th in enumerate(cabecalhos[:20], 1):
            try:
                print(f"    [{i:02d}] {_resumir(await th.inner_text(), 40)!r}")
            except Exception:
                pass

    for seletor in ("tbody tr", "[role='row']"):
        linhas = await page.locator(seletor).all()
        if linhas:
            print(f"\n  Linhas via {seletor!r}: {len(linhas)}")
            for i, tr in enumerate(linhas[:5], 1):
                try:
                    print(f"    [{i:02d}] {_resumir(await tr.inner_text(), 100)!r}")
                except Exception:
                    pass
            break


async def _inspecionar_pagina(page, rotulo: str):
    """Imprime a estrutura da página atual e salva screenshot + HTML."""
    print(f"\n✓ URL: {page.url}")
    try:
        print(f"✓ Título: {await page.title()}")
    except Exception:
        pass

    await _listar_inputs(page)
    await _listar_botoes(page)
    await _listar_links(page)
    await _listar_tabelas(page)

    png = f"logs/inspecao_{rotulo}.png"
    html_path = f"logs/inspecao_{rotulo}.html"
    try:
        await page.screenshot(path=png, full_page=True)
        html = await page.content()
        Path(html_path).write_text(html, encoding="utf-8")
        print(f"\n  Arquivos: {png} | {html_path} ({len(html)} caracteres)")
    except Exception as e:
        print(f"\n  (não foi possível salvar arquivos: {e})")


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    Path("logs").mkdir(exist_ok=True)

    browser = AirViewBrowser()
    page = None
    try:
        page = await browser.start()

        # ---- ETAPA 1: página de login (sem tentar logar) ----
        print("\n" + "#" * 70)
        print("#  ETAPA 1 — PÁGINA DE LOGIN")
        print("#" * 70)
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle",
                        timeout=TIMEOUTS["page_load"])
        await page.wait_for_timeout(4000)
        await _inspecionar_pagina(page, "login")

        # ---- ETAPA 2: tentar login e inspecionar /wireless ----
        print("\n" + "#" * 70)
        print("#  ETAPA 2 — LOGIN E PÁGINA /wireless")
        print("#" * 70)
        try:
            await perform_login(page)
            print(f"✓ Login OK — URL atual: {page.url}")

            await page.goto(f"{BASE_URL}/wireless", wait_until="networkidle",
                            timeout=TIMEOUTS["page_load"])
            await page.wait_for_timeout(4000)
            await _inspecionar_pagina(page, "wireless")
        except Exception as e:
            print(f"\n✗ Login não concluído: {e}")
            print("  Inspecionando a tela em que o navegador parou:")
            await _inspecionar_pagina(page, "apos_tentativa_login")

        print("\nInspeção concluída.")

    except Exception as e:
        logger.error(f"Falha na inspeção: {e}", exc_info=True)
        if page:
            try:
                await page.screenshot(path="logs/inspecao_erro.png", full_page=True)
                print("\nScreenshot do erro: logs/inspecao_erro.png")
            except Exception:
                pass
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
