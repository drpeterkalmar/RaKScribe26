r"""chirp-fachwortliste-n1 Schritt 3 (VM, rakauto): Messung chirp_3 OHNE vs. MIT SpeechMagic-Fachwortliste.

Läuft auf der VM. Audio (KaiScribe-PCM-WAVs in M:\Diktate, kp/rg, seit 02.11., keine Testpatienten-Fälle, keine
Philips-SpeechMagic-WAVs) geht NUR an Google Speech EU im Testprojekt (Token-Datei, 1 h gültig, wird gelöscht) – wie
die Produktion, nie an Anthropic. Referenz = vidierte Endfassung (lernen.db final) bzw. Brief-Datei (Befundteil) bei
noch offenen Fällen. Es wird die ECHTE Produktionsfunktion source_code/stt.py (chirp3_worker/chirp3_request) benutzt,
nur das Projekt im URL wird auf das Testprojekt umgebogen.
Ausgabe: nur Summen je Kürzel × Bedingung (WER, Fachwort-Fehler, Seiten/Zahlen, Minuten). Hypothesen bleiben auf der VM
(%LOCALAPPDATA%\chirp_fw\mess_<bed>.jsonl, für den späteren Mistral-Vergleich).
  py -3.12 cfw_messen.py <bedingungen z. B. ohne,sm5,sm10> [max_minuten_gesamt]
"""
import array
import collections
import concurrent.futures as cf
import json
import os
import re
import sqlite3
import struct
import sys
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import stt  # noqa: E402  (Kopie von RaKScribe26 source_code/stt.py, liest phrases.json daneben)
import sm  # noqa: E402

AUS = os.path.expandvars(r"%LOCALAPPDATA%\chirp_fw")
DB = r"C:\RaK\kaiscribe_lernen\daten\lernen.db"
LAEUFE = r"X:\KaiScribe\Daten\laeufe"
DIKTATE = "M:\\Diktate"
TESTPAT = "451898"
PREIS_EUR_MIN = 0.022
os.makedirs(AUS, exist_ok=True)
BED = (sys.argv[1] if len(sys.argv) > 1 else "ohne,sm5").split(",")
MAX_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0      # 200 min × 0,022 € = 4,40 € < Deckel 5 €
TOKF = os.path.join(HIER, "tok.json")
tok = json.load(open(TOKF, encoding="utf-8"))
try:
    os.remove(TOKF)
except OSError:
    pass
PROJEKT, TOKEN = tok["projekt"], tok["token"]
WORT = re.compile(r"[0-9]+(?:[.,][0-9]+)?|[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*")


def urlopen_test(req, timeout=60):
    url = re.sub(r"/projects/[^/]+/", "/projects/%s/" % PROJEKT, req.full_url)   # Produktion → Testprojekt
    neu = urllib.request.Request(url, data=req.data, method=req.get_method(), headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + TOKEN})
    for versuch in range(6):
        try:
            return urllib.request.urlopen(neu, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and versuch < 5:
                time.sleep(8 * (versuch + 1))
                continue
            raise


def wav_lesen(p):
    b = open(p, "rb").read()
    if b[:4] != b"RIFF":
        return None, 0
    i, sr, ch, bits, data = 12, 16000, 1, 16, None
    while i + 8 <= len(b):
        cid, n = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"fmt ":
            tag, ch, sr = struct.unpack("<HHI", b[i + 8:i + 16])
            bits = struct.unpack("<H", b[i + 22:i + 24])[0]
            if tag != 1 or bits != 16:
                return None, 0
        elif cid == b"data":
            data = b[i + 8:i + 8 + n]
        i += 8 + n + (n & 1)
    if data is None:
        return None, 0
    a = array.array("h")
    a.frombytes(data[:len(data) // 2 * 2])
    if ch == 2:
        a = a[::2]
    return a, sr


def befundtext_doc(nr):
    try:
        d = sm.doc_text(open(os.path.join(DIKTATE, nr + ".doc"), "rb").read())
    except Exception:
        return ""
    teile = re.findall(r"<bf\d*>(.*?)</bf\d*>", d, flags=re.S)
    return "\n".join(teile)


# ── Fälle ──
seit = time.mktime(time.strptime("20261102", "%Y%m%d"))
db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
faelle = []
for nr, ben, st, final, stt_roh in db.execute("SELECT nr, benutzer, status, final, stt FROM faelle "
                                              "WHERE status IN ('final','offen') AND benutzer IN ('kp','rg')"):
    p = os.path.join(DIKTATE, nr + ".wav")
    if not os.path.exists(p) or os.path.getmtime(p) < seit:
        continue
    ref = final if st == "final" and final else befundtext_doc(nr)
    if not ref or TESTPAT in (ref or ""):
        continue
    faelle.append({"nr": nr, "ben": ben, "st": st, "ref": ref, "stt_prod": stt_roh or "", "wav": p})
audio = {}
for f in faelle:
    a, sr = wav_lesen(f["wav"])
    if a is not None and len(a) > sr:
        audio[f["nr"]] = (a, sr)
faelle = [f for f in faelle if f["nr"] in audio]
minuten = sum(len(audio[f["nr"]][0]) / audio[f["nr"]][1] for f in faelle) / 60
z = collections.Counter((f["ben"], f["st"]) for f in faelle)
print("FAELLE", dict(("%s/%s" % k, v) for k, v in z.items()), "Audio-Minuten %.1f" % minuten,
      "Bedingungen", BED, "Kosten-Schaetzung %.2f EUR" % (minuten * len(BED) * PREIS_EUR_MIN))
if minuten * len(BED) > MAX_MIN:   # (obere Schranke; schon gemessene Bedingungen kosten nichts)
    print("CFW ABBRUCH Kostendeckel: %.0f min > %.0f min" % (minuten * len(BED), MAX_MIN))
    sys.exit(2)


def norm(t):
    return [w.lower() for w in WORT.findall(t or "")]


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


PH = json.load(open(os.path.join(HIER, "phrases.json"), encoding="utf-8"))
LISTE = set()
for p in PH["chirp"] + PH.get("chirp_sm", []):
    for w in norm(p):
        if len(w) >= 5 and not w.isdigit():
            LISTE.add(w)
de = {}
for i, zl in enumerate(open(os.path.join(HIER, "de_50k.txt"), encoding="utf-8")):
    t = zl.split()
    if t:
        de.setdefault(t[0].lower(), i)
SELTEN = lambda w: len(w) >= 6 and not w.isdigit() and de.get(w, 10 ** 9) >= 20000  # noqa: E731
SEITE = {"links", "rechts", "beidseits", "li", "re", "linke", "linken", "linker", "linkes", "rechte", "rechten",
         "rechter", "rechtes", "beidseitig"}


import difflib  # noqa: E402

KLASSEN = (("liste", lambda w: w in LISTE), ("selten", lambda w: SELTEN(w)),
           ("seite", lambda w: w in SEITE), ("zahl", lambda w: w[:1].isdigit()))


def fehlhoerer(h, r, max_len=4, min_ahnl=0.45):
    """Wortausrichtung Hypothese → Endfassung. Gezählt werden nur kurze, ähnlich geschriebene Ersetzungen (= in der
    Endfassung korrigierter Fehlhörer); eingefügter Vorlagentext und entfernte Diktat-Befehle zählen nicht.
    → {klasse: [treffer_richtig, fehlhoerer]} über die Endfassungs-Wörter."""
    out = {k: [0, 0] for k, _ in KLASSEN}
    out["alle"] = [0, 0]
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, h, r, autojunk=False).get_opcodes():
        if op == "equal":
            for w in r[j1:j2]:
                out["alle"][0] += 1
                for k, sel in KLASSEN:
                    if sel(w):
                        out[k][0] += 1
        elif op == "replace" and (i2 - i1) <= max_len and (j2 - j1) <= max_len:
            a, b = "".join(h[i1:i2]), "".join(r[j1:j2])
            if a != b and difflib.SequenceMatcher(None, a, b).ratio() < min_ahnl:
                continue
            for w in r[j1:j2]:
                out["alle"][1] += 1
                for k, sel in KLASSEN:
                    if sel(w):
                        out[k][1] += 1
    return out


def mass(h, r):
    """Kennzahlen eines Falls (Wortlisten)."""
    ch, cr = collections.Counter(h), collections.Counter(r)
    out = {"n_ref": len(r), "n_hyp": len(h), "lev": lev(h, r), "lcs": lcs(h, r), "fh": fehlhoerer(h, r)}
    for name, sel in (("liste", lambda w: w in LISTE), ("selten", SELTEN),
                      ("seite", lambda w: w in SEITE), ("zahl", lambda w: w[:1].isdigit())):
        ref_n = sum(c for w, c in cr.items() if sel(w))
        hit = sum(min(c, ch[w]) for w, c in cr.items() if sel(w))
        zuviel = sum(max(0, c - cr[w]) for w, c in ch.items() if sel(w))   # in der Hypothese, nicht in der Endfassung
        out[name] = [ref_n, hit, zuviel]
    return out


def lauf(bed, f):
    a, sr = audio[f["nr"]]
    smf = not bed.startswith("ohne")
    req = lambda tok_, loc, b64, sm=False: stt.chirp3_request(tok_, loc, b64, urlopen=urlopen_test, sm=sm)  # noqa: E731
    try:
        return stt.chirp3_worker(a, sr, "eu", TOKEN, request=req, sm=smf) or ""
    except Exception as e:
        return "\x00FEHLER " + type(e).__name__ + " " + str(getattr(e, "code", ""))


erg = {}
t0 = time.time()
_sm_voll = stt.chirp_sm_phrases
de_alle = None


def sm_selten():
    """Variante „smr“: nur Einträge, deren Wörter ALLE nicht in der öffentlichen Häufigkeitsliste (50.000) stehen."""
    return [p for p in _sm_voll() if all(w not in de for w in norm(p) if not w.isdigit())]


neu_min = 0.0
for bed in BED:
    if not bed.startswith("ohne"):
        stt.CHIRP_SM_BOOST = float(bed.lstrip("smr"))
        stt.chirp_sm_phrases = sm_selten if bed.startswith("smr") else _sm_voll
        print("PHRASEN", bed, len(stt.chirp_sm_phrases()), "Boost", stt.CHIRP_SM_BOOST)
    pf = os.path.join(AUS, "mess_%s.jsonl" % bed)
    alt = {}
    if os.path.exists(pf):        # schon gemessen (früherer Teil-Lauf) → nicht noch einmal bezahlen
        for zl in open(pf, encoding="utf-8"):
            d = json.loads(zl)
            if not d["hyp"].startswith("\x00"):
                alt[d["nr"]] = d["hyp"]
    offen = [f for f in faelle if f["nr"] not in alt]
    neu_min += sum(len(audio[f["nr"]][0]) / audio[f["nr"]][1] for f in offen) / 60
    with cf.ThreadPoolExecutor(2) as ex:
        neu = dict(zip([f["nr"] for f in offen], ex.map(lambda f: lauf(bed, f), offen)))
    hyps = [alt.get(f["nr"]) if f["nr"] in alt else neu[f["nr"]] for f in faelle]
    erg[bed] = hyps
    with open(os.path.join(AUS, "mess_%s.jsonl" % bed), "w", encoding="utf-8") as fh:
        for f, h in zip(faelle, hyps):
            fh.write(json.dumps({"nr": f["nr"], "ben": f["ben"], "hyp": h}, ensure_ascii=False) + "\n")
    print("LAUF", bed, "neu", len(offen), "Fehler", sum(1 for h in hyps if h.startswith("\x00")),
          dict(collections.Counter(h[:40] for h in hyps if h.startswith("\x00"))), "%.0fs" % (time.time() - t0))

# ── Auswertung (nur Summen) ──
import misheard  # noqa: E402
MH = misheard.compile_rules(misheard.load(HIER))
MIT_MH = False


def summe(idx, hyps_of):
    s = collections.Counter()
    lst = collections.defaultdict(lambda: [0, 0, 0])
    fh = collections.defaultdict(lambda: [0, 0])
    for i in idx:
        f = faelle[i]
        h = hyps_of(i)
        if h.startswith("\x00"):
            s["fehler"] += 1
            continue
        if MIT_MH:
            h = misheard.apply(h, MH)
        m = mass(norm(h), norm(f["ref"]))
        s["faelle"] += 1
        for k in ("n_ref", "n_hyp", "lev", "lcs"):
            s[k] += m[k]
        for k in ("liste", "selten", "seite", "zahl"):
            for j in range(3):
                lst[k][j] += m[k][j]
        for k, v in m["fh"].items():
            fh[k][0] += v[0]
            fh[k][1] += v[1]
    lst["_fh"] = fh
    return s, lst


def zeile(name, s, lst):
    n_ref, n_hyp = max(1, s["n_ref"]), max(1, s["n_hyp"])
    t = "%s faelle=%d WER=%.1f%% hyp_nicht_in_endf=%.1f%%" % (name, s["faelle"], 100 * s["lev"] / n_ref,
                                                            100 * (1 - s["lcs"] / n_hyp))
    for k in ("liste", "selten", "seite", "zahl"):
        r, hit, zv = lst[k]
        t += " %s_zuviel=%d" % (k, zv)
    for k in ("alle", "liste", "selten", "seite", "zahl"):
        ok_, fh_ = lst["_fh"][k]
        t += " FH_%s=%d/%d(%.2f%%)" % (k, fh_, ok_ + fh_, 100 * fh_ / max(1, ok_ + fh_))
    return t


voll = [i for i in range(len(faelle)) if all(not erg[b][i].startswith("\x00") for b in BED)]
gruppen = {"kp": [i for i in voll if faelle[i]["ben"] == "kp"],
           "rg": [i for i in voll if faelle[i]["ben"] == "rg"],
           "alle": voll}
for g, idx in gruppen.items():
    mins = sum(len(audio[faelle[i]["nr"]][0]) / audio[faelle[i]["nr"]][1] for i in idx) / 60
    print("GRUPPE", g, "faelle", len(idx), "min %.1f" % mins)
    s, lst = summe(idx, lambda i: faelle[i]["stt_prod"] or "\x00leer")
    print("ERG", zeile("%s/produktion" % g, s, lst))
    for bed in BED:
        s, lst = summe(idx, lambda i, b=bed: erg[b][i])
        print("ERG", zeile("%s/%s" % (g, bed), s, lst))
MIT_MH = True        # wie die EXE: Chirp-Text → Fehlhör-Liste (auto) → weiter
for g, idx in gruppen.items():
    for bed in BED:
        s_, lst = summe(idx, lambda i, b=bed: erg[b][i])
        print("ERGMH", zeile("%s/%s+fehlhoer" % (g, bed), s_, lst))
MIT_MH = False
# Wie viele Fälle ändern sich zwischen den Bedingungen? (Rauschen: ohne ↔ Produktion)
for bed in BED:
    gleich = sum(1 for i in range(len(faelle)) if erg[bed][i] == erg[BED[0]][i])
    gleich_prod = sum(1 for i in range(len(faelle)) if norm(erg[bed][i]) == norm(faelle[i]["stt_prod"]))
    print("AENDERUNG", bed, "gleich_wie_%s" % BED[0], gleich, "gleich_wie_produktion", gleich_prod, "von", len(faelle))
# Je Fall: besser / schlechter als die erste Bedingung (Vorzeichen-Test), Fehlhörer gesamt und Fachwort (liste ∪ selten)
def fh_fall(i, b):
    m = fehlhoerer(norm(erg[b][i]), norm(faelle[i]["ref"]))
    fw = sum(1 for _ in ())
    return m["alle"][1], m["liste"][1] + m["selten"][1]


for g, idx in gruppen.items():
    for bed in BED[1:]:
        z = collections.Counter()
        for i in idx:
            a0, f0 = fh_fall(i, BED[0])
            a1, f1 = fh_fall(i, bed)
            z["alle_" + ("besser" if a1 < a0 else "schlechter" if a1 > a0 else "gleich")] += 1
            z["fach_" + ("besser" if f1 < f0 else "schlechter" if f1 > f0 else "gleich")] += 1
        print("JEFALL", g, bed, "vs", BED[0], dict(sorted(z.items())))
print("MINUTEN_GESENDET %.2f KOSTEN_EUR %.2f" % (neu_min, neu_min * PREIS_EUR_MIN))
print("%.0fs" % (time.time() - t0))
