#!/usr/bin/env python3
"""KaiScribe Chirp-Warnung → Kanban (kaiscribe-sonnet-n3-beleg, 17.11.2026) — am MAC, täglicher Cron 20:30 (Zustellung local).

  python3 kaiscribe_chirp_warnung.py --vmssh <ris-mods>/automaten_vm/mac/vmssh.py [--tag JJJJ-MM-TT] [--trocken] [--beleg]

Lädt tools/vm/kaiscribe_nutzung_lesen.py auf die Automaten-VM, startet es dort als rakauto (X: nur lesen, über
C:\\RaK\\tmp\\n10_interaktiv.ps1 wie ks_kontrolle.ps1) und bekommt nur Zähler zurück (Tagesbericht, Monatszähler je PC,
Lauf-Dateien je Rechner/Modell/Version). Warnung, wenn
  - der Tagesbericht der EXE die Zeile „WARNUNG“ hat oder X:\\KaiScribe\\Daten\\nutzung\\warnung_<JJJJ-MM>.txt da ist, oder
  - die eigene Hochrechnung aus den Monatszählern (source_code/nutzung.py, ab dem ersten Tag mit Daten, Chirp + Live-
    Anzeige/Streaming, sobald die EXE die Live-Sekunden zählt) > 6 € liegt
    (die EXE bis 3.19.4 teilt durch den Tag des Monats und rechnet den November viel zu niedrig).
Dann genau EINE Kanban-Karte je Monat (Spalte peter).
kaiscribe-stt-tagesdeckel-n1 (24.11.2026): steht im Tagesbericht (heute oder gestern) eine Zeile „STT-DECKEL <PC> …“
(80 % der harten Tagesgrenze, Grenze erreicht oder Schleifenbremse), dann EINE Karte je Tag und PC für Hermes (Spalte
tun, nicht Peter): nachsehen, warum so viel Audio an Google ging. Dazu je Rechner der letzte Lauf (Modell, KaiScribe-Version) in den
Zustand; schreibt ein Rechner noch über Gemini (ohne „Rückfall“) oder mit KaiScribe < 3.19.0, einmal je Rechner und
Version die Karte „KaiScribe an <PC> einmal schließen/neu starten“. Zustand: ~/.hermes/work/kaiscribe-chirp/zustand.json und Titelsuche
in der Kartei (falls der Zustand fehlt). Keine Google-Quota-Änderung, keine Meldung.
Still bei Erfolg (keine Warnung oder Karte schon da); Fehler → Exit 1 + stderr (Cron-Doktor).
--trocken: nichts anlegen, Ergebnis ausgeben. --beleg: Tabelle je Rechner (für Berichte) ausgeben.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HIER))
sys.path.insert(0, os.path.join(REPO, "source_code"))
import nutzung  # noqa: E402

LESER = os.path.join(REPO, "tools", "vm", "kaiscribe_nutzung_lesen.py")
VM_DIR = "C:\\RaK\\einrichtung\\ks_nutzung"
KANBAN = os.path.expanduser("~/.hermes/scripts/kanban.py")
KARTEI = os.path.expanduser("~/.hermes/work/kanban/karten.json")
ZUSTAND = os.path.expanduser("~/.hermes/work/kaiscribe-chirp/zustand.json")
TITEL = "KaiScribe: Google-Spracherkennung hochgerechnet {eur} €/Monat ({monat}, > 6 €)"
TITEL_MARKE = "KaiScribe: Google-Spracherkennung hochgerechnet"

HUELLE = r"""param([string]$A = '')
if ($A -notmatch '^[A-Za-z0-9 _:,\-]*$') { 'NUTZUNG_LESEN=fehler GRUND=Argumente'; exit 1 }
$d = '%s'
$s = Join-Path $d 'ks_nutzung_lauf.ps1'
Set-Content -Path $s -Encoding UTF8 -Value "& cmd.exe /c C:\RaK\laufwerke.cmd C:\Windows\py.exe -3.12 -X utf8 $d\kaiscribe_nutzung_lesen.py $A 2>&1 | ForEach-Object { `"`$_`" }; 'KSN_RC=' + `$LASTEXITCODE"
& 'C:\RaK\tmp\n10_interaktiv.ps1' -Skript $s -Frist 300
""" % VM_DIR


def vm_lesen(vmssh, tage, ohne_laeufe=False):
    """Leser hochladen + als rakauto starten → Ausgabe (nur Zähler)."""
    r = subprocess.run([sys.executable, vmssh, "--hochladen", LESER, VM_DIR + "\\kaiscribe_nutzung_lesen.py"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise RuntimeError("Hochladen fehlgeschlagen: " + (r.stdout + r.stderr).strip()[-300:])
    args = "--tage " + ",".join(tage) + (" --ohne-laeufe" if ohne_laeufe else "")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "ks_nutzung.ps1")
        with open(p, "w", encoding="utf-8") as f:
            f.write(HUELLE)
        env = dict(os.environ, VM_ARGS="-A '%s'" % args, VM_TIMEOUT="420")
        env.pop("VM_STDIN", None)
        r = subprocess.run([sys.executable, vmssh, p], capture_output=True, text=True, env=env, timeout=500)
    aus = r.stdout
    if "NUTZUNG_LESEN=fertig" not in aus or "KSN_RC=0" not in aus:
        raise RuntimeError("VM-Lesen ohne Ergebnis: " + (aus + r.stderr).strip()[-500:])
    return aus


def auswerten(aus, tag):
    """Ausgabe von kaiscribe_nutzung_lesen.py → {monat, chirp_min, eur, hoch_eur, tage, erster, warn_exe, warn_eigen, …}."""
    monat = tag[:7]
    alle, laeufe = {}, []
    warn_datei, bericht, im_bericht = False, [], None
    deckel = []      # tagesdeckel-n1: (tag, zeile) aus den Tagesberichten von heute und gestern
    for z in aus.splitlines():
        m = re.match(r"^NUTZUNG (\d{4}-\d\d) (\S+) (\d{4}-\d\d-\d\d) (.*)$", z)
        if m and m.group(1) == monat:
            w = dict(x.split("=", 1) for x in m.group(4).split() if "=" in x)
            td = {"befunde": int(w.get("befunde", 0)), "ki": {k: int(w.get(k, 0)) for k in ("anthropic", "gemini", "rueckfall")},
                  "anthropic_usd": float(w.get("usd", 0)), "stt_s": {"chirp": float(w.get("chirp_s", 0)), "streaming": float(w.get("stream_s", 0))}, "rueckfall_grund": {}}
            for g in (w.get("gruende") or "-").split(";"):
                if ":" in g:
                    k, n = g.rsplit(":", 1)
                    td["rueckfall_grund"][k] = int(n)
            alle.setdefault(m.group(2), {"pc": m.group(2), "tage": {}})["tage"][m.group(3)] = td
            continue
        m = re.match(r"^LAUF (\S+) (.*)$", z)
        if m:
            w = dict(x.split("=", 1) for x in m.group(2).split() if "=" in x)
            w["tag"] = m.group(1)
            laeufe.append(w)
            continue
        if z.startswith("WARNDATEI %s " % monat):
            warn_datei = z.endswith(" ja")
        if z.startswith("TAGESBERICHT "):
            im_bericht = z.split()[1]
            continue
        if z.startswith("| STT-DECKEL ") and im_bericht:
            deckel.append((im_bericht, z[2:]))
        if z.startswith("| ") and im_bericht == tag:
            bericht.append(z[2:])
        elif not z.startswith("| "):
            im_bericht = None
    chirp_s = sum(td["stt_s"]["chirp"] for d in alle.values() for t_, td in d["tage"].items() if t_ <= tag)
    stream_s = sum(td["stt_s"]["streaming"] for d in alle.values() for t_, td in d["tage"].items() if t_ <= tag)
    erster = nutzung.erster_tag(alle)
    hoch = nutzung.hochrechnung_eur(chirp_s, tag, erster, stream_s)
    return {"monat": monat, "tag": tag, "chirp_min": chirp_s / 60.0, "stream_min": stream_s / 60.0,
            "eur": nutzung.chirp_eur(chirp_s) + nutzung.stream_eur(stream_s), "hoch_eur": hoch,
            "tage": nutzung.gezaehlte_tage(tag, erster), "erster": erster, "pcs": alle, "laeufe": laeufe,
            "bericht": bericht, "deckel": deckel, "warn_exe": warn_datei or any(b.startswith("WARNUNG") for b in bericht),
            "warn_eigen": nutzung.warnung_noetig(hoch, tag, erster)}


def karte_text(e):
    befunde = sum(td["befunde"] for d in e["pcs"].values() for td in d["tage"].values())
    rf = sum(td["ki"]["rueckfall"] for d in e["pcs"].values() for td in d["tage"].values())
    je_pc = ", ".join("%s %.0f min" % (pc, sum(td["stt_s"]["chirp"] + td["stt_s"]["streaming"]
                                               for td in d["tage"].values()) / 60) for pc, d in sorted(e["pcs"].items()))
    return ("Google-Spracherkennung %s bis %s: Chirp %.1f min (0,016 $/min) + Live-Anzeige %.1f min (0,024 $/min) ≈ "
            "%.2f €, hochgerechnet %.2f €/Monat aus %d Tagen (Grenze 6 €, Google-Gutschrift ~9 €/Monat). Je PC: %s. Befund-KI im Monat: %d Befunde über Claude, %d "
            "Rückfälle auf Gemini. Quelle: X:\\KaiScribe\\Daten\\nutzung (Tagesbericht %s%s). Entscheiden: a) so lassen "
            "(Mehrkosten zahlen) b) Budget/Gutschrift prüfen c) Spracherkennung billiger (Folgejob). Keine automatische "
            "Quota-Änderung." % (e["erster"] or e["monat"] + "-01", e["tag"], e["chirp_min"], e["stream_min"], e["eur"],
                                 e["hoch_eur"], e["tage"], je_pc or "–", befunde, rf, e["tag"],
                                 ", EXE-Zeile WARNUNG" if e["warn_exe"] else ", eigene Hochrechnung"))


def _zustand():
    try:
        with open(ZUSTAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def karte_schon_da(monat, kartei=None):
    kartei = kartei or KARTEI
    if monat in (_zustand().get("karten") or {}):
        return True
    try:
        with open(kartei, encoding="utf-8") as f:
            karten = json.load(f).get("karten", [])
    except (OSError, ValueError):
        return False
    return any(TITEL_MARKE in (k.get("titel") or "") and "(%s," % monat in (k.get("titel") or "") for k in karten)


def karte_anlegen(e):
    titel = TITEL.format(eur=("%.2f" % e["hoch_eur"]).replace(".", ","), monat=e["monat"])
    r = subprocess.run([sys.executable, KANBAN, "neu", titel, "--peter", "--was", karte_text(e),
                        "--kurz", "KaiScribe Spracherkennung > 6 €/Monat: a/b/c", "--auftrag", "kaiscribe-chirp-warnung"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError("kanban.py neu: " + (r.stdout + r.stderr).strip()[-300:])
    m = re.match(r"^#(\d+)", r.stdout.strip())
    z = _zustand()
    z.setdefault("karten", {})[e["monat"]] = {"karte": int(m.group(1)) if m else None, "hoch_eur": round(e["hoch_eur"], 2),
                                              "angelegt": datetime.datetime.now().isoformat(timespec="minutes")}
    os.makedirs(os.path.dirname(ZUSTAND), exist_ok=True)
    with open(ZUSTAND + ".tmp", "w", encoding="utf-8") as f:
        json.dump(z, f, ensure_ascii=False, indent=1)
    os.replace(ZUSTAND + ".tmp", ZUSTAND)
    return r.stdout.strip()


DECKEL_TITEL = "KaiScribe: Tagesdeckel Spracherkennung {pc} {tag}"


def deckel_karten(e, anlegen=True):
    """tagesdeckel-n1: je (Tag, PC) mit „STT-DECKEL“-Zeile EINE Karte für Hermes (Spalte tun). Rückgabe: neue Schlüssel."""
    z = _zustand()
    schon = z.setdefault("deckel_karten", {})
    neu = []
    for tag, zeile in e.get("deckel") or []:
        m = re.match(r"^STT-DECKEL (\S+?):", zeile)
        pc = m.group(1) if m else "?"
        schluessel = "%s %s" % (tag, pc)
        if schluessel in schon or schluessel in neu:
            continue
        if anlegen:
            r = subprocess.run([sys.executable, KANBAN, "neu", DECKEL_TITEL.format(pc=pc, tag=tag), "--tun",
                                "--was", "%s (Tagesbericht %s). Harte Schutzgrenze aus config.ini STT_TAGESDECKEL_MIN "
                                "(Standard 240 min/PC/Tag), normal 15–30 min. Prüfen: rakscribe.log am PC (Zeilen "
                                "[STT-DECKEL]), Schleife/Wiederholungen? Zähler %%APPDATA%%\\KaiScribe\\"
                                "stt_tagesdeckel_<PC>.json, gesicherte Aufnahmen %%APPDATA%%\\KaiScribe\\nicht_erkannt."
                                % (zeile, tag),
                                "--kurz", "KaiScribe Tagesdeckel %s" % pc, "--auftrag", "kaiscribe-stt-tagesdeckel"],
                               capture_output=True, text=True, timeout=60)
            if r.returncode:
                raise RuntimeError("kanban.py neu (Deckel): " + (r.stdout + r.stderr).strip()[-300:])
            schon[schluessel] = datetime.datetime.now().isoformat(timespec="minutes")
        neu.append(schluessel)
    if anlegen and neu:
        os.makedirs(os.path.dirname(ZUSTAND), exist_ok=True)
        with open(ZUSTAND + ".tmp", "w", encoding="utf-8") as f:
            json.dump(z, f, ensure_ascii=False, indent=1)
        os.replace(ZUSTAND + ".tmp", ZUSTAND)
    return neu


MIN_VERSION = (3, 19, 0)


def _version(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v or ""))[:3]) or (0,)


def alte_rechner(laeufe):
    """Läufe → {rechner: lauf} für Rechner, deren LETZTER Lauf noch alt ist (Gemini ohne Rückfall oder < 3.19.0)."""
    letzte = {}
    for w in sorted(laeufe, key=lambda w: (w["tag"], w.get("bis", ""))):
        letzte[w.get("rechner", "?")] = w
    return {pc: w for pc, w in letzte.items()
            if (str(w.get("modell", "")).startswith("gemini") and "ckfall" not in str(w.get("modell", "")))
            or _version(w.get("kaiscribe")) < MIN_VERSION}


def rechner_merken(e, anlegen=True):
    """Letzten Lauf je Rechner in den Zustand; alte Rechner → einmal je Rechner+Version eine Peter-Karte."""
    z = _zustand()
    r = z.setdefault("rechner", {})
    for w in sorted(e["laeufe"], key=lambda w: (w["tag"], w.get("bis", ""))):
        r[w.get("rechner", "?")] = {k: w.get(k) for k in ("tag", "bis", "modell", "kaiscribe")}
    neu = []
    for pc, w in alte_rechner(e["laeufe"]).items():
        schluessel = "%s %s %s" % (pc, w.get("kaiscribe"), w.get("modell"))
        if schluessel in z.setdefault("alt_karten", {}):
            continue
        if anlegen:
            subprocess.run([sys.executable, KANBAN, "neu", "KaiScribe an %s einmal schließen/neu starten" % pc, "--peter",
                            "--was", "KaiScribe an %s läuft noch mit %s / %s (letzter Lauf %s %s). Bitte KaiScribe dort "
                            "einmal schließen und neu starten (holt die aktuelle Version von X:, Befund-KI Claude)."
                            % (pc, w.get("kaiscribe"), w.get("modell"), w["tag"], w.get("bis")),
                            "--kurz", "KaiScribe %s neu starten" % pc, "--auftrag", "kaiscribe-chirp-warnung"],
                           check=True, capture_output=True, text=True, timeout=60)
            z["alt_karten"][schluessel] = datetime.datetime.now().isoformat(timespec="minutes")
        neu.append(schluessel)
    if anlegen:
        os.makedirs(os.path.dirname(ZUSTAND), exist_ok=True)
        with open(ZUSTAND + ".tmp", "w", encoding="utf-8") as f:
            json.dump(z, f, ensure_ascii=False, indent=1)
        os.replace(ZUSTAND + ".tmp", ZUSTAND)
    return neu


def beleg_tabelle(e):
    z = ["| Tag | Rechner | Modell | KaiScribe | Läufe |", "|---|---|---|---|---|"]
    for w in sorted(e["laeufe"], key=lambda w: (w["tag"], w.get("rechner", ""))):
        z.append("| %s | %s | %s | %s%s | %s (%s–%s) |" % (w["tag"], w.get("rechner"), w.get("modell"), w.get("kaiscribe"),
                                                         " Maske" if w.get("maske") == "ja" else "", w.get("anzahl"),
                                                         w.get("von"), w.get("bis")))
    return "\n".join(z)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--vmssh", required=True)
    ap.add_argument("--tag", default=str(datetime.date.today()))
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--beleg", action="store_true")
    a = ap.parse_args(argv)
    gestern = str(datetime.date.fromisoformat(a.tag) - datetime.timedelta(days=1))
    aus = vm_lesen(a.vmssh, [gestern, a.tag])
    e = auswerten(aus, a.tag)
    if a.beleg:
        print(beleg_tabelle(e))
    warn = e["warn_exe"] or e["warn_eigen"]
    if a.trocken or a.beleg:
        print("CHIRP %s: Chirp %.1f min + Live %.1f min ≈ %.2f €, hochgerechnet %.2f €/Monat aus %d Tagen, warn_exe=%s warn_eigen=%s karte_da=%s"
              % (e["tag"], e["chirp_min"], e["stream_min"], e["eur"], e["hoch_eur"], e["tage"], e["warn_exe"], e["warn_eigen"],
                 karte_schon_da(e["monat"])))
        if warn:
            print("KARTE (trocken): " + karte_text(e))
        print("ALTE_RECHNER %s" % (", ".join(rechner_merken(e, anlegen=False)) or "keine"))
        print("DECKEL %s" % (", ".join(deckel_karten(e, anlegen=False)) or "keine"))
        return 0
    if warn and not karte_schon_da(e["monat"]):
        karte_anlegen(e)      # still: die Karte selbst ist die Meldung
    rechner_merken(e)
    deckel_karten(e)          # tagesdeckel-n1: Karte für Hermes, nicht für Peter
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as ex:   # Cron-Doktor
        sys.stderr.write("KaiScribe Chirp-Warnung fehlgeschlagen: %s: %s\n" % (type(ex).__name__, ex))
        sys.exit(1)
