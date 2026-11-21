# Bericht kaiscribe-senf-anzeige-n1 – Opus-Senf als Hinweis im KaiScribe-Fenster (nur kp), Sa 21.11.2026

- **Gebaut (main, Version siehe unten):** eigene Zeile „Senf – nur Hinweis“ unter dem CAS-Band, nur für Kürzel aus
  `SENF_ANZEIGE` (Standard `kp`, `aus` = niemand). Anzeige je Status: „Senf läuft…“ (alle 15 s nachladen, max. 10 min) ·
  „Senf: unauffällig“ · Zeile(n) „RH xx · …“ · „Senf: kein Ergebnis“. Nachtrag 20.11.: markier-/kopierbar (Strg+A/Strg+C,
  Knopf „⧉ Kopieren“), schreibgeschützt, kein Einfüge-/Diktierziel; der Senf geht nie von selbst in Befund, EOL-Datei,
  Lauf-Datei oder Zwischenablage. Lesen nur lesend im Hintergrund, Frist 1 s; keine Ablage → Zeile aus, Diktat unberührt.
- **Ablage:** `X:\RaKScribe\Daten\senf\<Diktatnummer>.json` (Teil 1, ris-mods opus_senf 1.7.0, live seit 20.11. 19:55);
  Zwilling `X:\KaiScribe\Daten\senf` wird mitgesucht. Code `source_code/senf_anzeige.py`, Fenster `RaKScribe.py` (`_senf_*`).
- **Tests:** `tests/offline/test_senf_anzeige.py` 69/69 grün (3× hintereinander), ganze Offline-Reihe am Mac grün bis auf
  `test_cas_auftrag`/`test_maske_ablauf`, die mit /usr/bin/python3 (3.9) schon auf unverändertem main rot sind (GitHub grün).
- **Noch NICHT aktiv auf X:** Einspielen + Abnahme am Testpatienten 451898 (Feld sichtbar + CAS-Brief ohne Senf) brauchen
  den Büro-PC → Folgejob `kaiscribe-senf-anzeige-n1-einspielen` (`FOLGEJOB-KAISCRIBE-SENF-ANZEIGE-N1-EINSPIELEN.md`).
- **Offen:** Fenster-Optik nur mit Attrappen geprüft (kein Tk am Mac, Leicht-Spur) → Screenshot beim Einspielen; erster
  echter kp-Fall Mo 23.11.; viele Diktate ohne Senf (z. B. Sono) zeigen bis zu 10 min „Senf läuft…“, dann „kein Ergebnis“.
