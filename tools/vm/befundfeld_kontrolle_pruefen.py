"""Kontrolle Befundfeld-sicher (kaiscribe-befundfeld-sicher-n1-kontrolle, 23.11.2026) – Automaten-VM als rakauto, nur lesen.
Liest rakscribe.log (+ .1 … .5) unter X:\\KaiScribe\\Programm und X:\\RaKScribe sowie die Lauf-Dateien (nur nr/rechner/
benutzer/kaiscribe, nie Text). Ausgabe: Zähler, Uhrzeiten, Zeilenart, PC, Kürzel – Diktatnummern nur als A1, A2 …
  py -3.12 -X utf8 befundfeld_kontrolle_pruefen.py [--ab 2026-11-21] [--zeitleiste]
"""
import argparse
import collections
import glob
import json
import os
import re

WURZELN = [r"X:\KaiScribe", r"X:\RaKScribe"]
TEST_NR = "451898"
SICHER = re.compile(r"[^\w.,+:-]")
ZEILE = re.compile(r"^\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)\] (.*)$")

ARTEN = [
    ("REC", re.compile(r"^\[RECORD\] Aufnahme wird gestartet")),
    ("EINF_ZIEL", re.compile(r"^\[EINFÜGEN\] .*Diktat wird an Stelle")),
    ("EINF_PAUSE", re.compile(r"^\[EINFÜGEN\] In der Pause")),
    ("EINF_FERTIG", re.compile(r"^\[EINFÜGEN\] .*Zeichen an Stelle .* eingefügt")),
    ("EINF_FEHLER", re.compile(r"^\[EINFÜGEN\] Cursor-Stelle nicht lesbar")),
    ("BF_REC", re.compile(r"^\[BEFUNDFELD\] Record: (.*)$")),
    ("BF_ERG", re.compile(r"^\[BEFUNDFELD\] Ergänzung: (\d+) Zeichen")),
    ("RS_START", re.compile(r"^\[BEFUNDFELD\] Restructure \((\d+) Zeichen, (mit|ohne)")),
    ("RS_FERTIG", re.compile(r"^\[BEFUNDFELD\] Restructure fertig: (\d+)")),
    ("RS_FEHLER", re.compile(r"EXCEPTION - \[BEFUNDFELD\] Restructure|Restructure fehlgeschlagen")),
    ("RS_VERWORFEN", re.compile(r"Restructure verworfen")),
    ("RS_LEER", re.compile(r"Restructure: keine Änderung")),
    ("BF_UNDO", re.compile(r"^\[BEFUNDFELD\] Strg\+Z")),
    ("BF_CLEAR", re.compile(r"^\[BEFUNDFELD\] Clear all")),
    ("BF_RESET", re.compile(r"^\[BEFUNDFELD\] Reset")),
    ("CAS_AN", re.compile(r"^\[CAS\] Auftrag (\d+) \(([^)]*)\) angenommen( – Diktat läuft bzw\. Text steht schon da)?")),
    ("CAS_EOL", re.compile(r"^\[CAS\] EOL: Befund \((\d+) Zeichen\) an CAS-Diktat (\d+)")),
    ("LAUF", re.compile(r"^\[LAUF\] protokolliert: (\d+)_(\d{8})-(\d{6})")),
    ("PASTE", re.compile(r"^\[PASTE\]")),
    ("REC_ABBR", re.compile(r"^\[RECORD\] Start abgebrochen")),
    ("FEHLER", re.compile(r"Traceback|EXCEPTION|\bFEHLER\b|\bERROR\b")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", default="2026-11-21")
    ap.add_argument("--zeitleiste", action="store_true")
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--fenster", default="", help="TTHHMMSS-TTHHMMSS,…: alle Zeilen darin, maskiert (Tag + Kurztext)")
    ap.add_argument("--kompakt", action="store_true", help="nur Kopf + knappe Zeitleiste (Auswertung am Mac/Hetzner)")
    a = ap.parse_args()

    # Lauf-Dateien: Nr -> (rechner, benutzer, version) je Zeitpunkt
    lauf = {}
    for w in WURZELN:
        for p in glob.glob(os.path.join(w, "Daten", "laeufe", "*.json")):
            n = os.path.basename(p)
            m = re.match(r"(\d+)_(\d{8})-(\d{6})\.json$", n)
            if not m or m.group(2) < a.ab.replace("-", ""):
                continue
            if n in lauf:
                continue
            try:
                with open(p, encoding="utf-8-sig") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            lauf[n] = (m.group(1), SICHER.sub("", str(d.get("rechner") or "?")),
                       SICHER.sub("", str(d.get("benutzer") or "?")), SICHER.sub("", str(d.get("kaiscribe") or "?")))
    nr_pc = collections.defaultdict(set)
    nr_b = {}
    for nr, pc, b, v in lauf.values():
        nr_pc[nr].add(pc)
        nr_b[nr] = b
    vers = collections.Counter((v, pc) for nr, pc, b, v in lauf.values() if nr != TEST_NR)
    print("LAUFDATEIEN ab %s: %d (ohne Test %d)" % (a.ab, len(lauf), sum(vers.values())))
    print("LAUF_VERSION_PC " + " ".join(f"{v}@{pc}={k}" for (v, pc), k in sorted(vers.items())))

    # Logs
    dateien = []
    for w in WURZELN:
        for basis in (os.path.join(w, "Programm", "rakscribe.log"), os.path.join(w, "rakscribe.log")):
            for p in [basis] + [f"{basis}.{i}" for i in range(1, 10)]:
                if os.path.isfile(p):
                    dateien.append(p)
    zeilen = {}
    for p in dateien:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                inh = f.read().splitlines()
        except OSError:
            continue
        erst = next((ZEILE.match(z).group(1, 2) for z in inh if ZEILE.match(z)), None)
        letzt = next((ZEILE.match(z).group(1, 2) for z in reversed(inh) if ZEILE.match(z)), None)
        print(f"LOG {p} zeilen={len(inh)} von={erst} bis={letzt}")
        for i, z in enumerate(inh):
            m = ZEILE.match(z)
            if m and m.group(1) >= a.ab:
                zeilen.setdefault((m.group(1), m.group(2), z), (p, i))   # gleiche Zeile in zwei Logs nur einmal
    ev = []
    for (tg, uh, z), (p, i) in sorted(zeilen.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[1][0], kv[1][1])):
        msg = ZEILE.match(z).group(3)
        for art, rx in ARTEN:
            m = rx.search(msg)
            if m:
                ev.append((tg, uh, art, m.groups(), msg))
                break

    alias = {}

    def al(nr):
        if nr == TEST_NR:
            return "TEST"
        if nr not in alias:
            alias[nr] = "A%d" % (len(alias) + 1)
        return alias[nr]

    zaehl = collections.Counter(e[2] for e in ev)
    print("ZAEHLER " + " ".join(f"{k}={v}" for k, v in sorted(zaehl.items())))
    modi = collections.Counter(e[3][0] for e in ev if e[2] == "BF_REC")
    print("BF_REC_MODI " + " | ".join(f"{k}={v}" for k, v in sorted(modi.items())))
    for e in ev:
        if e[2] in ("FEHLER", "RS_FEHLER", "RS_VERWORFEN", "EINF_FEHLER"):
            print(f"FEHLERZEILE {e[0]} {e[1]} {e[2]} {re.sub(r'[0-9]{5,}', '<nr>', e[4])[:90]}")

    if a.fenster:
        for _tg, _uh, art, g, _m in ev:               # Aliase in derselben Reihenfolge wie --kompakt
            if art in ("CAS_AN", "LAUF"):
                al(g[0])
            elif art == "CAS_EOL":
                al(g[1])
        fen = [tuple(x.split("-")) for x in a.fenster.split(",") if "-" in x]
        for (tg, uh, z), _ in sorted(zeilen.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[1][0], kv[1][1])):
            k = tg[8:] + uh.replace(":", "")
            if not any(v <= k <= b for v, b in fen):
                continue
            msg = ZEILE.match(z).group(3)
            for nr in re.findall(r"\d{5,}", msg):
                msg = msg.replace(nr, alias.get(nr, "TEST" if nr == TEST_NR else "<z>"))
            tag = re.match(r"^(\[[^\]]{1,20}\]|EXCEPTION)?", msg).group(0) or "-"
            if tag in ("[SENF]",) or msg.startswith("[CAS] Hinweis") or msg.startswith("[CAS] Leistungen"):
                msg = tag + " …"
            msg = re.sub(r"„[^“]*“|\"[^\"]*\"", "„…“", msg)     # Zitate (evtl. Titel/Text) weg
            print(f"{k} {msg[:110]}")
        return
    if a.kompakt:
        kurz = {"Neuer Befund": "N", "Ergänzung": "E", "Neuer Befund (IB-Lab-Gerüst)": "G"}
        for tg, uh, art, g, msg in ev:
            if art == "FEHLER":
                continue
            if art == "BF_REC":
                m0 = g[0].replace(" (an Cursor-Stelle)", "")
                z = kurz.get(m0, m0[:8]) + ("@" if "Cursor" in g[0] else "")
            elif art == "CAS_AN":
                z = f"{al(g[0])} {g[1]} {'T' if g[2] else '-'} {','.join(sorted(nr_pc.get(g[0], {'?'})))}"
            elif art == "CAS_EOL":
                z = f"{al(g[1])} {g[0]}"
            elif art == "LAUF":
                z = f"{al(g[0])} {','.join(sorted(nr_pc.get(g[0], {'?'})))}"
            elif art in ("BF_ERG", "RS_FERTIG"):
                z = g[0]
            elif art == "RS_START":
                z = f"{g[0]} {g[1]}"
            else:
                z = ""
            print(f"{tg[8:]}{uh.replace(':', '')} {art} {z}".rstrip())
        return

    # Ablauf: Fälle zwischen CAS_AN und CAS_EOL; Befundfeld-Ereignisse dazwischen (Log ist PC-gemischt → Überlappung melden)
    offen = {}          # nr -> dict
    faelle = []
    letzte_rec = None
    for tg, uh, art, g, msg in ev:
        t = f"{tg} {uh}"
        if art == "CAS_AN":
            nr = g[0]
            offen[nr] = {"nr": nr, "b": g[1], "an": t, "schon_text": bool(g[2]), "ev": [], "eol": None}
        elif art == "CAS_EOL":
            nr = g[1]
            f = offen.pop(nr, None) or {"nr": nr, "b": nr_b.get(nr, "?"), "an": None, "schon_text": False, "ev": []}
            f["eol"] = t
            f["ueberlapp"] = sorted(al(x) for x in offen)
            faelle.append(f)
        elif art in ("BF_REC", "BF_ERG", "RS_START", "RS_FERTIG", "RS_LEER", "EINF_ZIEL", "EINF_PAUSE",
                     "EINF_FERTIG", "BF_UNDO", "BF_CLEAR", "BF_RESET", "LAUF", "REC_ABBR"):
            kurz = art if art != "BF_REC" else "REC:" + {"Neuer Befund": "NEU", "Ergänzung": "ERG"}.get(
                g[0].replace(" (an Cursor-Stelle)", ""), g[0][:20]) + ("@Cursor" if "Cursor" in g[0] else "")
            if art == "LAUF":
                kurz = "LAUF:" + al(g[0])
            for f in offen.values():
                f["ev"].append((uh, kurz))
            if not offen:
                faelle_ohne = faelle  # noqa
            letzte_rec = (t, kurz)
    for f in offen.values():
        f["eol"] = None
        f["ueberlapp"] = []
        faelle.append(f)

    print("FAELLE (CAS angenommen … EOL), Nr als Alias, Zeitleiste der Befundfeld-Zeilen dazwischen:")
    auff = []
    for f in sorted(faelle, key=lambda f: f["an"] or f["eol"] or ""):
        nr = f["nr"]
        pcs = ",".join(sorted(nr_pc.get(nr, {"?"})))
        evs = f["ev"]
        recs = [k for _, k in evs if k.startswith("REC:")]
        laeufe_fremd = sorted({k[5:] for _, k in evs if k.startswith("LAUF:") and k[5:] != al(nr)})
        merk = []
        if recs and recs[0].startswith("REC:ERG") and not f["schon_text"]:
            merk.append("ERSTES_DIKTAT_ERGAENZUNG_OHNE_TEXT_HINWEIS")
        if recs and recs[0].startswith("REC:ERG") and f["schon_text"]:
            merk.append("ERGAENZUNG_AUF_STEHENDEN_TEXT")
        if laeufe_fremd and not f["ueberlapp"]:
            merk.append("FREMDER_LAUF_IM_FALL")
        print(f"  {al(nr)} b={f['b']} pc={pcs} an={f['an']} eol={f['eol']} schon_text={'ja' if f['schon_text'] else 'nein'}"
              f" ueberlapp={','.join(f['ueberlapp']) or '-'} recs={' '.join(recs) or '-'}"
              + (f" MERK={'+'.join(merk)}" if merk else ""))
        if a.zeitleiste:
            print("     " + " ".join(f"{u[:5]}{k}" for u, k in evs))
        if merk:
            auff.append((al(nr), merk))
    print("AUFFAELLIG %d: %s" % (len(auff), "; ".join(f"{x}:{'+'.join(m)}" for x, m in auff) or "-"))

    # Peters Muster: Record ohne [EINFÜGEN]-Zeile, dann neuer Befund (je Benutzer/Tag) – zeitlich nach Benutzer kp
    print("RECORDS je Kürzel (aus offenem CAS-Fall):")
    je = collections.Counter()
    for f in faelle:
        for _, k in f["ev"]:
            if k.startswith("REC:"):
                je[(f["b"], k)] += 1
    for (b, k), n in sorted(je.items()):
        print(f"  {b} {k}={n}")
    # Record-Zeilen außerhalb eines CAS-Falls (F10 ohne CAS)
    print("ZEITLEISTE ALLE RECORD/EINFÜGEN/ERG/RS/EOL (Uhrzeit, Art; PC über Lauf-Datei wenn eindeutig):")
    for tg, uh, art, g, msg in ev:
        if art in ("BF_REC", "EINF_ZIEL", "EINF_PAUSE", "EINF_FERTIG", "BF_ERG", "RS_START", "RS_FERTIG", "RS_LEER",
                   "CAS_AN", "CAS_EOL", "LAUF", "BF_UNDO", "BF_CLEAR", "BF_RESET", "REC_ABBR", "PASTE"):
            zus = ""
            if art == "BF_REC":
                zus = g[0]
            elif art == "CAS_AN":
                zus = f"{al(g[0])} {g[1]}{' schon_text' if g[2] else ''} pc={','.join(sorted(nr_pc.get(g[0], {'?'})))}"
            elif art == "CAS_EOL":
                zus = f"{al(g[1])} {g[0]}Z"
            elif art == "LAUF":
                zus = f"{al(g[0])} pc={','.join(sorted(nr_pc.get(g[0], {'?'})))}"
            elif art == "BF_ERG":
                zus = f"{g[0]}Z"
            elif art == "RS_START":
                zus = f"{g[0]}Z {g[1]}"
            if a.alle:
                print(f"  {tg[5:]} {uh} {art} {zus}")


if __name__ == "__main__":
    main()
