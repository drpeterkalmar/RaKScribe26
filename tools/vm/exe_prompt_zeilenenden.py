"""Nur lesen (kaiscribe-kosten-je-befund-n1, 25.11.2026): In welcher Form steckt radiology_prompt.txt in der KaiScribe-EXE
auf X:? Liest das PyInstaller-Paket (CArchive) der EXE, entpackt NUR radiology_prompt.txt im Speicher und gibt Zahlen aus:
Bytes, Anzahl CRLF/LF, ob die Cache-Marke „<normalbefund_template>\\n“ gefunden wird (llm_anbieter.fester_anfang).
Der Prompt enthält nur Regeln (keine Patientendaten); ausgegeben wird trotzdem nur Zahlen + Versionsmarker.

  py -3.12 exe_prompt_zeilenenden.py [Pfad zur EXE …]   (Standard: X:\\KaiScribe\\KaiScribe.exe, X:\\RaKScribe\\rakscribe26.exe)
"""
import os
import re
import struct
import sys
import zlib

MAGIC = b"MEI\014\013\012\013\016"


def eintraege(pfad):
    with open(pfad, "rb") as f:
        f.seek(0, 2)
        groesse = f.tell()
        f.seek(max(0, groesse - 8192))
        ende = f.read()
        i = ende.rfind(MAGIC)
        if i < 0:
            raise ValueError("kein PyInstaller-Paket")
        cookie_pos = groesse - len(ende) + i
        f.seek(cookie_pos)
        _m, pkg_len, toc_off, toc_len, _py = struct.unpack("!8sIIII", f.read(24))
        start = cookie_pos + 88 - pkg_len          # Cookie (8s I I I I 64s) = 88 Bytes am Paketende
        f.seek(start + toc_off)
        toc = f.read(toc_len)
        pos = 0
        while pos < len(toc):
            e_len, off, ln, uln, flag, typ = struct.unpack("!IIIIBc", toc[pos:pos + 18])
            name = toc[pos + 18:pos + e_len].rstrip(b"\0").decode("utf-8", "replace")
            pos += e_len
            yield name, start + off, ln, flag
        return


def lesen(pfad, gesucht):
    for name, off, ln, flag in eintraege(pfad):
        if name.replace("\\", "/").split("/")[-1] == gesucht:
            with open(pfad, "rb") as f:
                f.seek(off)
                roh = f.read(ln)
            return zlib.decompress(roh) if flag else roh
    return None


def main():
    pfade = sys.argv[1:] or [r"X:\KaiScribe\KaiScribe.exe", r"X:\RaKScribe\rakscribe26.exe"]
    for p in pfade:
        if not os.path.exists(p):
            print("EXE %s fehlt" % p)
            continue
        try:
            b = lesen(p, "radiology_prompt.txt")
        except Exception as e:
            print("EXE %s fehler=%s" % (p, type(e).__name__))
            continue
        if b is None:
            print("EXE %s prompt=fehlt" % p)
            continue
        t = b.decode("utf-8", "replace")
        m = re.search(r"RAKSCRIBE_PROMPT_VERSION:\s*([\w.-]+)", t)
        print("EXE %s bytes=%d crlf=%d lf_gesamt=%d marke_lf=%s marke_crlf=%s version=%s groesse_exe=%d"
              % (p, len(b), b.count(b"\r\n"), b.count(b"\n"), "<normalbefund_template>\n" in t,
                 "<normalbefund_template>\r\n" in t, m.group(1) if m else "-", os.path.getsize(p)))
        tj = lesen(p, "templates.json")
        if tj is not None:
            print("EXE %s templates_bytes=%d templates_crlf=%d" % (p, len(tj), tj.count(b"\r\n")))
    print("EXE_PROMPT=fertig")


if __name__ == "__main__":
    main()
