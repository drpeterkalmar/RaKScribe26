# kaiscribe-senf-abgleich-ibl-vara-n1-einspielen-n2 – neue KaiScribe-EXE (Senf-Abgleich nachträglich) einspielen + Abnahme 451898

Wie `kaiscribe-sm-waechter-bleibt-n1-einspielen(-n2)`: nach Ordi-Schluss (ab 20:15), Ruhe-Prüfung, SHA prüfen, `kaiscribe_x_tauschen.ps1 -Schritt exe`.
Release-Regel Georg: erst Lauf an Testpatient 451898 (nie vidieren), sonst Rollback. Liegt heute schon ein anderer RaKScribe26-Einspiel-Auftrag in der Queue → dort anhängen.
Abnahme: Probe-Ablage per `vm_senf.py ablage --nr <Nr> --status fertig --befund unauffaellig --zeile "RH 5 · Probe · unauffällig"` (rakauto-Aufgabe),
Diktat öffnen, danach `a_`-Eintrag „Vara: neutral (Score 50/100)“ mit `v` 2 von Hand nachschieben → Feld zeigt ihn binnen 15 s, SM fügt genau eine Zeile nach.
Danach `vm_senf.py ablage --nr <Nr> --weg` und die Datei auch in X:\RaKScribe\Daten\senf löschen. Meldung erst wenn live belegt, nur über die Queue. Bericht ≤ 8 Zeilen, nur Diktatnummern.
