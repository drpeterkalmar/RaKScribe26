"""Gate (Umbau Schritt 13): Spracherkennung der EXE (stt.py) — chirp_3-Request, Segmentierung 50 s / 4 s,
Overlap-Stitch (gemeinsame Fälle mit der Web-App: sync_fixtures.json), Phrasenlisten. Ohne Netz (Stubs).
Aufruf: /usr/bin/python3 tests/offline/test_stt.py"""
import base64, io, json, pathlib, sys, wave
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import numpy as np  # noqa: E402
import stt  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


F = json.loads((ROOT / "sync_fixtures.json").read_text(encoding="utf-8"))
falsch = [(a, b, soll, stt.stitch_overlaps(a, b)) for a, b, soll in F["stitch"] if stt.stitch_overlaps(a, b) != soll]
check(f"stitch_overlaps: {len(F['stitch'])} gemeinsame Fälle (sync_fixtures.json)", not falsch, str(falsch[:2]))

# Segmentierung 50 s + 4 s Rückhören (Stub statt Google)
aufrufe = []


def stub(token, loc, b64):
    w = wave.open(io.BytesIO(base64.b64decode(b64)))
    pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    aufrufe.append((token, loc, w.getframerate(), w.getnchannels(), len(pcm) / 16000, int(pcm[0])))
    return ["eins zwei drei vier fünf sechs", "fünf sechs sieben acht", "sieben acht neun"][len(aufrufe) - 1]


pcm = (np.arange(120 * 16000) // 16000).astype(np.int16).reshape(-1, 1)  # Sekunde i → Wert i, Form (n, 1) wie die Aufnahme
text = stt.chirp3_worker(pcm, 16000, "eu", "tok", request=stub)
check("120 s → 3 Segmente à 50 / 50 / 28 s", [round(a[4]) for a in aufrufe] == [50, 50, 28], str(aufrufe))
check("Segmente beginnen bei 0 / 46 / 92 s (4 s Rückhören)", [a[5] for a in aufrufe] == [0, 46, 92])
check("16 kHz mono, Token + Location durchgereicht", all(a[:4] == ("tok", "eu", 16000, 1) for a in aufrufe))
check("Texte zusammengefügt", text == "eins zwei drei vier fünf sechs sieben acht neun", text)
aufrufe.clear()
check("≤ 50 s → genau ein Request", stt.chirp3_worker(pcm[:30 * 16000], 16000, "eu", "t", request=stub) == "eins zwei drei vier fünf sechs"
      and len(aufrufe) == 1)
check("Request liefert None → None", stt.chirp3_worker(pcm[:16000], 16000, "eu", "t", request=lambda *a: None) is None)

# chirp3_request: URL, Header, Body, Antwort
gesehen = {}


class Antwort:
    def __init__(self, daten):
        self.daten = daten

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps(self.daten).encode()


def urlopen(req, timeout):
    gesehen.update(url=req.full_url, auth=req.get_header("Authorization"), body=json.loads(req.data), timeout=timeout)
    return Antwort({"results": [{"alternatives": [{"transcript": "Knie rechts"}]}, {"alternatives": [{"transcript": "unauffällig."}]}]})


t = stt.chirp3_request("tok", "eu", "QUJD", urlopen=urlopen)
check("chirp3_request: EU-Endpoint, Bearer-Token, Timeout 60 s",
      gesehen["url"] == "https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize"
      and gesehen["auth"] == "Bearer tok" and gesehen["timeout"] == 60, str(gesehen.get("url")))
cfg = gesehen["body"]["config"]
check("chirp3_request: Modell chirp_3, de-DE, PhraseSet = phrases.json chirp (Boost 10)",
      cfg["model"] == "chirp_3" and cfg["languageCodes"] == ["de-DE"] and gesehen["body"]["content"] == "QUJD"
      and [p["value"] for p in cfg["adaptation"]["phraseSets"][0]["inlinePhraseSet"]["phrases"]] == stt.chirp_phrases()
      and {p["boost"] for p in cfg["adaptation"]["phraseSets"][0]["inlinePhraseSet"]["phrases"]} == {10})
check("chirp3_request: Ergebnisse mit Leerzeichen verbunden", t == "Knie rechts unauffällig.")
stt.chirp3_request("tok", "global", "", urlopen=urlopen)
check("Location global → speech.googleapis.com", gesehen["url"].startswith("https://speech.googleapis.com/v2/projects/rakscribe/locations/global/"))

import subprocess
ts = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "sync_test.mjs"], cwd=ROOT / "web_app",
                    capture_output=True, text=True)
check("Web stitchOverlaps: dieselben Fälle (sync_test.mjs)", ts.returncode == 0, ts.stdout[-500:] + ts.stderr[-500:])
PHR = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))
check("Phrasenlisten aus phrases.json: Streaming 292, chirp_3 68 (Stand Gutachten)",
      stt.medical_phrases() == PHR["medical_exe"] and stt.chirp_phrases() == PHR["chirp"]
      and (len(stt.medical_phrases()), len(stt.chirp_phrases())) == (292, 68))
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt stt.py (keine eigenen Listen/Worker mehr)", "_stt.chirp3_worker" in src and "CHIRP_PHRASES = [" not in src
      and "MEDICAL_PHRASES = [" not in src and "phrases=_stt.medical_phrases()" in src)

print("\n" + ("✅ SPRACHERKENNUNG PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
