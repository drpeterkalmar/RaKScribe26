r"""rho_osteopen_kontrolle.py 1.0 (kaiscribe-rho-osteopen-kontrolle, 23.11.2026) – NUR LESEN, Automaten-VM als rakauto.

Georg 22.11.2026: Rho-Score ≥ 7 → „Osteopenischer Knochenaspekt.“ statt Mineralisations-Normalsatz in ALLEN
Röntgen-Teilen. Je Brief eines Tages (CAS LETTERS, nur SELECT über casdb, READ ONLY) mit Rho-Text
(„Knochendichtescreening“): Weg (KaiScribe „(KI)“ / Formatierer-Screening „niedrige Knochenmineraldichte“), Teile,
Teile mit „Osteopenischer Knochenaspekt“, Normalsätze daneben, Knochendichte selbst diktiert (Lauf-Datei KaiScribe),
dazu die [ibl]-Zeilen der Formatierer-Logs zur Nummer (nur Kategorien + Formatierer-Version).
Ausgabe nur Kurz-ID (MMTT-NNN), Zahlen, Kategorien, Strukturkürzel – kein Name, kein Text.

  C:\RaK\laufwerke.cmd C:\Windows\py.exe -3.12 -X utf8 rho_osteopen_kontrolle.py 20261123 [--ab 07:00]
Strukturkürzel je Zeile des Befundteils: T Titel, E „Ergebnis“, O Osteopenischer Knochenaspekt, N Normalsatz,
R Rho/Screening, P sonst Osteopenie/-porose, . sonst.
"""
import glob
import json
import os
import re
import sys

PROG = r"C:\RaK\kaiscribe_lernen\prog"
for p in (PROG, os.path.join(PROG, "bruecke")):
    sys.path.insert(0, p)
import casdb  # noqa: E402

A = sys.argv[1:]
TAG = A[0] if A and re.fullmatch(r"\d{8}", A[0]) else None
AB = A[A.index("--ab") + 1] if "--ab" in A else "07:00"
LAEUFE = [r"X:\KaiScribe\Daten\laeufe", r"X:\RaKScribe\Daten\laeufe"]
LOGS = (glob.glob(r"X:\KaiScribe\Daten\protokolle\format_*.log") + glob.glob(r"X:\RaKScribe\Daten\protokolle\format_*.log")
        + [os.path.join(os.environ.get("LOCALAPPDATA", ""), "RaK-Befund", "format.log")])

# ── wörtlich wie KaiScribe 3.22.4 befund_regeln (osteopen_ersetzen) ──
OSTEOPEN = "osteopenischer knochenaspekt"
_OSTEO_WORT = re.compile(r"mineral|kalksalz|knochenstruktur|spongiosa", re.I)
_OSTEO_NORMAL = re.compile(r"^(?:regelrecht|unauffällig|normal|regulär|altersentsprechend|altersgerecht|homogen)"
                           r"(?:e|er|em|en|es)?$")
_OSTEO_ERLAUBT = frozenset((
    "im übrigen ansonsten sonst die der das des den mitdargestellten mitabgebildeten abgebildeten dargestellten erfassten "
    "miterfassten übrigen skelettabschnitte skelettanteile knochen knöchernen ist sind stellt stellen sich dar zeigt zeigen "
    "bezüglich hinsichtlich mineralgehalt mineralisation knochenmineralisation knochenmineralgehalt kalksalzgehalt "
    "knochenstruktur knochenstrukturen spongiosastruktur und sowie bei scharfer scharf abgrenzbarkeit abgrenzbar "
    "spongiosabälkchen soweit erfasst mitabgebildet beckens femurs").split())
_OSTEO_DIKTIERT = re.compile(r"mineral|osteopen|osteopor|kalksalz|entkalk|kalkarm|knochenarm|knochendicht|"
                             r"knochenatroph|demineral", re.I)
_OSTEO_IM_BEFUND = re.compile(r"osteopen|osteopor|demineral|kalksalzminder|kalkarm|vermindert\w*\s+(?:knochen)?mineral",
                              re.I)
_RHO_RE = re.compile(r"(?<![\w-])(?:rho|ro|roh|row)(?:[\s-]*(?:score|skor|stufe))?(?:[\s:,-]*(?:von\s+)?\d{1,2})?(?![\w-])|"
                     r"zus[äa]tzlich\w*\s+(?:dexa|dxa)\w*|opportunistische\w*\s+knochen\w*[\s-]*screening", re.I)
RHO_TITEL = "opportunistisches knochendichtescreening (ki)"
RHO_ZEILE = re.compile(r"knochendichtescreening|\(rho\)|knochenmineraldichte|dexa|dxa|ki-schätzung rho|rho-score", re.I)


def _osteo_normal(satz):
    w = re.findall(r"[a-zäöüß]+", satz.lower())
    return (bool(w) and _OSTEO_WORT.search(satz) is not None and any(_OSTEO_NORMAL.match(x) for x in w)
            and all(x in _OSTEO_ERLAUBT or _OSTEO_NORMAL.match(x) for x in w))


def normal_saetze(zeile):
    n = 0
    for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", zeile):
        s = s.strip()
        if _osteo_normal(s) or (", " in s and _osteo_normal(s.partition(", ")[0])):
            n += 1
    return n


def norm(t):
    return re.sub(r"\s+", " ", str(t or "").lower()).strip()


def ist_ergebnis(z):
    return bool(re.match(r"^(ergebnis|zusammenfassung|beurteilung)\s*:?\s*$", norm(z))) or norm(z).startswith("ergebnis:")


U, UE = "\u00a7U\u00a7", "\u00a7E\u00a7"
_SATZWORT = re.compile(r"\b(?:keine?[nrsm]?|ist|sind|zeigt|zeigen|regelrecht\w*|unauffällig\w*|normal\w*|erhalten\w*|"
                       r"nachweis\w*|hinweis\w*|verdacht|empfohlen|besteht|bestehen|liegt|vor|mit|ohne)\b", re.I)


def markieren(roh):
    """Unterstreichung im RTF als Text-Marker (Titel im CAS-Brief = fett + unterstrichen)."""
    roh = re.sub(r"\\ul(?:none|0)(?![a-z0-9])\s?", lambda m: " " + "\\'a7E\\'a7" + " ", roh)
    return re.sub(r"\\ul(?![a-z0-9-])\s?", lambda m: " " + "\\'a7U\\'a7" + " ", roh)


def ist_titel(z):
    s = z.strip()
    if U in s:
        innen = re.sub(r"\s+", "", "".join(re.findall(re.escape(U) + r"(.*?)(?:" + re.escape(UE) + r"|$)", s)))
        voll = re.sub(r"\s+", "", s.replace(U, "").replace(UE, ""))
        if voll and len(innen) >= 0.6 * len(voll) and not ist_ergebnis(s.replace(U, "").replace(UE, "")):
            return True
    s = s.replace(U, "").replace(UE, "").strip()
    if not s or len(s) > 90 or ist_ergebnis(s) or s[0] in "-•*–" or re.match(r"^\d+[.)]", s):
        return False
    if s.endswith(("!", "?", ",", ";")) or _SATZWORT.search(s):
        return False
    if s.endswith(".") and not re.search(r"(?:a\.\s?p|p\.\s?a|seitl|re|li|bds|ebenen|ap|pa)\.$", s, re.I):
        return False
    return s[0].isupper() or s[0].isdigit()


def brief_auswerten(text):
    zeilen = [z.strip() for z in (text or "").replace("\r", "\n").split("\n") if z.strip()]
    code, teile, teil, im_erg, im_rho = [], [], None, False, False
    for z0 in zeilen:
        z = z0.replace(U, "").replace(UE, "").strip()
        n = norm(z)
        if not z:
            continue
        if ist_titel(z0):
            im_rho = n.startswith(RHO_TITEL[:-5]) and "(ki)" in n
            im_erg = False
            teil = {"rho": im_rho, "o": 0, "n": 0, "p": 0, "zeilen": 0}
            teile.append(teil)
            code.append("T")
            continue
        if re.match(r"^befund\s*:?\s*$", n):
            code.append("B")
            continue
        if ist_ergebnis(z):
            im_erg = True
            code.append("E")
            continue
        if teil is None:
            teil = {"rho": False, "o": 0, "n": 0, "p": 0, "zeilen": 0}
            teile.append(teil)
        if im_rho or RHO_ZEILE.search(z):
            code.append("R")
            continue
        if im_erg:
            code.append("e" if not _OSTEO_IM_BEFUND.search(z) else "P")
            continue
        teil["zeilen"] += 1
        if OSTEOPEN in n:
            teil["o"] += 1
            code.append("O")
        elif normal_saetze(z):
            teil["n"] += normal_saetze(z)
            code.append("N")
        elif _OSTEO_IM_BEFUND.search(z):
            teil["p"] += 1
            code.append("P")
        else:
            code.append(".")
    unters = [t for t in teile if not t["rho"] and t["zeilen"]]
    text = (text or "").replace(U, "").replace(UE, "")
    return {
        "ki": RHO_TITEL in norm(text), "fmt": "niedrige knochenmineraldichte" in norm(text),
        "teile": len(unters), "mit_o": sum(1 for t in unters if t["o"]), "normal": sum(t["n"] for t in unters),
        "teile_mit_n": sum(1 for t in unters if t["n"]), "sonst_osteo": sum(t["p"] for t in unters),
        "code": "".join(code)[:120]}


def md_auswerten(md):
    """KaiScribe-Vorschlag (## Titel / ## Befund / ## Ergebnis) → Teile, mit O, Normalsätze."""
    teile, t, im_bef = [], None, True
    for z in (md or "").split("\n"):
        s = z.strip()
        if s.startswith("## "):
            k = s[3:].strip().rstrip(":").lower()
            if k == "befund":
                im_bef = True
            elif k == "ergebnis":
                im_bef = False
            else:
                t = {"rho": k == RHO_TITEL, "o": 0, "n": 0}
                teile.append(t)
                im_bef = True
            continue
        if not s or not im_bef:
            continue
        if t is None:
            t = {"rho": False, "o": 0, "n": 0}
            teile.append(t)
        if t["rho"]:
            continue
        t["o"] += OSTEOPEN in norm(s)
        t["n"] += normal_saetze(s)
    u = [x for x in teile if not x["rho"]]
    return {"ki": any(x["rho"] for x in teile), "teile": len(u), "mit_o": sum(1 for x in u if x["o"]),
            "normal": sum(x["n"] for x in u)}


def lauf(nr):
    dateien = []
    for o in LAEUFE:
        dateien += glob.glob(os.path.join(o, f"{nr}_*.json"))
    if not dateien:
        return None
    dateien.sort(key=lambda p: os.path.basename(p))
    try:
        with open(dateien[-1], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {"n": len(dateien), "lesbar": False}
    diktat = " ".join(str(d.get(k) or "") for k in ("stt_roh", "diktat"))
    rest = _RHO_RE.sub(" ", diktat)
    m = md_auswerten(d.get("ergebnis_vorschlag") or "")
    return {"n": len(dateien), "lesbar": True, "v": str(d.get("kaiscribe") or "?")[:10],
            "pc": str(d.get("rechner") or "?")[:12], "zeit": os.path.basename(dateien[-1]).split("_")[1][9:13],
            "diktiert": bool(_OSTEO_DIKTIERT.search(rest)), "rho_diktiert": bool(_RHO_RE.search(diktat)), "md": m}


def format_zeilen(nrs):
    """{nr: [(log, version, art)]} aus allen Formatierer-Logs (nur [ibl]-Zeilen dieser Nummern)."""
    aus = {}
    for p in LOGS:
        if not os.path.isfile(p):
            continue
        name = os.path.basename(p).replace("format_", "").replace(".log", "") or "?"
        if "RaK-Befund" in p:
            name = "VM"
        ver = "?"
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for z in f:
                    m = re.search(r"gestartet v(\d+\.\d+\.\d+)", z)
                    if m:
                        ver = m.group(1)
                        continue
                    m = re.search(r"\[ibl\] (\d{11}): (.*)$", z)
                    if not m or m.group(1) not in nrs or not z.startswith(TAG[:4] + "-" + TAG[4:6] + "-" + TAG[6:]):
                        continue
                    t = m.group(2)
                    art = []
                    if "Rho-Screening-Baustein eingefügt" in t:
                        art.append("screening")
                    o = re.search(r"(\d+) Untersuchung\(en\) mit „Osteopenischer", t)
                    if o:
                        art.append("osteopen=" + o.group(1))
                    if "Beschreibung nennt Osteopenie" in t:
                        art.append("grund_osteo_schon")
                    if "kein Mineralisations-Normalsatz" in t:
                        art.append("grund_kein_normalsatz")
                    if "Normalsatz schon einmal ersetzt" in t:
                        art.append("grund_schon_ersetzt")
                    if re.match(r"\d+ Wert\(e\)", t):
                        art.append("zusammenfassung")
                    if art:
                        aus.setdefault(m.group(1), []).append((name, ver, z[11:16], "+".join(art)))
        except OSError:
            continue
    return aus


def main():
    if not TAG:
        raise SystemExit(__doc__)
    e = casdb.Einstellungen({})
    befehl = [casdb.sqlplus_finden(e.sqlplus)]
    anm = casdb.anmeldung_lesen(e.anmeldung)
    if not befehl[0] or not anm:
        print("FEHLER kein sqlplus/keine Anmeldung")
        sys.exit(1)
    nr = "TO_CHAR(l.listdate,'YYYYMMDD') || LPAD(w.numberinlist,3,'0')"
    liste_sql = (casdb._KOPF + casdb._abschnitt("liste", f"""
SELECT JSON_OBJECT('nr' VALUE {nr}, 'wrid' VALUE TO_CHAR(w.warterowid), 'st' VALUE w.status, 'obl' VALUE w.obletter,
  'obg' VALUE w.obgelesen, 'wer' VALUE w.ddwer, 'rt' VALUE TO_CHAR(w.recordtime,'HH24:MI'))
FROM sysadm.warterow w JOIN sysadm.wartelist l ON l.id = w.wartelistid
WHERE l.listdate >= TO_DATE('{TAG}','YYYYMMDD') AND l.listdate < TO_DATE('{TAG}','YYYYMMDD') + 1
  AND NVL(w.status,'?') <> '!' AND EXISTS (SELECT 1 FROM sysadm.letters t WHERE t.id = w.warterowid);""")
                 + "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n")
    _c, aus = casdb.sqlplus_ausfuehren(befehl, e.ziel, anm[0], anm[1], liste_sql, frist_s=120)
    _v, _f, a, fehler = casdb.abschnitte(aus)
    besuche = casdb._json_zeilen(a.get("liste"))
    print(f"LISTE briefe={len(besuche)} fehler={','.join(fehler) or '-'}")
    besuche = [b for b in besuche if re.fullmatch(r"\d{11}", str(b.get("nr") or "")) and re.fullmatch(r"\d+", str(b.get("wrid") or ""))]
    texte = {}
    abc = "abcdefghijklmnopqrstuvwxyz"
    for i in range(0, len(besuche), 12):
        teil = besuche[i:i + 12]
        s = casdb._KOPF
        for k, b in enumerate(teil):
            s += casdb._abschnitt("b_" + abc[k], f"SELECT t.letter FROM sysadm.letters t WHERE t.id = {int(b['wrid'])} AND ROWNUM = 1;")
        s += "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n"
        try:
            _c, aus = casdb.sqlplus_ausfuehren(befehl, e.ziel, anm[0], anm[1], s, frist_s=300)
        except Exception as ex:  # noqa: BLE001
            print(f"STAPEL {i} FEHLER {type(ex).__name__}")
            continue
        _v, _f, a, fehler = casdb.abschnitte(aus)
        for k, b in enumerate(teil):
            if "b_" + abc[k] in a:
                roh = casdb._brief_roh(a["b_" + abc[k]])
                try:
                    texte[b["nr"]] = casdb._befundteil(casdb._klartext(markieren(roh))) if roh else ""
                except Exception:  # noqa: BLE001
                    texte[b["nr"]] = casdb.befundtext(a["b_" + abc[k]])
            else:
                texte[b["nr"]] = None
        if fehler:
            print(f"STAPEL {i} fehler={','.join(sorted(fehler))}")
    rho = [b for b in besuche if texte.get(b["nr"]) and "knochendichtescreening" in norm(texte[b["nr"]])]
    nicht = sum(1 for b in besuche if texte.get(b["nr"]) is None)
    print(f"BRIEFE gelesen={len(besuche) - nicht} nicht_lesbar={nicht} mit_rho_text={len(rho)}")
    fz = format_zeilen({b["nr"] for b in rho})
    summe = {}
    for b in sorted(rho, key=lambda x: x["nr"]):
        n = b["nr"]
        kid = n[4:8] + "-" + n[8:]
        r = brief_auswerten(texte[n])
        lf = lauf(n)
        weg = "+".join(w for w, j in (("KI", r["ki"]), ("FMT", r["fmt"])) if j) or "sonst"
        stand = f"{b.get('st') or '-'}/{b.get('obl') or '-'}/{b.get('obg') or '-'}"
        if r["normal"]:
            urteil = "NORMALSATZ_DANEBEN"
        elif r["teile"] and r["mit_o"] >= r["teile"]:
            urteil = "ERSETZT_ALLE"
        elif r["mit_o"]:
            urteil = "ERSETZT_TEIL"
        elif r["sonst_osteo"]:
            urteil = "OSTEO_DIKTIERT"
        else:
            urteil = "KEIN_NORMALSATZ_KEIN_ERSATZ"
        summe[weg + ":" + urteil] = summe.get(weg + ":" + urteil, 0) + 1
        ls = ("-" if lf is None else
              f"n={lf['n']} v={lf.get('v')} pc={lf.get('pc')} um={lf.get('zeit')} rho_dikt={'ja' if lf.get('rho_diktiert') else 'nein'} "
              f"knochendichte_dikt={'ja' if lf.get('diktiert') else 'nein'} vorschlag_ki={'ja' if lf.get('md', {}).get('ki') else 'nein'} "
              f"vorschlag_teile={lf.get('md', {}).get('teile')} vorschlag_mit_o={lf.get('md', {}).get('mit_o')} "
              f"vorschlag_normal={lf.get('md', {}).get('normal')}") if (lf is None or lf.get("lesbar")) else f"n={lf['n']} unlesbar"
        print(f"FALL {kid} zeit={b.get('rt')} ab={'ja' if (b.get('rt') or '') >= AB else 'nein'} st={stand} "
              f"wer={(b.get('wer') or '-')[:3]} weg={weg} teile={r['teile']} mit_osteopen={r['mit_o']} "
              f"normalsaetze={r['normal']} teile_mit_normal={r['teile_mit_n']} sonst_osteo={r['sonst_osteo']} → {urteil}")
        print(f"  STRUKTUR {r['code']}")
        print(f"  LAUF {ls}")
        for name, ver, uhr, art in fz.get(n, []):
            print(f"  FMT {name} v{ver} {uhr} {art}")
    print("SUMME " + " ".join(f"{k}={v}" for k, v in sorted(summe.items())))
    print("KONTROLLE_FERTIG v1.0")


if __name__ == "__main__":
    main()
