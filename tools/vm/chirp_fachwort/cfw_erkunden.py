"""chirp-fachwortliste-n1 Schritt 0 (VM, rakauto, NUR LESEN): was liegt da? Ausgabe nur Zähler/Struktur, kein Text."""
import collections
import json
import os
import sqlite3
import struct
import time

W = os.path.expandvars(r"%LOCALAPPDATA%\smi_work")
DB = r"C:\RaK\kaiscribe_lernen\daten\lernen.db"
LAEUFE = r"X:\KaiScribe\Daten\laeufe"
DIKTATE = r"M:\Diktate"

for f in ("fachwoerter_top1000.txt", "pairs.jsonl", "wer.jsonl", "index.jsonl"):
    p = os.path.join(W, f)
    print("SMI", f, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)
try:
    p0 = json.loads(open(os.path.join(W, "pairs.jsonl"), encoding="utf-8").readline())
    print("PAIRS-Schluessel", sorted(p0))
except Exception as e:
    print("PAIRS-Fehler", e)

db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
print("FAELLE-Spalten", [r[1] for r in db.execute("PRAGMA table_info(faelle)")])
seit = time.mktime(time.strptime("20261102", "%Y%m%d"))
z = collections.Counter()
for nr, ben, st, ez, stt, fin, kc in db.execute("SELECT nr, benutzer, status, erst_zeit, stt, final, kuerzel_cas FROM faelle"):
    z[(ben, st, (ez or 0) >= seit, bool(stt), bool(fin))] += 1
for k, v in sorted(z.items(), key=lambda x: -x[1]):
    print("FALL", k, v)


def wav_info(p):
    with open(p, "rb") as f:
        h = f.read(64)
    if h[:4] != b"RIFF":
        return ("kein-riff", 0)
    tag, ch, sr = struct.unpack("<HHI", h[20:28])
    return (tag, sr)


fmt = collections.Counter()
dauer = collections.defaultdict(float)
for nr, ben, st in db.execute("SELECT nr, benutzer, status FROM faelle WHERE status='final'"):
    p = os.path.join(DIKTATE, nr + ".wav")
    if not os.path.exists(p):
        fmt[(ben, "fehlt")] += 1
        continue
    t, sr = wav_info(p)
    fmt[(ben, t, sr)] += 1
    if t == 1:
        dauer[ben] += (os.path.getsize(p) - 44) / (2.0 * sr)
print("WAV", dict(fmt))
print("PCM-Minuten", {k: round(v / 60, 1) for k, v in dauer.items()})
# Lauf-Dateien: Schlüssel
try:
    n = sorted(os.listdir(LAEUFE))
    print("LAEUFE", len(n))
    j = json.load(open(os.path.join(LAEUFE, n[-1]), encoding="utf-8-sig"))
    print("LAUF-Schluessel", sorted(j))
except Exception as e:
    print("LAEUFE-Fehler", e)
