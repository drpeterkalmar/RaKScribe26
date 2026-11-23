"""Kontrolle Senf-Anzeige (kaiscribe-senf-anzeige-kontrolle, 23.11.2026) – läuft auf der Automaten-VM als rakauto, nur lesen.
Ausgabe: nur Zähler, Zustände, Uhrzeiten, Versionen, Ja/Nein – nie Nr, Name oder Text.
  py -3.12 -X utf8 senf_kontrolle_pruefen.py [--tag JJJJMMTT] [--ab HH:MM]
"""
import argparse
import collections
import glob
import json
import os
import re
import datetime

WURZELN = [r"X:\KaiScribe", r"X:\RaKScribe"]
SICHER = re.compile(r"[^\w.,+:-]")
SENF_MUSTER = re.compile(r"\bRH\s?\d{1,3}\s·\s|\[SENF\]|Senf", re.I)


def maske(t, n=120):
    t = re.sub(r"\d{5,}", "<nr>", str(t))
    return t.strip()[:n]


def uhr_von(z):
    m = re.match(r"^\D*(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d)", z)
    return (m.group(1), m.group(2)) if m else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="20261123")
    ap.add_argument("--ab", default="07:00")
    a = ap.parse_args()
    tag = f"{a.tag[:4]}-{a.tag[4:6]}-{a.tag[6:]}"

    # 1 Lauf-Dateien
    gesehen = {}
    for w in WURZELN:
        for p in glob.glob(os.path.join(w, "Daten", "laeufe", f"*_{a.tag}-*.json")):
            gesehen.setdefault(os.path.basename(p), p)
    vers, pcs, kp_laeufe = collections.Counter(), collections.Counter(), []
    senf_in_lauf = 0
    for n, p in sorted(gesehen.items()):
        if n.startswith("451898"):
            continue
        try:
            with open(p, encoding="utf-8-sig") as f:
                raw = f.read()
            d = json.loads(raw)
        except (OSError, ValueError):
            print("LAUF_UNLESBAR")
            continue
        vers[SICHER.sub("", str(d.get("kaiscribe") or "?"))] += 1
        pcs[SICHER.sub("", str(d.get("rechner") or "?"))] += 1
        if re.search(r"\[SENF\]|RH\s?\d{1,3}\s·\s", raw):
            senf_in_lauf += 1
        kp_laeufe.append(n.split("_")[0])
    print("LAEUFE echt=%d senf_text_in_lauf_dateien=%d" % (sum(vers.values()), senf_in_lauf))
    print("LAEUFE_VERSION " + " ".join(f"{k}={v}" for k, v in sorted(vers.items())))
    print("LAEUFE_PC " + " ".join(f"{k}={v}" for k, v in sorted(pcs.items())))

    # 2 Logs
    logs = []
    for w in WURZELN:
        logs += glob.glob(os.path.join(w, "Programm", "rakscribe.log")) + glob.glob(os.path.join(w, "rakscribe.log"))
    logs = sorted(set(logs))
    anz_an, zust, fehler, w10013, eset = {}, collections.Counter(), [], 0, 0
    fertig_dauer = []
    benutzer_an = collections.Counter()
    zust_b = collections.Counter()
    senf_nrs_ohne_an = set()
    for lp in logs:
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(lp)).strftime("%Y-%m-%d %H:%M")
        print(f"LOG {lp} geaendert={mt}")
        beginn = {}
        try:
            fh = open(lp, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for z in fh:
                tg, uh = uhr_von(z)
                if tg != tag or uh < a.ab + ":00":
                    continue
                if re.search(r"Traceback|\bFEHLER\b|ERROR|Exception", z):
                    fehler.append(maske(z))
                if "10013" in z:
                    w10013 += 1
                if re.search(r"ESET", z):
                    eset += 1
                m = re.search(r"\[SENF\] Auftrag (\d+): Anzeige an \((\w+)\)", z)
                if m:
                    benutzer_an[m.group(2)] += 1
                    beginn[m.group(1)] = uh
                    anz_an[m.group(1)] = m.group(2)
                    continue
                m = re.search(r"\[SENF\] (\d+): (laeuft|läuft|fertig|kein|Auftrag zu)", z)
                if m:
                    zst = m.group(2).replace("ä", "ae")
                    zust[zst] += 1
                    zust_b[(anz_an.get(m.group(1), "?"), zst)] += 1
                    if zst == "fertig" and m.group(1) in beginn:
                        t0 = datetime.datetime.strptime(beginn[m.group(1)], "%H:%M:%S")
                        t1 = datetime.datetime.strptime(uh, "%H:%M:%S")
                        fertig_dauer.append(int((t1 - t0).total_seconds()))
                    if m.group(1) not in anz_an:
                        senf_nrs_ohne_an.add(m.group(1))
                    continue
                if "[SENF]" in z:
                    zust["sonst"] += 1
                    if "noch nicht da" in z:
                        zust_b[("alle", "zu_ohne_senf")] += 1
    print("SENF_ANZEIGE_AN " + " ".join(f"{k}={v}" for k, v in sorted(benutzer_an.items())) + " faelle=%d" % len(anz_an))
    print("SENF_ZUSTAND " + " ".join(f"{k}={v}" for k, v in sorted(zust.items())))
    print("SENF_ZUSTAND_JE_KUERZEL " + " ".join(f"{k[0]}:{k[1]}={v}" for k, v in sorted(zust_b.items())))
    print("SENF_OHNE_ANZEIGE_AN=%d" % len(senf_nrs_ohne_an))
    print("SENF_FERTIG_SEKUNDEN " + (",".join(map(str, fertig_dauer)) or "-"))
    print("LOG_FEHLER=%d WINERROR10013=%d ESET=%d" % (len(fehler), w10013, eset))
    for z in collections.Counter(fehler).most_common(6):
        print("LOG_FEHLER_ZEILE %dx %s" % (z[1], z[0]))

    # 2b Senf-Text in <Nr>.rakscribe.txt der kp-Fälle (nur Zähler)
    ja = nein = fehlt = 0
    for w in WURZELN:
        for nr in anz_an:
            if anz_an[nr] != "kp":
                continue
            kand = glob.glob(os.path.join(w, "**", nr + ".rakscribe.txt"), recursive=True)[:1]
            if not kand:
                continue
            try:
                t = open(kand[0], encoding="utf-8-sig", errors="replace").read()
            except OSError:
                fehlt += 1
                continue
            if SENF_MUSTER.search(t):
                ja += 1
            else:
                nein += 1
    print("KP_BRIEF_MIT_SENF ja=%d nein=%d unlesbar=%d" % (ja, nein, fehlt))

    # 3 VM-Seite
    for p in (r"C:\RaK\opus_senf\log\takt_letzt.txt",):
        if os.path.exists(p):
            print("TAKT_LETZT geaendert=%s zeilen=%d" % (datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%H:%M"),
                  sum(1 for _ in open(p, errors="replace"))))
    sl = glob.glob(r"C:\RaK\opus_senf\log\senf_202611.log")
    takt_n, takt_zeilen, fehl = [], 0, 0
    for p in sl:
        for z in open(p, encoding="utf-8", errors="replace"):
            if a.tag[:4] + "-" + a.tag[4:6] + "-" + a.tag[6:] not in z and a.tag not in z:
                continue
            if "ablage_takt" in z:
                takt_zeilen += 1
                m = re.search(r"\bn\W+(\d+)", z)
                if m:
                    takt_n.append(int(m.group(1)))
            if "ablage_fehler" in z:
                fehl += 1
    print("VM_ABLAGE_TAKT zeilen=%d n_max=%s n_ab1=%d ablage_fehler=%d" % (takt_zeilen, max(takt_n) if takt_n else "-",
          sum(1 for x in takt_n if x >= 1), fehl))
    zahlen = {}
    for w in WURZELN:
        ds = glob.glob(os.path.join(w, "Daten", "senf", "*.json"))
        zahlen[w] = len(ds)
    print("SENF_ABLAGE " + " ".join(f"{k}={v}" for k, v in zahlen.items()))
    for w in WURZELN:
        ds = glob.glob(os.path.join(w, "Daten", "senf", "*.json"))
        st = collections.Counter()
        for p in ds:
            try:
                d = json.load(open(p, encoding="utf-8-sig"))
                st[str(d.get("status", "?"))] += 1
            except (OSError, ValueError):
                st["unlesbar"] += 1
        print("SENF_ABLAGE_STATUS %s %s" % (w, " ".join(f"{k}={v}" for k, v in sorted(st.items()))))
    print("SENF_KONTROLLE_ENDE")


if __name__ == "__main__":
    main()
