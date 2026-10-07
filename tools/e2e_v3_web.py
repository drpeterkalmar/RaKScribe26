#!/usr/bin/env python3
"""tools/e2e_v3_web.py — Playwright-E2E der Web v3.0 (lokaler vite preview):
1) Start: Gate sichtbar, Aufnahme-Button disabled, F10 wirkungslos
2) falscher Schlüssel → Fehlermeldung
3) Drag&Drop des Praxis-Keys (echtes DataTransfer-Drop-Event) → Gate weg
4) Reload → bleibt freigeschaltet (beide Schlüssel persistiert)
5) Audio-Upload (echtes Diktat) → Befund mit ## Befund/## Ergebnis
6) Menü → Schlüssel entfernen → Gate wieder da
7) Mobil 390x844: kein Horizontal-Scroll, Gate-Button sichtbar
Screenshots → ~/dev/RaKScribe26-work/shots/"""
import json, os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path.home() / "dev/RaKScribe26"
SHOTS = pathlib.Path.home() / "dev/RaKScribe26-work/shots"; SHOTS.mkdir(parents=True, exist_ok=True)
KEY = pathlib.Path(os.environ["PRAXIS_KEY"]).read_text()
AUDIO = ROOT / "web_app/public/schulter_diktat.ogg"
srv = subprocess.Popen(["npx", "vite", "preview", "--port", "4179", "--strictPort"], cwd=ROOT / "web_app",
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)
URL = "http://localhost:4179/RaKScribe26/"
res = []
def check(name, cond):
    res.append((name, bool(cond))); print(("✅ " if cond else "❌ ") + name)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        ctx = b.new_context(viewport={"width": 1400, "height": 860}, permissions=["microphone"])
        pg = ctx.new_page(); logs = []
        pg.on("console", lambda m: logs.append(m.text))
        pg.goto(URL); pg.wait_for_selector(".gate")
        check("1 Gate beim Start sichtbar", pg.is_visible("text=Praxis-Schlüssel laden"))
        check("1 Status zeigt Gesperrt", pg.inner_text(".state-pill").strip().startswith("Gesperrt"))
        check("1 Aufnahme-Button gesperrt", pg.is_disabled(".btn-record"))
        pg.keyboard.press("F10"); time.sleep(0.5)
        check("1 F10 ohne Schlüssel wirkungslos", pg.locator(".state-pill.state-recording").count() == 0)
        pg.screenshot(path=str(SHOTS / "web_1_gate.png"))
        # 2 falscher Schlüssel via Einfügen
        pg.click("text=Schlüssel einfügen"); pg.fill(".paste-area", "kein schluessel"); pg.click("text=Übernehmen")
        check("2 falscher Schlüssel → Fehlermeldung", pg.is_visible(".gate-error"))
        pg.click(".gate-close")
        # 3 Drag&Drop (echtes DataTransfer)
        pg.evaluate("""(txt) => {
            const dt = new DataTransfer();
            dt.items.add(new File([txt], 'rakscribe-praxis-key.json', {type: 'application/json'}));
            for (const t of ['dragenter','dragover','drop']) window.dispatchEvent(new DragEvent(t, {dataTransfer: dt, bubbles: true, cancelable: true}));
        }""", KEY)
        pg.wait_for_selector(".gate", state="detached", timeout=5000)
        check("3 Drag&Drop → Gate weg", pg.locator(".gate").count() == 0)
        check("3 Schlüssel-Chip aktiv", pg.is_visible(".key-chip.ok"))
        pg.screenshot(path=str(SHOTS / "web_2_workspace.png"))
        # 4 Reload
        pg.reload(); time.sleep(1.5)
        check("4 nach Reload weiterhin freigeschaltet", pg.locator(".gate").count() == 0 and pg.is_enabled(".btn-record"))
        # 5 Audio-Upload
        pg.set_input_files("input[accept^='audio']", str(AUDIO))
        pg.wait_for_function("() => (document.querySelector('.report-view')?.innerText || '').includes('Ergebnis') && document.querySelectorAll('.report-view h3').length >= 2", timeout=90000)
        check("5 Befund formatiert (Überschriften gerendert, kein '##')", '##' not in pg.inner_text('.report-view'))
        pg.click(".seg button:has-text('Bearbeiten')")
        rep = pg.input_value(".editor-report")
        pg.click(".seg button:has-text('Formatiert')")
        check("5 Audio → Befund mit ## Befund + ## Ergebnis", "## Befund" in rep and "## Ergebnis" in rep and len(rep.split("## Ergebnis")[1].strip()) > 5)
        check("5 Fachbegriffe (Supraspinatus, Bizeps)", "supraspinatus" in rep.lower() and "bizeps" in rep.lower())
        pg.screenshot(path=str(SHOTS / "web_3_befund.png"))
        print("----- BEFUND -----\n" + rep[:900] + "\n------------------")
        # 6 Menü → entfernen
        pg.click(".menu .icon-button"); pg.screenshot(path=str(SHOTS / "web_4_menu.png"))
        pg.click("text=Schlüssel entfernen"); time.sleep(0.5)
        check("6 Schlüssel entfernen → Gate wieder da", pg.is_visible("text=Praxis-Schlüssel laden"))
        # Datei-Dialog-Pfad (wie iPhone-Picker)
        kp = pathlib.Path("/tmp/_e2e_key.json"); kp.write_text(KEY)
        pg.set_input_files(".gate input[type=file]", str(kp)); kp.unlink()
        pg.wait_for_selector(".gate", state="detached", timeout=5000)
        check("6 Datei-Dialog-Pfad → freigeschaltet", pg.locator(".gate").count() == 0)
        # 7 Mobil
        m = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mp = m.new_page(); mp.goto(URL); mp.wait_for_selector(".gate")
        sw = mp.evaluate("document.documentElement.scrollWidth")
        check(f"7 Mobil: kein Horizontal-Scroll (scrollWidth={sw})", sw <= 390)
        check("7 Mobil: Gate-Button sichtbar", mp.is_visible("text=Schlüssel-Datei wählen"))
        mp.screenshot(path=str(SHOTS / "web_5_mobil.png"))
        errs = [l for l in logs if "error" in l.lower() and "favicon" not in l.lower()]
        print("Konsole-Fehler:", errs[:5])
        b.close()
finally:
    srv.terminate()
bad = [n for n, ok in res if not ok]
print(f"\n{len(res) - len(bad)}/{len(res)} PASS")
sys.exit(1 if bad else 0)
