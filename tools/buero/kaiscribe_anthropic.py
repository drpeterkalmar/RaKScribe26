"""KaiScribe auf Claude Sonnet umstellen – Helfer am Büro-PC (kaiscribe-sonnet-n2, 16.11.2026, Peters Go 14.11.).

Läuft am Büro-PC als Benutzer cas (py -3.12, nur Standardbibliothek), aufgerufen vom Ordi-Hermes. Gibt NIE einen
Schlüssel, eine Schlüssellänge, Diktat- oder Patientendaten aus – nur ja/nein, Feldnamen, HTTP-Status, Zeilen der
config.ini, die mit LLM_/ANTHROPIC_ beginnen, und KaiScribe-Logzeilen [KI]/[INIT] (enthalten keine Inhalte).

  py -3.12 kaiscribe_anthropic.py schluessel [--datei X:\\RaKScribe\\rakscribe-praxis-key.json] [--pruefen]
      Anthropic-Schlüssel des Praxisbetriebs (Konto A, Windows-Anmeldeinformation „RaK-Anthropic-KaiFormat“ des
      Benutzers cas, seit KaiFormat n2) als Feld "anthropic_api_key" in die Praxis-Schlüsseldatei auf X: übernehmen
      (alle Befund-PCs lesen sie neben der EXE). Vorher Sicherung X:\\RaKScribe\\_alt\\…; vertex_api_key/stt bleiben
      unverändert (zurückgelesen). --pruefen: ein Mini-Aufruf an Anthropic (max. 5 Token, kein Patiententext) →
      HTTP-Status. Schluss: ANTHKEY=<ok|schon|rot> …
  py -3.12 kaiscribe_anthropic.py config [--datei X:\\RaKScribe\\config.ini] [--anbieter anthropic|gemini]
      [SETTINGS] LLM_ANBIETER / ANTHROPIC_MODELL / ANTHROPIC_FRIST setzen (Sicherung vorher). gemini = Notschalter
      zurück. Wirkt beim nächsten Start von KaiScribe. Schluss: KSCONFIG=<ok|schon|rot> …
  py -3.12 kaiscribe_anthropic.py probe --exe <Kopie\\rakscribe26.exe> [--schluessel X:\\RaKScribe\\rakscribe-praxis-key.json]
      Die EXE-KOPIE (nie X:\\RaKScribe\\rakscribe26.exe) im WAV-Modus (Gast, kein CAS, kein Mikrofon, keine
      Spracherkennung) mit einem getippten Testsatz „Befund aus Text“ starten, warten, beenden. Gibt die [KI]-/[INIT]-
      Zeilen ihres rakscribe.log und den synthetischen Befund aus. Schluss: KSPROBE=<ok|rot> ANBIETER=<…>
Exit 0 = ok/schon, 1 = rot.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ZIEL = "RaK-Anthropic-KaiFormat"
X = "X:\\RaKScribe"
SCHLUESSEL = os.path.join(X, "rakscribe-praxis-key.json")
CONFIG = os.path.join(X, "config.ini")
ALT = os.path.join(X, "_alt")
WERTE = {"anthropic": [("LLM_ANBIETER", "anthropic"), ("ANTHROPIC_MODELL", "claude-sonnet-5-5"), ("ANTHROPIC_FRIST", "20")],
         "gemini": [("LLM_ANBIETER", "gemini")]}
TESTSATZ = "Kniegelenk links. Mäßige Gonarthrose medial. Kleiner Gelenkerguss."


def stempel():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def key_windows(ziel=ZIEL):
    """Generische Windows-Anmeldeinformation lesen (wie ris-mods bruecke/ki_format.key_windows). Nie ausgeben."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
                    ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
                    ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
                    ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
                    ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]
    p = ctypes.POINTER(CREDENTIAL)()
    adv = ctypes.windll.advapi32
    if not adv.CredReadW(ziel, 1, 0, ctypes.byref(p)):
        return None
    try:
        roh = ctypes.string_at(p.contents.CredentialBlob, p.contents.CredentialBlobSize)
    finally:
        adv.CredFree(p)
    for kod in ("utf-16-le", "utf-8"):
        try:
            k = roh.decode(kod).strip("\x00").strip()
        except UnicodeDecodeError:
            continue
        if k.startswith("sk-ant-"):
            return k
    return None


def lese_json(pfad):
    with open(pfad, "rb") as f:
        roh = f.read()
    if roh.startswith(b"\xff\xfe") or roh.startswith(b"\xfe\xff"):
        roh = roh.decode("utf-16").encode("utf-8")
    if roh.startswith(b"\xef\xbb\xbf"):
        roh = roh[3:]
    return json.loads(roh.decode("utf-8"))


def schluessel_einsetzen(datei, key, alt_ordner):
    """→ ('ok'|'schon', Sicherungspfad|None). Wirft bei jedem Problem (dann ist nichts geändert)."""
    d = lese_json(datei)
    if not isinstance(d, dict):
        raise ValueError("Schlüsseldatei ist kein JSON-Objekt")
    if d.get("anthropic_api_key") == key:
        return "schon", None
    os.makedirs(alt_ordner, exist_ok=True)
    sicherung = os.path.join(alt_ordner, os.path.basename(datei) + ".vor-sonnet-" + stempel())
    shutil.copy2(datei, sicherung)
    neu = dict(d, anthropic_api_key=key)
    tmp = datei + ".neu"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(neu, f, ensure_ascii=False, indent=2)
    os.replace(tmp, datei)
    z = lese_json(datei)
    if z.get("anthropic_api_key") != key or any(z.get(k) != d.get(k) for k in d):
        shutil.copy2(sicherung, datei)
        raise ValueError("Zurückgelesen ungleich – Sicherung zurückgespielt")
    return "ok", sicherung


def anthropic_pruefen(key, urlopen=None):
    """Mini-Aufruf (max. 5 Token, fester Text ohne Patientendaten) → HTTP-Status als Text."""
    body = {"model": "claude-sonnet-5-5", "max_tokens": 5, "messages": [{"role": "user", "content": "Antworte nur: OK"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with (urlopen or urllib.request.urlopen)(req, timeout=20) as r:
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return type(e).__name__ + ":" + re.sub(r"\s+", " ", str(e))[:80]


def config_setzen(text, werte):
    """config.ini-Text → neuer Text: Schlüssel in [SETTINGS] ersetzen bzw. direkt nach dem Kopf ergänzen."""
    zeilen = text.splitlines()
    kopf = next((i for i, z in enumerate(zeilen) if z.strip().upper() == "[SETTINGS]"), None)
    if kopf is None:
        zeilen = ["[SETTINGS]"] + zeilen
        kopf = 0
    ende = next((i for i in range(kopf + 1, len(zeilen)) if zeilen[i].strip().startswith("[")), len(zeilen))
    fehlt = []
    for name, wert in werte:
        rx = re.compile(r"^\s*" + name + r"\s*=", re.I)
        treffer = [i for i in range(kopf + 1, ende) if rx.match(zeilen[i])]
        if treffer:
            for i in treffer:
                zeilen[i] = f"{name} = {wert}"
        else:
            fehlt.append(f"{name} = {wert}")
    if fehlt:
        zeilen[ende:ende] = ["# kaiscribe-sonnet-n2 (16.11.2026, Peters Go 14.11.): Befund-KI Claude Sonnet maskiert, "
                             "Gemini nur Rückfall; zurück: LLM_ANBIETER = gemini"] + fehlt
    return "\n".join(zeilen) + "\n"


def config_zeilen(text):
    return [z.strip() for z in text.splitlines() if re.match(r"^\s*(\[|LLM_|ANTHROPIC_)", z, re.I)]


def cmd_schluessel(a):
    key = key_windows()
    if not key:
        print("Anmeldeinformation", ZIEL, "vorhanden/verwertbar: nein")
        print("ANTHKEY=rot GRUND=keine_anmeldeinformation")
        return 1
    print("Anmeldeinformation", ZIEL, "vorhanden/verwertbar: ja")
    try:
        erg, sich = schluessel_einsetzen(a["--datei"], key, ALT)
    except Exception as e:
        print("ANTHKEY=rot GRUND=" + type(e).__name__ + ":" + str(e)[:120])
        return 1
    felder = sorted(lese_json(a["--datei"]).keys())
    print("Sicherung:", sich or "-", "| Felder jetzt:", ", ".join(felder))
    api = anthropic_pruefen(key) if "--pruefen" in a else "-"
    print(f"ANTHKEY={erg} FELDER={','.join(felder)} API={api}")
    return 0 if api in ("-", "200") else 1


def cmd_config(a):
    datei, anbieter = a["--datei"], a.get("--anbieter", "anthropic")
    if anbieter not in WERTE:
        print("KSCONFIG=rot GRUND=anbieter")
        return 1
    with open(datei, encoding="utf-8-sig", errors="replace") as f:
        alt = f.read()
    neu = config_setzen(alt, WERTE[anbieter])
    if neu.strip() == alt.strip():
        print("\n".join(config_zeilen(alt)))
        print("KSCONFIG=schon")
        return 0
    os.makedirs(ALT, exist_ok=True)
    sich = os.path.join(ALT, "config.ini.vor-sonnet-" + stempel())
    shutil.copy2(datei, sich)
    tmp = datei + ".neu"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(neu)
    os.replace(tmp, datei)
    print("Sicherung:", sich)
    print("\n".join(config_zeilen(neu)))
    print(f"KSCONFIG=ok ANBIETER={anbieter}")
    return 0


def befund_aus_zustand(z):
    """Voller Befundtext aus dem Selbsttest-Zustand (result_voll; „result“ ist nach 600 Zeichen abgeschnitten – daran
    scheiterte die erste Probe am 16.11.: „Gonarthrose“ stand im Ergebnis hinter Zeichen 600)."""
    m = (z or {}).get("befund") or {}
    return (m.get("result_voll") or m.get("result") or "").strip()


def ist_produktions_exe(pfad):
    import ntpath
    return ntpath.normcase(ntpath.normpath(pfad)) == ntpath.normcase(ntpath.join(X, "rakscribe26.exe"))


def cmd_probe(a):
    if ist_produktions_exe(a["--exe"]):
        print("KSPROBE=rot GRUND=nur_mit_kopie")
        return 1
    exe = os.path.abspath(a["--exe"])
    w =os.path.dirname(exe)
    ablauf, zustand = os.path.join(w, "probe_ablauf.json"), os.path.join(w, "probe_zustand.json")
    with open(ablauf, "w", encoding="utf-8") as f:
        json.dump({"max_s": 240, "schritte": [{"warte_s": 3}, {"trigger": "text_ins#probe|" + TESTSATZ},
                                               {"warte_auf": "kontrolle", "timeout_s": 180}, {"merke": "befund"},
                                               {"ende": True}]}, f, ensure_ascii=False)
    log = os.path.join(w, "rakscribe.log")
    start = os.path.getsize(log) if os.path.exists(log) else 0
    env = {k: v for k, v in os.environ.items() if not k.startswith("RAKSCRIBE_")}
    t0 = time.time()
    p = subprocess.Popen([exe, "--wav-ablauf", ablauf, "--schluessel", a.get("--schluessel", SCHLUESSEL),
                          "--zustand", zustand], cwd=w, env=env)
    try:
        p.wait(timeout=300)
    except subprocess.TimeoutExpired:
        p.terminate()
    dauer = time.time() - t0
    zeilen = []
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            f.seek(start)
            zeilen = [z.rstrip() for z in f if re.search(r"\[(KI|INIT)\]|Traceback|Error|10013", z)]
    print("\n".join(zeilen[-25:]))
    try:
        with open(zustand, encoding="utf-8") as f:
            befund = befund_aus_zustand(json.load(f))
    except Exception:
        befund = ""
    print("Befund (synthetischer Testsatz):\n" + befund)
    anbieter = "anthropic" if any("Anbieter=anthropic" in z for z in zeilen) else \
        ("rueckfall" if any("Anthropic nicht verwendet" in z for z in zeilen) else "unklar")
    ok = anbieter == "anthropic" and "## Befund" in befund and "Gonarthrose" in befund
    print(f"KSPROBE={'ok' if ok else 'rot'} ANBIETER={anbieter} EXIT={p.poll()} DAUER={dauer:.0f}s")
    return 0 if ok else 1


def argumente(argv):
    a, i = {}, 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            a[argv[i]] = argv[i + 1]
            i += 2
        else:
            a[argv[i]] = True
            i += 1
    return a


def main(argv):
    if not argv or argv[0] not in ("schluessel", "config", "probe"):
        print(__doc__)
        return 1
    a = argumente(argv[1:])
    if argv[0] == "schluessel":
        a.setdefault("--datei", SCHLUESSEL)
        return cmd_schluessel(a)
    if argv[0] == "config":
        a.setdefault("--datei", CONFIG)
        return cmd_config(a)
    if "--exe" not in a:
        print("KSPROBE=rot GRUND=--exe fehlt")
        return 1
    return cmd_probe(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
