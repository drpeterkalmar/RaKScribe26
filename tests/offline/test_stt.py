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

# v3.16.8: Ergebnisse ohne „transcript“/„alternatives“ (Stille in einem Maskenfeld) → kein KeyError, leer zählt nicht
luecken = {"results": [{"alternatives": [{"transcript": "Mammae beidseits"}]}, {"languageCode": "de-de", "resultEndOffset": "3s"},
                       {"alternatives": []}, {"alternatives": [{"confidence": 0.1}]}, {"alternatives": [{"transcript": "  "}]},
                       {"alternatives": [{"transcript": "unauffällig."}]}]}
check("transkript_aus: Stücke ohne transcript/alternatives übersprungen (KeyError 'transcript', Diktat 019)",
      stt.transkript_aus(luecken) == "Mammae beidseits unauffällig.", stt.transkript_aus(luecken))
check("transkript_aus: ganz ohne Text → leerer Text, kein Fehler",
      stt.transkript_aus({}) == "" and stt.transkript_aus({"results": [{}]}) == "" and stt.transkript_aus(None) == "")


def urlopen_luecke(req, timeout):
    return Antwort(luecken)


check("chirp3_request: Antwort mit leeren Stücken → nur der Text",
      stt.chirp3_request("tok", "eu", "QUJD", urlopen=urlopen_luecke) == "Mammae beidseits unauffällig.")
check("Location global → speech.googleapis.com", gesehen["url"].startswith("https://speech.googleapis.com/v2/projects/rakscribe/locations/global/"))

import subprocess
ts = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "sync_test.mjs"], cwd=ROOT / "web_app",
                    capture_output=True, text=True)
check("Web stitchOverlaps: dieselben Fälle (sync_test.mjs)", ts.returncode == 0, ts.stdout[-500:] + ts.stderr[-500:])
PHR = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))
check("Phrasenlisten aus phrases.json: Streaming 292, chirp_3 85 (Gutachten 68 + 11 Georg 20.11. + 6 Georg 23.11.2026)",
      stt.medical_phrases() == PHR["medical_exe"] and stt.chirp_phrases() == PHR["chirp"]
      and (len(stt.medical_phrases()), len(stt.chirp_phrases())) == (292, 85))
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt stt.py (keine eigenen Listen/Worker mehr)", "_stt.chirp3_worker" in src and "CHIRP_PHRASES = [" not in src
      and "MEDICAL_PHRASES = [" not in src and "phrases=_stt.medical_phrases()" in src)

# chirp-fachwortliste-n1 (Peter 24.11.2026): SpeechMagic-Fachwortliste als Schalter je Kürzel, Standard aus
import re  # noqa: E402
SM = stt.chirp_sm_phrases()
alle = stt.chirp_phrases() + SM
check("chirp_sm: Liste aus phrases.json, ohne die 85 kuratierten, keine Doppelten",
      200 <= len(SM) <= 400 and SM == [p for p in PHR["chirp_sm"] if p.lower() not in {c.lower() for c in PHR["chirp"]}]
      and len({p.lower() for p in alle}) == len(alle), str(len(SM)))
check("chirp_sm: Google-Grenzen (chirp_3 ≤ 1.000 Phrasen, ≤ 100 Zeichen je Phrase, Boost ≤ 20)",
      len(alle) <= 1000 and max(len(p) for p in alle) <= 100 and 0 < stt.CHIRP_SM_BOOST <= stt.CHIRP_BOOST <= 20)
check("chirp_sm: keine Titel/Anreden/Ziffern (Namensschutz, Liste nur Fachwörter)",
      not [p for p in SM if re.search(r"\d|\b(Dr|Prof|Frau|Herr|Herrn|Prim|OA|Pat|Mag)\b", p)])
gesehen.clear()
stt.chirp3_request("tok", "eu", "QUJD", urlopen=urlopen)
ps0 = gesehen["body"]["config"]["adaptation"]["phraseSets"]
stt.chirp3_request("tok", "eu", "QUJD", urlopen=urlopen, sm=True)
ps1 = gesehen["body"]["config"]["adaptation"]["phraseSets"]
check("chirp3_request: ohne Schalter genau wie bisher (1 PhraseSet, 85 × Boost 10)",
      len(ps0) == 1 and [p["value"] for p in ps0[0]["inlinePhraseSet"]["phrases"]] == stt.chirp_phrases())
check("chirp3_request sm=True: + 2. PhraseSet = chirp_sm mit eigenem Boost, kuratierte unverändert",
      len(ps1) == 2 and ps1[0] == ps0[0] and [p["value"] for p in ps1[1]["inlinePhraseSet"]["phrases"]] == SM
      and {p["boost"] for p in ps1[1]["inlinePhraseSet"]["phrases"]} == {stt.CHIRP_SM_BOOST})
kw = []
alt_stub = lambda token, loc, b64: kw.append("alt") or "x"  # noqa: E731
neu_stub = lambda token, loc, b64, sm=False: kw.append(sm) or "x"  # noqa: E731
p1 = np.zeros(16000, dtype=np.int16)
stt.SM_AKTIV = None
stt.chirp3_worker(p1, 16000, "eu", "t", request=alt_stub)
stt.SM_AKTIV = lambda: False
stt.chirp3_worker(p1, 16000, "eu", "t", request=alt_stub)
stt.SM_AKTIV = lambda: 1 / 0
stt.chirp3_worker(p1, 16000, "eu", "t", request=alt_stub)
check("chirp3_worker: Schalter aus/fehlt/Fehler → Request ohne sm-Argument (alte Attrappen der Tests bleiben gültig)",
      kw == ["alt", "alt", "alt"], str(kw))
stt.SM_AKTIV = lambda: True
stt.chirp3_worker(np.zeros(60 * 16000, dtype=np.int16), 16000, "eu", "t", request=neu_stub)
stt.SM_AKTIV = None
check("chirp3_worker: Schalter an → jedes Segment mit sm=True", kw[3:] == [True, True], str(kw))
sys.path.insert(0, str(ROOT / "source_code"))
import tempfile, config as _cfg  # noqa: E401,E402
with tempfile.TemporaryDirectory() as td:
    werte = {}
    for name, zeile in (("fehlt", ""), ("kp", "CHIRP_SM = kp\n"), ("zwei", "CHIRP_SM = kp, RG\n"), ("aus", "CHIRP_SM = aus\n")):
        pf = pathlib.Path(td) / (name + ".ini")
        pf.write_text("[SETTINGS]\n" + zeile, encoding="utf-8")
        werte[name] = _cfg.load_config(str(pf)).chirp_sm
check("config.ini CHIRP_SM: Standard aus (niemand), kp | kp, rg | aus",
      werte == {"fehlt": [], "kp": ["kp"], "zwei": ["kp", "rg"], "aus": []}, str(werte))
check("EXE: Schalter je Befunder des CAS-Diktats (SM_AKTIV ← _chirp_sm_an, Logzeile [CHIRP3] Fachwortliste)",
      "_stt.SM_AKTIV = getattr(app, \"_chirp_sm_an\", None)" in src and "def _chirp_sm_an(self)" in src
      and "_senf.aktiv(a.benutzer, liste)" in src and "[CHIRP3] Fachwortliste SpeechMagic an" in src)

print("\n" + ("✅ SPRACHERKENNUNG PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
