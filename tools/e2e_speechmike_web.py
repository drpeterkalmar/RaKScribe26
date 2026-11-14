#!/usr/bin/env python3
"""tools/e2e_speechmike_web.py — Playwright-E2E v3.8.0 (SpeechMike, Peter 11.10., Nachtrag 1–4) für die Web-App.

navigator.hid ist nachgebaut (Attrappe eines SpeechMike 0911:0c1c, Usage-Page 0xFFA0): Tasten = echte Tastenberichte
(0x80 …, Bitmaske Byte 7/8) über das inputreport-Ereignis, LED-Befehle werden mitgeschrieben. Google (Token, 6-s-Chunks,
chirp_3, Gemini) ist per page.route gemockt; Mikrofon = Chromium-Testgerät. Lokaler vite preview, KEIN Praxis-Schlüssel
(selbst erzeugter Dummy). Geprüft:
  Record → Aufnahme (LED rot) → Record → Pause (LED rot blinkend, Abschnitt sofort repariert: chirp_3 + Fehlhör-Liste,
  kein Befund) → EOL in der Pause: nichts → Record → weiter → INS → Befund rechts, NICHTS kopiert (LED grün) → von Hand
  ändern → EOL → genau der geänderte Text in der Zwischenablage, alles leer (LED aus); „Nur Text“ per F2 → INS =
  korrigierter Text; F10 unverändert (Befund + automatisch kopiert); F1 = Neu; ohne Freigabe: „SpeechMike verbinden“
  (requestDevice mit SpeechMike-Filtern); ohne WebHID: kein Menüpunkt.
  /usr/bin/python3 tools/e2e_speechmike_web.py      (vorher: cd web_app && npm run build)
"""
import json, os, pathlib, re, signal, subprocess, sys, time
from playwright.sync_api import sync_playwright
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = pathlib.Path(os.environ.get("SHOTS", ROOT.parent / "RaKScribe26-work" / "shots")); SHOTS.mkdir(parents=True, exist_ok=True)
PORT = 4183
URL = f"http://localhost:{PORT}/RaKScribe26/"
NORMAL = "Kniegelenk rechts in 2 Ebenen unauffällig."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅ " if ok else "❌ ") + name + ("" if ok else f"  {detail}"), flush=True)
    fails += (not ok)


def dummy_key():
    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return json.dumps({"vertex_api_key": "AQ.e2e-dummy-key-not-valid-0000000000",
                       "stt": {"type": "service_account", "private_key": pem, "client_email": "e2e@dummy.iam.gserviceaccount.com"}})


HID_ATTRAPPE = r"""
(modus) => {
  if (modus === 'ohne') { Object.defineProperty(Navigator.prototype, 'hid', { get: () => undefined, configurable: true }); return; }
  window.__hidSent = []; window.__hidAnfragen = [];
  class Geraet extends EventTarget {
    constructor() { super(); Object.assign(this, { opened: false, vendorId: 0x0911, productId: 0x0c1c,
      productName: 'SpeechMike Premium', collections: [{ usagePage: 0xffa0, usage: 1 }] }); }
    async open() { this.opened = true; }
    async close() { this.opened = false; }
    async sendReport(id, data) { window.__hidSent.push([id, Array.from(data)]); }
  }
  const dev = new Geraet();
  let erlaubt = modus === 'erlaubt';
  const hid = new EventTarget();
  hid.getDevices = async () => (erlaubt ? [dev] : []);
  hid.requestDevice = async (o) => { window.__hidAnfragen.push(o); erlaubt = true; return [dev]; };
  Object.defineProperty(Navigator.prototype, 'hid', { get: () => hid, configurable: true });
  const BIT = { F1: 1 << 1, F2: 1 << 2, RECORD: 1 << 8, STOP: 1 << 9, PLAY: 1 << 10, EOL: 1 << 13, INS: 1 << 14 };
  const senden = (maske) => {
    const u = new Uint8Array([0x80, 0, 0, 0, 0, 0, 0, maske & 255, maske >> 8]);
    const e = new Event('inputreport');
    Object.assign(e, { device: dev, reportId: 0, data: new DataView(u.buffer) });
    dev.dispatchEvent(e);
  };
  window.__hidDruck = (taste) => { senden(BIT[taste]); setTimeout(() => senden(0), 60); };
}
"""

ANTWORTEN = {"chirp": [], "chunk": "Knie rechts", "gemini": NORMAL}
AUFRUFE = {"chirp": [], "chunk": 0, "gemini": 0, "token": 0}
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}


def google(route):
    req = route.request
    if req.method == "OPTIONS":
        return route.fulfill(status=204, headers=CORS)
    url = req.url
    if "oauth2.googleapis.com/token" in url:
        AUFRUFE["token"] += 1
        body = {"access_token": "e2e-token", "expires_in": 3600}
    elif "/recognizers/_:recognize" in url:  # chirp_3 (Reparatur bei der Pause bzw. Endtext)
        AUFRUFE["chirp"].append(len(json.loads(req.post_data or "{}").get("content", "")))
        text = ANTWORTEN["chirp"].pop(0) if ANTWORTEN["chirp"] else NORMAL
        body = {"results": [{"alternatives": [{"transcript": text}]}]}
    elif "speech:recognize" in url:          # 6-s-Chunks (Live-Anzeige)
        AUFRUFE["chunk"] += 1
        body = {"results": [{"alternatives": [{"transcript": ANTWORTEN["chunk"]}]}]}
    elif "aiplatform" in url:                # Schlüsselprüfung, Call 0 (Korrektur)
        AUFRUFE["gemini"] += 1
        body = {"candidates": [{"content": {"parts": [{"text": ANTWORTEN["gemini"]}]}, "finishReason": "STOP"}]}
    else:
        body = {}
    route.fulfill(status=200, headers={**CORS, "Content-Type": "application/json"}, body=json.dumps(body))


def neue_seite(browser, modus):
    ctx = browser.new_context(viewport={"width": 1400, "height": 860},
                              permissions=["microphone", "clipboard-read", "clipboard-write"])
    ctx.add_init_script(script=f"({HID_ATTRAPPE})({json.dumps(modus)})")
    ctx.route(re.compile(r"https://([a-z0-9-]+\.)*googleapis\.com/.*"), google)
    pg = ctx.new_page()
    pg.on("dialog", lambda d: (print("DIALOG:", d.message[:160]), d.dismiss()))
    pg.goto(URL)
    pg.wait_for_selector(".gate")
    return ctx, pg


def schluessel(pg):
    pg.click("text=Schlüssel einfügen")
    pg.fill(".paste-area", dummy_key())
    pg.click("text=Übernehmen")
    pg.wait_for_selector(".gate", state="detached", timeout=20000)


def taste(pg, name, warten=0.5):
    pg.evaluate(f"window.__hidDruck('{name}')")
    time.sleep(warten)


def label(pg):
    return pg.inner_text(".state-label")


def detail(pg):
    el = pg.query_selector(".state-detail")
    return el.inner_text() if el else ""


def led(pg):
    s = pg.evaluate("window.__hidSent")
    return s[-1] if s else None


def diktat(pg):
    return pg.locator("textarea.editor").first.input_value()


def befund(pg):
    pg.click(".seg button:text-is('Bearbeiten')")
    v = pg.input_value(".editor-report")
    pg.click(".seg button:text-is('Formatiert')")
    return v


def zwischenablage(pg):
    return pg.evaluate("navigator.clipboard.readText()")


LED = {"aus": [2, 0, 0, 0, 0, 0, 0, 0, 0], "aufnahme": [2, 0, 0, 0, 0, 0, 12, 0, 0], "pause": [2, 0, 0, 0, 0, 0, 4, 0, 0],
       "verarbeitung": [2, 0, 0, 0, 0, 0, 10, 0, 0], "befund_bereit": [2, 0, 0, 0, 0, 0, 3, 0, 0]}


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


srv = subprocess.Popen(["npx", "vite", "preview", "--port", str(PORT), "--strictPort"], cwd=ROOT / "web_app",
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
try:
    time.sleep(4)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--mute-audio", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
                                    "--use-angle=metal", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        # ── 1. SpeechMike bereits freigegeben (getDevices) ─────────────────────────────────────────────────────────
        ctx, pg = neue_seite(b, "erlaubt")
        schluessel(pg)
        check("1 SpeechMike automatisch verbunden (Anzeige oben)", warte(lambda: pg.is_visible("text=SpeechMike verbunden"), 10))
        check("1 LED nach dem Verbinden: aus", warte(lambda: led(pg) == [0, LED["aus"]], 5), str(led(pg)))
        pg.evaluate("navigator.clipboard.writeText('ALTER INHALT')")

        ANTWORTEN["chirp"] = ["Kniegelenk rechts pinnatus Sehne", NORMAL]
        taste(pg, "RECORD")
        check("2 Record → Aufnahme, LED rot", warte(lambda: label(pg) == "Aufnahme") and warte(lambda: led(pg) == [0, LED["aufnahme"]], 5),
              f"{label(pg)} / {led(pg)}")
        time.sleep(7)  # ein 6-s-Live-Chunk
        check("2 Live-Anzeige läuft (6-s-Chunk)", warte(lambda: "Knie rechts" in diktat(pg), 10), repr(diktat(pg)))
        taste(pg, "RECORD")
        check("3 Record → Pause, LED rot blinkend", warte(lambda: label(pg) == "Pause") and warte(lambda: led(pg) == [0, LED["pause"]], 5),
              f"{label(pg)} / {led(pg)}")
        check("3 Pause: Abschnitt sofort repariert (chirp_3 + Fehlhör-Liste), markiert",
              warte(lambda: diktat(pg) == "Kniegelenk rechts Supraspinatussehne", 15)
              and pg.is_visible("text=bis zur Pause repariert"), repr(diktat(pg)))
        check("3 Pause: kein Befund, nichts kopiert", pg.is_visible(".report-empty") and zwischenablage(pg) == "ALTER INHALT")
        pg.screenshot(path=str(SHOTS / "web_speechmike_pause.png"))
        taste(pg, "EOL")
        check("3 EOL in der Pause → nichts, Hinweis", label(pg) == "Pause" and "Erst INS" in detail(pg)
              and zwischenablage(pg) == "ALTER INHALT", detail(pg))
        n_chirp = len(AUFRUFE["chirp"])
        taste(pg, "RECORD")
        check("4 Record → weiter, LED rot", warte(lambda: label(pg) == "Aufnahme") and warte(lambda: led(pg) == [0, LED["aufnahme"]], 5))
        time.sleep(1.5)
        taste(pg, "INS", 0.1)
        check("4 INS → Befund wird erstellt (LED gelb)", warte(lambda: [0, LED["verarbeitung"]] in pg.evaluate("window.__hidSent"), 5))
        check("4 INS → Befund rechts, Hinweis „Befund prüfen“, LED grün",
              warte(lambda: label(pg) == "Bereit" and pg.is_visible(".report-view h3"), 20)
              and "Befund prüfen" in detail(pg) and warte(lambda: led(pg) == [0, LED["befund_bereit"]], 5), f"{detail(pg)} / {led(pg)}")
        check("4 Endtext aus der GANZEN Aufnahme (2. chirp_3-Aufruf länger als die Reparatur)",
              len(AUFRUFE["chirp"]) == n_chirp + 1 and AUFRUFE["chirp"][-1] > AUFRUFE["chirp"][0], str(AUFRUFE["chirp"]))
        check("4 INS: NICHTS kopiert", zwischenablage(pg) == "ALTER INHALT", zwischenablage(pg)[:60])
        pg.screenshot(path=str(SHOTS / "web_speechmike_kontrolle.png"))
        b1 = befund(pg)
        pg.click(".seg button:text-is('Bearbeiten')")
        pg.locator(".editor-report").press("End")
        pg.locator(".editor-report").evaluate("el => el.setSelectionRange(el.value.length, el.value.length)")
        pg.keyboard.type("\nVon Hand ergänzt.")
        pg.click(".seg button:text-is('Formatiert')")
        geaendert = befund(pg)
        check("5 Befund von Hand geändert", geaendert == b1 + "\nVon Hand ergänzt.", repr(geaendert[-40:]))
        taste(pg, "EOL")
        check("5 EOL → genau der geänderte Befund kopiert", warte(lambda: zwischenablage(pg) == geaendert.strip(), 5),
              repr(zwischenablage(pg)[-40:]))
        check("5 … alles leer, Hinweis „Befund kopiert – im RIS …“, LED aus",
              diktat(pg) == "" and pg.is_visible(".report-empty") and "Befund kopiert" in detail(pg)
              and warte(lambda: led(pg) == [0, LED["aus"]], 5), f"{detail(pg)} / {led(pg)}")
        taste(pg, "EOL")
        check("5 EOL ohne Befund → nichts, Hinweis", "Erst INS" in detail(pg) and zwischenablage(pg) == geaendert.strip())

        # ── 6. „Nur Text“ (Nachtrag 4) ────────────────────────────────────────────────────────────────────────────
        taste(pg, "F2")
        check("6 F2 → Nur Text an", pg.is_checked(".switch input") and "Nur Text: an" in detail(pg))
        ANTWORTEN["chirp"] = ["kniegelenk rechts kleiner erguss"]
        ANTWORTEN["gemini"] = "Kniegelenk rechts: kleiner Erguss."
        taste(pg, "RECORD")
        warte(lambda: label(pg) == "Aufnahme")
        time.sleep(1.5)
        taste(pg, "INS")
        check("6 Nur Text, INS → korrigierter Text ohne Überschriften, nichts kopiert",
              warte(lambda: label(pg) == "Bereit" and befund(pg) == "Kniegelenk rechts: kleiner Erguss.", 20)
              and zwischenablage(pg) == geaendert.strip(), repr(befund(pg)))
        taste(pg, "F2")
        check("6 F2 mit fertigem Text: bleibt unverändert", not pg.is_checked(".switch input")
              and befund(pg) == "Kniegelenk rechts: kleiner Erguss.")
        taste(pg, "EOL")
        check("6 Nur Text, EOL → genau dieser Text kopiert, leer", warte(lambda: zwischenablage(pg) == "Kniegelenk rechts: kleiner Erguss.", 5)
              and diktat(pg) == "")
        ANTWORTEN["gemini"] = NORMAL

        # ── 6b. Cursor im Befund + Record (Nachdiktat) → INS: nur das NEUE an der Cursor-Stelle ──────────────────
        ANTWORTEN["chirp"] = [NORMAL]
        taste(pg, "RECORD"); warte(lambda: label(pg) == "Aufnahme"); time.sleep(1.5); taste(pg, "INS")
        warte(lambda: label(pg) == "Bereit" and pg.is_visible(".report-view h3"), 20)
        B = befund(pg)
        pg.click(".seg button:text-is('Bearbeiten')")
        pg.locator(".editor-report").evaluate("el => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }")
        ANTWORTEN["chirp"] = ["zusätzlich kleiner Gelenkerguss"]
        ANTWORTEN["gemini"] = "Zusätzlich kleiner Gelenkerguss."
        vorher = zwischenablage(pg)
        taste(pg, "RECORD")
        check("6b Cursor im Befund: Record → Aufnahme fürs Einfügen an der Cursor-Stelle, links bleibt das Diktat",
              warte(lambda: label(pg) == "Aufnahme") and "Cursor-Stelle" in detail(pg) and diktat(pg).startswith(NORMAL), detail(pg))
        time.sleep(1.5)
        taste(pg, "INS")
        warte(lambda: label(pg) == "Bereit", 20)
        r = pg.input_value(".editor-report")
        check("6b INS → nur das NEU Diktierte an der Cursor-Stelle, alter Befund bleibt, nichts kopiert",
              r.startswith(B.rstrip()) and "Zusätzlich kleiner Gelenkerguss." in r[len(B.rstrip()):]
              and NORMAL not in r[len(B.rstrip()):] and zwischenablage(pg) == vorher, repr(r[len(B.rstrip()) - 10:]))
        check("6b … links das Gesamtdiktat (bisher + neu)", diktat(pg) == NORMAL + " Zusätzlich kleiner Gelenkerguss.", repr(diktat(pg)))
        ANTWORTEN["gemini"] = NORMAL
        taste(pg, "F1")
        warte(lambda: diktat(pg) == "")

        # ── 7. F10 unverändert, F1 = Neu ──────────────────────────────────────────────────────────────────────────
        pg.click("body")
        pg.keyboard.press("F10")
        check("7 F10 → Aufnahme (wie bisher)", warte(lambda: label(pg) == "Aufnahme"))
        time.sleep(1.5)
        pg.keyboard.press("F10")
        check("7 F10 → Befund + automatisch kopiert (wie bisher)",
              warte(lambda: label(pg) == "Bereit" and zwischenablage(pg).startswith("## "), 20), zwischenablage(pg)[:40])
        taste(pg, "RECORD")
        warte(lambda: label(pg) == "Aufnahme")
        check("7 Record nach F10: frisches Diktat (Feld geleert)", diktat(pg) in ("", "Knie rechts"), repr(diktat(pg)))
        taste(pg, "F1")
        check("7 F1 → Neu: Aufnahme verworfen, alles leer, LED aus", warte(lambda: label(pg) == "Bereit") and diktat(pg) == ""
              and befund(pg) == "" and warte(lambda: led(pg) == [0, LED["aus"]], 5), f"{label(pg)} / {diktat(pg)!r} / {led(pg)}")
        ctx.close()

        # ── 8. noch keine Freigabe → Menü „SpeechMike verbinden“ ──────────────────────────────────────────────────
        ctx, pg = neue_seite(b, "neu")
        schluessel(pg)
        pg.click("button[aria-label='Menü']")
        check("8 ohne Freigabe: Menüpunkt „SpeechMike verbinden“", pg.is_visible("text=SpeechMike verbinden")
              and not pg.is_visible(".sm-chip"))
        pg.click("button:has-text('SpeechMike verbinden')")
        check("8 Klick → requestDevice mit den SpeechMike-Filtern, danach verbunden",
              warte(lambda: pg.is_visible(".sm-chip"), 5)
              and pg.evaluate("window.__hidAnfragen[0].filters.every(f => f.vendorId === 0x0911 && f.usagePage === 0xffa0)"))
        ctx.close()

        # ── 9. Browser ohne WebHID (Safari/iPhone) ────────────────────────────────────────────────────────────────
        ctx, pg = neue_seite(b, "ohne")
        schluessel(pg)
        pg.click("button[aria-label='Menü']")
        check("9 ohne WebHID: kein SpeechMike-Menüpunkt, App läuft", not pg.is_visible("text=SpeechMike verbinden")
              and pg.is_visible("text=Schlüssel-Datei laden…") and pg.is_visible("text=EOL = fertig & weiter"))
        ctx.close()
        b.close()
finally:
    try:
        os.killpg(srv.pid, signal.SIGTERM)
    except Exception:
        srv.terminate()
print(f"Google-Attrappe: {AUFRUFE}")
print("FAILS:", fails)
sys.exit(1 if fails else 0)
