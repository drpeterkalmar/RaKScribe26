# waechter-zaehlt-nicht-n2 – Wächter zieht den Fenster-Starter nach + Kontrolle mit echten Brücken-Diktaten (ab Mi 25.11. 17:45, Kanban #541)

Von `waechter-zaehlt-nicht-n1-kontrolle` (BERICHT-WAECHTER-ZAEHLT-NICHT-N1.md, Teil 3). Stand 25.11. 09:45: Brücke
2.5.35 + KaiScribe 3.28.2 auf X:. Morgens kamen zwei Anmeldungen (07:25:47, 07:27:27) mit **nur dem Wächter 3.28.2**, ohne Fenster-Start
(`[INIT] Nutzungszähler` seit 06:00 = 0). Es gab kein einziges CAS-Diktat über die Brücke, keine_antwort = 0 ist also nicht belegt.

## Ursache
Der korrigierte Starter (`warte_auf_x.vbs` mit `--sm-waechter`-Ausnahme, ab 3.25.1) wird nur von
`Bereitschaft.nachziehen()` geschrieben, und das läuft nur im **Fenster** (`RaKScribe.py` `_autostart_nachziehen`). Der
Wächter (`sm_waechter_main`, Thread `autostart()` → `WaechterAutostart.sichern`) zieht ihn nicht nach. An PCs, an denen das
Fenster seit dem Fix nie lief (CASWS10: letzter Fenster-Start 23.11. 17:33), bleibt der alte Starter liegen. Der zählt den
Wächter als „KaiScribe läuft schon“, und das Fenster kommt nie.

## Auftrag
1. Bau (RaKScribe26, offline am Hetzner): Im Wächter-Start (`sm_waechter_main`, nach `WaechterAutostart.sichern`) auch
   `Bereitschaft(...).nachziehen(exe)` aufrufen. Nur wenn der Fenster-Autostart an ist (`an()`), nie etwas neu anlegen, Fehler
   nur loggen (`[AUTOSTART] … (Wächter)`). Prüfen, ob der Wächter danach selbst das Fenster minimiert starten soll, wenn kein
   Mutex `Local\RaKScribe26-Einzelinstanz` da ist und der Fenster-Autostart an ist (einmal, z. B. 120 s nach dem Start;
   das ist dieselbe Regel wie beim Starter). Selbst entscheiden und begründen. Tests: `test_bereitschaft.py` + neuer Fall
   „Wächter allein, alter Starter → nach Wächter-Start steht der neue Starter da“, `test_sm_waechter_bleibt.py`.
2. Version erst beim Zusammenführen (`cj zusammenfuehren --vorher …`), Release wie üblich, Tausch auf X: per
   `kaiscribe_x_tauschen.ps1` am Abend (nach 17:30, nie Mo 06:30–09:30), Windows-UI-Test grün.
3. Kontrolle (nur lesen, über `peer run vm` oder ordi): `bruecke_<PC>.log` seit 06:00 des Kontrolltags je PC
   keine_antwort / angenommen <Version> / `[rakscribe] gestartet`, dazu Fenster-Starts (`[INIT] Nutzungszähler … (<PC>)`)
   kurz nach den Wächter-Starts der Anmeldungen. Grün = keine_antwort 0 bei ≥ 1 echtem Brücken-Diktat **und** Fenster-Start
   nach der Anmeldung an CASWS10/CASWS08. Erst dann #541 fertig. Die Meldung an Georg („KaiScribe startet wieder von
   selbst, auch wenn nur der Wächter läuft“) schickt die Queue mit dem Abschluss.
4. Gibt es bis dahin echte Brücken-Diktate mit `keine_antwort`: die Zeilen zitieren (Zeit + Kurztext, keine
   Patientendaten), Brücken-Version prüfen.

Regeln: keine Klicks an Befund-PCs, CAS nur lesen, keine Patientendaten in Berichten. Meldungsruhe.
Leseskripte zum Wiederverwenden: `~/cj/work/waechter-zaehlt-nicht-n1-kontrolle/auftrag4.txt`, `auftrag5.txt` (Hetzner).
