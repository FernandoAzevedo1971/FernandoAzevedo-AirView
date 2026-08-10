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


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    Path("logs").mkdir(exist_ok=True)

    browser = AirViewBrowser()
    page = None
    try:
        page = await browser.start()

        print("\nRealizando login...")
        await perform_login(page)
        print(f"✓ Login OK — URL atual: {page.url}")

        print("\nAbrindo /wireless...")
        await page.goto(f"{BASE_URL}/wireless", wait_until="networkidle",
                        timeout=TIMEOUTS["page_load"])
        await page.wait_for_timeout(4000)

        print(f"✓ URL: {page.url}")
        print(f"✓ Título: {await page.title()}")

        await _listar_inputs(page)
        await _listar_botoes(page)
        await _listar_links(page)
        await _listar_tabelas(page)

        await page.screenshot(path="logs/inspecao_wireless.png", full_page=True)
        html = await page.content()
        Path("logs/inspecao_wireless.html").write_text(html, encoding="utf-8")

        print("\n" + "=" * 70)
        print("  ARQUIVOS GERADOS")
        print("=" * 70)
        print("  logs/inspecao_wireless.png   (screenshot)")
        print(f"  logs/inspecao_wireless.html  (HTML, {len(html)} caracteres)")
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
