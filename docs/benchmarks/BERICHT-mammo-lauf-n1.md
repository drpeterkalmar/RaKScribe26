# kaiscribe-mammo-lauf-n1 – Mammo-Maske schreibt eine Lauf-Datei (KaiScribe 3.19.1, Kanban #300, ex #320)

Mo 16.11.2026 04:25–05:00. Befund aus hermi-ks-k4 (14.11.): Bei der Mammo-Maske schrieb KaiScribe beim INS keine Lauf-Datei,
deshalb zählte die Hermi-Kontrolle Mammo-Befunde als `ohne_schnappschuss` (T016/T033).

## Änderung (RaKScribe26 d282a8e, Version 91c6cf2 = 3.19.1)
- `_maske_bauen` ruft nach dem Masken-Befund `_lauf_protokollieren` auf, also derselbe Weg wie beim Diktat:
  `_cas.lauf_daten` + `lauf_schreiben` im Hintergrund nach `X:\RaKScribe\Daten\laeufe\<Nr>_<Zeit>.json`. `ergebnis_vorschlag`
  ist genau der Text, der beim INS rechts erscheint (inkl. IB-Lab-Einsatz).
- Format wie beim Diktat, dazu ein Feld `maske` (Art: screening/kurativ/…). `stt_roh` = je diktiertem Feld „Label: Diktat“.
  `vorlagen` leer, `diktat` fehlt (bei der Maske gibt es keinen einzelnen Prompt-Text).
- Sonst ändert sich an der Maske nichts: Anzeige, Warnung, EOL-Prüfung und Brücken-Datei bleiben gleich. Ein Schreibfehler
  ergibt wie bisher nur eine Zeile `[LAUF] nicht geschrieben (…)` im Log, ohne Inhalt.

## Tests
- `tests/offline/test_maske_ablauf.py`: neue Prüfung nach dem ersten INS. Es entsteht genau eine Datei `20261015001_*.json` mit
  `ergebnis_vorschlag` = Befund, Nr, Benutzer, `maske=screening`, STT je Feld, Modell/Prompt-Stand, Version. Auf GitHub grün
  (Lauf 43798579980, alle Gates). Am Mac laufen die Tk-Gates nicht (Python 3.9 mit Tk, aber Zeitverhalten/f-Strings → auf dem
  unveränderten Stand genauso rot). Deshalb habe ich am Mac eine Probe gebaut: alle Felder übernehmen, dann INS. Ergebnis:
  1 Lauf-Datei, `ergebnis_vorschlag` gleich dem Befund, `maske=screening`.
- Release 3.19.1 (GitHub Actions): `rakscribe26.exe` 56.805.713 B, sha256 `3dd3f3a04ef2…`, Windows-UI-Test **115/115**.

## Einspielen (Ordi-Hermes, Büro-PC CASWS14, Mo 16.11. 04:49–04:52, Ordi zu)
- A1: abgelehnt („jemand verbunden“). Die Sitzung rdp-tcp#8 war der eigene Mac-Client (`rdp_ordi.sh`, seit 14.11. 23:21).
  Er hatte sich um 03:03:34 nach einem Netzaussetzer selbst neu verbunden (Mac-Log). Mit dieser Klarstellung lief A1b.
- A1b: Download 18 s, SHA ok. `KS_TAUSCH=ok neu=3dd3f3a04ef2 alt=c7fcd46a5f26`, Sicherung
  `rakscribe26.exe.vor3.19.1-20261116-045124.alt`, Neustart 04:51:25. Titel „KaiScribe 3.19.1 - Röntgen am Kai“ (minimiert),
  `[INIT] Befund-KI: anthropic/claude-sonnet-5-5, Korrektur: anthropic/claude-sonnet-5-5 - maskiert, Rückfall Gemini`,
  0 Netz-/Fehlerzeilen, kein Dialog der Sicherheitssoftware. config.ini und Schlüsseldatei blieben unverändert.
- Die anderen Befund-PCs bekommen 3.19.1 beim nächsten Start von KaiScribe (X:).
- Rückweg: `kaiscribe_x_tauschen.ps1 -Schritt zurueck`, nur außerhalb 06:30–20:10.
- Auftrag/Antworten: `docs/benchmarks/mammo_lauf_n1/`.

## Echttest am 451898: Folgejob
Den Echttest am Testpatienten (Mammo-Maske über die Teststrecke KS mit Ton vom Mac, MammoDoppel, Roboter, Prüfung auf der VM)
habe ich vor 06:30 nicht mehr angefangen. Er braucht mehrere Ordi-Runden. Hätte ich vor Ordi-Beginn abbrechen müssen, wären
VM-Schalter und Testeinträge in einem halben Zustand geblieben. Deshalb läuft er als Folgejob **kaiscribe-mammo-lauf-n2-echttest**
(ris-mods, Ressource ordi, prio 1). Er startet frühestens heute 17:30, nach Ordi-Ende, und soll vor dem Hermi-Einschalten um
20:10 fertig sein.
