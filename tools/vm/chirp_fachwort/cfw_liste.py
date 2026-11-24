r"""chirp-fachwortliste-n1 Schritt 1 (VM, rakauto, NUR LESEN an CAS/M:/X:): Fachwortliste für Chirp aus den
SpeechMagic-Briefen – mit strengem, maschinellem Namensfilter. Läuft komplett auf der VM.

Eingaben (VM): %LOCALAPPDATA%\smi_work\pairs.jsonl (SpeechMagic-Rohtext ↔ Befundtext), M:\Diktate\<nr>.doc (Briefköpfe),
lernen.db (KaiScribe-STT ↔ vidierte Endfassung, Vidier-Änderungen), CAS (nur SELECT, READ ONLY: alle Namen/Orte/Straßen aus
PRIVADRESS, WARTEROW, ALLARZTE, USERS) + hochgeladen: de_50k.txt (öffentliche deutsche Häufigkeitsliste), phrases.json,
misheard_words.json (RaKScribe26).
Filter (Peter 24.11.: „ich vertraue dir“ → im Zweifel streichen):
  (a) Wort (oder ein Teil davon) kommt in einem CAS-Namens-/Orts-/Straßenfeld, einem Briefkopf-Feld oder nach
      Dr./Prof./Prim./OA/Frau/Herr/Pat./Kollege … vor → raus (außer es steht in den kuratierten Phrasenlisten).
  (b) Großgeschrieben, nicht im Wörterbuch (de_50k, Phrasenlisten, zerlegbares Kompositum) und ohne eindeutige
      lat./med. Endung → raus.
  (c) Orts-/Straßennamen: über (a) (CAS ORT/STRASSE) + Endungen -straße/-gasse/-weg/-platz/-dorf/-berg … → raus.
  Dazu: nur Wörter, die in ≥ MIN_DF verschiedenen Briefen DIKTIERT (SpeechMagic-Rohtext) UND in der Endfassung stehen.
Ausgabe: %LOCALAPPDATA%\chirp_fw\chirp_sm_liste.json + Stufen-Zähler. Auf die Konsole NUR Zähler und die gefilterte
Endliste (nur Fachwörter) – die Rohliste und alle Namen bleiben auf der VM.
"""
import collections
import json
import os
import re
import sqlite3
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
for p in (r"C:\RaK\kaiscribe_lernen\prog\bruecke", r"C:\RaKScribe-Py\ris-mods\bruecke"):
    sys.path.insert(0, p)
import casdb  # noqa: E402
import sm  # noqa: E402

SMI = os.path.expandvars(r"%LOCALAPPDATA%\smi_work")
AUS = os.path.expandvars(r"%LOCALAPPDATA%\chirp_fw")
DB = r"C:\RaK\kaiscribe_lernen\daten\lernen.db"
DIKTATE = "M:\\Diktate"
MIN_DF = 5
ZIEL_WORT = int(sys.argv[1]) if len(sys.argv) > 1 else 260
ZIEL_PHRASE = int(sys.argv[2]) if len(sys.argv) > 2 else 40
os.makedirs(AUS, exist_ok=True)
t0 = time.time()
WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*")


def low(w):
    return w.lower()


# ── Kuratierte Listen (sicher, von Peter/KaiScribe gepflegt) ──
PH = json.load(open(os.path.join(HIER, "phrases.json"), encoding="utf-8"))
MH = json.load(open(os.path.join(HIER, "misheard_words.json"), encoding="utf-8"))
kuratiert = set()
for k in ("chirp", "medical_exe", "medical_web"):
    for p in PH[k]:
        for w in WORT.findall(p):
            kuratiert.add(low(w))
        kuratiert.add(low(p))
chirp85 = set(low(p) for p in PH["chirp"])
mh_mean = collections.Counter()
for r in MH["rules"]:
    for w in WORT.findall(r.get("mean", "")):
        mh_mean[low(w)] += 1
        kuratiert.add(low(w))
# ── Wörterbuch ──
de = {}
for i, z in enumerate(open(os.path.join(HIER, "de_50k.txt"), encoding="utf-8")):
    t = z.split()
    if t:
        de.setdefault(t[0].lower(), i)
GELAEUFIG = set(w for w, r in de.items() if r < 20000)   # „Chirp kann das sicher“ (Alltagswörter)
WB = set(de) | kuratiert
print("WB", len(de), "gelaeufig", len(GELAEUFIG), "kuratiert", len(kuratiert))

# ── (a) Namen aus CAS (nur SELECT, READ ONLY) – bleibt auf der VM ──
SPALTEN = [("privadress", c) for c in ("name", "vorname", "birthname", "midname", "ort", "strasse")] + \
          [("warterow", c) for c in ("name", "vorname", "senderdname", "senderdvorname")] + \
          [("allarzte", c) for c in ("name", "vorname", "ort", "strasse")] + \
          [("users", c) for c in ("name", "name1", "name2")]
sql = casdb._KOPF
for tab, col in SPALTEN:
    sql += casdb._abschnitt(f"{tab}_{col}".replace("1", "_eins").replace("2", "_zwei"), f"SELECT DISTINCT 'W|' || UPPER(TRIM({col})) FROM sysadm.{tab} "
                                            f"WHERE {col} IS NOT NULL;")
sql += "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n"
CACHE = os.path.join(AUS, "namen_cache.json")      # bleibt auf der VM (rakauto-Profil), 1 Tag gültig
if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < 86400:
    c = json.load(open(CACHE, encoding="utf-8"))
    namen, n_werte = collections.Counter(c["namen"]), c["n_werte"]
    print("CAS aus Cache (VM)", "Werte", n_werte, "Namens-Token", len(namen))
else:
    anm = casdb.anmeldung_lesen()
    sp = casdb.sqlplus_finden()
    if not anm or not sp:
        print("CFW FEHLER CAS-Anmeldung", bool(anm), sp)
        sys.exit(1)
    rc, out = casdb.sqlplus_ausfuehren([sp], "CASMED", anm[0], anm[1], sql, frist_s=900)
    namen = collections.Counter()      # Token → Anzahl Quellen-Werte
    n_werte = 0
    for z in out.splitlines():
        if z.startswith("W|"):
            n_werte += 1
            for w in WORT.findall(z[2:]):
                for teil in w.split("-"):
                    if len(teil) >= 3:
                        namen[low(teil)] += 1
    _v, _f, _abs, fehler = casdb.abschnitte(out)
    print("CAS rc", rc, "Werte", n_werte, "Namens-Token", len(namen), "Abschnitte ok", sorted(_abs),
          "Fehler", {k: sorted(set(v))[:3] if isinstance(v, (list, set, tuple)) else str(v)[:20] for k, v in fehler.items()},
          "%.0fs" % (time.time() - t0))
    if n_werte < 10000:
        print("CFW FEHLER zu wenige CAS-Namen – Abbruch (im Zweifel nichts)")
        sys.exit(1)
    json.dump({"namen": namen, "n_werte": n_werte}, open(CACHE, "w", encoding="utf-8"))

# ── (a) Briefköpfe + Namen nach Titeln (alle Paare) ──
pairs = [json.loads(z) for z in open(os.path.join(SMI, "pairs.jsonl"), encoding="utf-8")]
TITEL = re.compile(r"(?:\b(?:Dr|Prof|Doz|Prim|Mag|OA|OÄ|FA|FÄ|Pat|DGKS|DGKP|MTRA|Dipl|Ing)\.?(?:\s*(?:med|univ|dent|"
                   r"scient|rer|nat|phil|techn)\.)*|"
                   r"\b(?:Frau|Herr|Herrn|Patient|Patientin|Kollege|Kollegin|Kollegen|Primar|Primaria|Oberarzt|"
                   r"Oberärztin|Fachärztin|Facharzt|Ärztin|Arzt|Kopie an|i\.\s?V|z\.\s?H|zH|Hd|Gruß|Grüße|Grüßen|"
                   r"Ordination|Praxis|Klinik|Klinikum|LKH|KH|Krankenhaus|Spital|Zentrum|Institut|Station))"
                   r"[\s.:,]+((?:[A-ZÄÖÜ][\wäöüß\-]+[\s.]*){1,3})")
briefkopf = set()
n_doc = 0
for p in pairs:
    texte = [p.get("fin", ""), p.get("raw", "")]
    try:
        d = sm.doc_text(open(os.path.join(DIKTATE, p["nr"] + ".doc"), "rb").read())
        n_doc += 1
        texte.append(d)
        for m in re.finditer(r"MERGEFIELD\s+\"?(\w+)\"?\s*\x14?([^\x13\x15\n]*)", d):
            if re.match(r"(Pat|Art|Benutzer|Sign|Post|Kopie|Zuw|Arzt|Name|Vor|Ort|Str|Adr|Titel)", m.group(1), re.I):
                for w in WORT.findall(m.group(2)):
                    for teil in w.split("-"):
                        briefkopf.add(low(teil))
        # Briefkopf = alles vor dem Befundteil (Adressblock, Anrede)
        kopf = d.split("<bf", 1)[0] if "<bf" in d else d[:600]
        for w in WORT.findall(kopf):
            if w[:1].isupper() and low(w) not in de:
                for teil in w.split("-"):
                    briefkopf.add(low(teil))
    except Exception:
        pass
    for t in texte:
        for m in TITEL.finditer(t or ""):
            for w in WORT.findall(m.group(1)):
                for teil in w.split("-"):
                    briefkopf.add(low(teil))
print("Briefe", len(pairs), "Docs gelesen", n_doc, "Briefkopf/Titel-Token", len(briefkopf))
NAMEN = set(namen) | briefkopf

# ── Häufigkeit: diktiert (SM-Rohtext) UND in der Endfassung, je Brief ──
df = collections.Counter()
form = {}
miss_sm = collections.Counter()       # in Endfassung, nicht im Rohtext (Vorlage/Korrektur)
fin_df = collections.Counter()
bi = collections.Counter()
bi_form = {}
for p in pairs:
    raw, fin = p.get("raw", "") or "", p.get("fin", "") or ""
    rw = set(low(w) for w in WORT.findall(raw))
    fw_list = WORT.findall(fin)
    fw = set(low(w) for w in fw_list)
    for w in fw_list:
        form.setdefault(low(w), collections.Counter())[w] += 1
    for w in fw:
        fin_df[w] += 1
        if w in rw:
            df[w] += 1
        else:
            miss_sm[w] += 1
    rawlow = " " + " ".join(low(x) for x in WORT.findall(raw)) + " "
    seen = set()
    paare_fin = [(a, b) for teil in re.split(r"[.,:;!?()\n\r\t/]+", fin) for a, b in zip(WORT.findall(teil), WORT.findall(teil)[1:])]
    for a, b in paare_fin:
        k = low(a) + " " + low(b)
        if k in seen or len(a) < 2 or len(b) < 4:
            continue
        seen.add(k)
        if " " + k + " " in rawlow:
            bi[k] += 1
            bi_form.setdefault(k, collections.Counter())[a + " " + b] += 1

# ── Belege, dass Chirp falsch hört: Wortausrichtung KaiScribe-STT ↔ vidierte Endfassung (lernen.db); nur ERSETZUNGEN
#    (kurze, ähnlich klingende Blöcke) zählen – eingefügter Vorlagentext (Normaltext, Ergebnis) zählt nicht.
import difflib  # noqa: E402


def ersetzt(quelle, ziel, zaehler, max_len=3, min_ahnl=0.45):
    """Wörter aus ziel, die in der Ausrichtung quelle→ziel als Ersetzung eines ähnlich geschriebenen Blocks stehen."""
    q = [low(w) for w in WORT.findall(quelle or "")]
    z = [low(w) for w in WORT.findall(ziel or "")]
    gesehen = set()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, q, z, autojunk=False).get_opcodes():
        if op != "replace" or (i2 - i1) > max_len or (j2 - j1) > max_len:
            continue
        a, b = "".join(q[i1:i2]), "".join(z[j1:j2])
        if a == b:                        # nur Getrennt-/Zusammenschreibung → zählt auch (Chirp trennt falsch)
            pass
        elif difflib.SequenceMatcher(None, a, b).ratio() < min_ahnl:
            continue
        for w in z[j1:j2]:
            if w not in gesehen:
                gesehen.add(w)
                zaehler[w] += 1


chirp_miss = collections.Counter()     # Chirp (KaiScribe-STT) → Endfassung ersetzt
chirp_hat = collections.Counter()      # Wort stand richtig im STT
aend = collections.Counter()           # Vidier-Änderung (KaiScribe-Erstfassung → Endfassung), ähnliche Ersetzung
sm_fehl = collections.Counter()        # SpeechMagic-Rohtext → Endfassung ersetzt (akustisch schwierig)
db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
n_ks = 0
for stt, fin in db.execute("SELECT stt, final FROM faelle WHERE status='final' AND stt IS NOT NULL AND stt<>'' "
                           "AND final IS NOT NULL"):
    n_ks += 1
    ersetzt(stt, fin, chirp_miss)
    sw = set(low(w) for w in WORT.findall(stt))
    for w in sw:
        chirp_hat[w] += 1
for alt, neu in db.execute("SELECT alt, neu FROM aenderungen"):
    ersetzt(alt, neu, aend)
for p in pairs:
    ersetzt(p.get("raw", ""), p.get("fin", ""), sm_fehl)
print("KaiScribe-Paare", n_ks, "Chirp-Ersetzungen", sum(chirp_miss.values()), "Vidier", sum(aend.values()),
      "SM-Ersetzungen", sum(sm_fehl.values()))

# ── Filter ──
MED_ENDUNG = re.compile(r"(itis|itiden|osis|osen|ose|om|ome|omen|omas|ie|ien|ia|iae|ae|us|um|ica|icum|icus|alis|ale|"
                        r"ales|aris|are|ion|ionen|tion|tionen|ismus|ismen|algie|ektomie|graphie|grafie|gramm|skopie|"
                        r"plastie|pathie|ämie|urie|ase|asen|ität|ulär|ulären|ulärer|ulare|ären|äre|ärer|al|ale|alen|aler|"
                        r"ell|elle|ellen|eller|iv|ive|iven|iver|ös|öse|ösen|öser|ierung|ierungen|ieren|iert|ierte|ierten|"
                        r"kardial|ventrikulär|lumbal|thorakal|zervikal|cervical|abdominal|femoral|tibial|humeral|osseär)$")
ORT_ENDUNG = re.compile(r"(straße|strasse|gasse|weg|platz|allee|ring|kai|dorf|berg|burg|bach|feld|felden|kirchen|"
                        r"hausen|heim|stadt|statt|tal|thal|au|eck|hof|brunn|bruck|stein|wald|markt|sankt|st)$")
STOP = set("""durch nicht noch sowie sowohl jedoch sonst ansonsten eher mehr weniger keine keiner keinen keinem
kann können könnte wären sollte sollten bitte danke diese dieser diesen dieses dabei damit davon dazu wurde wurden werden
""".split())


def zerlegbar(w, tiefe=0):
    """Kompositum aus Wörterbuch-Teilen (≥ 3 Buchstaben, Fugen-s/-n/-e erlaubt)?"""
    if w in WB:
        return True
    for suf in ("en", "e", "n", "s", "er", "es", "ungen", "ung"):
        if w.endswith(suf) and w[:-len(suf)] in WB and len(w) - len(suf) >= 4:
            return True
    if tiefe >= 2:
        return False
    for i in range(3, len(w) - 2):
        a, b = w[:i], w[i:]
        if a in WB or (a[-1:] in "sne" and a[:-1] in WB and len(a) > 4):
            if zerlegbar(b, tiefe + 1):
                return True
    return False


grund = collections.Counter()


def pruefen(w):
    """→ None (ok) oder Grund. w = Kleinform."""
    if w in kuratiert:
        return None
    teile = w.split("-")
    if any(t in NAMEN for t in teile):
        return "a_name"
    if ORT_ENDUNG.search(w) and not zerlegbar(w) and not MED_ENDUNG.search(w):
        return "c_ort"
    f = form.get(w, collections.Counter())
    gross = sum(c for x, c in f.items() if x[:1].isupper())
    if gross >= 0.5 * max(1, sum(f.values())):
        if not all(zerlegbar(t) or MED_ENDUNG.search(t) for t in teile):
            return "b_unbekannt"
    elif not all(zerlegbar(t) or MED_ENDUNG.search(t) for t in teile):
        return "b_unbekannt_klein"
    return None


kand = [w for w, c in df.items() if c >= MIN_DF and len(w) >= 5 and w not in STOP]
print("Kandidaten df>=%d" % MIN_DF, len(kand))
ok = []
for w in kand:
    g = pruefen(w)
    if g:
        grund[g] += 1
    else:
        ok.append(w)
print("nach Namens-/Woerterbuchfilter", len(ok), dict(grund))


def schreibung(w):
    return form[w].most_common(1)[0][0]


# Alltagswort = in der öffentlichen Häufigkeitsliste (Untertitel) unter den ersten 20.000 → „Chirp kann das“.
FUNKTION = set(w for w, r in de.items() if r < 400)


def stamm(w):
    for suf in ("ungen", "en", "er", "es", "em", "e", "n", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


rows = []
for w in ok:
    if w in chirp85 or miss_sm[w] > df[w] or w in FUNKTION:   # schon kuratiert / meist Vorlagentext / Funktionswort
        continue
    beleg = 3 * min(chirp_miss[w], 5) + 2 * min(aend[w], 5) + 3 * min(mh_mean[w], 2) + min(sm_fehl[w], 6) // 2
    rows.append({"w": w, "wert": schreibung(w), "df": df[w], "beleg": beleg, "chirp_miss": chirp_miss[w],
                 "aend": aend[w], "mh": mh_mean[w], "sm_fehl": sm_fehl[w], "gelaeufig": w in GELAEUFIG,
                 "vorlage": round(miss_sm[w] / max(1, fin_df[w]), 2)})
# (1) Belege (Chirp-/Vidier-Ersetzung oder Fehlhör-Liste): auch geläufige Wörter;
# (2) Fachwörter (nicht Alltagswort) mit SpeechMagic-Ersetzungen bzw. nach Diktat-Häufigkeit.
stark = [r for r in rows if (r["chirp_miss"] or r["aend"] or r["mh"])]
stark.sort(key=lambda r: (-r["beleg"], -r["df"]))
fach = [r for r in rows if not r["gelaeufig"] and r not in stark]
fach.sort(key=lambda r: (-(min(r["sm_fehl"], 6) // 2 + (1 if r["df"] >= 30 else 0)), -r["df"]))
wahl, staemme = [], collections.Counter()
for r in stark + fach:
    st = stamm(r["w"])
    if staemme[st] >= (2 if r in stark else 1):      # Beugeformen: höchstens eine (mit Beleg zwei)
        continue
    staemme[st] += 1
    wahl.append(r)
    if len(wahl) >= ZIEL_WORT:
        break
# Mehrwortphrasen: häufig diktiert (≥ 20 Briefe, im selben Satzteil), jedes Wort einzeln geprüft, kein Funktionswort,
# mindestens ein Fachwort (nicht Alltagswort)
phr = []
for k, c in bi.most_common():
    if c < 20:
        break
    a, b = k.split(" ")
    if any(x in STOP or x in FUNKTION or len(x) < 2 for x in (a, b)):
        continue
    if pruefen(a) or pruefen(b):
        continue
    if a in GELAEUFIG and b in GELAEUFIG:
        continue
    phr.append({"w": k, "wert": bi_form[k].most_common(1)[0][0], "df": c})
    if len(phr) >= ZIEL_PHRASE:
        break
erg = {"stand": time.strftime("%Y-%m-%d %H:%M"), "quelle": "SpeechMagic-Briefe M:\\Diktate (%d Paare)" % len(pairs),
       "min_df": MIN_DF, "filter": dict(grund), "kandidaten": len(kand), "nach_filter": len(ok),
       "woerter": wahl, "phrasen": phr}
json.dump(erg, open(os.path.join(AUS, "chirp_sm_liste.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("AUSWAHL Woerter", len(wahl), "davon mit Chirp-/Vidier-/Fehlhoer-Beleg", sum(1 for r in wahl if r in stark),
      "Phrasen", len(phr))
print("LISTE-WOERTER " + json.dumps([[r["wert"], r["df"], r["chirp_miss"], r["aend"], r["mh"], r["sm_fehl"]]
                                     for r in wahl]))
print("LISTE-PHRASEN " + json.dumps([[r["wert"], r["df"]] for r in phr]))
print("%.0fs" % (time.time() - t0))
