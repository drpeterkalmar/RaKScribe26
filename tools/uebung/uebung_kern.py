"""KaiScribe-Übungsmodus – Kern des Übungsdienstes (kaiscribe-uebung-n1, Peter/Georg 25.11.2026).

Reine Logik ohne Netz, ohne CAS, ohne Windows: Anzeige-Maske, Wort-Vergleich, Word-Datei im CAS-Befundlayout, Konten
(PBKDF2), STT-Deckel der Übung, Zugriffszähler (nur Zahlen), Varianten-Regel (von außen nur „anonym“).

HARTE SPERRE (im Code, nicht Einstellung): Dieses Modul und der Dienst (uebung_dienst.py) bauen KEINE Verbindung nach
außen auf – kein CAS-Auftrag, keine Brücke, kein Roboter/Word ins CAS, keine Plaza/ELGA/marc/Teleimage, kein
SpeechMagic-Senf. Sie lesen nur die vorher gespiegelten Tagesdateien (spiegel.py) und schreiben nur die Übungsablage.
tests/offline/test_uebung.py prüft das (Import-Liste, 0 Aufrufe an Netz/Unterprozess).

Nur Python-Stdlib (läuft auf der Automaten-VM mit py -3.12).
"""
from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import hmac
import html
import io
import json
import os
import re
import secrets
import sys
import threading
import zipfile

VERSION = "1.0.0"
HIER = os.path.dirname(os.path.abspath(__file__))
for _p in (HIER, os.path.join(HIER, "..", "..", "source_code")):
    if os.path.isfile(os.path.join(_p, "ki_maske.py")) and _p not in sys.path:
        sys.path.insert(0, _p)
import ki_maske  # noqa: E402

KUERZEL = ("kp", "rg")                 # Peter 25.11.: Übende nur kp und rg
VARIANTEN = ("anonym", "haus")
DECKEL_MIN_JE_KUERZEL = 60             # eigener STT-Deckel der Übung (Live: 240 min/Tag/PC bleibt unberührt)
DECKEL_MIN_ORDIZEIT = 20               # an Ordi-Tagen (Mo–Fr) vor 17:00 zusammen höchstens so viel
ORDI_ENDE_STUNDE = 17
STT_FAKTOR = 2                         # Web: Live-Anzeige (v1) + chirp_3 je Aufnahme → doppelt buchen
PBKDF2_RUNDEN = 200_000
TOKEN_STUNDEN = 12
SPERRE_FEHLVERSUCHE = 5
SPERRE_MIN = 15

TAG_RE = re.compile(r"^\d{8}$")
FALL_RE = re.compile(r"^[A-Z]{1,2}\d{1,4}$")

try:
    from zoneinfo import ZoneInfo
    _WIEN = ZoneInfo("Europe/Vienna")
except Exception:  # noqa: BLE001 – Windows ohne tzdata: Ortszeit (VM steht in Wien)
    _WIEN = None


def jetzt():
    return dt.datetime.now(_WIEN) if _WIEN else dt.datetime.now()


# ───────────────────────────────────────────── Varianten ─────────────────────────────────────────────
def variante_fuer(herkunft, gewuenscht="anonym"):
    """herkunft: 'tailscale' (über tailscale serve / Tailnet-IP) | 'lan' (Ordi-Netz) | sonst → immer 'anonym'.
    Von außen (Tailscale) NUR anonym – egal was gewünscht ist. 'haus' nur aus dem LAN und nur auf Wunsch."""
    if herkunft == "lan" and gewuenscht == "haus":
        return "haus"
    return "anonym"


# ───────────────────────────────────────────── Anzeige-Maske ─────────────────────────────────────────────
_ERSATZ = {"P": "[Name]", "N": "[Nr.]", "A": "[Adresse]", "E": "[E-Mail]"}


def anzeige_maske(text, namen=(), geburtsdatum=None):
    """Vorbefund/echter Befund für die Variante „anonym“: Namen, Geburtsdatum, Adressen, lange Nummern, E-Mail raus;
    übrige Datumsangaben (Vorbefund vom …) bleiben (Peter: „Vorbefund-Daten bleiben“). Gleiche Maske wie KaiFormat
    (source_code/ki_maske.py), danach Datums-Platzhalter zurück – außer es ist das Geburtsdatum."""
    if not text:
        return ""
    t = str(text).replace(ki_maske.KLAMMER_AUF, "(").replace(ki_maske.KLAMMER_ZU, ")")
    m = ki_maske.Maske(namen, geburtsdatum)
    zeilen = [m.maskieren(z) for z in t.split("\n")]
    geb = set(ki_maske._datum_varianten(geburtsdatum)) if geburtsdatum else set()

    def zurueck(mm):
        ph = mm.group(0)
        art = mm.group(1)
        if art == "D":
            wert = m.zu_wert.get(ph, "")
            if any(g and g in wert for g in geb):
                return "[Geb.-Datum]"
            return wert
        return _ERSATZ.get(art, "[…]")
    aus = "\n".join(ki_maske._PLATZHALTER.sub(zurueck, z) for z in zeilen)
    for g in sorted(geb, key=len, reverse=True):       # Geburtsdatum in jeder Schreibweise (Restprüfung wie KaiFormat)
        if g and len(g) >= 6:
            aus = aus.replace(g, "[Geb.-Datum]")
    return aus


def rest_unsicher(text, namen=(), geburtsdatum=None):
    """Unabhängige Nachprüfung eines anonymen Texts: bekannter Name, Geburtsdatum, Ziffernfolge ≥ 5, „@“ → Grund."""
    t = str(text or "")
    for v in ki_maske._namen_varianten(namen):
        if re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", t, flags=re.IGNORECASE):
            return "name"
    for v in ki_maske._datum_varianten(geburtsdatum) if geburtsdatum else ():
        if v and len(v) >= 6 and v in t:
            return "geburtsdatum"
    if re.search(r"\d{5,}", t):
        return "nummer"
    if "@" in t:
        return "email"
    return None


# ───────────────────────────────────────────── Vergleich ─────────────────────────────────────────────
_WORT = re.compile(r"\S+")


def _klar(md):
    """KaiScribe-Markdown → Klartext für den Vergleich (## und ** weg)."""
    t = re.sub(r"(?m)^#{1,6}\s*", "", str(md or ""))
    t = t.replace("**", "")
    return t


def _wn(w):
    return w.lower().strip(".,;:()!?\"'")


def wort_diff(uebung, echt):
    """→ [[op, text], …] mit op '=' gleich, '-' nur im echten Befund (fehlt in der Übung), '+' nur in der Übung.
    Wortweise, Groß/Klein und Satzzeichen am Rand egal. Zeilenumbrüche bleiben als '\n'-Wörter erhalten."""
    def toks(t):
        out = []
        for z in _klar(t).split("\n"):
            out += _WORT.findall(z)
            out.append("\n")
        while out and out[-1] == "\n":
            out.pop()
        return out
    a, b = toks(echt), toks(uebung)
    sm = difflib.SequenceMatcher(None, [_wn(x) for x in a], [_wn(x) for x in b], autojunk=False)
    ops = []

    def add(op, ws):
        if not ws:
            return
        txt = " ".join(ws).replace(" \n ", "\n").replace("\n ", "\n").replace(" \n", "\n")
        if ops and ops[-1][0] == op:
            ops[-1][1] += " " + txt
        else:
            ops.append([op, txt])
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            add("=", b[j1:j2])
        else:
            add("-", a[i1:i2])
            add("+", b[j1:j2])
    return ops


def diff_zahlen(ops):
    n = {"=": 0, "-": 0, "+": 0}
    for op, t in ops:
        n[op] += len([w for w in t.split() if w])
    gesamt = n["="] + max(n["-"], n["+"])
    return {"gleich": n["="], "fehlt": n["-"], "neu": n["+"],
            "aehnlich_prozent": round(100 * n["="] / gesamt) if gesamt else 100}


def diff_html(ops, kopf, uebung_md, echt_text, diktat=""):
    """Vergleichsdatei für die Ablage (eigenständiges HTML)."""
    e = html.escape
    teile = []
    for op, t in ops:
        t = e(t).replace("\n", "<br>")
        teile.append(t if op == "=" else f'<del title="nur im echten Befund">{t}</del>' if op == "-"
                     else f'<ins title="nur in der Übung">{t}</ins>')
    z = diff_zahlen(ops)
    return f"""<!doctype html><html lang="de"><meta charset="utf-8"><title>Übung {e(kopf)}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}}
.balken{{background:#b00020;color:#fff;padding:.4rem .8rem;font-weight:700}}del{{background:#fde2e2;color:#8a1020}}
ins{{background:#e0f4e4;color:#14532d;text-decoration:none;border-bottom:2px solid #2e7d32}}
.spalten{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:.6rem}}</style>
<div class="balken">ÜBUNG – nichts wurde gesendet</div>
<h1>{e(kopf)}</h1>
<p>Gleich {z['gleich']} Wörter · <del>nur im echten Befund</del> {z['fehlt']} · <ins>nur in der Übung</ins> {z['neu']} ·
Übereinstimmung {z['aehnlich_prozent']} %</p>
<h2>Vergleich (Übung gegen den damals vidierten Befund)</h2><p>{''.join(' ' + x for x in teile)}</p>
<div class="spalten"><div><h2>Übung</h2><pre>{e(_klar(uebung_md))}</pre></div>
<div><h2>Echter Befund</h2><pre>{e(echt_text or '')}</pre></div></div>
<h2>Diktat (Spracherkennung)</h2><pre>{e(diktat or '')}</pre>
<p><small>KaiScribe-Übung {VERSION} · {e(jetzt().strftime('%d.%m.%Y %H:%M'))}</small></p></html>"""


# ───────────────────────────────────────────── Word (CAS-Befundlayout) ─────────────────────────────────────────────
_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _run(text, fett=False, unter=False, pt=None, farbe=None):
    rpr = ""
    if fett or unter or pt or farbe:
        rpr = "<w:rPr>" + ("<w:b/>" if fett else "") + ('<w:u w:val="single"/>' if unter else "") + \
              (f'<w:color w:val="{farbe}"/>' if farbe else "") + (f'<w:sz w:val="{int(pt * 2)}"/>' if pt else "") + "</w:rPr>"
    return f'<w:r>{rpr}<w:t xml:space="preserve">{html.escape(text, quote=False)}</w:t></w:r>'


def _absatz(runs, rechts=False, abstand=0):
    ppr = "<w:pPr>" + ('<w:jc w:val="right"/>' if rechts else "") + f'<w:spacing w:after="{abstand}"/>' + "</w:pPr>"
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def _inline(t):
    """**fett** → Runs."""
    runs = []
    for i, teil in enumerate(re.split(r"\*\*", t)):
        if teil:
            runs.append(_run(teil, fett=i % 2 == 1))
    return runs or [_run("")]


def docx_cas(fall, befund_md, kuerzel, uebungstag):
    """Befund als .docx im CAS-Befundlayout: Kopf Praxis, Fallzeile (nur Pseudonym), QR-Platzhalter, Untersuchung fett
    unterstrichen, Befundtext, Ergebnis nummeriert, Unterschrift-Zeile. Fußzeile ÜBUNG. → bytes."""
    rh = fall.get("id") or "?"
    kopf_rechts = [_absatz([_run("Röntgen am Kai", fett=True, pt=14)], rechts=True),
                   _absatz([_run("Fachärzte für Radiologie", pt=9)], rechts=True, abstand=200)]
    falltext = f"{rh} · {fall.get('alter', '?')} J. · {fall.get('geschlecht') or '?'} · Untersuchungstag " \
               f"{uebungstag[6:8]}.{uebungstag[4:6]}.{uebungstag[:4]}"
    qr = ('<w:tbl><w:tblPr><w:tblW w:w="1600" w:type="dxa"/><w:jc w:val="right"/><w:tblBorders>'
          + "".join(f'<w:{s} w:val="single" w:sz="8" w:space="0" w:color="888888"/>' for s in ("top", "left", "bottom", "right"))
          + '</w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w="1600"/></w:tblGrid><w:tr><w:trPr><w:trHeight w:val="1600"/>'
          '</w:trPr><w:tc><w:tcPr><w:tcW w:w="1600" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
          + _absatz([_run("QR", fett=True, farbe="888888")], rechts=False) + "</w:tc></w:tr></w:tbl>")
    koerper = kopf_rechts + [qr, _absatz([_run(falltext, pt=10)], abstand=240)]
    if fall.get("untersuchungen"):
        koerper.append(_absatz([_run("Leistung laut CAS: " + "; ".join(fall["untersuchungen"]), pt=9, farbe="555555")],
                               abstand=160))
    for z in str(befund_md or "").split("\n"):
        s = z.rstrip()
        if not s.strip():
            koerper.append(_absatz([_run("")]))
            continue
        m = re.match(r"^#{1,6}\s*(.*)$", s)
        if m:
            titel = m.group(1).replace("**", "")
            ist_teil = re.match(r"^(befund|ergebnis|zusammenfassung|beurteilung)\s*:?\s*$", titel, re.I)
            koerper.append(_absatz([_run(titel, fett=True, unter=not ist_teil)], abstand=60))
            continue
        koerper.append(_absatz(_inline(s), abstand=0))
    koerper += [_absatz([_run("")]), _absatz([_run(f"Befund: {kuerzel} (Übung)", pt=10)]),
                _absatz([_run("ÜBUNG – nichts wurde gesendet. Nicht für Patienten.", fett=True, farbe="B00020", pt=9)])]
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_W}><w:body>' + "".join(koerper) +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
           'w:left="1418" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {_W}><w:docDefaults><w:rPrDefault><w:rPr>'
              '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="22"/><w:lang w:val="de-AT"/></w:rPr>'
              '</w:rPrDefault></w:docDefaults></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
          'content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType='
          '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName='
          '"/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/'
             'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
             '2006/relationships/styles" Target="styles.xml"/></Relationships>')
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("word/styles.xml", styles)
    return puffer.getvalue()


def docx_text(daten):
    """Klartext einer docx (für Tests und für Hermes' spätere Korrektur-Lesung)."""
    with zipfile.ZipFile(io.BytesIO(daten)) as z:
        x = z.read("word/document.xml").decode("utf-8")
    absaetze = re.findall(r"<w:p>(.*?)</w:p>", x, flags=re.S)
    return "\n".join(html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", a, flags=re.S))) for a in absaetze)


# ───────────────────────────────────────────── Konten ─────────────────────────────────────────────
def kennwort_hash(kennwort, salz=None):
    salz = salz or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", kennwort.encode("utf-8"), bytes.fromhex(salz), PBKDF2_RUNDEN).hex()
    return {"salz": salz, "hash": h, "runden": PBKDF2_RUNDEN}


def kennwort_ok(eintrag, kennwort):
    try:
        h = hashlib.pbkdf2_hmac("sha256", str(kennwort).encode("utf-8"), bytes.fromhex(eintrag["salz"]),
                                int(eintrag.get("runden") or PBKDF2_RUNDEN)).hex()
        return hmac.compare_digest(h, eintrag["hash"])
    except (KeyError, ValueError, TypeError):
        return False


class Sitzungen:
    """Anmeldung je Kürzel: Token im Speicher (12 h), Sperre nach 5 Fehlversuchen für 15 min (je Kürzel)."""

    def __init__(self, konten, uhr=None):
        self.konten = {k: v for k, v in (konten or {}).items() if k in KUERZEL}
        self.uhr = uhr or (lambda: dt.datetime.now().timestamp())
        self.token = {}
        self.fehl = {}
        self.lock = threading.Lock()

    def anmelden(self, kuerzel, kennwort):
        k = str(kuerzel or "").strip().lower()
        with self.lock:
            n, bis = self.fehl.get(k, (0, 0))
            if bis > self.uhr():
                return None, "gesperrt"
            if k not in self.konten or not kennwort_ok(self.konten[k], kennwort):
                n += 1
                self.fehl[k] = (0, self.uhr() + SPERRE_MIN * 60) if n >= SPERRE_FEHLVERSUCHE else (n, 0)
                return None, "falsch"
            self.fehl.pop(k, None)
            t = secrets.token_urlsafe(32)
            self.token[t] = (k, self.uhr() + TOKEN_STUNDEN * 3600)
            return t, None

    def wer(self, token):
        with self.lock:
            e = self.token.get(str(token or ""))
            if not e:
                return None
            if e[1] < self.uhr():
                self.token.pop(token, None)
                return None
            return e[0]

    def abmelden(self, token):
        with self.lock:
            self.token.pop(str(token or ""), None)


# ───────────────────────────────────────────── Zähler + Deckel (nur Zahlen) ─────────────────────────────────────────────
class Zaehler:
    """Zugriffe zählen, keine Inhalte: {tag: {kürzel: {anmeldung, fall, abgabe, loesung, word, stt_s}}} – atomar."""

    def __init__(self, pfad, uhr=jetzt):
        self.pfad, self.uhr = pfad, uhr
        self.lock = threading.Lock()

    def _lesen(self):
        try:
            with open(self.pfad, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _schreiben(self, d):
        tmp = self.pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=True)
        os.replace(tmp, self.pfad)

    def zaehlen(self, kuerzel, was, menge=1):
        with self.lock:
            d = self._lesen()
            tag = self.uhr().strftime("%Y%m%d")
            k = d.setdefault(tag, {}).setdefault(str(kuerzel or "-"), {})
            k[was] = k.get(was, 0) + menge
            for alt in sorted(d)[:-60]:          # 60 Tage reichen
                d.pop(alt, None)
            self._schreiben(d)

    def heute(self):
        with self.lock:
            return self._lesen().get(self.uhr().strftime("%Y%m%d"), {})

    def stt_rest_s(self, kuerzel):
        """Restsekunden Übungs-STT für dieses Kürzel heute (Deckel je Kürzel + an Ordi-Tagen vor 17:00 gemeinsam)."""
        h = self.heute()
        eigen = DECKEL_MIN_JE_KUERZEL * 60 - h.get(kuerzel, {}).get("stt_s", 0)
        t = self.uhr()
        if t.weekday() < 5 and t.hour < ORDI_ENDE_STUNDE:
            alle = sum(v.get("stt_s", 0) for v in h.values() if isinstance(v, dict))
            eigen = min(eigen, DECKEL_MIN_ORDIZEIT * 60 - alle)
        return max(0, int(eigen))


# ───────────────────────────────────────────── Spiegel lesen ─────────────────────────────────────────────
def spiegel_lesen(ordner, tag, variante):
    """<ordner>/<tag>/<variante>.json → dict oder None. Nur gültige Tage/Varianten."""
    if not TAG_RE.match(str(tag or "")) or variante not in VARIANTEN:
        return None
    p = os.path.join(ordner, tag, variante + ".json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def tage(ordner):
    try:
        return sorted((t for t in os.listdir(ordner) if TAG_RE.match(t) and os.path.isfile(os.path.join(ordner, t, "anonym.json"))),
                      reverse=True)
    except OSError:
        return []


FALL_OEFFENTLICH = ("id", "kuerzel", "zeit", "untersuchungen", "leistungen", "alter", "geschlecht", "zuweisung", "ibl",
                    "vara", "senf", "vorbefund", "hinweise", "patient", "audio")


def fall_ohne_loesung(fall):
    """Fallkarte für die Anzeige: nur freigegebene Felder, NIE die Lösung (echter Befund) und nie die Diktatnummer."""
    return {k: fall[k] for k in FALL_OEFFENTLICH if k in fall}


def ablage_name(fall_id, kuerzel):
    if not FALL_RE.match(str(fall_id or "")) or kuerzel not in KUERZEL:
        raise ValueError("ungültig")
    return f"{fall_id}_{kuerzel}"
