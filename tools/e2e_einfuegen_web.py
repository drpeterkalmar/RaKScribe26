#!/usr/bin/env python3
"""tools/e2e_einfuegen_web.py — Playwright-E2E v3.5.0 (Peter 07.10.): Befund bearbeiten und an der Cursor-Stelle diktieren.

Echte Spracherkennung (chirp_3) + Gemini, Mikrofon = WAV-Datei (Chromium fake device), lokaler vite preview.
  PRAXIS_KEY=<pfad> AUDIO=<wav, z. B. „Zusätzlich kleiner Gelenkerguss …“> /usr/bin/python3 tools/e2e_einfuegen_web.py
1) Schlüssel laden, Befund in der Text-Ansicht tippen (bearbeitbar)
2) Cursor mitten in den Befund, F10 … F10 → Diktat an genau der Stelle, Rest unverändert
3) Text markieren, Aufnahme-Knopf → Markierung durch das Diktat ersetzt
4) Klick in die formatierte Ansicht → Text-Ansicht mit Cursor an derselben Stelle
5) ohne Cursor im Befund → normaler neuer Befund
"""
import os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = pathlib.Path(os.environ["PRAXIS_KEY"]).read_text()
AUDIO = os.environ["AUDIO"]
SHOTS = pathlib.Path(os.environ.get("SHOTS", ROOT.parent / "RaKScribe26-work" / "shots")); SHOTS.mkdir(parents=True, exist_ok=True)
srv = subprocess.Popen(["npx", "vite", "preview", "--port", "4181", "--strictPort"], cwd=ROOT / "web_app",
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)
URL = "http://localhost:4181/RaKScribe26/"
BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt.\n\n## Ergebnis\nUnauffälliger Befund."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅ " if ok else "❌ ") + name + ("" if ok else f"  {detail}"))
    fails += (not ok)


def diktieren(pg, per_knopf=False, sekunden=5):
    if per_knopf:
        pg.click(".btn-record")
    else:
        pg.keyboard.press("F10")
    pg.wait_for_selector(".btn-record.is-recording", timeout=10000)
    time.sleep(sekunden)
    pg.keyboard.press("F10")
    pg.wait_for_function("() => !document.querySelector('.btn-record.is-recording') && "
                         "!document.querySelector('.panel-report .spin')", timeout=90000)
    time.sleep(0.5)


def bericht(pg):
    if pg.locator(".editor-report").count():
        return pg.input_value(".editor-report")
    pg.click(".seg button:text-is('Bearbeiten')")
    return pg.input_value(".editor-report")


try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                    f"--use-file-for-fake-audio-capture={AUDIO}"])
        ctx = b.new_context(viewport={"width": 1400, "height": 860}, permissions=["microphone", "clipboard-read", "clipboard-write"])
        pg = ctx.new_page()
        def _dialog(d):
            print("DIALOG:", d.message[:200])
            d.dismiss()
        pg.on("dialog", _dialog)
        pg.goto(URL); pg.wait_for_selector(".gate")
        pg.click("text=Schlüssel einfügen"); pg.fill(".paste-area", KEY); pg.click("text=Übernehmen")
        pg.wait_for_selector(".gate", state="detached", timeout=20000)

        # 1 Befund tippen (Text-Ansicht bearbeitbar)
        pg.click(".seg button:text-is('Bearbeiten')")
        pg.fill(".editor-report", BEFUND)
        check("1 Befund in der Text-Ansicht bearbeitbar", pg.input_value(".editor-report") == BEFUND)

        # 2 Cursor vor „Bänder“, F10 … F10
        pos = BEFUND.index("Bänder")
        pg.focus(".editor-report")
        pg.evaluate(f"() => document.querySelector('.editor-report').setSelectionRange({pos}, {pos})")
        diktieren(pg)
        r = bericht(pg)
        vor, nach = r.split("Bänder intakt.")[0] if "Bänder intakt." in r else r, ""
        check("2 Befund bleibt erhalten (Titel, Ergebnis, Bänder-Satz)", r.startswith("## Kniegelenk rechts\n\n## Befund\nKein Erguss. ")
              and "Bänder intakt.\n\n## Ergebnis\nUnauffälliger Befund." in r, repr(r))
        eingefuegt = r[len("## Kniegelenk rechts\n\n## Befund\nKein Erguss. "):r.find("Bänder intakt.")].strip()
        check("2 Diktat steht an der Cursor-Stelle (vor „Bänder“)", "erguss" in eingefuegt.lower(), repr(eingefuegt))
        print("   eingefügt:", repr(eingefuegt))
        sel = pg.evaluate("() => { const e = document.querySelector('.editor-report'); return [document.activeElement === e, e.selectionStart]; }")
        check("2 Cursor danach hinter dem eingefügten Text, Fokus im Befund", sel[0] and r[:sel[1]].rstrip().endswith(eingefuegt[-8:]), str(sel))
        pg.screenshot(path=str(SHOTS / "web_einfuegen_cursor.png"))

        # 3 Markierung „Kein Erguss.“ → per Aufnahme-Knopf ersetzen
        pg.fill(".editor-report", BEFUND)
        a = BEFUND.index("Kein Erguss.")
        pg.focus(".editor-report")
        pg.evaluate(f"() => document.querySelector('.editor-report').setSelectionRange({a}, {a + len('Kein Erguss.')})")
        diktieren(pg, per_knopf=True)
        r = bericht(pg)
        check("3 Markierung durch das Diktat ersetzt", "Kein Erguss." not in r and "Bänder intakt." in r
              and r.startswith("## Kniegelenk rechts\n\n## Befund\n"), repr(r))

        # 4 Klick in die formatierte Ansicht
        pg.fill(".editor-report", BEFUND)
        pg.click(".seg button:text-is('Formatiert')")
        el = pg.locator(".report-view p", has_text="Bänder intakt")
        bb = el.bounding_box()
        assert bb is not None
        pg.mouse.click(bb["x"] + 2, bb["y"] + bb["height"] / 2)
        time.sleep(0.4)
        info = pg.evaluate("() => { const e = document.querySelector('.editor-report'); return e ? [document.activeElement === e, e.selectionStart] : null; }")
        check("4 Klick in formatierte Ansicht → Text-Ansicht, Fokus + Cursor im Befund", info and info[0]
              and BEFUND.index("Kein Erguss.") <= info[1] <= BEFUND.index("Bänder intakt.") + 3, str(info))

        # 5 ohne Cursor im Befund → normaler Befund
        pg.click(".panel-dictation .editor") if pg.locator(".panel-dictation .editor").count() else pg.click("h2")
        pg.evaluate("() => document.activeElement && document.activeElement.blur()")
        diktieren(pg)
        r = bericht(pg)
        check("5 ohne Cursor im Befund: neuer strukturierter Befund (Kniegelenk-Vorlage weg)", "## Befund" in r and "## Ergebnis" in r
              and "Kein Erguss. Bänder intakt." not in r, repr(r[:200]))
        pg.screenshot(path=str(SHOTS / "web_einfuegen_normal.png"))
        b.close()
finally:
    srv.terminate()
print("FAILS:", fails)
sys.exit(1 if fails else 0)
