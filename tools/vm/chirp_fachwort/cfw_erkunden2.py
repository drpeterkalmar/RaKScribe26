"""chirp-fachwortliste-n1 Schritt 0b (VM, rakauto, NUR LESEN): alle PCM-WAVs (KaiScribe) in M:\\Diktate seit 02.11.,
Zuordnung Befunder über Lauf-Dateien/lernen.db, Brief-Datei vorhanden? Nur Zähler."""
import collections
import json
import os
import re
import sqlite3
import struct
import time

DB = r"C:\RaK\kaiscribe_lernen\daten\lernen.db"
LAEUFE = r"X:\KaiScribe\Daten\laeufe"
DIKTATE = r"M:\Diktate"
seit = time.mktime(time.strptime("20261102", "%Y%m%d"))

lauf = {}
for n in sorted(os.listdir(LAEUFE)):
    m = re.match(r"^(\d{11})_", n)
    if not m:
        continue
    try:
        j = json.load(open(os.path.join(LAEUFE, n), encoding="utf-8-sig"))
    except Exception:
        continue
    lauf[m.group(1)] = (j.get("benutzer") or "").lower()
db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
fall = {nr: (b, st) for nr, b, st in db.execute("SELECT nr, benutzer, status FROM faelle")}
z = collections.Counter()
mins = collections.defaultdict(float)
tage = collections.Counter()
for n in os.listdir(DIKTATE):
    m = re.match(r"^(\d{11})\.wav$", n, re.I)
    if not m:
        continue
    p = os.path.join(DIKTATE, n)
    st = os.stat(p)
    if st.st_mtime < seit:
        continue
    with open(p, "rb") as f:
        h = f.read(64)
    if h[:4] != b"RIFF" or struct.unpack("<H", h[20:22])[0] != 1:
        continue
    sr = struct.unpack("<I", h[24:28])[0]
    nr = m.group(1)
    ben = lauf.get(nr) or (fall.get(nr) or ("?",))[0] or "?"
    stat = (fall.get(nr) or ("", "kein-fall"))[1]
    doc = os.path.exists(os.path.join(DIKTATE, nr + ".doc"))
    srr = os.path.exists(os.path.join(DIKTATE, nr + ".srr"))
    z[(ben, stat, doc, srr)] += 1
    mins[(ben, stat)] += (st.st_size - 44) / (2.0 * sr) / 60
    tage[(ben, nr[4:6] + "-" + nr[6:8])] += 1
for k, v in sorted(z.items(), key=lambda x: -x[1]):
    print("PCM", k, v)
print("MIN", {"%s/%s" % k: round(v, 1) for k, v in mins.items()})
print("TAGE", sorted(tage.items()))
print("AENDERUNGEN", db.execute("SELECT klasse, COUNT(*) FROM aenderungen GROUP BY klasse").fetchall())
