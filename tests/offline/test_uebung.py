"""Gate kaiscribe-uebung-n1 (Peter/Georg 25.11.2026): KaiScribe-Übungsmodus – Übungsdienst der VM (tools/uebung).

Teil 1: Kern – Anzeige-Maske (anonym), Wort-Vergleich, Word im CAS-Layout, Konten, STT-Deckel der Übung, Varianten.
Teil 2: Dienst über HTTP (echter Server auf 127.0.0.1, Zufallsport): Anmeldung kp/rg, nur eigene Fälle, Lösung erst
        nach der Abgabe, Ablage .docx + .html, Variante „haus“ von außen nie, Pfad-Ausbruch, STT-Buchung.
Teil 3: HARTE SPERRE – der Dienst öffnet keine ausgehende Verbindung und startet keinen Unterprozess (0 Aufrufe,
        abgefangen), importiert keinen Ausgang (CAS/Brücke/Roboter/Plaza/ELGA/SpeechMagic); der Spiegel lässt nur
        lesendes SQL zu.
Synthetische Daten, keine Patientendaten.  Aufruf: python3 tests/offline/test_uebung.py"""
import ast
import http.client
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading
import datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[2]
UE = ROOT / "tools" / "uebung"
sys.path.insert(0, str(UE))
import uebung_kern as K  # noqa: E402
import uebung_dienst as D  # noqa: E402
import spiegel as SP  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ── Teil 1: Kern ──
t = ("Vorbefund vom 12.03.2024: Patientin Huber Maria, geb. 03.04.1958, SVNR 1234 030458, Hauptstraße 12, 8010 Graz.\n"
     "Dr. Gruber bittet um Kontrolle. Kein Erguss.")
m = K.anzeige_maske(t, ["Huber", "Maria", "Gruber"], "03.04.1958")
check("Maske: Namen raus", "Huber" not in m and "Maria" not in m and "Gruber" not in m, m)
check("Maske: Geburtsdatum raus", "03.04.1958" not in m and "[Geb.-Datum]" in m, m)
check("Maske: SVNR/Nummern raus", "030458" not in m and "1234 0304" not in m, m)
check("Maske: Adresse raus", "Hauptstraße 12" not in m and "8010" not in m, m)
check("Maske: Vorbefund-Datum bleibt", "12.03.2024" in m, m)
check("Maske: Befundtext bleibt", "Kein Erguss." in m, m)
check("Restprüfung: sauber", K.rest_unsicher(m, ["Huber", "Maria", "Gruber"], "03.04.1958") is None,
      K.rest_unsicher(m, ["Huber", "Maria", "Gruber"], "03.04.1958"))
check("Restprüfung: Name erkannt", K.rest_unsicher("Frau Huber", ["Huber"], None) == "name")
check("Restprüfung: Nummer erkannt", K.rest_unsicher("Nr 1234567", [], None) == "nummer")

ops = K.wort_diff("## Knie rechts\n\n## Befund\nKein Erguss. Leichte Arthrose.",
                  "Knie rechts\nBefund:\nKein Erguss. Mäßige Arthrose.")
txt = {op: " ".join(x for o, x in ops if o == op) for op in "=-+"}
check("Vergleich: gleiche Wörter", "Erguss." in txt["="] and "Arthrose." in txt["="], ops)
check("Vergleich: nur echt / nur Übung", "Mäßige" in txt["-"] and "Leichte" in txt["+"], ops)
z = K.diff_zahlen(ops)
check("Vergleich: Zahlen", z["fehlt"] >= 1 and z["neu"] >= 1 and 0 < z["aehnlich_prozent"] < 100, z)
h = K.diff_html([["=", "a <b>"], ["-", "x"], ["+", "y"]], "RH1 <script>", "## T", "echt", "diktat")
check("Vergleich-HTML: maskiert HTML, markiert", "<script>" not in h and "&lt;b&gt;" in h and "<del" in h and "<ins" in h
      and "ÜBUNG – nichts wurde gesendet" in h)

fall = {"id": "RH12", "alter": 64, "geschlecht": "w", "untersuchungen": ["Röntgen Kniegelenk re. 2 Ebenen"]}
doc = K.docx_cas(fall, "## Kniegelenk rechts in 2 Ebenen\n\n## Befund:\nKein **Erguss**.\n\n## Ergebnis:\n1. Unauffällig.",
                 "kp", "20261123")
import zipfile, io  # noqa: E402,E401
zf = zipfile.ZipFile(io.BytesIO(doc))
check("Word: gültiges docx", {"[Content_Types].xml", "word/document.xml", "_rels/.rels"} <= set(zf.namelist()))
dt_ = K.docx_text(doc)
check("Word: CAS-Layout (Kopf, Fallzeile, QR, Titel, Text, ÜBUNG)",
      all(x in dt_ for x in ("Röntgen am Kai", "RH12 · 64 J. · w", "QR", "Kniegelenk rechts in 2 Ebenen", "Kein Erguss.",
                             "1. Unauffällig.", "ÜBUNG – nichts wurde gesendet")), dt_)
check("Word: Titel fett+unterstrichen", '<w:b/><w:u w:val="single"/>' in zf.read("word/document.xml").decode())

e = K.kennwort_hash("geheim-123")
check("Konto: Kennwort ok / falsch", K.kennwort_ok(e, "geheim-123") and not K.kennwort_ok(e, "x"))
uhr = [1000.0]
s = K.Sitzungen({"kp": e, "zz": e}, uhr=lambda: uhr[0])
check("Konto: nur kp/rg zugelassen", list(s.konten) == ["kp"])
tok, f = s.anmelden("KP", "geheim-123")
check("Anmeldung kp", tok and s.wer(tok) == "kp", f)
for _ in range(5):
    s.anmelden("kp", "falsch")
check("Sperre nach 5 Fehlversuchen", s.anmelden("kp", "geheim-123") == (None, "gesperrt"))
uhr[0] += K.SPERRE_MIN * 60 + 1
check("Sperre läuft ab", s.anmelden("kp", "geheim-123")[0] is not None)
uhr[0] += K.TOKEN_STUNDEN * 3600 + 1
check("Token läuft ab", s.wer(tok) is None)

with tempfile.TemporaryDirectory() as td:
    abend = dt.datetime(2026, 11, 25, 20, 0)
    zl = K.Zaehler(os.path.join(td, "z.json"), uhr=lambda: abend)
    check("Deckel: 60 min je Kürzel", zl.stt_rest_s("kp") == 3600)
    zl.zaehlen("kp", "stt_s", 3000)
    check("Deckel: Rest nach Buchung", zl.stt_rest_s("kp") == 600 and zl.stt_rest_s("rg") == 3600)
    frueh = dt.datetime(2026, 11, 25, 10, 0)
    zl2 = K.Zaehler(os.path.join(td, "z2.json"), uhr=lambda: frueh)
    zl2.zaehlen("rg", "stt_s", 1000)
    check("Deckel: Ordi-Tag vor 17:00 gemeinsam 20 min", zl2.stt_rest_s("kp") == 200, zl2.stt_rest_s("kp"))
    sa = dt.datetime(2026, 11, 28, 10, 0)
    zl3 = K.Zaehler(os.path.join(td, "z2.json"), uhr=lambda: sa)
    check("Deckel: Samstag ohne Ordi-Grenze", zl3.stt_rest_s("kp") == 3600)

check("Variante: Tailscale → immer anonym", K.variante_fuer("tailscale", "haus") == "anonym")
check("Variante: LAN + Wunsch haus → haus", K.variante_fuer("lan", "haus") == "haus")
check("Variante: unbekannt → anonym", K.variante_fuer("?", "haus") == "anonym")
check("Fallkarte ohne Lösung/Nr", "loesung" not in K.fall_ohne_loesung({"id": "RH1", "loesung": "x", "nr": "1"})
      and "nr" not in K.fall_ohne_loesung({"id": "RH1", "nr": "1"}))

# Senf-Text des Spiegels = KaiScribe-Senf-Anzeige (source_code/senf_anzeige.anzeige)
sys.path.insert(0, str(ROOT / "source_code"))
import senf_anzeige as SA  # noqa: E402
for d in ({"status": "fertig", "befund": "auffaellig", "zeilen": ["RH 7 · Knie · Erguss"]},
          {"status": "fertig", "befund": "unauffaellig", "zeilen": [],
           "eintraege": [{"id": "a_1", "zeilen": ["Vara: auffällig (Score 82)"], "abgleich": [{"art": "zusatz", "text": "IB Lab: KL 3 re."}]}]},
          {"status": "fertig", "befund": "nicht_beurteilbar", "zeilen": ["RH 9 · Hand"]},
          {"status": "laeuft"}, {"status": "fehler"}):
    zu, tx = SA.anzeige(d)
    check(f"Spiegel-Senf = KaiScribe-Anzeige ({d.get('befund') or d['status']})",
          SP.senf_text(d) == (tx if zu == SA.FERTIG else None), (SP.senf_text(d), tx))

# ── Teil 2 + 3: Dienst über HTTP, mit abgefangenen Ausgängen ──
ausgaenge = []
_orig_connect = socket.socket.connect
_orig_cc = socket.create_connection
_orig_popen = subprocess.Popen
_orig_system = os.system


def _im_server():
    return threading.current_thread() is not threading.main_thread()


def connect_fang(self, adr):
    if _im_server():
        ausgaenge.append(("connect", str(adr)))
        raise OSError("Übung: ausgehende Verbindung gesperrt")
    return _orig_connect(self, adr)


def cc_fang(*a, **k):
    if _im_server():
        ausgaenge.append(("create_connection", str(a[:1])))
        raise OSError("gesperrt")
    return _orig_cc(*a, **k)


class PopenFang:
    def __init__(self, *a, **k):
        ausgaenge.append(("popen", str(a[:1])[:60]))
        raise OSError("gesperrt")


socket.socket.connect = connect_fang
socket.create_connection = cc_fang
subprocess.Popen = PopenFang
os.system = lambda *a: ausgaenge.append(("system", "")) or 1

with tempfile.TemporaryDirectory() as td:
    basis = pathlib.Path(td) / "basis"
    (basis / "daten" / "20261123").mkdir(parents=True)
    (basis / "web").mkdir()
    (basis / "web" / "index.html").write_text("<!doctype html><title>KaiScribe</title>", encoding="utf-8")
    (pathlib.Path(td) / "geheim.txt").write_text("GEHEIM", encoding="utf-8")
    konten = {"kp": K.kennwort_hash("kp-pass-1"), "rg": K.kennwort_hash("rg-pass-1")}
    (basis / "konten.json").write_text(json.dumps(konten), encoding="utf-8")
    f_kp = {"id": "RH12", "kuerzel": "kp", "zeit": "08:10", "untersuchungen": ["Röntgen Knie re."], "alter": 64,
            "geschlecht": "w", "senf": "RH 12 · Knie · Erguss", "ibl": [{"modul": "KOALA", "text": "KL 2"}],
            "vorbefund": {"datum": "2024-03-12", "kurz": "RK", "text": "Damals unauffällig."},
            "loesung": "Kniegelenk rechts\nBefund:\nKleiner Erguss.\nErgebnis:\n1. Kleiner Gelenkerguss."}
    f_rg = dict(f_kp, id="RH13", kuerzel="rg", loesung="Anderer Befund.")
    (basis / "daten" / "20261123" / "anonym.json").write_text(json.dumps({"tag": "20261123", "faelle": [f_kp, f_rg]}),
                                                              encoding="utf-8")
    haus = dict(f_kp, patient="Huber Maria", nr="20261123012")
    (basis / "daten" / "20261123" / "haus.json").write_text(json.dumps({"tag": "20261123", "faelle": [haus]}),
                                                            encoding="utf-8")
    ablage = pathlib.Path(td) / "X_KaiScribe-Uebung"
    dienst = D.Dienst(str(basis), ablage=str(ablage), lan=False)
    srv = D.server(dienst, "127.0.0.1", 0)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()

    def req(meth, pfad, body=None, token=None, kopf=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        hd = dict(kopf or {})
        if token:
            hd["Authorization"] = "Bearer " + token
        b = json.dumps(body).encode() if body is not None else None
        if b is not None:
            hd["Content-Type"] = "application/json"
        c.request(meth, pfad, body=b, headers=hd)
        r = c.getresponse()
        daten = r.read()
        c.close()
        try:
            return r.status, json.loads(daten.decode()), dict(r.getheaders())
        except ValueError:
            return r.status, daten, dict(r.getheaders())

    st, j, _h = req("GET", "/api/status")
    check("Dienst: Status anonym, Kürzel kp/rg", st == 200 and j["variante"] == "anonym" and j["kuerzel"] == ["kp", "rg"], j)
    st, j, _h = req("GET", "/api/faelle?tag=20261123")
    check("Dienst: ohne Anmeldung 401", st == 401)
    st, j, _h = req("POST", "/api/anmelden", {"kuerzel": "kp", "kennwort": "falsch"})
    check("Dienst: falsches Kennwort 403", st == 403)
    st, j, _h = req("POST", "/api/anmelden", {"kuerzel": "kp", "kennwort": "kp-pass-1"})
    tk = j.get("token")
    check("Dienst: Anmeldung kp", st == 200 and tk and j["kuerzel"] == "kp" and j["stt_rest_s"] > 0, j)
    st, j, _h = req("GET", "/api/tage", token=tk)
    check("Dienst: Übungstage", st == 200 and j["tage"] == ["20261123"], j)
    st, j, _h = req("GET", "/api/faelle?tag=20261123&variante=haus", token=tk,
                    kopf={"Tailscale-User-Login": "peter@example"})
    check("Dienst: nur eigene Fälle, Tailscale → anonym", st == 200 and [f["id"] for f in j["faelle"]] == ["RH12"]
          and j["variante"] == "anonym", j)
    st, j, _h = req("GET", "/api/fall?tag=20261123&id=RH12&variante=haus", token=tk)
    roh = json.dumps(j, ensure_ascii=False)
    check("Dienst: Fallkarte mit Senf/IB Lab/Vorbefund", st == 200 and j["fall"]["senf"].startswith("RH 12")
          and j["fall"]["ibl"][0]["modul"] == "KOALA" and j["fall"]["vorbefund"]["text"], j)
    check("Dienst: Fallkarte ohne Lösung, ohne Name/Nr (auch bei Wunsch haus)",
          "Kleiner Erguss" not in roh and "Huber" not in roh and "20261123012" not in roh, roh)
    st, j, _h = req("GET", "/api/fall?tag=20261123&id=RH13", token=tk)
    check("Dienst: fremder Fall (rg) für kp 404", st == 404)
    st, j, _h = req("GET", "/api/loesung?tag=20261123&id=RH12", token=tk)
    check("Dienst: Lösung vor Abgabe gesperrt (403)", st == 403)
    st, j, _h = req("POST", "/api/stt", {"sekunden": 30}, token=tk)
    check("Dienst: STT buchen (×2 Live+chirp)", st == 200 and j["stt_rest_s"] == 3600 - 60, j)
    befund = "## Kniegelenk rechts\n\n## Befund:\nKein Erguss.\n\n## Ergebnis:\n1. Unauffällig."
    st, j, _h = req("POST", "/api/abgabe", {"tag": "20261123", "id": "RH12", "befund": befund, "diktat": "kein erguss"},
                    token=tk)
    check("Dienst: Abgabe", st == 200 and j["ablage"] == "RH12_kp.docx" and j["versuch"] == 1, j)
    dx = ablage / "20261123" / "kp" / "RH12_kp.docx"
    hx = ablage / "20261123" / "kp" / "RH12_kp.html"
    check("Ablage: <tag>\\<kürzel>\\<RH>_<kürzel>.docx + .html", dx.is_file() and hx.is_file())
    check("Ablage: Word enthält Übungsbefund", dx.is_file() and "Kein Erguss." in K.docx_text(dx.read_bytes()))
    check("Ablage: Vergleich markiert Unterschiede", hx.is_file() and "<del" in hx.read_text(encoding="utf-8")
          and "Kleiner" in hx.read_text(encoding="utf-8"))
    st, j, _h = req("GET", "/api/loesung?tag=20261123&id=RH12", token=tk)
    check("Dienst: Lösung nach Abgabe + Vergleich", st == 200 and "Kleiner Erguss." in j["loesung"]
          and any(o == "-" for o, _x in j["diff"]), j)
    st, b, hd = req("GET", "/api/word?tag=20261123&id=RH12", token=tk)
    check("Dienst: Word-Download", st == 200 and isinstance(b, bytes) and b[:2] == b"PK"
          and "RH12_kp.docx" in hd.get("Content-Disposition", ""), (st, hd))
    st, j, _h = req("POST", "/api/abgabe", {"tag": "20261123", "id": "RH12", "befund": befund}, token=tk)
    check("Ablage: zweiter Versuch überschreibt nicht (_2)", st == 200 and j["ablage"] == "RH12_kp_2.docx", j)
    st, j, _h = req("GET", "/api/faelle?tag=20261123", token=tk)
    check("Dienst: Fall als abgegeben markiert", st == 200 and j["faelle"][0]["abgegeben"] is True, j)
    st, b, _h = req("GET", "/index.html")
    check("Dienst: Web-App ausgeliefert", st == 200 and b"KaiScribe" in b)
    st, b, _h = req("GET", "/../geheim.txt")
    st2, b2, _h = req("GET", "/%2e%2e/geheim.txt")
    check("Dienst: kein Pfad-Ausbruch", b"GEHEIM" not in (b if isinstance(b, bytes) else b"")
          and b"GEHEIM" not in (b2 if isinstance(b2, bytes) else b""))
    st, j, hd = req("OPTIONS", "/api/fall", kopf={"Origin": "https://drpeterkalmar.github.io"})
    check("Dienst: CORS/Private-Network nur für die Pages-Herkunft",
          hd.get("Access-Control-Allow-Origin") == "https://drpeterkalmar.github.io"
          and hd.get("Access-Control-Allow-Private-Network") == "true")
    st, j, hd = req("OPTIONS", "/api/fall", kopf={"Origin": "https://boese.example"})
    check("Dienst: fremde Herkunft ohne CORS", "Access-Control-Allow-Origin" not in hd)
    zz = json.loads((basis / "zaehler.json").read_text(encoding="utf-8"))
    roh_z = json.dumps(zz)
    check("Zähler: nur Zahlen, keine Inhalte", "Erguss" not in roh_z and "RH12" not in roh_z
          and list(zz.values())[0]["kp"]["abgabe"] == 2, zz)
    # rg sieht nur seinen Fall, Lösung von kp nicht
    st, j, _h = req("POST", "/api/anmelden", {"kuerzel": "rg", "kennwort": "rg-pass-1"})
    tr = j.get("token")
    st, j, _h = req("GET", "/api/loesung?tag=20261123&id=RH13", token=tr)
    check("Dienst: rg – Lösung erst nach eigener Abgabe", st == 403)
    # neuer Dienst (Neustart) kennt die Abgaben noch
    d2 = D.Dienst(str(basis), ablage=str(ablage))
    check("Dienst: Abgaben überstehen Neustart", ("kp", "20261123", "RH12") in d2.abgaben)
    srv.shutdown()
    srv.server_close()

socket.socket.connect = _orig_connect
socket.create_connection = _orig_cc
subprocess.Popen = _orig_popen
os.system = _orig_system
check("SPERRE: 0 ausgehende Verbindungen/Unterprozesse aus dem Dienst", ausgaenge == [], ausgaenge)

# ── Teil 3: statische Sperre ──
ERLAUBT = {"__future__", "argparse", "json", "mimetypes", "os", "re", "sys", "threading", "urllib.parse", "http.server",
           "uebung_kern", "datetime", "difflib", "hashlib", "hmac", "html", "io", "secrets", "zipfile", "zoneinfo",
           "ki_maske"}
AUSGANG = ("casdb", "bruecke", "roboter", "cas_auftrag", "sm_einfuegen", "einfuegen", "plaza", "elga", "marc", "teleimage",
           "speechmagic", "clipboard", "pynetdicom", "pydicom", "smtplib", "urllib.request", "http.client", "requests",
           "subprocess", "socket", "ctypes", "win32", "pywinauto", "ftplib", "ssl")
for datei in ("uebung_dienst.py", "uebung_kern.py"):
    baum = ast.parse((UE / datei).read_text(encoding="utf-8"))
    importe = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.Import):
            importe |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            importe.add(n.module or "")
    fremd = sorted(i for i in importe if i not in ERLAUBT)
    check(f"SPERRE statisch: {datei} importiert nur Erlaubtes", not fremd, fremd)
    check(f"SPERRE statisch: {datei} ohne Ausgangs-Modul", not [i for i in importe if any(i == a or i.startswith(a + ".")
                                                                                       for a in AUSGANG)])
    roh = (UE / datei).read_text(encoding="utf-8")
    check(f"SPERRE statisch: {datei} ruft kein exec/eval/os.system/startfile",
          not any(x in roh for x in ("os.system(", "startfile(", "eval(", "exec(", "__import__(")))
km = ast.parse((ROOT / "source_code" / "ki_maske.py").read_text(encoding="utf-8"))
km_imp = {a.name for n in ast.walk(km) if isinstance(n, ast.Import) for a in n.names} | \
         {n.module for n in ast.walk(km) if isinstance(n, ast.ImportFrom)}
check("SPERRE statisch: ki_maske nur Stdlib ohne Netz", km_imp <= {"__future__", "re", "unicodedata"}, km_imp)


class CasStub:
    _KOPF = "SET PAGESIZE 0\nWHENEVER SQLERROR CONTINUE\nSET TRANSACTION READ ONLY;\nSELECT '###V###' FROM dual;\n"

    @staticmethod
    def _abschnitt(name, sql):
        return f"PROMPT ###Q {name}###\n{sql.strip()}\nPROMPT ###E {name}###\n"


cas = CasStub
try:
    sys.path.insert(0, os.path.expanduser("~/dev/ris-mods/bruecke"))
    import casdb as cas  # noqa: F811
except Exception:  # noqa: BLE001
    pass
for name, sql in (("Liste", SP.liste_sql(cas, "20261123")), ("Spalten", SP.spalten_sql(cas)),
                  ("Patient", SP.patient_sql(cas, ["12", "13"], "SEX"))):
    check(f"Spiegel: {name}-SQL nur lesend (READ ONLY + ROLLBACK, nur SELECT)",
          "SELECT" in sql and "ROLLBACK" in sql and not SP.VERBOTEN_SQL.search(sql.replace("'", "")), sql[-200:])
for boese in ("UPDATE sysadm.warterow SET status='x'", "DELETE FROM sysadm.letters", "INSERT INTO x VALUES (1)",
              "COMMIT", "MERGE INTO x"):
    try:
        SP.sql_sicher(cas._KOPF + boese + ";\nROLLBACK;\n")
        check(f"Spiegel: „{boese[:20]}…“ abgewiesen", False)
    except ValueError:
        check(f"Spiegel: „{boese[:20]}…“ abgewiesen", True)
check("Spiegel: Patient-SQL nimmt nur Ziffern-IDs", "1; DROP" not in SP.patient_sql(cas, ["1; DROP TABLE x", "7"], "SEX"))
check("Spiegel: Geschlecht-Spalte nur aus Liste", "a.BOESE" not in SP.patient_sql(cas, ["7"], "BOESE"))
with tempfile.TemporaryDirectory() as td_ibl:
    for n in ("202611230121_frog.txt", "202611230121_frog.json", "20261123012_koala.txt", "202611230131_rho.txt"):
        pathlib.Path(td_ibl, n).write_text("Text " + n, encoding="utf-8")
    alt_ibl, SP.IBL_ORDNER = SP.IBL_ORDNER, td_ibl
    ib = SP.ibl_lesen("20261123012")
    SP.IBL_ORDNER = alt_ibl
    check("Spiegel: IB Lab je Accession (<nr><z>_<modul>.txt), fremde Nummer nicht", sorted(x["modul"] for x in ib) == ["FROG", "KOALA"], ib)
check("Spiegel: Alter am Untersuchungstag", SP.alter_am("24.11.1960", "20261123") == 65 and SP.alter_am("23.11.1960", "20261123") == 66)
an_h, an_a = SP.fall_bauen({"nr": "20261123012", "rh": "12", "wer": "kp", "rt": "08:10"},
                           {"besuch": {"zuweiser": "Dr. Gruber Franz", "info": "Knieschmerz re. seit 2 Wo, Huber"},
                            "leistungen": [{"untersuchung": True, "text": "Röntgen Kniegelenk re.", "kurz": "RK"}],
                            "vorbefund": {"datum": "2024-03-12", "kurz": "RK", "text": "Frau Huber, Erguss 2024."},
                            "befundtext": "Kniegelenk rechts\nBefund: Erguss bei Frau Huber Maria."},
                           {"name": "Huber", "vorname": "Maria", "geb": "03.04.1958", "sex": "W"}, "20261123")
roh_a = json.dumps(an_a, ensure_ascii=False)
check("Spiegel anonym: kein Name/Zuweiser/Nr/Geburtsdatum", not any(x in roh_a for x in ("Huber", "Maria", "Gruber",
                                                                                         "20261123012", "1958")), roh_a)
check("Spiegel anonym: RH-Pseudonym, Alter, Geschlecht, Leistung", an_a["id"] == "RH12" and an_a["alter"] == 68
      and an_a["geschlecht"] == "w" and an_a["untersuchungen"] == ["Röntgen Kniegelenk re."], an_a)
check("Spiegel haus: Name + Diktatnummer (nur Haus)", an_h["patient"] == "Huber Maria" and an_h["nr"] == "20261123012")

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
