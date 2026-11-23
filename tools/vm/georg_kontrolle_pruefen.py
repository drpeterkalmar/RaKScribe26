"""Montags-Kontrolle Georgs Diktiertag (kaiscribe-georg-2011-kontrolle, 23.11.2026) – läuft auf der Automaten-VM als
rakauto (X: nur lesen; keine Datenbank, keine Bilder). Gibt nur Zähler, Kategorien, Uhrzeiten und Versionen aus – nie Nr,
Benutzer oder Befundtext.

  py -3.12 -X utf8 georg_kontrolle_pruefen.py [--tag JJJJMMTT] [--ab HH:MM] [--version 3.20.5]

Teile:
  LAEUFE   Lauf-Dateien des Tages (X:\\KaiScribe\\Daten\\laeufe und X:\\RaKScribe\\Daten\\laeufe): je PC/Version, Testpatient
           451898 getrennt gezählt
  FALL     je echtem Lauf mit Kategorie (FROG, MEHRFACH, KNIE_BDS, GWS_AP, RHO) Ja/Nein-Prüfungen
  LOG      rakscribe.log: Fehler-/Traceback-Zeilen seit --ab (Zähler + Anfang, Ziffern maskiert), WinError 10013, Token
  BRUECKE  bruecke_<PC>.log: Versionen seit dem Tag, „[ablage] … zurückgestellt“, ok=True/False
"""
import argparse
import collections
import glob
import json
import os
import re

TEST_NR = "451898"
SICHER = re.compile(r"[^\w.,+:-]")
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern"
RHO = "Opportunistisches Knochendichtescreening"
TITEL_AUS = re.compile(r"^(?:#+\s*)?(Befund|Ergebnis|Beurteilung|Anmerkung)\s*:?\s*$", re.I)
TITEL_Z = collections.Counter()
WURZELN = [r"X:\KaiScribe", r"X:\RaKScribe"]


def ja(b):
    return "ja" if b else "nein"


def maske(t, n=120):
    t = re.sub(r"\d{5,}", "<nr>", str(t))
    t = re.sub(r"\b[A-ZÄÖÜ][a-zäöüß]+,\s*[A-ZÄÖÜ][a-zäöüß]+\b", "<name>", t)
    return t.strip()[:n]


def bloecke(rep):
    """[(Titel, Befund, Ergebnis)] – Titel = Zeile vor „Befund“ (mit oder ohne „## “)."""
    zeilen = [z.rstrip() for z in rep.splitlines()]
    out = []
    i = 0
    while i < len(zeilen):
        z = zeilen[i].strip()
        m = TITEL_AUS.match(z)
        if m and m.group(1).lower() == "befund":
            # Titel = letzte nicht leere Zeile davor
            j = i - 1
            while j >= 0 and not zeilen[j].strip():
                j -= 1
            titel = re.sub(r"^#+\s*", "", zeilen[j].strip()) if j >= 0 else ""
            bef, erg, k, teil = [], [], i + 1, "b"
            while k < len(zeilen):
                zk = zeilen[k].strip()
                mk = TITEL_AUS.match(zk)
                if mk and mk.group(1).lower() == "befund":
                    break
                if mk and mk.group(1).lower() in ("ergebnis", "beurteilung"):
                    teil = "e"
                elif zk:
                    (bef if teil == "b" else erg).append(zk)
                k += 1
            # letzte Zeile von erg kann der nächste Titel sein
            if k < len(zeilen) and (erg or bef):
                (erg if erg else bef).pop()
            out.append((titel, " ".join(bef), " ".join(erg)))
            i = k
        else:
            i += 1
    return out


def laeufe(tag):
    gesehen = {}
    for w in WURZELN:
        for p in glob.glob(os.path.join(w, "Daten", "laeufe", f"*_{tag}-*.json")):
            gesehen.setdefault(os.path.basename(p), p)
    return [gesehen[k] for k in sorted(gesehen, key=lambda n: n.split("_", 1)[1])]


def fall_pruefen(d, uhr, pc, ks):
    rep = str(d.get("ergebnis_vorschlag") or "")
    diktat = str(d.get("diktat") or d.get("stt_roh") or "").lower()
    vorl = [str(v) for v in d.get("vorlagen") or []]
    mods = [str(x).split()[0].upper() for x in d.get("ibl_module") or [] if str(x).split()]
    bl = bloecke(rep)
    titel = [t for t, _b, _e in bl]
    for t in titel:
        TITEL_Z[maske(t, 60)] += 1
    kopf = f"FALL {uhr} rechner={pc} kaiscribe={ks}"
    kat = []
    if "SQUIRREL" in mods:
        print(f"{kopf} kat=SQUIRREL module={'+'.join(mods)} titel={'|'.join(maske(t, 40) for t in titel)}")
    if "FROG" in mods:
        kat.append("FROG")
        print(f"{kopf} kat=FROG module={'+'.join(mods)} ibl_zeilen={int(d.get('ibl_zeilen') or 0)} "
              f"anmerkung={ja('Anmerkung:' in rep)} schluss={ja(SCHLUSS in rep)} "
              f"ohne_diagnose_im_text={ja(re.search(r'ohne (?:Diagnose|Pathologie)', rep, re.I))}")
    echte = [t for t in titel if t and RHO not in t]
    if len(vorl) >= 2 or len(echte) >= 2:
        kat.append("MEHRFACH")
        rho_letzt = bool(titel) and RHO in titel[-1]
        print(f"{kopf} kat=MEHRFACH vorlagen={len(vorl)} bloecke={len(bl)} titel_je_teil={ja(all(titel))} "
              f"module={'+'.join(mods) or '-'} lama={ja('LAMA' in mods)} "
              f"traglinie={ja('Traglinie des Ganzbeines' in rep)} rho={ja(RHO in rep)} rho_letzter_block={ja(rho_letzt)}")
    elif RHO in rep:
        kat.append("RHO")
        print(f"{kopf} kat=RHO bloecke={len(bl)} rho_letzter_block={ja(bool(titel) and RHO in titel[-1])} "
              f"rho_diktiert={ja(re.search(r'rho|ro score|roskore', diktat))}")
    for t, b, e in bl:
        tl = t.lower()
        if "knie" in tl and ("beid" in tl or "bds" in tl):
            kat.append("KNIE_BDS")
            el = e.lower()
            r, li = el.find("rechts"), el.find("links")
            print(f"{kopf} kat=KNIE_BDS stellung_zuerst={ja(re.match(r'(?:Normale )?(?:Form und )?Stellung|Regelrechte Stellung|Normale', b))} "
                  f"beginnt_im_uebrigen={ja(b.lower().startswith('im übrigen'))} "
                  f"ergebnis_rechts_vor_links={'beide fehlen' if r < 0 and li < 0 else ja(r >= 0 and (li < 0 or r < li))} "
                  f"ki_punkt={ja(re.search(r'(?:^|[.\s])KI:', e))}")
        if "wirbelsäule" in tl and ("a.-p" in tl or "a.p" in tl or "ganz" in tl):
            kat.append("GWS_AP")
            print(f"{kopf} kat=GWS_AP titel_ap={ja('a.-p' in tl or 'a.p' in tl)} "
                  f"beschriftung={ja('Wirbelsäule:' in b)} normale_stellung={ja('Normale Stellung' in b)} "
                  f"skoliose_im_text={ja('skolio' in b.lower())} skoliose_diktiert={ja('skolio' in diktat)} "
                  f"squirrel={ja('SQUIRREL' in mods)} seitausbiegung={ja('seitausbiegung' in b.lower())}")
    return kat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="20261123")
    ap.add_argument("--ab", default="07:00")
    ap.add_argument("--version", default="3.20.5")
    a = ap.parse_args()
    tagstr = f"{a.tag[:4]}-{a.tag[4:6]}-{a.tag[6:]}"

    # ── Läufe ──
    pcs, vers, kats, mods_z = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    test = 0
    dateien = laeufe(a.tag)
    print("LAEUFE_ORDNER " + " ".join(f"{w}={len(glob.glob(os.path.join(w, 'Daten', 'laeufe', f'*_{a.tag}-*.json')))}"
                                      for w in WURZELN))
    letzte = ""
    for p in dateien:
        n = os.path.basename(p)
        m = re.match(r"^(\d+)_(\d{8})-(\d{4})", n)
        if not m:
            continue
        uhr = f"{m.group(3)[:2]}:{m.group(3)[2:]}"
        try:
            with open(p, encoding="utf-8-sig") as f:
                d = json.load(f)
        except (OSError, ValueError):
            print(f"LAUF_UNLESBAR {uhr}")
            continue
        if m.group(1).startswith(TEST_NR):
            test += 1
            continue
        pc = SICHER.sub("", str(d.get("rechner") or "?"))
        ks = SICHER.sub("", str(d.get("kaiscribe") or "?"))
        pcs[pc] += 1
        vers[ks] += 1
        letzte = uhr
        for x in d.get("ibl_module") or []:
            if str(x).split():
                mods_z[str(x).split()[0].upper()] += 1
        for k in fall_pruefen(d, uhr, pc, ks):
            kats[k] += 1
    print("TITEL " + " | ".join(f"{k}={v}" for k, v in TITEL_Z.most_common(40)))
    print(f"LAEUFE echt={sum(pcs.values())} test451898={test} letzter={letzte or '-'}")
    print("LAEUFE_PC " + " ".join(f"{k}={v}" for k, v in sorted(pcs.items())))
    print("LAEUFE_VERSION " + " ".join(f"{k}={v}" for k, v in sorted(vers.items())))
    print("LAEUFE_MODULE " + " ".join(f"{k}={v}" for k, v in sorted(mods_z.items())))
    print("KATEGORIEN " + " ".join(f"{k}={kats.get(k, 0)}" for k in ("FROG", "MEHRFACH", "RHO", "KNIE_BDS", "GWS_AP")))

    # ── rakscribe.log ──
    kandidaten = []
    for w in WURZELN:
        for muster in ("*.log", os.path.join("Programm", "*.log"), os.path.join("Daten", "*.log"), os.path.join("Daten", "protokolle", "*.log"),
                       os.path.join("Daten", "logs", "*.log"), os.path.join("logs", "*.log")):
            kandidaten += [x for x in glob.glob(os.path.join(w, muster)) if not os.path.basename(x).startswith("bruecke_")]
    print("LOG_DATEIEN " + " ".join(f"{x}:{os.path.getsize(x)}" for x in kandidaten))
    for lp in kandidaten:
            if os.path.getsize(lp) == 0:
                continue
            st = os.stat(lp)
            fehler, tb, w10013, token, rot, start = [], 0, 0, 0, collections.Counter(), collections.Counter()
            aktiv = False
            try:
                with open(lp, encoding="utf-8", errors="replace") as f:
                    for z in f:
                        mz = re.match(r"^\[?(\d{4}-\d\d-\d\d) (\d\d:\d\d)", z)
                        if mz:
                            aktiv = mz.group(1) == tagstr and mz.group(2) >= a.ab
                        if not aktiv:
                            continue
                        if "Traceback" in z:
                            tb += 1
                        if "10013" in z:
                            w10013 += 1
                        if re.search(r"token", z, re.I) and re.search(r"fehl|error|ungültig|invalid|abgelaufen", z, re.I):
                            token += 1
                        if re.search(r"\b(ERROR|FEHLER|Fehler|Exception|CRITICAL)\b", z) and "Traceback" not in z:
                            fehler.append(z)
                        mr = re.search(r"\[IBL\] Hinweise:.*rot \(Prüfzeile\): (\d+)", z)
                        if mr:
                            rot[mr.group(1)] += 1
                            if mr.group(1) != "0":
                                mm = re.search(r"Hinweise: (\d+)(?: \(([\w, ]+)\))?", z)
                                print(f"IBL_ROT {mz.group(2) if mz else '?'} hinweise={mm.group(1) if mm else '?'} "
                                      f"module={SICHER.sub('', (mm.group(2) or '-') if mm else '?')} rot={mr.group(1)}")
                        ms = re.search(r"\[start\] v([\d.]+)", z)
                        if ms:
                            start[ms.group(1)] += 1
            except OSError as e:
                print(f"LOG_UNLESBAR {lp} {e.__class__.__name__}")
                continue
            print(f"LOG {lp} groesse={st.st_size} geaendert={__import__('time').strftime('%Y-%m-%d %H:%M', __import__('time').localtime(st.st_mtime))} "
                  f"fehler={len(fehler)} traceback={tb} winerror10013={w10013} token_fehler={token} "
                  f"ibl_rot={dict(rot)} starts={dict(start)}")
            arten = collections.Counter(maske(re.sub(r"^\S+ \S+\s*", "", z), 120) for z in fehler)
            for t, n in arten.most_common(12):
                print(f"LOG_FEHLER n={n} {t}")

    # ── Brücke ──
    for w in WURZELN:
        for p in sorted(glob.glob(os.path.join(w, "Daten", "protokolle", "bruecke_*.log"))):
            pc = SICHER.sub("", os.path.basename(p)[8:-4])
            v, zur, okt, okf, fe = collections.Counter(), 0, 0, 0, 0
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    for z in f:
                        if not z.startswith(tagstr):
                            continue
                        ms = re.search(r"\[start\] v([\d.]+)", z)
                        if ms:
                            v[ms.group(1)] += 1
                        if "[ablage]" in z and "zurückgestellt" in z:
                            zur += 1
                        okt += z.count("ok=True")
                        okf += z.count("ok=False")
                        if re.search(r"Traceback|\bFEHLER\b|\bERROR\b", z):
                            fe += 1
            except OSError:
                continue
            letzte_v = "?"
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    for z in f:
                        ms = re.search(r"\[start\] v([\d.]+)", z)
                        if ms:
                            letzte_v = ms.group(1)
            except OSError:
                pass
            print(f"BRUECKE {w[3:]} pc={pc} version_zuletzt={letzte_v} starts_heute={dict(v)} zurueckgestellt={zur} "
                  f"ok_true={okt} ok_false={okf} fehler={fe}")


if __name__ == "__main__":
    main()
