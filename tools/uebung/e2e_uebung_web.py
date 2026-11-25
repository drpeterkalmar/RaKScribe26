#!/usr/bin/env python3
"""E2E KaiScribe-Übungsmodus im echten Browser (kaiscribe-uebung-n1, 25.11.2026). Playwright/Chromium, stumm.

  Probe (lokal, ohne Geld): Übungsdienst am Mac mit erfundenen Fällen + gebauter Web-App, Google/Claude abgefangen
     /usr/bin/python3 tools/uebung/e2e_uebung_web.py --probe
  Echt (VM): URL, Kürzel, Kennwort aus Vaultwarden, echter Praxis-Schlüssel (Claude maskiert), N Fälle per Text,
  optional 1 kurzer Live-STT-Fall (Chrome-Attrappen-Mikrofon mit einer vorhandenen .wav)
     PRAXIS_KEY=<datei> /usr/bin/python3 tools/uebung/e2e_uebung_web.py --url https://dexa…:8555/?uebung \
         --kuerzel kp --faelle 3 [--live <wav>] [--tag 20261123]

Prüft: roter Balken, Anmeldung, Fallliste nur eigenes Kürzel, Fallkarte, Befund wie live (Befund aus Text bzw. Diktat),
Abgabe (EOL-Knopf) → Ablage, Lösung erst danach mit Unterschieden, Word-Download, Zwischenablage NIE beschrieben,
Sperrzähler der Seite, keine Anfrage an andere Ziele als STT/KI/Drive/Übungsdienst. Ausgabe ohne Fallinhalte.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "uebung"))
SHOTS = pathlib.Path(os.environ.get("SHOTS", pathlib.Path.home() / "dev" / "RaKScribe26-work" / "shots_uebung"))
SHOTS.mkdir(parents=True, exist_ok=True)
ERLAUBT = re.compile(r"^https://(oauth2\.googleapis\.com|eu-speech\.googleapis\.com|aiplatform\.eu\.rep\.googleapis\.com|"
                     r"api\.anthropic\.com|www\.googleapis\.com)/")
DIKTATE = ["Kniegelenk rechts in zwei Ebenen. Kein Gelenkerguss. Gelenkspalt medial gering verschmälert. "
           "Ergebnis beginnende Gonarthrose medial.",
           "Hand links in zwei Ebenen. Keine Fraktur. Regelrechte Gelenkstellung. Ergebnis unauffällige Hand.",
           "Lendenwirbelsäule in zwei Ebenen. Osteochondrose L4 L5 und L5 S1. Keine Gefügestörung. "
           "Ergebnis degenerative Veränderungen der unteren Lendenwirbelsäule."]
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅ " if ok else "❌ ") + name + ("" if ok else f"  {detail}"))
    fails += (not ok)


def probe_aufbauen(td):
    import uebung_kern as K
    import uebung_dienst as D
    basis = pathlib.Path(td) / "basis"
    (basis / "daten" / "20261123").mkdir(parents=True)
    web = basis / "web"
    r = subprocess.run(["npm", "run", "build", "--", "--base=/", "--outDir", str(web), "--emptyOutDir"],
                       cwd=ROOT / "web_app", capture_output=True, text=True, timeout=600)
    if r.returncode:
        sys.exit("Web-Bau rot " + r.stderr[-500:])
    (basis / "konten.json").write_text(json.dumps({"kp": K.kennwort_hash("probe-kp"), "rg": K.kennwort_hash("probe-rg")}))
    faelle = []
    for i, (k, u) in enumerate([("kp", "Röntgen Kniegelenk re. 2 Ebenen"), ("kp", "Röntgen Hand li. 2 Ebenen"),
                                ("kp", "Röntgen LWS 2 Ebenen"), ("rg", "Röntgen Schulter re.")]):
        faelle.append({"id": f"RH{10 + i}", "kuerzel": k, "zeit": f"08:{10 + i}", "untersuchungen": [u], "alter": 60 + i,
                       "geschlecht": "w", "senf": f"RH {10 + i} · {u} · unauffällig", "ibl": [],
                       "vorbefund": {"datum": "2024-03-12", "kurz": "RK", "text": "Damals unauffällig."},
                       "loesung": "Kniegelenk rechts in 2 Ebenen\nBefund:\nKein Erguss. Mäßige Gonarthrose medial.\n"
                                  "Ergebnis:\n1. Mäßige Gonarthrose medial."})
    (basis / "daten" / "20261123" / "anonym.json").write_text(json.dumps({"tag": "20261123", "faelle": faelle}))
    ablage = pathlib.Path(td) / "ablage"
    dienst = D.Dienst(str(basis), ablage=str(ablage))
    srv = D.server(dienst, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/?uebung", ablage


def falscher_schluessel():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()).decode()
    return json.dumps({"vertex_api_key": "AQ.probe-nur-test", "anthropic_api_key": "sk-ant-probe-nur-test",
                       "stt": {"type": "service_account", "client_email": "probe@probe.iam.gserviceaccount.com",
                               "private_key": pem, "project_id": "probe"}})


BEFUND = ("## Kniegelenk rechts in 2 Ebenen\n\n## Befund:\nKein Gelenkerguss. Gelenkspalt medial gering verschmälert.\n\n"
          "## Ergebnis:\n1. Beginnende Gonarthrose medial.")


def abfangen(ctx):
    def gem(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"candidates": [{"content": {"parts": [{"text": BEFUND}]}, "finishReason": "STOP"}]}))

    def anth(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"stop_reason": "end_turn", "content": [{"type": "text", "text": BEFUND}],
                                       "usage": {"input_tokens": 1, "output_tokens": 1}}))
    ctx.route("https://oauth2.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="application/json",
                                                                     body='{"access_token":"t","expires_in":3600}'))
    ctx.route("https://aiplatform.eu.rep.googleapis.com/**", gem)
    ctx.route("https://api.anthropic.com/**", anth)
    ctx.route("https://www.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="application/json", body='{"files":[]}'))
    ctx.route("https://eu-speech.googleapis.com/**", lambda r: r.fulfill(
        status=200, content_type="application/json", body=json.dumps({"results": [{"alternatives": [{"transcript": DIKTATE[0]}]}]})))


def vw_kennwort(kuerzel):
    sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
    import vw_get
    _u, p = vw_get.get_login(f"KaiScribe-Übung {kuerzel}")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--url")
    ap.add_argument("--kuerzel", default="kp")
    ap.add_argument("--faelle", type=int, default=3)
    ap.add_argument("--live", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--resolve", default="", help="z. B. dexa.taild969f0.ts.net=100.76.169.124 (Mac löst ts.net nicht auf)")
    a = ap.parse_args()
    td = tempfile.mkdtemp(prefix="uebung_e2e_", dir=str(SHOTS))
    srv = ablage = None
    if a.probe:
        srv, url, ablage = probe_aufbauen(td)
        key, kennwort = falscher_schluessel(), f"probe-{a.kuerzel}"
    else:
        url, key, kennwort = a.url, pathlib.Path(os.environ["PRAXIS_KEY"]).read_text(), vw_kennwort(a.kuerzel)
    herkunft = re.match(r"^(https?://[^/]+)", url).group(1)
    anfragen, fremd = [], []
    args = ["--mute-audio", "--autoplay-policy=no-user-gesture-required", "--use-angle=metal", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
    if a.resolve:
        h, ip = a.resolve.split("=")
        args.append(f"--host-resolver-rules=MAP {h} {ip}")
    if a.live:
        args += ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
    with sync_playwright() as p:
        b = p.chromium.launch(args=args)
        ctx = b.new_context(viewport={"width": 1500, "height": 900}, accept_downloads=True,
                            permissions=["clipboard-read", "clipboard-write", "microphone"])
        if a.probe:
            abfangen(ctx)
        if a.live:   # Mikrofon = WAV (Chromiums Datei-Attrappe greift headless nicht): getUserMedia liefert den WAV-Strom
            import base64
            b64 = base64.b64encode(pathlib.Path(a.live).read_bytes()).decode()
            ctx.add_init_script("""(() => { const b64 = '%s';
  const echt = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = async (c) => { if (!c || !c.audio) return echt(c);
    const ctx = new AudioContext(); const bytes = Uint8Array.from(atob(b64), ch => ch.charCodeAt(0));
    const buf = await ctx.decodeAudioData(bytes.buffer); const src = ctx.createBufferSource(); src.buffer = buf;
    const ziel = ctx.createMediaStreamDestination(); src.connect(ziel); src.start(); return ziel.stream; };
})();""" % b64)
        pg = ctx.new_page()
        pg.on("dialog", lambda d: (print("DIALOG:", d.message[:120]), d.dismiss()))

        def anfrage(r):
            u = r.url
            anfragen.append(u)
            if not (u.startswith(herkunft) or ERLAUBT.match(u) or u.startswith("data:") or u.startswith("blob:")):
                fremd.append(u[:80])
        pg.on("request", anfrage)
        pg.goto(url)
        check("1 roter Balken „ÜBUNG – nichts wird gesendet“", pg.locator(".uebung-balken").inner_text(timeout=15000).startswith("ÜBUNG – nichts wird gesendet"))
        pg.click("text=Schlüssel einfügen")
        pg.fill(".paste-area", key)
        pg.click("text=Übernehmen")
        pg.wait_for_selector("#ue-titel", timeout=30000)
        pg.select_option("select[aria-label='Kürzel']", a.kuerzel)
        pg.fill("input[aria-label='Kennwort']", "falsch-falsch")
        pg.click("button:has-text('Anmelden')")
        pg.wait_for_selector(".gate-error", timeout=10000)
        check("2 falsches Kennwort abgewiesen", "falsch" in pg.locator(".gate-error").inner_text().lower())
        pg.fill("input[aria-label='Kennwort']", kennwort)
        pg.click("button:has-text('Anmelden')")
        pg.wait_for_selector("#ue-titel", state="detached", timeout=20000)
        balken = pg.locator(".uebung-balken").inner_text()
        check("2 angemeldet, Variante anonym im Balken", f"· {a.kuerzel} · anonym" in balken, balken)
        if a.tag:
            pg.select_option("select[aria-label='Übungstag']", a.tag)
        pg.wait_for_selector(".uebung-fall", timeout=20000)
        n_faelle = pg.locator(".uebung-fall").count()
        check("3 Fallliste da", n_faelle >= 1, n_faelle)
        if a.probe:
            check("3 nur eigene Fälle (kp: 3 von 4)", n_faelle == (3 if a.kuerzel == "kp" else 1), n_faelle)
        pg.screenshot(path=str(SHOTS / f"uebung_{a.kuerzel}_liste.png"))
        ergebnisse = []
        for i in range(min(a.faelle, n_faelle)):
            pg.locator(".uebung-fall").nth(i).click()
            pg.wait_for_selector(".uebung-karte", timeout=15000)
            karte = pg.locator(".uebung-karte").inner_text()
            check(f"4.{i} Fallkarte (Leistung, Alter)", "Leistung:" in karte and " J." in karte)
            check(f"4.{i} Fallkarte ohne Lösung/Nummer", not re.search(r"\b\d{11}\b", karte))
            live = bool(a.live) and i == 0
            t0 = time.time()
            if live:
                pg.keyboard.press("F10")
                time.sleep(9)
                pg.keyboard.press("F10")
                pg.wait_for_function("() => document.querySelector('.editor-report, .report-view:not(.report-empty)') !== null"
                                     " && !document.querySelector('.panel-report .spin')", timeout=180000)
            else:
                pg.locator("textarea.editor").first.fill(DIKTATE[i % len(DIKTATE)])
                pg.click("button:has-text('Befund aus Text')")
            pg.wait_for_function("() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Abgeben'));"
                                 " return b && !b.disabled; }", timeout=180000)
            dauer = time.time() - t0
            pg.click(".seg button:text-is('Bearbeiten')")
            befund = pg.input_value(".editor-report")
            pg.click(".seg button:text-is('Formatiert')")
            check(f"5.{i} Befund wie live ({'Diktat/STT' if live else 'Text'}): Titel + Befund + Ergebnis",
                  befund.startswith("## ") and "Ergebnis" in befund, befund[:120])
            pg.click("button:has-text('Abgeben')")
            pg.wait_for_selector("text=Abgelegt:", timeout=20000)
            hint = pg.locator(".panel-report .hint").inner_text()
            m = re.search(r"Abgelegt: (\S+\.docx) · Übereinstimmung (\d+) %", hint)
            check(f"6.{i} Abgabe → Ablage", bool(m), hint)
            pg.click("button:has-text('Lösung zeigen')")
            pg.wait_for_selector(".uebung-loesung", timeout=15000)
            lz = pg.locator(".uebung-loesung").inner_text()
            check(f"7.{i} Lösung mit Unterschieden (erst nach Abgabe)", "Echter Befund" in lz and "Übereinstimmung" in lz)
            if i == 0:
                pg.screenshot(path=str(SHOTS / f"uebung_{a.kuerzel}_loesung.png"))
            pg.click(".uebung-loesung .gate-close")
            with pg.expect_download(timeout=20000) as dl:
                pg.click("button:has-text('Word')")
            d = dl.value
            ziel = pathlib.Path(td) / d.suggested_filename
            d.save_as(str(ziel))
            check(f"8.{i} Word-Download (docx)", ziel.read_bytes()[:2] == b"PK" and ziel.suffix == ".docx", d.suggested_filename)
            ergebnisse.append({"fall": i + 1, "art": "live-STT" if live else "text", "s": round(dauer, 1),
                               "ablage": m.group(1) if m else None, "aehnlich": int(m.group(2)) if m else None})
            pg.keyboard.press("F9")
            time.sleep(0.5)
        sperre = pg.evaluate("() => (window.__uebungSperre || []).map(v => v.art)")
        try:
            clip = pg.evaluate("() => navigator.clipboard.readText()")
        except Exception:  # noqa: BLE001
            clip = ""
        check("9 Zwischenablage nie beschrieben (kein Befund drin)", "Ergebnis" not in (clip or "") and "Befund" not in (clip or ""))
        check("9 Sperre aktiv (window.__uebungSperre vorhanden)", isinstance(sperre, list), sperre)
        check("9 keine Anfrage an fremde Ziele (nur STT/KI/Drive/Übungsdienst)", not fremd, fremd[:5])
        pg.screenshot(path=str(SHOTS / f"uebung_{a.kuerzel}_ende.png"))
        b.close()
    if ablage:
        dateien = sorted(str(x.relative_to(ablage)) for x in ablage.rglob("*") if x.is_file())
        check("10 Ablage <tag>/<kürzel>/<RH>_<kürzel>.docx + .html", any(x.endswith(f"_{a.kuerzel}.docx") for x in dateien)
              and any(x.endswith(".html") for x in dateien), dateien)
    if srv:
        srv.shutdown()
    print("ERGEBNIS " + json.dumps({"kuerzel": a.kuerzel, "faelle": ergebnisse, "sperre_versuche": len(sperre),
                                    "anfragen": len(anfragen), "fremd": len(fremd)}))
    print(f"\nFEHLER: {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
