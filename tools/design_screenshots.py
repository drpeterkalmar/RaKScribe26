#!/usr/bin/env python3
"""tools/design_screenshots.py — Bildschirmfotos der Web-App in festen Zuständen (Design-Test unslop, 04.11.2026).

Kein Praxis-Schlüssel: selbst erzeugter Dummy, Google (Token, Chunks, chirp_3, Gemini) per page.route gemockt,
Mikrofon = Chromium-Testgerät, Browser stumm. Zustände je Fenstergröße (1920×1080, 1366×768):
  01_gesperrt, 02_fehler_schluessel, 03_bereit, 04_aufnahme, 05_verarbeitung, 06_befund_formatiert,
  07_befund_bearbeiten, 08_menue, 09_fehler_verarbeitung
Aufruf: /usr/bin/python3 tools/design_screenshots.py <dist-Ordner> <Ausgabe-Ordner> [port]
"""
import json, pathlib, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).expanduser(); OUT.mkdir(parents=True, exist_ok=True)
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 4191
URL = f"http://localhost:{PORT}/RaKScribe26/"
GROESSEN = {"1920": (1920, 1080), "1366": (1366, 768)}

DIKTAT = ("Schulter rechts in zwei Ebenen. Mäßiggradige Omarthrose mit kaudalem Osteophyten. Tendinosis calcarea "
          "der Supraspinatussehne mit einem 17 mm messenden Kalkdepot. Akromion Typ 2 nach Bigliani.")
BEFUND = """## Röntgen Schulter rechts in 2 Ebenen

## Befund
Mäßiggradige Omarthrose mit kaudalem Osteophyten am Humeruskopf. Gelenkspalt glenohumeral leicht verschmälert.
Schollige Verkalkung in Projektion auf die Supraspinatussehne, Ausdehnung 17 mm.
Akromion Typ 2 nach Bigliani, subakromialer Raum mit 8 mm normal weit.
AC-Gelenk mit geringer Arthrose, keine Stufenbildung.

## Ergebnis
1. Tendinosis calcarea der Supraspinatussehne (Kalkdepot 17 mm).
2. Mäßiggradige Omarthrose.
3. Geringe AC-Gelenksarthrose."""

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}
MODUS = {"gemini": "ok"}   # ok | warten | fehler
WARTEND = []


def dummy_key():
    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return json.dumps({"vertex_api_key": "AQ.design-dummy-key-not-valid-000000000",
                       "stt": {"type": "service_account", "private_key": pem, "client_email": "design@dummy.iam.gserviceaccount.com"}})


def antwort(route, body, status=200):
    route.fulfill(status=status, headers={**CORS, "Content-Type": "application/json"}, body=json.dumps(body))


def gemini_ok(route):
    antwort(route, {"candidates": [{"content": {"parts": [{"text": BEFUND}]}, "finishReason": "STOP"}]})


def google(route):
    req = route.request
    if req.method == "OPTIONS":
        return route.fulfill(status=204, headers=CORS)
    url = req.url
    if "oauth2.googleapis.com/token" in url:
        return antwort(route, {"access_token": "design-token", "expires_in": 3600})
    if "/recognizers/_:recognize" in url or "speech:recognize" in url:
        return antwort(route, {"results": [{"alternatives": [{"transcript": DIKTAT}]}]})
    if "aiplatform" in url:
        if MODUS["gemini"] == "warten":
            return WARTEND.append(route)
        if MODUS["gemini"] == "fehler":
            return antwort(route, {"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}}, 503)
        return gemini_ok(route)
    antwort(route, {})


def warte(bed, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if bed():
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def lauf(browser, groesse):
    w, h = GROESSEN[groesse]
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                              permissions=["microphone", "clipboard-read", "clipboard-write"])
    ctx.route(re.compile(r"https://([a-z0-9-]+\.)*googleapis\.com/.*"), google)
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.dismiss())
    shot = lambda name: pg.screenshot(path=str(OUT / f"{name}_{groesse}.png"))
    MODUS["gemini"] = "ok"
    pg.goto(URL); pg.wait_for_selector(".gate"); time.sleep(0.5)
    shot("01_gesperrt")
    pg.click("text=Schlüssel einfügen"); pg.fill(".paste-area", "kein schluessel"); pg.click("text=Übernehmen")
    pg.wait_for_selector(".gate-error"); time.sleep(0.3)
    shot("02_fehler_schluessel")
    pg.fill(".paste-area", dummy_key()); pg.click("text=Übernehmen")
    pg.wait_for_selector(".gate", state="detached", timeout=20000); time.sleep(0.8)
    pg.mouse.move(w - 5, h - 5)
    shot("03_bereit")
    # Aufnahme: F10, warten bis ein 6-s-Stück erkannt ist
    pg.keyboard.press("F10")
    warte(lambda: DIKTAT[:20] in pg.locator("textarea.editor").first.input_value(), 20); time.sleep(0.6)
    shot("04_aufnahme")
    pg.keyboard.press("F10")
    warte(lambda: pg.inner_text(".state-label") == "Bereit" and pg.locator(".report-view h3").count() > 0, 40)
    # Verarbeitung + Befund über „Befund aus Text“ (Gemini hängt, bis das Foto gemacht ist)
    pg.keyboard.press("F9"); time.sleep(0.5)
    pg.locator("textarea.editor").first.fill(DIKTAT)
    MODUS["gemini"] = "warten"
    pg.click("button:has-text('Befund aus Text')")
    warte(lambda: WARTEND, 15); time.sleep(0.6)
    shot("05_verarbeitung")
    MODUS["gemini"] = "ok"
    while WARTEND:
        gemini_ok(WARTEND.pop(0)); time.sleep(0.3)
    warte(lambda: pg.inner_text(".state-label") in ("Bereit", "Kopiert") and pg.locator(".report-view h3").count() > 0, 20)
    time.sleep(0.6); pg.mouse.move(w - 5, h - 5)
    shot("06_befund_formatiert")
    pg.click(".seg button:text-is('Bearbeiten')"); time.sleep(0.3)
    shot("07_befund_bearbeiten")
    pg.click(".seg button:text-is('Formatiert')"); time.sleep(0.2)
    pg.click(".menu .icon-button"); time.sleep(0.3)
    shot("08_menue")
    pg.keyboard.press("Escape"); time.sleep(0.2)
    MODUS["gemini"] = "fehler"
    pg.click("button:has-text('Befund aus Text')")
    warte(lambda: "Fehler" in pg.inner_text(".state-pill"), 30); time.sleep(0.6)
    pg.mouse.move(w - 5, h - 5)
    shot("09_fehler_verarbeitung")
    ctx.close()


srv = subprocess.Popen(["npx", "vite", "preview", "--port", str(PORT), "--strictPort", "--outDir", str(DIST)],
                       cwd=ROOT / "web_app", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
try:
    time.sleep(4)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--mute-audio", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
        for g in GROESSEN:
            lauf(b, g)
            print("fertig:", g, flush=True)
        b.close()
finally:
    srv.terminate()
    try:
        srv.wait(5)
    except Exception:
        srv.kill()
print("Fotos in", OUT)
