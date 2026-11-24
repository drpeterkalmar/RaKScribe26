#!/usr/bin/env python3
"""chirp-fachwortliste-n1: Messung am MAC starten – das Rechnen und alle Google-Aufrufe laufen auf der VM.

  python3 tools/chirp_sm/messen_mac.py ohne,sm5,sm10 [max_minuten]

Holt einen 1-h-Token des TESTPROJEKTS (tools/testkosten.py, Dienstkonto rakscribe-test), prüft die Kostengrenzen,
lädt stt.py + phrases.json + Mess-Skript auf die VM (tools/mac/chirp_vm.py, als rakauto), bucht danach die wirklich
gesendeten Minuten im Testkosten-Buch. Ausgabe nur Summen (siehe cfw_messen.py).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import testkosten as tk  # noqa: E402

DL = os.path.expanduser("~/.hermes/work/chirp-fachwortliste-n1/dl/de_50k.txt")
SM = os.path.expanduser("~/dev/ris-mods/speechmagic_inventur/sm.py")


def main():
    bed = sys.argv[1] if len(sys.argv) > 1 else "ohne,sm5"
    max_min = sys.argv[2] if len(sys.argv) > 2 else "200"
    # Die allgemeine Google-Testsperre (Peter 14.11.2026, GCP_MONAT_USD = 0) bleibt unverändert. Diese eine Messung hat
    # Peter am 24.11.2026 im Auftrag chirp-fachwortliste-n1 ausdrücklich freigegeben: „Nur Projekt rakscribe-test,
    # Kostendeckel 5 € für die Messung“. Deckel hier: Job-Summe im Testkosten-Buch ≤ 5 € (≈ 5,8 $ bei 0,86 €/$).
    summe = tk.BUCH.summe_job(tk.KONTO_GCP_TEST)
    if summe > 5.0 / 0.86 - 1.0:
        sys.exit("ABBRUCH: Job hat schon %.2f $ Google-Testkosten (Deckel 5 €)" % summe)
    print("Job-Summe Google-Test bisher %.2f $ (Deckel 5 €)" % summe)
    with tempfile.TemporaryDirectory() as t:
        tokf = os.path.join(t, "tok.json")
        with open(tokf, "w") as f:
            json.dump({"projekt": tk.projekt(), "token": tk.bearer()}, f)
        os.chmod(tokf, 0o600)
        cmd = [sys.executable, os.path.join(ROOT, "tools", "mac", "chirp_vm.py"),
               os.path.join(ROOT, "tools", "vm", "chirp_fachwort", "cfw_messen.py"),
               os.path.join(ROOT, "source_code", "stt.py"), os.path.join(ROOT, "phrases.json"), SM, DL, tokf,
               os.path.join(ROOT, "source_code", "misheard.py"), os.path.join(ROOT, "misheard_words.json"),
               "--", bed, max_min]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.environ.get("FRIST", "1500")) + 300,
                           env=dict(os.environ))
    aus = r.stdout + r.stderr
    keep = re.compile(r"^(FAELLE|LAUF|GRUPPE|ERG|AENDERUNG|JEFALL|ERGMH|PHRASEN|MINUTEN_GESENDET|CFW|PY_RC|ALSKONTO|[0-9]+s$|Traceback|"
                      r"  File|[A-Za-z]+Error)")
    zeilen = [re.sub(r"^([A-Za-z]+Error).*", r"\1", z) for z in aus.splitlines() if keep.match(z)]
    print("\n".join(zeilen))
    m = re.search(r"MINUTEN_GESENDET ([0-9.]+)", aus)
    if m and float(m.group(1)) > 0:
        minuten = float(m.group(1))
        tk.BUCH.buchen("stt", "chirp_3", minuten * tk.STT_USD_JE_MINUTE, 0, 0, 0)
        print("GEBUCHT %.2f min = %.2f $ (Listenpreis) im Testkosten-Buch" % (minuten, minuten * tk.STT_USD_JE_MINUTE))
    sys.exit(0 if "PY_RC=0" in aus else 1)


if __name__ == "__main__":
    main()
