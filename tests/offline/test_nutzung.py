"""Gate (kaiscribe-sonnet-n2): Nutzungszähler der EXE — Claude-Aufrufe, Rückfälle auf Gemini (nur Kategorie), Chirp-
Audiosekunden je PC/Tag/Monat, Tagesbericht über alle PCs, Warnung bei Chirp hochgerechnet > 6 €/Monat.
Aufruf: python3 tests/offline/test_nutzung.py"""
import datetime
import json
import os
import pathlib
import sys
import tempfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import llm_anbieter as la  # noqa: E402
import nutzung  # noqa: E402
import stt  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


d = tempfile.mkdtemp(prefix="rks_nutz_")
T = datetime.datetime(2026, 11, 16, 9, 30)
z8 = nutzung.Zaehler(d, "CASWS08", jetzt=lambda: T)
z10 = nutzung.Zaehler(d, "CASWS10", jetzt=lambda: T)

check("Ordner neben dem Lauf-Protokoll", nutzung.ordner_aus("X:\\RaKScribe\\Daten\\laeufe")
      == "X:\\RaKScribe\\Daten\\nutzung", nutzung.ordner_aus("X:\\RaKScribe\\Daten\\laeufe"))
check("LAUF_ORDNER = aus → APPDATA", nutzung.ordner_aus("aus", appdata="/tmp/ad") == os.path.join("/tmp/ad", "RaKScribe", "nutzung"))
check("PC-Name aus COMPUTERNAME, Dateiname-sicher", nutzung.pc_name({"COMPUTERNAME": "CAS WS08"}) == "CAS_WS08")

# Weiche → Zähler (wie in der EXE: beobachter=NUTZUNG.ki)
def antwort(b):
    rest = b["messages"][0]["content"][-1]["text"]
    ph = " ".join(p for p in __import__("re").findall(r"⟦[PDNAE]\d+⟧", la.diktat_teil(rest)))
    return {"type": "message", "stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 200},
            "content": [{"type": "text", "text": "## Knie\n\n## Befund\nText vom " + ph + " lang genug.\n\n## Ergebnis\n1. X."}]}


gp = "Regeln\n<normalbefund_template>\nNormal.\n</normalbefund_template>\n<diktat>\nKnie rechts 12.3.2025 Erguss\n</diktat>"
w = la.Weiche("anthropic", gemini_fn=lambda p, s: "## Knie\n\n## Befund\nGemini.\n\n## Ergebnis\n1. G.",
              sender=lambda b, f: antwort(b), beobachter=z8.ki)
w(gp, "sys", rolle="gen")
w(gp, "sys", rolle="gen")
w2 = la.Weiche("anthropic", gemini_fn=lambda p, s: "## Knie\n\n## Befund\nGemini.\n\n## Ergebnis\n1. G.",
               sender=lambda b, f: (_ for _ in ()).throw(TimeoutError("timed out")), beobachter=z10.ki)
w2(gp, "sys", rolle="gen")
z8.stt(65.0)
z10.stt(30.0)
z10.stt(0)

roh8 = json.loads(pathlib.Path(d, "2026-11_CASWS08.json").read_text(encoding="utf-8"))
td = roh8["tage"]["2026-11-16"]
check("CASWS08: 2 Claude-Befunde, Kosten, Chirp 65 s", td["ki"].get("anthropic") == 2 and td["befunde"] == 2
      and td["anthropic_usd"] > 0 and td["stt_s"]["chirp"] == 65.0, td)
roh10 = json.loads(pathlib.Path(d, "2026-11_CASWS10.json").read_text(encoding="utf-8"))
t10 = roh10["tage"]["2026-11-16"]
check("CASWS10: Rückfall gezählt mit Kategorie (ohne Werte)", t10["ki"].get("rueckfall") == 1
      and list(t10["rueckfall_grund"]) == ["Anthropic-Ausfall (TimeoutError)"], t10)
alles = json.dumps([roh8, roh10], ensure_ascii=False)
check("Zählerdateien ohne Diktat/Datum/Text", "12.3.2025" not in alles and "Erguss" not in alles and "Knie" not in alles)

text, warn = nutzung.tagesbericht(d, "2026-11-16")
check("Tagesbericht: Befunde, Claude, Rückfälle, je PC", "3 Befunde" in text and "Aufrufe Claude 2" in text
      and "Rückfälle auf Gemini 1" in text and "CASWS08" in text and "CASWS10" in text, text)
check("Tagesbericht: Chirp-Minuten + €", "Monat 1.6 min" in text and "€" in text and not warn, text)
check("Tagesbericht-Datei geschrieben", pathlib.Path(d, "tagesbericht_2026-11-16.txt").exists())

# Warnung: 16 Tage, hochgerechnet > 6 € → ~ 6 € / 0.016 $/min / 0.87 = 431 min im Monat ≈ 230 min bis zum 16.
z8.stt(240 * 60)
text, warn = nutzung.tagesbericht(d, "2026-11-16")
check("Warnung ab hochgerechnet > 6 €/Monat + warnung-Datei", warn and "WARNUNG" in text
      and pathlib.Path(d, "warnung_2026-11.txt").exists(), text)
check("Hochrechnung: 1 Tag × 30 = Monat", abs(nutzung.hochrechnung_eur(60, "2026-11-01")
                                              - nutzung.chirp_eur(60) * 30) < 1e-9)

# Chirp-Worker zählt jedes Stück (inkl. Rückhören)
gezaehlt = []
stt.ZAEHLER = gezaehlt.append
pcm = np.zeros(16000 * 70, dtype=np.int16)
stt.chirp3_worker(pcm, 16000, "eu", "tok", request=lambda *a: "text")
stt.ZAEHLER = None
check("chirp3_worker: Sekunden je Stück (50 s + 24 s mit 4 s Rückhören)", gezaehlt == [50.0, 24.0], gezaehlt)

# Laufwerk weg → nie fatal
pathlib.Path(d, "datei.txt").write_text("x")
nutzung.Zaehler(os.path.join(d, "datei.txt", "x"), "PC").stt(5)
nutzung.Zaehler(os.path.join(d, "datei.txt", "x"), "PC").ki({"anbieter": "anthropic"})
check("Schreibfehler still", True)

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
