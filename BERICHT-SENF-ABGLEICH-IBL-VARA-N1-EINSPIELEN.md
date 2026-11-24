# Bericht opus-senf-abgleich-ibl-vara-n1-einspielen – KaiScribe zeigt den Senf-Abgleich auch nachträglich (Teil 2)

- **Gebaut (Mac, Offline-Tests grün):** `senf_anzeige.py` – nach „fertig“ weiterlesen alle 15 s bis 15 min nach dem Öffnen, bei höherem `v` neu anzeigen;
  Zeilen des `a_…`-Eintrags und `IB Lab:`-Zusätze auch bei „Senf: unauffällig“. `sm_einfuegen.py` – nach dem Einfügen weiterlesen (15 s / 15 min),
  bei höherem `v` nur neue Zeilen nachfügen (Merker `senf:v<v>`, auch nach Wiederöffnen nie doppelt, nie wieder „[SENF] unauffällig“);
  „IB Lab: …“ nie, wenn SM_IBL für den Benutzer aktiv ist (kp); bei „unauffällig“ kommen die `a_`-Zeilen mit Marke „[SENF] “ nach „[SENF] unauffällig“.
- **Tests:** `test_senf_anzeige` (v 1→2, Vara-Zeile bei unauffällig, niedrigeres v ignoriert, Ende nach 15 min), `test_sm_einfuegen`
  (Vara nachgefügt genau einmal, kein „IB Lab:“ bei SM_IBL, Merker `senf:v1/v2`, Wiederöffnen, v 3, SM_IBL aus, Ende nach 15 min). Tk-Tests nur in GitHub.
- **Nicht gemacht:** Einspielen auf X: und Abnahme am Testpatienten 451898 (Probe-Ablage, v 2 von Hand) – braucht Büro-PC/Ordi-Hermes nach Ordi-Schluss,
  nicht aus diesem Lauf erreichbar. Folgejob `kaiscribe-senf-abgleich-ibl-vara-n1-einspielen-n2` (Datei `FOLGEJOB-…`). Bis dahin zeigt die laufende EXE den Abgleich nur, wenn das Diktat nach ihm geöffnet wird.
