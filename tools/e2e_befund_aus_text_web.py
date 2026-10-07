#!/usr/bin/env python3
"""tools/e2e_befund_aus_text_web.py — Playwright-E2E v3.6.0 (Peter 07.10.): Text im Diktat-Feld tippen/einfügen und per
Knopf „Befund aus Text“ (bzw. Strg+Enter) strukturieren lassen. Echtes Gemini, lokaler vite preview, kein Mikrofon.
  PRAXIS_KEY=<pfad> /usr/bin/python3 tools/e2e_befund_aus_text_web.py
"""
import os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = pathlib.Path(os.environ["PRAXIS_KEY"]).read_text()
SHOTS = pathlib.Path(os.environ.get("SHOTS", ROOT.parent / "RaKScribe26-work" / "shots")); SHOTS.mkdir(parents=True, exist_ok=True)
srv = subprocess.Popen(["npx", "vite", "preview", "--port", "4182", "--strictPort"], cwd=ROOT / "web_app",
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)
URL = "http://localhost:4182/RaKScribe26/"
DIKTAT = ("Schulter rechts. Mäßiggradige Omarthrose. Tendinosis calcarea der Supraspinatussehne mit einem 17 mm "
          "messenden Kalkdepot. Geringe Bursitis subacromialis.")
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅ " if ok else "❌ ") + name + ("" if ok else f"  {detail}"))
    fails += (not ok)


def warten_fertig(pg):
    pg.wait_for_function("() => !document.querySelector('.panel-report .spin') && "
                         "document.querySelector('.state-label, .status-text') !== null", timeout=5000)
    pg.wait_for_function("() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Befund aus Text'));"
                         " return b && !b.disabled; }", timeout=120000)
    time.sleep(0.5)


def bericht(pg):
    pg.click(".seg button:text-is('Bearbeiten')")
    return pg.input_value(".editor-report")


try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1400, "height": 860}, permissions=["clipboard-read", "clipboard-write"])
        pg = ctx.new_page()

        def _dialog(d):
            print("DIALOG:", d.message[:200])
            d.dismiss()
        pg.on("dialog", _dialog)
        pg.goto(URL); pg.wait_for_selector(".gate")
        pg.click("text=Schlüssel einfügen"); pg.fill(".paste-area", KEY); pg.click("text=Übernehmen")
        pg.wait_for_selector(".gate", state="detached", timeout=20000)
        knopf = pg.locator("button", has_text="Befund aus Text")
        check("1 Knopf da, bei leerem Diktat-Feld gesperrt", knopf.count() == 1 and knopf.is_disabled())

        # 2 Text einfügen (Paste) und Knopf
        pg.evaluate(f"() => navigator.clipboard.writeText({DIKTAT!r})")
        pg.click(".panel-dictation .editor") if pg.locator(".panel-dictation .editor").count() else pg.locator("textarea.editor").first.click()
        pg.keyboard.press("Meta+V" if sys.platform == "darwin" else "Control+V")
        diktat = pg.locator("textarea.editor").first.input_value()
        check("2 Text ins Diktat-Feld eingefügt", diktat == DIKTAT, repr(diktat))
        t0 = time.time()
        knopf.click()
        warten_fertig(pg)
        r = bericht(pg)
        print(f"   Befund in {time.time() - t0:.1f}s:\n   " + r.replace("\n", "\n   "))
        check("2 strukturierter Befund (Titel, Befund, Ergebnis)", r.startswith("## ") and "## Ergebnis" in r and "## Befund" in r, repr(r[:200]))
        check("2 Inhalt übernommen (Omarthrose, Kalkdepot 17 mm, Bursitis)", all(w in r for w in ("Omarthrose", "17 mm", "Bursitis")), repr(r))
        check("2 Diktat-Feld bleibt stehen", pg.locator("textarea.editor").first.input_value() == DIKTAT)
        pg.click(".seg button:text-is('Formatiert')")
        pg.screenshot(path=str(SHOTS / "web_befund_aus_text.png"))

        # 3 getippt + Strg+Enter, auch bei „Nur Text“ → strukturiert
        pg.keyboard.press("F9"); time.sleep(0.5)
        pg.click(".switch")
        pg.locator("textarea.editor").first.click()
        pg.keyboard.type("Kniegelenk links unauffällig")
        pg.keyboard.press("Control+Enter")
        warten_fertig(pg)
        r = bericht(pg)
        check("3 Strg+Enter, Normalbefund strukturiert trotz „Nur Text“", "Kniegelenk" in r and "## Ergebnis" in r, repr(r[:200]))
        check("3 kein Zeilenumbruch ins Diktat", pg.locator("textarea.editor").first.input_value() == "Kniegelenk links unauffällig")
        pg.click(".switch")
        b.close()
finally:
    srv.terminate()
print("FAILS:", fails)
sys.exit(1 if fails else 0)
