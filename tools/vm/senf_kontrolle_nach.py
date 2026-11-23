"""Senf-Kontrolle kp-Verlauf (23.11.2026), nur lesen: je kp-Auftrag Zustandsfolge, Nr nur als laufende Nummer."""
import re
lp = r"X:\KaiScribe\Programm\rakscribe.log"
zeilen = [z.rstrip() for z in open(lp, encoding="utf-8", errors="replace") if "2026-11-23" in z[:30] and "[SENF]" in z]
kp = {}
for z in zeilen:
    m = re.search(r"\[SENF\] Auftrag (\d+): Anzeige an \(kp\)", z)
    if m:
        kp[m.group(1)] = len(kp) + 1
n_kp = {nr: i for nr, i in kp.items()}
for z in zeilen:
    m = re.search(r"(\d\d:\d\d:\d\d).*\[SENF\] (?:Auftrag )?(\d+)[: ]", z)
    if m and m.group(2) in n_kp:
        print("KP%d %s %s" % (n_kp[m.group(2)], m.group(1), re.sub(r"\d{5,}", "<nr>", z.split("[SENF]", 1)[1])[:110]))
import os, json
print("--- Ablage zu den kp-Aufträgen")
for nr, i in n_kp.items():
    for w in (r"X:\KaiScribe", r"X:\RaKScribe"):
        p = os.path.join(w, "Daten", "senf", nr + ".json")
        if os.path.exists(p):
            try:
                d = json.load(open(p, encoding="utf-8-sig"))
                print("KPABL%d %s status=%s befund=%s zeit=%s eintraege=%s" % (i, w[-9:], d.get("status"), d.get("befund"), str(d.get("zeitpunkt") or d.get("zeit"))[-8:], len(d.get("eintraege") or [])))
            except Exception as e:
                print("KPABL%d unlesbar" % i)
        else:
            print("KPABL%d %s keine_datei" % (i, w[-9:]))
