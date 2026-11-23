r"""rho_titel_kontrolle.py 1.0 (kaiscribe-rho-titel-nummer-n1, 23.11.2026) – NUR LESEN, Automaten-VM als rakauto.

Georg 22.11.2026 (Punkt 47, RH 49): „Die Überschrift bei opp gross machen und mit Punkt 1. Starten“. Je Brief eines Tages
mit Rho-Text („Knochendichtescreening“) bzw. mit „Amerkung“ (CAS LETTERS, nur SELECT über casdb, READ ONLY): Zeilen-
Struktur MIT Zeichenformat (fett/unterstrichen/Schriftgröße aus dem RTF), Nummerierung der Ergebnis-Punkte je Teil und die
Struktur des KaiScribe-Vorschlags aus der Lauf-Datei. Ausgabe nur Kurz-ID (MMTT-NNN), Zahlen, Kürzel – kein Name, kein Text.

  python3 tools/vm/x_lauf_mac.py tools/vm/rho_titel_kontrolle.py 20261120 [--nr 049]
Kürzel je Zeile des Befundteils:
  T[fu]<pt>  Überschrift (f fett, u unterstrichen, pt Schriftgröße) – Rho-Überschrift als K<ki|fm>[fu]<pt>
             (ki = KaiScribe „(KI)“, fm = Formatierer „auf niedrige Knochenmineraldichte“)
  E Ergebnis-Kopf, B Befund-Kopf, R Rho-Text im Befund, 1/2/… nummerierter Ergebnispunkt (Zahl), e unnummeriert, u Schlussanmerkung (LCE/HKA/… = …) ohne Nummer,
  r Rho-Ergebnis unnummeriert, rN Rho-Ergebnis mit Nummer N, A „Anmerkung:“, X „Amerkung“ (Tippfehler), . sonst;
  mit Lauf-Datei hinter jedem Brief-Kürzel = (Zeile so im KaiScribe-Vorschlag) bzw. + (nicht im Vorschlag)
"""
import glob
import json
import os
import re
import sys

PROG = r"C:\RaK\kaiscribe_lernen\prog"
for p in (PROG, os.path.join(PROG, "bruecke")):
    sys.path.insert(0, p)
import casdb  # noqa: E402

# wie KaiScribe befund_regeln._UNNUM_RE (Schlussanmerkungen ohne Nummer) → Kürzel „u“
_UNNUM = re.compile(r"^(?:im\s+)?vergleich\s+zu[rm]?\s+vor|^HKA = |^Weitere Winkelmessungen sind den KI-Auswertungsbildern"
                    r"|^(?:LCE|AI|CCD) = ", re.I)

A = sys.argv[1:]
TAG = A[0] if A and re.fullmatch(r"\d{8}", A[0]) else None
NUR = A[A.index("--nr") + 1] if "--nr" in A else None
LAEUFE = [r"X:\KaiScribe\Daten\laeufe", r"X:\RaKScribe\Daten\laeufe"]
M = "\u00a7"


def markieren(roh):
    """Zeichenformat im RTF als Text-Marker; Gruppen als §G§/§g§ (innerhalb der Gruppe, damit übersprungene Ziele
    ihre Marker mitnehmen)."""
    roh = roh.strip()
    kopf, roh = (roh[:5], roh[5:]) if roh.startswith("{\\rtf") else ("", roh)   # äußerste Gruppe bleibt unmarkiert
    r = re.sub(r"(?<!\\)\{", "{\\'a7G\\'a7", roh)
    r = re.sub(r"(?<!\\)\}", "\\'a7g\\'a7}", r)
    r = kopf + r
    r = re.sub(r"\\plain(?![a-z])\s?", "\\'a7P\\'a7", r)
    r = re.sub(r"\\ul(?:none|0)(?![a-z0-9])\s?", "\\'a7u\\'a7", r)
    r = re.sub(r"\\ul(?![a-z0-9-])\s?", "\\'a7U\\'a7", r)
    r = re.sub(r"\\b0(?![a-z0-9])\s?", "\\'a7b\\'a7", r)
    r = re.sub(r"\\b(?![a-z0-9-])\s?", "\\'a7B\\'a7", r)
    return re.sub(r"\\fs(\d+)(?![a-z0-9])\s?", lambda m: "\\'a7F" + m.group(1) + "\\'a7", r)


_TOK = re.compile(M + r"(G|g|P|u|U|b|B|F\d+)" + M)


def zeilen_mit_format(text):
    """Text mit Markern → [(zeile, fett, unterstrichen, pt)] je nicht leerer Zeile (Format am ersten sichtbaren Zeichen,
    pt = größte Schrift der Zeile)."""
    stapel, st = [], {"b": False, "u": False, "fs": 24}
    aus, buf, erste, groesst = [], [], None, 0
    pos = 0

    def zeile_ende():
        nonlocal buf, erste, groesst
        z = "".join(buf).strip()
        if z:
            f = erste or (False, False, 24)
            aus.append((z, f[0], f[1], groesst / 2 if groesst else f[2] / 2))
        buf, erste, groesst = [], None, 0

    for m in list(_TOK.finditer(text)) + [None]:
        stueck = text[pos:m.start() if m else len(text)]
        for ch in stueck:
            if ch == "\n":
                zeile_ende()
                continue
            buf.append(ch)
            if not ch.isspace():
                if erste is None:
                    erste = (st["b"], st["u"], st["fs"])
                groesst = max(groesst, st["fs"])
        if m is None:
            break
        pos = m.end()
        k = m.group(1)
        if k == "G":
            stapel.append(dict(st))
        elif k == "g":
            st = stapel.pop() if stapel else st
        elif k == "P":
            st = {"b": False, "u": False, "fs": 24}
        elif k in ("U", "u"):
            st["u"] = k == "U"
        elif k in ("B", "b"):
            st["b"] = k == "B"
        else:
            st["fs"] = int(k[1:])
    zeile_ende()
    return aus


def norm(t):
    return re.sub(r"\s+", " ", str(t or "").lower()).strip()


def ist_ergebnis(z):
    return bool(re.match(r"^(ergebnis|zusammenfassung|beurteilung)\s*:?\s*$", norm(z)))


_SATZWORT = re.compile(r"\b(?:keine?[nrsm]?|ist|sind|zeigt|zeigen|regelrecht\w*|unauffällig\w*|normal\w*|erhalten\w*|"
                       r"nachweis\w*|hinweis\w*|verdacht|empfohlen|besteht|bestehen|liegt|vor|mit|ohne)\b", re.I)


def titel_artig(z, fett, unter):
    if unter and not ist_ergebnis(z):
        return True
    s = z.strip()
    if not s or len(s) > 90 or ist_ergebnis(s) or s[0] in "-•*–" or re.match(r"^\d+[.)]", s):
        return False
    if s.endswith(("!", "?", ",", ";", ".")) or _SATZWORT.search(s):
        return False
    return fett and (s[0].isupper() or s[0].isdigit())


def _kern(t):
    return re.sub(r"^(?:\d+\s*[.)]\s*|(?:a|an)merkung:\s*)", "", norm(t)).strip(" .")


def brief_struktur(zeilen, vorschlag=""):
    """vorschlag (Markdown der Lauf-Datei) → nach jedem Kürzel „=“ (Zeile steht so im Vorschlag) bzw. „+“ (nicht)."""
    vk = {_kern(x.lstrip("# ")) for x in (vorschlag or "").split("\n") if x.strip()}
    code, im_erg, im_rho = [], False, False
    for z, fett, unter, pt in zeilen:
        n = norm(z)
        if vorschlag and code:
            code[-1] += "=" if code[-1][-1:] not in "=+" and _kern(z_alt) in vk else "+" if code[-1][-1:] not in "=+" else ""
        z_alt = z
        fmt = ("f" if fett else "") + ("u" if unter else "") + f"{pt:g}"
        rho_kopf = n.startswith("opportunistisches knochendichtescreening") and not n.endswith("empfohlen.") \
            and "mittels" not in n and len(n) < 90
        if rho_kopf or titel_artig(z, fett, unter):
            im_rho, im_erg = rho_kopf, False
            code.append(("K" + ("ki" if "(ki)" in n else "fm" if "mineraldichte" in n else "?") if rho_kopf else "T") + fmt)
            continue
        if re.match(r"^befund\s*:?\s*$", n):
            code.append("B")
            continue
        if ist_ergebnis(z):
            im_erg = True
            code.append("E")
            continue
        if "amerkung" in n:
            code.append("X")
            continue
        if n.startswith("anmerkung"):
            code.append("A")
            continue
        num = re.match(r"^(\d+)\s*[.)]\s", z)
        if im_erg:
            rho_e = "knochendichtescreening" in n
            if rho_e:
                code.append("r" + (num.group(1) if num else ""))
            else:
                code.append(num.group(1) if num else ("u" if _UNNUM.match(z.strip()) else "e"))
            continue
        code.append("R" if (im_rho or "knochendichtescreening" in n) else ".")
    if vorschlag and code:
        code[-1] += "=" if _kern(z_alt) in vk else "+"
    return " ".join(code)


def md_struktur(md):
    code, im_erg, im_rho = [], False, False
    for z in (md or "").split("\n"):
        s = z.strip()
        if not s:
            continue
        if s.startswith("## "):
            k = s[3:].strip().rstrip(":").lower()
            if k == "befund":
                code.append("B")
            elif k == "ergebnis":
                im_erg = True
                code.append("E")
            else:
                im_rho, im_erg = k.startswith("opportunistisches knochendichtescreening"), False
                code.append("K" if im_rho else "T")
            continue
        n = norm(s)
        if "amerkung" in n:
            code.append("X")
            continue
        if n.startswith("anmerkung"):
            code.append("A")
            continue
        num = re.match(r"^(\d+)\s*[.)]\s", s)
        if im_erg:
            code.append(("r" if "knochendichtescreening" in n else "") + (num.group(1) if num else (
                "" if "knochendichtescreening" in n else "u" if _UNNUM.match(s) else "e")))
        else:
            code.append("R" if (im_rho or "knochendichtescreening" in n) else ".")
    return " ".join(code)


def lauf_md(nr):
    dateien = sorted(sum((glob.glob(os.path.join(o, f"{nr}_*.json")) for o in LAEUFE), []), key=os.path.basename)
    try:
        with open(dateien[-1], encoding="utf-8") as f:
            return json.load(f).get("ergebnis_vorschlag") or ""
    except (OSError, ValueError, IndexError):
        return ""


def lauf(nr):
    dateien = []
    for o in LAEUFE:
        dateien += glob.glob(os.path.join(o, f"{nr}_*.json"))
    if not dateien:
        return None
    dateien.sort(key=lambda p: os.path.basename(p))
    try:
        with open(dateien[-1], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {"n": len(dateien), "lesbar": False}
    felder = sorted(k for k in d if isinstance(d.get(k), str) and "## " in d.get(k))
    return {"n": len(dateien), "lesbar": True, "v": str(d.get("kaiscribe") or "?")[:10],
            "pc": str(d.get("rechner") or "?")[:12],
            "md": md_struktur(d.get("ergebnis_vorschlag") or ""), "felder": ",".join(felder)[:80],
            "amerkung": sum("amerkung" in norm(v) for v in d.values() if isinstance(v, str))}


def main():
    if not TAG:
        raise SystemExit(__doc__)
    e = casdb.Einstellungen({})
    befehl = [casdb.sqlplus_finden(e.sqlplus)]
    anm = casdb.anmeldung_lesen(e.anmeldung)
    if not befehl[0] or not anm:
        print("FEHLER kein sqlplus/keine Anmeldung")
        sys.exit(1)
    nr = "TO_CHAR(l.listdate,'YYYYMMDD') || LPAD(w.numberinlist,3,'0')"
    liste_sql = (casdb._KOPF + casdb._abschnitt("liste", f"""
SELECT JSON_OBJECT('nr' VALUE {nr}, 'wrid' VALUE TO_CHAR(w.warterowid), 'st' VALUE w.status, 'obl' VALUE w.obletter,
  'obg' VALUE w.obgelesen, 'wer' VALUE w.ddwer, 'rt' VALUE TO_CHAR(w.recordtime,'HH24:MI'))
FROM sysadm.warterow w JOIN sysadm.wartelist l ON l.id = w.wartelistid
WHERE l.listdate >= TO_DATE('{TAG}','YYYYMMDD') AND l.listdate < TO_DATE('{TAG}','YYYYMMDD') + 1
  AND NVL(w.status,'?') <> '!' AND EXISTS (SELECT 1 FROM sysadm.letters t WHERE t.id = w.warterowid);""")
                 + "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n")
    _c, aus = casdb.sqlplus_ausfuehren(befehl, e.ziel, anm[0], anm[1], liste_sql, frist_s=120)
    _v, _f, a, fehler = casdb.abschnitte(aus)
    besuche = casdb._json_zeilen(a.get("liste"))
    besuche = [b for b in besuche if re.fullmatch(r"\d{11}", str(b.get("nr") or "")) and re.fullmatch(r"\d+", str(b.get("wrid") or ""))]
    if NUR:
        besuche = [b for b in besuche if b["nr"].endswith(NUR)]
    print(f"LISTE briefe={len(besuche)} fehler={','.join(fehler) or '-'}")
    texte = {}
    abc = "abcdefghijklmnopqrstuvwxyz"
    for i in range(0, len(besuche), 12):
        teil = besuche[i:i + 12]
        s = casdb._KOPF
        for k, b in enumerate(teil):
            s += casdb._abschnitt("b_" + abc[k], f"SELECT t.letter FROM sysadm.letters t WHERE t.id = {int(b['wrid'])} AND ROWNUM = 1;")
        s += "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n"
        try:
            _c, aus = casdb.sqlplus_ausfuehren(befehl, e.ziel, anm[0], anm[1], s, frist_s=300)
        except Exception as ex:  # noqa: BLE001
            print(f"STAPEL {i} FEHLER {type(ex).__name__}")
            continue
        _v, _f, a, fehler = casdb.abschnitte(aus)
        for k, b in enumerate(teil):
            roh = casdb._brief_roh(a["b_" + abc[k]]) if "b_" + abc[k] in a else ""
            texte[b["nr"]] = roh or None
    amerk, rho = 0, []
    for b in besuche:
        roh = texte.get(b["nr"])
        if not roh:
            continue
        klar = casdb._befundteil(casdb._klartext(roh))
        am = "amerkung" in norm(klar)
        amerk += am
        if "knochendichtescreening" in norm(klar) or am:
            rho.append((b, roh, am))
    print(f"BRIEFE gelesen={sum(1 for v in texte.values() if v)} mit_rho_oder_amerkung={len(rho)} amerkung={amerk}")
    for b, roh, am in sorted(rho, key=lambda x: x[0]["nr"]):
        n = b["nr"]
        try:
            mk = casdb._klartext(markieren(roh))
            a_, e_ = mk.find("<bf0>"), mk.find("</bf0>")
            if a_ >= 0 and e_ > a_:
                mk = mk[a_ + 5:e_]
            mk = casdb._TAG.sub("", mk)
            struktur = brief_struktur(zeilen_mit_format(mk), (lauf_md(n) or ""))
        except Exception as ex:  # noqa: BLE001
            struktur = f"FEHLER {type(ex).__name__}"
        lf = lauf(n)
        print(f"FALL {n[4:8]}-{n[8:]} zeit={b.get('rt')} st={b.get('st') or '-'}/{b.get('obl') or '-'} "
              f"wer={(b.get('wer') or '-')[:3]} amerkung={'ja' if am else 'nein'}")
        print(f"  BRIEF {struktur[:400]}")
        if lf is None:
            print("  LAUF -")
        elif not lf.get("lesbar"):
            print(f"  LAUF n={lf['n']} unlesbar")
        else:
            print(f"  LAUF n={lf['n']} v={lf['v']} pc={lf['pc']} amerkung={lf['amerkung']} felder={lf['felder']}")
            print(f"  VORSCHLAG {lf['md'][:300]}")


if __name__ == "__main__":
    main()
