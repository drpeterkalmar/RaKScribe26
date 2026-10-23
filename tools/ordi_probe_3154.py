r"""Probelauf RaKScribe 3.15.4 (ab 3.15.5 mit --version/--prompt) am Büro-PC — für den Ordi-Hermes, nur
Python-Standardbibliothek, synthetische Texte.

Startet die gelieferte rakscribe26.exe im eingebauten Selbsttest als GAST (wie der Probelauf der Mammo-Maske): eigene
Ordner (APPDATA/LOCALAPPDATA im Arbeitsordner), kein SpeechMike-Gerät (Tasten nur über den Selbsttest, derselbe
Dekodierer), keine globalen F9/F10, kein Autostart-Abgleich, nichts in den Vordergrund, Mikrofon/Google/chirp_3/Korrektur
durch Attrappen ersetzt (FAKEAUDIO), Test-Schlüssel = wertloser Dummy. Eine schon laufende RaKScribe bleibt unberührt
(eigener Mutex, eigener Auftragsordner). Die EXE beendet sich selbst (Phase „ende“, Sicherheitsnetz RAKSCRIBE_SELFTEST_ENDE);
nur wenn sie trotzdem hängt, beendet das Skript GENAU diesen einen Prozess, den es selbst gestartet hat.

Fälle (Peter 15.10.2026): A1 SpeechMike Ambient erkannt → Hilfezeile Play/Command, Play übernimmt, Command = Maske aus/an;
A2 Text im grauen Vorbefund markiert + Record → nur die Markierung ersetzt; A3 Tippen in der Pause; A4 F3/F4 auf der
Tastatur; A5 SpeechMike III/Premium → Hilfezeile F3/F4 wie bisher; E1/E2 CAS-Befund rechts: Record → Pause → in den
Befund geklickt → Record → INS = Diktat an der Stelle (auch mit „Nur Text“); B1 CAS-Leistung beidseits + Diktat
„… links unauffällig“ → „… beidseits …“ (Normalbefund ohne KI); K1 Häkchen-Farbe im Menü; P1 (nur mit --prompt):
eingebauter Befund-Prompt hat den erwarteten Versionsmarker (v3.15.5: umschriebene Skelettbefunde).

Aufruf:  py -3.12 ordi_probe_3154.py --exe <rakscribe26.exe> --arbeit <neuer Arbeitsordner> --schluessel <dummy_key.json>
         [--version 3.15.5 --prompt 2026-10-15-v3155-umschriebene-befunde]
Ausgabe: Tabelle (Fall | erwartet | beobachtet | ok) + SHA256 der Tabelle, <Arbeitsordner>\ergebnis.json; Exit 0 = alles ok.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

VB_TEXT = ("Mammographie beidseits – Screening\n\nInspektion und Palpation: Unauffällig.\n\nMammographie: Verglichen mit "
           "05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen sowie Gefäßverkalkungen. Im Übrigen "
           "unauffällig strukturierter Drüsenkörper. Cutis und Subcutis unauffällig.\n\nSonographie: Keine suspekten "
           "mammären oder axillären Veränderungen.\n\nErgebnis:\nMastopathie mit insuspekten Verkalkungen.\nACR: 2\n"
           "BIRADS: 2")
VB = {"nr": "20991231001", "datum": "2024-06-05", "untersuchung": "Mammographie bds. Screening", "text": VB_TEXT,
      "zeichen": len(VB_TEXT), "gekuerzt": False, "werte": {"acr": "2", "birads": "2"}, "mammo": True}
A_MAMMO = ("Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen sowie Gefäßverkalkungen. "
           "Neu aufgetretener Herd links oben außen. Cutis und Subcutis unauffällig.")
TESTBEFUND = ("## TEST RaKScribe-Brücke – bitte nicht vidieren\n\n## Befund\nTESTBEFUND ohne Diktat und ohne Patientenbezug. "
              "Dieser Text prüft nur die Übergabe von RaKScribe an CAS.\n\n## Ergebnis\nTEST – bitte nicht vidieren.")


def _l(kurz, text, mod, vorlage, mammo=None, seite=None):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "mammo": mammo}


L_MAMS = _l("t-mammo-scr", "Mammographie bds. Screening", "Röntgen", "mammographie_beidseits", "screening")
L_SONO = _l("t-mamma-sono", "Ultraschall der Mamma o.V.", "Sono", "mammasonographie_beidseits")
L_HG_BDS = _l("t-hg-bds", "Handgelenk bds.", "Röntgen", "handgelenk_in_2_ebenen", seite="beidseits")


def prozesse():
    """Laufende rakscribe26-Prozesse (PIDs) — nur lesen (tasklist, Ausgabe tolerant dekodiert)."""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=30).stdout
        txt = out.decode("utf-8", errors="replace") if out else ""
    except Exception:
        return []
    pids = []
    for z in txt.splitlines():
        t = [x.strip('"') for x in z.split('","')]
        if t and t[0].lower().startswith("rakscribe26"):
            pids.append(t[1] if len(t) > 1 else "?")
    return sorted(pids)


class Lauf:
    def __init__(self, exe, arbeit, schluessel, sekunden, version="3.15.4", prompt=""):
        self.arbeit = os.path.abspath(arbeit)
        self.version, self.prompt = version, prompt
        self.exe_quelle, self.schluessel, self.sekunden = exe, schluessel, sekunden
        self.state = os.path.join(self.arbeit, "selbsttest.json")
        self.cas = os.path.join(self.arbeit, "localappdata", "RaKScribe")
        self.zeilen, self.dumps, self.p = [], {}, None

    def _datei(self, name, d):
        os.makedirs(self.cas, exist_ok=True)
        ziel = os.path.join(self.cas, name)
        with open(ziel + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(ziel + ".tmp", ziel)

    def auftrag(self, nr, aid, leistungen, vb=None):
        self._datei("cas_auftrag.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp",
                                         "bruecke_pid": os.getpid(), "zeit": time.time(), "zeit_text": "",
                                         "testbefund": False})
        time.sleep(2.0)
        self._datei(f"cas_leistungen_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "roh": "Probe",
                                                   "leistungen": leistungen, "quelle": "CAS-Datenbank",
                                                   "katalog": "Probe", "ms": 300, "zeit": time.time()})
        if vb is not None:
            self._datei(f"cas_kontext_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "quelle": "CAS-Datenbank",
                                                    "zuweiser": "", "info": "", "befunder": "kp", "vorbefund": vb,
                                                    "zeit": time.time()})

    def _lesen(self):
        try:
            with open(self.state, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def warten(self, phase, frist=40):
        t0 = time.time()
        while time.time() - t0 < frist:
            d = self._lesen()
            if phase in d:
                return d[phase]
            if self.p is not None and self.p.poll() is not None:
                return None
            time.sleep(0.3)
        return None

    def ph(self, name, warten=0.0, frist=40):
        if warten:
            time.sleep(warten)
        with open(self.state + ".trigger", "w", encoding="utf-8") as f:
            f.write(name)
        z = self.warten(name, frist)
        self.dumps[name] = z
        return z or {}

    def check(self, fall, erwartet, beobachtet, ok):
        self.zeilen.append((fall, erwartet, str(beobachtet)[:160].replace("\n", " ").replace("|", "/"), bool(ok)))

    def starten(self):
        if os.path.exists(self.arbeit):
            raise SystemExit(f"Arbeitsordner {self.arbeit} gibt es schon – bitte einen neuen angeben")
        os.makedirs(os.path.join(self.arbeit, "exe"))
        os.makedirs(os.path.join(self.arbeit, "appdata", "RaKScribe"))
        os.makedirs(self.cas)
        exe = os.path.join(self.arbeit, "exe", "rakscribe26.exe")
        shutil.copyfile(self.exe_quelle, exe)
        shutil.copyfile(self.schluessel, os.path.join(self.arbeit, "appdata", "RaKScribe", "rakscribe-praxis-key.json"))
        env = dict(os.environ, APPDATA=os.path.join(self.arbeit, "appdata"),
                   LOCALAPPDATA=os.path.join(self.arbeit, "localappdata"), RAKSCRIBE_SELFTEST=self.state,
                   RAKSCRIBE_SELFTEST_FAKEAUDIO="1", RAKSCRIBE_SELFTEST_GAST="1",
                   RAKSCRIBE_SELFTEST_ENDE=str(self.sekunden), RAKSCRIBE_SELFTEST_GEOMETRY="1240x820+40+40")
        self.t0 = time.time()
        self.p = subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env)
        st = self.warten("ready", 120)
        self.check("V0", f"EXE startet als Gast-Selbsttest, Version {self.version}, bereit",
                   f"{(st or {}).get('title')} / {(st or {}).get('status')} / {round(time.time() - self.t0, 1)} s",
                   bool(st) and any(f"{n} {self.version} " in str(st.get("title")) for n in ("KaiScribe", "RaKScribe")) and st.get("status") == "READY")
        if self.prompt:
            self.check("P1", f"eingebauter Befund-Prompt = {self.prompt}",
                       f"{(st or {}).get('prompt_version')} / {(st or {}).get('prompt_quelle')}",
                       (st or {}).get("prompt_version") == self.prompt)
        return bool(st)

    def beenden(self):
        if self.p is None:
            return
        try:
            with open(self.state + ".trigger", "w", encoding="utf-8") as f:
                f.write("ende")
            rc = self.p.wait(timeout=45)
            self.check("V99", "RaKScribe beendet sich selbst (Phase „ende“)", f"Exit {rc}", rc == 0)
        except subprocess.TimeoutExpired:
            self.p.kill()            # nur DIESER eine, selbst gestartete Prozess
            self.check("V99", "RaKScribe beendet sich selbst (Phase „ende“)", "hing – eigener Prozess beendet", False)

    def faelle(self):
        def m(d, feld=None, std=None):
            z = (d or {}).get("maske") or {}
            return z if feld is None else z.get(feld, std)

        def q(d):
            return [f.get("quelle") for f in m(d, "felder", []) or []]

        self.auftrag("20991231301", "probe-a1", [L_MAMS, L_SONO], VB)
        d = self.ph("cas_status#a0", 1.5)
        self.check("A0", "Mammo-Maske gezeigt, 4 Felder Vorbefund; ohne SpeechMike Hilfezeile mit Tastatur (F3/F4)",
                   f"{q(d)} / {m(d, 'hilfe')}", q(d) == ["vorbefund"] * 4
                   and "Bild↓/Bild↑ = Feld · F3 = übernehmen · F4 = Maske aus" in str(m(d, "hilfe")))
        d = self.ph("geraet#ambient")
        self.check("A1a", "SpeechMike Ambient erkannt → Hilfezeile „Play = übernehmen · Command = Maske aus“, ohne F3",
                   m(d, "hilfe"), "Play = übernehmen · Command = Maske aus" in str(m(d, "hilfe"))
                   and "F3" not in str(m(d, "hilfe")))
        d = self.ph("sm_PLAY#a1")
        self.check("A1b", "Play → Inspektion übernommen", q(d), q(d)[:1] == ["uebernommen"])
        a, b = self.ph("sm_COMMAND#a1"), self.ph("sm_COMMAND#a2")
        self.check("A1c", "Command → Maske aus, Command → wieder an", f"{m(a, 'an')} / {m(b, 'an')}",
                   m(a, "an") is False and m(b, "an") is True)
        self.ph("sm_FF#a1")
        self.ph("maske_markieren#1|109|160")
        self.ph("chirp#neu aufgetretener Herd links oben außen")
        self.ph("sm_RECORD#a1")
        d = self.ph("sm_RECORD#a2", 1.5)
        f1 = (m(d, "felder") or [{}, {}])[1]
        self.check("A2", "Markierung im grauen Vorbefund + Record → nur die Markierung ersetzt (getippt), Pause",
                   f"{f1.get('quelle')} / {str(f1.get('text'))[:90]}", f1.get("quelle") == "getippt"
                   and str(f1.get("text", "")).startswith(A_MAMMO[:200]) and d.get("job_zustand") == "PAUSED")
        d = self.ph("maske_tippen#2|Keine suspekten Herde.")
        self.check("A3", "In der Pause tippen → getippt", f"{q(d)} / {d.get('job_zustand')}",
                   q(d)[2:3] == ["getippt"] and d.get("job_zustand") == "PAUSED")
        self.ph("sm_FF#a2")
        self.ph("sm_FF#a3")
        d = self.ph("kb_F3#a1")
        self.check("A4a", "F3 auf der Tastatur → Ergebnis übernommen", q(d), q(d)[3:] == ["uebernommen"])
        d = self.ph("sm_INS#a1", 1.0)
        r = str(d.get("result_voll") or "")
        self.check("A4b", "INS → Befund mit eingesetztem Satz und getippter Sonographie", r[:120],
                   "Mammographie: " + A_MAMMO in r and "Sonographie: Keine suspekten Herde." in r)
        a, b = self.ph("kb_F4#a1"), self.ph("kb_F4#a2")
        self.check("A4c", "F4 auf der Tastatur → Maske aus/an", f"{m(a, 'an')} / {m(b, 'an')}",
                   m(a, "an") is False and m(b, "an") is True)
        d = self.ph("geraet#premium")
        self.check("A5", "SpeechMike III/Premium → Hilfezeile wie bisher (F3/F4)", m(d, "hilfe"),
                   "F3 = übernehmen · F4 = Maske aus" in str(m(d, "hilfe")))
        self.ph("geraet#auto")
        self.ph("cas_abbrechen#a1")
        self.auftrag("20991231302", "probe-e1", [L_HG_BDS])
        self.ph("cas_status#e0", 1.5)
        self.ph("cas_testbefund#e1")
        self.ph("diktat_setzen#Handgelenk links SL-Spalt erweitert")
        self.ph("befund_fokus_weg#e1")
        self.ph("chirp#zusätzlich kleiner Gelenkerguss|zusätzlich kleiner Gelenkerguss")
        self.ph("sm_RECORD#e1")
        self.ph("sm_RECORD#e2", 1.0)
        self.ph("befund_markieren#" + str(TESTBEFUND.index("Dieser Text")))
        w = self.ph("sm_RECORD#e3")
        d = self.ph("sm_INS#e1", 1.5)
        r = str(d.get("result_voll") or "")
        self.check("E1", "CAS-Befund: Record → Pause → in den Befund geklickt → Record → INS = Diktat an der Stelle",
                   f"Ziel {w.get('einfuegen_ziel')} / {r[60:170]}", w.get("einfuegen_ziel") is not None
                   and "ohne Patientenbezug. Zusätzlich kleiner Gelenkerguss Dieser Text prüft nur" in r)
        self.ph("nur_text_an#e1")
        self.ph("chirp#ersetzt|ersetzt")
        self.ph("befund_fokus_weg#e2")
        self.ph("sm_RECORD#e4")
        self.ph("sm_RECORD#e5", 1.0)
        i0 = TESTBEFUND.index("TESTBEFUND ohne")
        self.ph(f"befund_markieren#{i0}|{i0 + len('TESTBEFUND')}")
        self.ph("sm_RECORD#e6")
        d = self.ph("sm_INS#e2", 1.5)
        r = str(d.get("result_voll") or "")
        self.check("E2", "… mit „Nur Text“: Markierung durch das Diktat ersetzt (kein Befundumbau)", r[40:150],
                   "## Befund\nErsetzt ohne Diktat und ohne Patientenbezug." in r)
        self.ph("nur_text_aus#e1")
        self.ph("cas_abbrechen#e1")
        self.auftrag("20991231303", "probe-b1", [L_HG_BDS])
        self.ph("cas_status#b0", 1.5)
        d = self.ph("text_ins#b1|Handgelenk links unauffällig", 1.0)
        r = str(d.get("result_voll") or d.get("result") or "")
        self.check("B1", "CAS-Leistung beidseits + Diktat „Handgelenk links unauffällig“ → „Handgelenk beidseits in 2 "
                   "Ebenen“, Ergebnis beidseits (ohne KI)", r[:120], r.startswith("## Handgelenk beidseits in 2 Ebenen")
                   and "beidseits." in r.split("## Ergebnis")[-1])
        self.ph("cas_abbrechen#b1")
        self.check("K1", "Häkchen im ☰-Menü weiß, Schalter „Nur Text“ mit Rahmen", f"{d.get('menu_haken')} / "
                   f"{d.get('nur_text_switch')}", d.get("menu_haken") == "#FFFFFF"
                   and str((d.get("nur_text_switch") or {}).get("border_width")) == "2")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--arbeit", required=True)
    ap.add_argument("--schluessel", required=True, help="wertloser Test-Schlüssel (z. B. dummy_key.json des Probelaufs)")
    ap.add_argument("--sekunden", type=int, default=300, help="Sicherheitsnetz: die EXE endet spätestens danach")
    ap.add_argument("--version", default="3.15.4", help="erwartete Version im Fenstertitel")
    ap.add_argument("--prompt", default="", help="erwarteter Versionsmarker des eingebauten Befund-Prompts (Fall P1)")
    a = ap.parse_args(argv)
    vorher = prozesse()
    lauf = Lauf(a.exe, a.arbeit, a.schluessel, a.sekunden, a.version, a.prompt)
    try:
        if lauf.starten():
            lauf.faelle()
    finally:
        lauf.beenden()
    time.sleep(2)
    nachher = prozesse()
    lauf.check("V100", "laufende RaKScribe-Prozesse vorher = nachher (fremde unberührt, eigener weg)",
               f"vorher {vorher} / nachher {nachher}", vorher == nachher)
    zeilen = ["| Fall | erwartet | beobachtet | ok |", "|---|---|---|---|"]
    zeilen += [f"| {f} | {e} | {b} | {'ja' if o else 'NEIN'} |" for f, e, b, o in lauf.zeilen]
    tabelle = "\n".join(zeilen)
    sha = hashlib.sha256(tabelle.encode("utf-8")).hexdigest()
    print(tabelle)
    print(f"\nSHA256 Tabelle: {sha[:16]}  ·  {sum(o for *_, o in lauf.zeilen)}/{len(lauf.zeilen)} ok  ·  "
          f"Dauer {round(time.time() - lauf.t0, 1) if hasattr(lauf, 't0') else '-'} s")
    log = os.path.join(lauf.arbeit, "exe", "rakscribe.log")
    zeilen_log = []
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            zeilen_log = [z.rstrip() for z in f if any(k in z for k in ("[MASKE]", "[SELBSTTEST]", "[EINFÜGEN]", "[CAS]",
                                                                         "EXCEPTION"))]
    except OSError:
        pass
    with open(os.path.join(lauf.arbeit, "ergebnis.json"), "w", encoding="utf-8") as f:
        json.dump({"tabelle": lauf.zeilen, "sha256": sha, "log": zeilen_log[-120:], "dumps": lauf.dumps}, f,
                  ensure_ascii=False, indent=1)
    print("\nrakscribe.log ([MASKE]/[SELBSTTEST]/[EINFÜGEN]/[CAS]/EXCEPTION, letzte 30 Zeilen):")
    print("\n".join(zeilen_log[-30:]))
    return 0 if all(o for *_, o in lauf.zeilen) else 1


if __name__ == "__main__":
    sys.exit(main())
