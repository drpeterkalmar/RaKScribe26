"""Nur lesen: oberste Ebene von X:\\KaiScribe und X:\\RaKScribe (Name, Größe, Änderungszeit) + *.log rekursiv (2 Ebenen)."""
import glob, os, time
for w in (r"X:\KaiScribe", r"X:\RaKScribe"):
    for p in sorted(os.listdir(w)):
        q = os.path.join(w, p)
        if os.path.isfile(q) and (p.lower().endswith((".exe", ".log", ".ini", ".alt", ".json")) or "log" in p.lower()):
            print("DATEI", q, os.path.getsize(q), time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(q))))
        elif os.path.isdir(q):
            print("ORDNER", q)
    for q in glob.glob(os.path.join(w, "*", "*", "rakscribe*.log*")) + glob.glob(os.path.join(w, "*", "rakscribe*.log*")):
        print("LOG", q, os.path.getsize(q), time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(q))))
