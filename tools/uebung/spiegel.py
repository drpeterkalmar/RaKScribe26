r"""KaiScribe-Übung: einen vergangenen Ordi-Tag spiegeln (kaiscribe-uebung-n1, 25.11.2026) – Automaten-VM, rakauto.

NUR LESEN: CAS ausschließlich per SELECT über casdb (sqlplus, READ ONLY, am Ende ROLLBACK), dazu die Senf-Ablage
(C:\RaK\opus_senf\senf\<nr>.json bzw. X:\RaKScribe\Daten\senf\) und die IB-Lab-Bausteine (X:\IBL-Vorbefunde\<nr>_*.txt).
Keine Bilder, kein C-MOVE/C-STORE, kein Header, nichts an Befund-PCs. Testpatient 451898 nie.

Ergebnis (bleibt auf der VM): <basis>\daten\<JJJJMMTT>\anonym.json + haus.json – je Fall (nur vidierte/gedruckte
Befunde der Kürzel kp und rg):
  id (RH<Tageslisten-Nr.>), kuerzel, zeit, untersuchungen, leistungen, alter, geschlecht, ibl, senf, vorbefund, loesung
  anonym: kein Name, keine SVNR/Pat.-Nr./Diktatnummer, kein Geburtsdatum (nur Alter), keine Adresse; Vorbefund und
          Lösung maskiert (ki_maske wie KaiFormat, Vorbefund-Daten bleiben), Restprüfung – unsicher → Text ausgeblendet
  haus:   wie CAS (Name, Diktatnummer, Zuweiser) – nur für einen ausdrücklich eingeschalteten LAN-Zugang
Konsole: nur Zähler.

  py -3.12 -X utf8 spiegel.py --tag 20261123 [--basis C:\RaK\kaiscribe_uebung] [--max 80] [--erkunden]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
for _p in (r"C:\RaK\kaiscribe_lernen\prog\bruecke", r"C:\RaK\kaiscribe_lernen\prog", r"C:\RaKScribe-Py\ris-mods\bruecke"):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)
import uebung_kern as K  # noqa: E402

TESTPATIENT = "451898"
SENF_ORDNER = [r"C:\RaK\opus_senf\senf", r"X:\RaKScribe\Daten\senf", r"X:\KaiScribe\Daten\senf"]
IBL_ORDNER = r"X:\IBL-Vorbefunde"
VERBOTEN_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COMMIT|EXECUTE|EXEC|CALL|LOCK)\b",
                          re.I)
GESCHLECHT_SPALTEN = ("SEX", "GESCHLECHT", "SEXUS", "GENDER")
IBL_MAX = 1500
TEXT_MAX = 6000


def sql_sicher(sql):
    """Nur lesende Skripte: kein DML/DDL/COMMIT (PL/SQL-Blöcke gibt es hier nicht). Wirft ValueError."""
    ohne_text = re.sub(r"'[^']*'", "''", sql)
    m = VERBOTEN_SQL.search(ohne_text)
    if m:
        raise ValueError("SQL nicht lesend: " + m.group(1).upper())
    if "ROLLBACK" not in sql.upper() or "SET TRANSACTION READ ONLY" not in sql.upper():
        raise ValueError("SQL ohne READ ONLY/ROLLBACK")
    return sql


def liste_sql(casdb, tag):
    if not K.TAG_RE.match(tag):
        raise ValueError("tag")
    nr = "TO_CHAR(l.listdate,'YYYYMMDD') || LPAD(w.numberinlist,3,'0')"
    return sql_sicher(casdb._KOPF + casdb._abschnitt("liste", f"""
SELECT JSON_OBJECT('nr' VALUE {nr}, 'rh' VALUE TO_CHAR(w.numberinlist), 'pid' VALUE TO_CHAR(w.patientid),
  'wer' VALUE LOWER(TRIM(w.ddwer)), 'rt' VALUE TO_CHAR(w.recordtime,'HH24:MI'), 'ob' VALUE w.obletter,
  'gel' VALUE w.obgelesen RETURNING VARCHAR2(4000))
FROM sysadm.warterow w JOIN sysadm.wartelist l ON l.id = w.wartelistid
WHERE l.listdate >= TO_DATE('{tag}','YYYYMMDD') AND l.listdate < TO_DATE('{tag}','YYYYMMDD') + 1
  AND NVL(w.status,'?') <> '!' AND LOWER(TRIM(w.ddwer)) IN ({",".join("'" + k + "'" for k in K.KUERZEL)})
  AND EXISTS (SELECT 1 FROM sysadm.letters t WHERE t.id = w.warterowid)
ORDER BY w.numberinlist;""") + "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n")


def spalten_sql(casdb):
    return sql_sicher(casdb._KOPF + casdb._abschnitt("spalten", """
SELECT column_name FROM all_tab_columns WHERE owner = 'SYSADM' AND table_name = 'PRIVADRESS'
  AND column_name IN ('SEX','GESCHLECHT','SEXUS','GENDER','BIRTHDATEDATE');""") + "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n")


def patient_sql(casdb, pids, sex_spalte):
    ids = ",".join(str(int(p)) for p in pids if str(p).isdigit()) or "0"
    sex = f"'sex' VALUE a.{sex_spalte}, " if sex_spalte in GESCHLECHT_SPALTEN else ""
    return sql_sicher(casdb._KOPF + casdb._abschnitt("patient", f"""
SELECT JSON_OBJECT('pid' VALUE TO_CHAR(p.id), 'name' VALUE a.name, 'vorname' VALUE a.vorname, {sex}
  'geb' VALUE TO_CHAR(a.birthdatedate,'DD.MM.YYYY') RETURNING VARCHAR2(4000))
FROM sysadm.patients p LEFT JOIN sysadm.privadress a ON a.id = p.adressid
WHERE p.id IN ({ids});""") + "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n")


def alter_am(geb, tag):
    try:
        g = dt.datetime.strptime(geb, "%d.%m.%Y").date()
        t = dt.datetime.strptime(tag, "%Y%m%d").date()
        return t.year - g.year - ((t.month, t.day) < (g.month, g.day))
    except (TypeError, ValueError):
        return None


def geschlecht(v):
    s = str(v or "").strip().upper()[:1]
    return {"M": "m", "W": "w", "F": "w", "1": "m", "2": "w"}.get(s, "")


def senf_text(d):
    """Ablage-Inhalt → Senf-Text wie KaiScribe (source_code/senf_anzeige.anzeige, hier nachgebaut: senf_anzeige zieht
    KaiScribes umzug.py, das auf der VM mit dem gleichnamigen Brücken-Modul kollidiert) oder None (läuft/kein Ergebnis)."""
    if not isinstance(d, dict) or str(d.get("status") or "").strip().lower() != "fertig":
        return None
    zeilen = [" ".join(str(z).split()) for z in d.get("zeilen") or [] if str(z).strip()]
    bef = str(d.get("befund") or "").strip().lower()
    if bef == "unauffaellig":
        text = "Senf: unauffällig"
    elif bef == "nicht_beurteilbar":
        text = "\n".join(["Senf: nicht beurteilbar"] + zeilen)
    else:
        text = "\n".join(zeilen) if zeilen else ("Senf: auffällig" if bef == "auffaellig" else "Senf: kein Ergebnis")
    extra = []
    for e in d.get("eintraege") or []:
        if not isinstance(e, dict) or not str(e.get("id") or "").startswith("a_"):
            continue
        for z in e.get("zeilen") or []:
            z = " ".join(str(z).split())
            if z and z not in extra:
                extra.append(z)
        for a in e.get("abgleich") or []:
            if isinstance(a, dict) and str(a.get("art") or "").lower() == "zusatz":
                z = " ".join(str(a.get("text") or "").split())
                if z and z not in extra:
                    extra.append(z)
    extra = [z for z in extra if z not in text.split("\n")]
    if extra:
        text += "\n" + "\n".join(extra)
    return text[:2000]


def senf_lesen(nr):
    for o in SENF_ORDNER:
        p = os.path.join(o, nr + ".json")
        try:
            with open(p, encoding="utf-8-sig") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        return senf_text(d), d
    return None, None


def ibl_lesen(nr):
    """Abholer-Dateien heißen nach der Accession-Nummer (Diktatnummer + 1 Ziffer je Leistung): <nr><z>_<modul>.txt."""
    out, gesehen = [], set()
    for p in sorted(glob.glob(os.path.join(IBL_ORDNER, nr + "*_*.txt"))):
        m = re.fullmatch(re.escape(nr) + r"\d?_([a-z0-9]{2,20})\.txt", os.path.basename(p), re.I)
        if not m:
            continue
        modul = m.group(1).upper()
        if modul in gesehen:
            continue
        gesehen.add(modul)
        try:
            with open(p, encoding="utf-8-sig", errors="replace") as f:
                t = f.read().strip()
        except OSError:
            continue
        if t:
            out.append({"modul": modul, "text": t[:IBL_MAX]})
    return out


def untersuchungen(leistungen):
    out = []
    for l in leistungen or []:
        if l.get("untersuchung") and l.get("text"):
            t = " ".join(str(l["text"]).split())
            if t not in out:
                out.append(t)
    return out


def fall_bauen(b, ausk, pat, tag):
    """→ (haus, anonym) für einen Besuch. ausk = casdb-Auskunft (besuch, leistungen, vorbefund, befundtext)."""
    rh = int(b["rh"])
    fid = f"RH{rh}"
    namen = [x for x in (pat.get("name"), pat.get("vorname")) if x and len(str(x).strip()) >= 2]
    bes = ausk.get("besuch") or {}
    zw = str(bes.get("zuweiser") or "")
    zw_namen = [w for w in re.findall(r"[A-ZÄÖÜ][a-zäöüß\-]{2,}", zw) if w.lower() not in ("dr", "med", "univ", "prof")]
    alle_namen = namen + zw_namen
    geb = pat.get("geb") or None
    leist = [{"kurz": l.get("kurz"), "text": l.get("text"), "modalitaet": l.get("modalitaet")}
             for l in ausk.get("leistungen") or [] if l.get("untersuchung")]
    vb = ausk.get("vorbefund") or None
    senf, _roh = senf_lesen(b["nr"])
    ibl = ibl_lesen(b["nr"])
    loesung = (ausk.get("befundtext") or "")[:TEXT_MAX]
    gemeinsam = {"id": fid, "kuerzel": b["wer"], "zeit": b.get("rt"), "untersuchungen": untersuchungen(ausk.get("leistungen")),
                 "leistungen": leist, "alter": alter_am(geb, tag), "geschlecht": geschlecht(pat.get("sex"))}
    haus = dict(gemeinsam, nr=b["nr"], patient=" ".join(namen), zuweisung=zw, info=bes.get("info") or "",
                ibl=ibl, senf=senf, loesung=loesung,
                vorbefund=({"datum": vb.get("datum"), "kurz": vb.get("kurz"), "text": vb.get("text")} if vb else None))
    hinweise = []

    def anon(text, was):
        t = K.anzeige_maske(text, alle_namen, geb)
        if K.rest_unsicher(t, alle_namen, geb):
            hinweise.append(f"{was} ausgeblendet (Maske unsicher)")
            return ""
        return t
    anonym = dict(gemeinsam,
                  ibl=[{"modul": x["modul"], "text": anon(x["text"], "IB Lab " + x["modul"])} for x in ibl],
                  senf=(anon(senf, "Senf") if senf else None),
                  loesung=anon(loesung, "Lösung"),
                  zuweisung=(anon(bes.get("info") or "", "Zuweisung")[:300] or None),
                  vorbefund=({"datum": vb.get("datum"), "kurz": vb.get("kurz"), "text": anon(vb.get("text"), "Vorbefund")}
                             if vb else None))
    anonym["hinweise"] = hinweise
    return haus, anonym


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--basis", default=r"C:\RaK\kaiscribe_uebung")
    ap.add_argument("--max", type=int, default=120)
    ap.add_argument("--erkunden", action="store_true", help="nur Spalten/Zähler, nichts schreiben")
    a = ap.parse_args()
    if not K.TAG_RE.match(a.tag):
        sys.exit("tag JJJJMMTT")
    import casdb
    e = casdb.Einstellungen({})
    befehl = [casdb.sqlplus_finden(e.sqlplus)]
    anm = casdb.anmeldung_lesen(e.anmeldung)
    if not befehl[0] or not anm:
        print("SPIEGEL FEHLER kein sqlplus/keine Anmeldung")
        sys.exit(1)

    def frage(sql, frist=180):
        _c, aus = casdb.sqlplus_ausfuehren(befehl, e.ziel, anm[0], anm[1], sql_sicher(sql), frist_s=frist)
        _v, _f, abs_, fehler = casdb.abschnitte(aus)
        return abs_, fehler

    abs_, fehler = frage(spalten_sql(casdb))
    spalten = [str(z).strip().upper() for z in abs_.get("spalten") or [] if str(z).strip()]
    sex_spalte = next((s for s in GESCHLECHT_SPALTEN if s in spalten), None)
    print(f"SPIEGEL spalten geschlecht={sex_spalte or '-'} geb={'BIRTHDATEDATE' in spalten} fehler={','.join(fehler) or '-'}")
    abs_, fehler = frage(liste_sql(casdb, a.tag))
    besuche = [b for b in casdb._json_zeilen(abs_.get("liste"))
               if re.fullmatch(r"\d{11}", str(b.get("nr") or "")) and str(b.get("wer") or "") in K.KUERZEL
               and str(b.get("pid") or "").lstrip("0") != TESTPATIENT and str(b.get("rh") or "").isdigit()]
    final = [b for b in besuche if casdb.befundstand({"obletter": b.get("ob"), "obgelesen": b.get("gel")})["vidiert"]
             or str(b.get("ob") or "") == "B"]
    print(f"SPIEGEL liste={len(besuche)} final={len(final)} " +
          " ".join(f"{k}={sum(1 for b in final if b['wer'] == k)}" for k in K.KUERZEL) + f" fehler={','.join(fehler) or '-'}")
    if a.erkunden:
        return
    final = final[:a.max]
    pats = {}
    pids = sorted({b["pid"] for b in final})
    for i in range(0, len(pids), 200):
        abs_, _f = frage(patient_sql(casdb, pids[i:i + 200], sex_spalte))
        for z in casdb._json_zeilen(abs_.get("patient")):
            pats[str(z.get("pid"))] = z
    direkt = casdb.Direkt(e)
    haus_l, anon_l, z = [], [], {"ok": 0, "fehler": 0, "senf": 0, "ibl": 0, "vorbefund": 0, "loesung": 0, "ausgeblendet": 0}
    for b in final:
        ant = direkt.fragen(b["nr"], teile=("besuch", "leistungen", "vorbefund", "mammo", "brief"), frist_s=120)
        if not ant.ok or not (ant.daten or {}).get("gefunden"):
            z["fehler"] += 1
            continue
        h, an = fall_bauen(b, ant.daten, pats.get(str(b["pid"]), {}), a.tag)
        haus_l.append(h)
        anon_l.append(an)
        z["ok"] += 1
        z["senf"] += bool(an.get("senf"))
        z["ibl"] += bool(an.get("ibl"))
        z["vorbefund"] += bool(an.get("vorbefund"))
        z["loesung"] += bool(an.get("loesung"))
        z["ausgeblendet"] += len(an.get("hinweise") or [])
    ziel = os.path.join(a.basis, "daten", a.tag)
    os.makedirs(ziel, exist_ok=True)
    stand = K.jetzt().isoformat(timespec="seconds")
    for name, faelle in (("haus", haus_l), ("anonym", anon_l)):
        d = {"tag": a.tag, "variante": name, "stand": stand, "version": K.VERSION, "faelle": faelle,
             "senf_fehlt": sum(1 for f in faelle if not f.get("senf"))}
        tmp = os.path.join(ziel, name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(ziel, name + ".json"))
    print("SPIEGEL " + json.dumps(z) + " " + " ".join(f"{k}={sum(1 for f in anon_l if f['kuerzel'] == k)}" for k in K.KUERZEL))


if __name__ == "__main__":
    main()
