"""Gate (stt-mistral-vergleich-n1): Mess-Harness Voxtral vs. chirp_3 – Kennzahlen, Kostendeckel, Datenschutz-Sperre,
keine Google-Aufrufe. Ohne Netz. Aufruf: python3 tests/offline/test_voxtral_ab.py"""
import importlib.util
import os  # noqa: F401
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vx", ROOT / "tools" / "stt_mistral" / "voxtral_ab.py")
vx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vx)

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("OK  " if ok else "FAIL") + " " + name + (f"  [{detail}]" if detail and not ok else ""))
    fails += not ok


check("WER 0 bei gleichem Text (Satzzeichen egal)", vx.wer("Keine Fraktur, links.", "keine fraktur links") == 0.0)
check("WER: 1 Ersetzung von 4 = 25 %", vx.wer("keine Fraktur links lateral", "keine Fraktur rechts lateral") == 25.0)
check("WER: fehlendes Wortende zählt", vx.wer("a b c d", "a b") == 50.0)
k = vx.bewerte("x", "Keine Fraktur links, Cobb-Winkel 9,5 Grad zwischen Th4 und Th8.",
               "Eine Fraktur rechts, Cobb Winkel 9,5° zwischen DH4 und Th8.", ["Cobb-Winkel", "Fraktur"])
check("Verneinung verloren wird gezählt", k["verneinung"] == [0, 1], k)
check("Seitenwechsel wird erkannt", k["seite_ok"] is False, k)
check("Zahlen streng: DH4 ≠ Th4, 9,5° = 9,5 Grad", k["zahlen"] == [2, 3], k)
check("Fachwort mit Bindestrich/Leerzeichen gleich", k["fachwort"] == [2, 2], k)
v, fl = vx.listen()
check("Listen-Varianten innerhalb der Bias-Grenze", all(len(b) <= vx.BIAS_MAX for b in v.values()) and not v["ohne"])
check("chirp85 = phrases.json chirp", v["chirp85"][:5] == fl[:5])
z = vx.zusammenfassen(vx.chirp_basis(fl))
check("chirp_3-Altwerte: 18 Läufe, keine Seitenfehler", z["chirp_3 +85 (04.10.)"]["n"] == 18
      and z["chirp_3 +85 (04.10.)"]["seite_falsch"] == 0, z)
km = vx.kosten_monat()
check("Monatskosten aus Peters Woche (102/125 min)", km["min_endtext"] == 444 and km["mistral_batch_usd"] == 1.77, km)
check("Testdeckel höchstens 5 €", vx.LIMIT_EUR <= 5.0)
with tempfile.TemporaryDirectory() as d:
    b = vx.Kostenbuch(pathlib.Path(d) / "k.jsonl")
    b.buche("a", 1, 4.99)
    try:
        b.vorab(10)
        check("Deckel bricht ab", False)
    except SystemExit:
        check("Deckel bricht ab", True)
    check("Kostenbuch summiert beim Neustart", abs(vx.Kostenbuch(pathlib.Path(d) / "k.jsonl").eur - 4.99) < 1e-9)
src = (ROOT / "tools" / "stt_mistral" / "voxtral_ab.py").read_text(encoding="utf-8")
check("echte Diktate nur mit MISTRAL_AVV_BESTAETIGT", 'if not os.environ.get("MISTRAL_AVV_BESTAETIGT")' in src)
check("keine Google-Aufrufe im Harness", "googleapis" not in src and "import testkosten" not in src)
print("FAILS:", fails)
sys.exit(1 if fails else 0)
