# Bericht kaiscribe-senf-anzeige-n1 – Opus-Senf als Hinweis im KaiScribe-Fenster (nur kp), Sa 21.11.2026

- **Gebaut (main, Version 3.21.0):** eigene Zeile „Senf – nur Hinweis“ unter dem CAS-Band, nur für Kürzel aus
  `SENF_ANZEIGE` (Standard `kp`, `aus` = niemand). Anzeige je Status: „Senf läuft…“ (alle 15 s nachladen, max. 10 min) ·
  „Senf: unauffällig“ · Zeile(n) „RH xx · …“ · „Senf: kein Ergebnis“. Nachtrag 20.11.: markier-/kopierbar (Strg+A/Strg+C,
  Knopf „⧉ Kopieren“), schreibgeschützt, kein Einfüge-/Diktierziel; der Senf geht nie von selbst in Befund, EOL-Datei,
  Lauf-Datei oder Zwischenablage. Lesen nur lesend im Hintergrund, Frist 1 s; keine Ablage → Zeile aus, Diktat unberührt.
- **Ablage:** `X:\RaKScribe\Daten\senf\<Diktatnummer>.json` (Teil 1, ris-mods opus_senf 1.7.0, live seit 20.11. 19:55);
  Zwilling `X:\KaiScribe\Daten\senf` wird mitgesucht. Code `source_code/senf_anzeige.py`, Fenster `RaKScribe.py` (`_senf_*`).
- **Tests:** `tests/offline/test_senf_anzeige.py` 69/69 grün (3× hintereinander), ganze Offline-Reihe am Mac grün bis auf
  `test_cas_auftrag`/`test_maske_ablauf`, die mit /usr/bin/python3 (3.9) schon auf unverändertem main rot sind (GitHub grün).
- **GitHub:** Tests + Pages-Deploy auf `bb88ae7` grün; EXE-Release 3.21.0 baut der Folgejob (Bau nur per Hand).
- **Noch NICHT aktiv auf X:** Einspielen + Abnahme am Testpatienten 451898 (Feld sichtbar + CAS-Brief ohne Senf) brauchen
  den Büro-PC → Folgejob `kaiscribe-senf-anzeige-n1-einspielen` (`FOLGEJOB-KAISCRIBE-SENF-ANZEIGE-N1-EINSPIELEN.md`).
- **Offen:** Fenster-Optik nur mit Attrappen geprüft (kein Tk am Mac, Leicht-Spur) → Screenshot beim Einspielen; erster
  echter kp-Fall Mo 23.11.; viele Diktate ohne Senf (z. B. Sono) zeigen bis zu 10 min „Senf läuft…“, dann „kein Ergebnis“.

## Einspielen (kaiscribe-senf-anzeige-n1-einspielen, Sa 21.11.2026 14:10–16:15, Wochenende)
- **Live auf X: KaiScribe 3.21.1** (EXE `e9f2c699b22b`, UI-Test + GitHub Tests grün; Tausch 15:36 per `kaiscribe_x_tauschen.ps1 -Schritt exe`, Rückweg `.alt` = 3.21.0, davor 3.20.5). 3.21.0 war 14:44–15:36 live, kein Netz-/ESET-Fehler.
- **Gefunden + behoben (3.21.1, af32704):** Die VM schreibt nach `X:\KaiScribe\Daten\senf` und spiegelt ~1 min später in `X:\RaKScribe\Daten\senf`; 3.21.0 nahm den ersten Ordner (Zwilling hing auf „läuft“) → „fertig“ kam nie an. Jetzt gewinnt das jüngste Ergebnis (`zeit`), bei Gleichstand „fertig“. 3 neue Tests, Datei grün (FEHLER: 0).
- **Beleg 451898 (nie vidiert, alle storniert):** Senf-Zeile unter dem CAS-Band sichtbar („Senf / nur Hinweis“, Text „RH 0 · Probe · TESTSENF bitte ignorieren“; 3.21.0 zeigte „Senf läuft…“); Knopf „Kopieren“ und Strg+A/Strg+C liefern genau die Zeile (Log `[SENF] kopiert (40 Zeichen, Knopf|Strg+C)`); Lauf 20261121029 bis EOL: Brief `<Nr>.rakscribe.txt`, Lauf-Datei und CAS ohne TESTSENF/„RH 0“/„Senf“ (je 0); Log `[SENF] 20261121029: fertig`.
- **Nicht live belegt:** Gegenprobe anderes Kürzel (nur Offline-Test „nur kp“); Lauf 028 hing mit 150 s Stille im Nachlauf in Chirp3 (Testartefakt, Lauf abgebrochen, nichts im Brief); Teststrecke meldet `f_ablage` nur wegen SMB-Cache (K\quelle hat den Fix f8a21ff noch nicht).
- **Offen:** Kontrolle des ersten echten kp-Falls Mo 23.11. ab 11:30 (Job `kaiscribe-senf-anzeige-kontrolle`, nur lesen). Viele Diktate ohne Senf (z. B. Sono) zeigen bis zu 10 min „Senf läuft…“. ESET-Fenster „Anwendung geändert (rakscribe26.exe)“ stand schon vor dem Tausch offen (nicht angeklickt, Netz ok).
