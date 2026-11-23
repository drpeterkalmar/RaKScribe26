# sm-senf-laenge-n1-einspielen – KaiScribe 3.22.6 (SM-Senf nicht mehr nach 300 Zeichen abgeschnitten) einspielen + Abnahme

Von `sm-senf-laenge-n1` (Mo 23.11.2026, Teil 1 am Mac ohne Büro-PC). Peter 23.11. ~17:35, RH 146: Senf in SpeechMagic endete
mitten im Wort „… stationär. (V“. Einspielen erlaubt: Montag nach 17:30, außerhalb der Ordi-Zeit (Peters Meldung liegt vor).
Release-Regel (Georg): erst Lauf am Testpatienten 451898, sonst Rollback. 451898 NIE vidieren. CAS nur lesen.
Patientendaten nur VM, Logs nur Status-/Nummernzeilen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Was eingespielt wird
GitHub-Release **3.22.6** (main 74167d6, Latest), Asset `KaiScribe.exe` / `rakscribe26.exe`,
sha256 KaiScribe.exe `e1f02503e770929053c0134fe3aa58cd3553f09f8adfb77e1887cc0e9b70af39`. CI grün: Tests, Build Windows EXE, Windows UI-Test (EXE).
- `sm_einfuegen.senf_zeilen`: Senf-Zeile bis **1200 Zeichen** vollständig (bis 3.22.5 hart `[:300]`). Länger → am letzten
  „. “/„; “ vor 1200 abgeschnitten + „ …“, ohne Satzende am letzten Leerzeichen; nie mitten im Wort.
- `senf_anzeige.py` (KaiScribe-Senf-Feld) kürzte nie je Zeile, nur die ganze Datei auf 2000 → unverändert.
- Sonst nichts geändert (Wächter, Merker, Einfügen gleich wie 3.22.5).

## Ablauf
1. Tausch über das bestehende Skript (wie 3.22.5, Bericht `BERICHT-SM-WAECHTER-BLEIBT-N1-EINSPIELEN.md` Nachtrag n2):
   Ordi-Hermes lädt das Asset von GitHub, SHA prüfen, `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.22.6 -Sha <sha>`.
   Alte EXE bleibt als `.alt` (Rollback `-Schritt zurueck`). Laufende Prozesse NICHT abschießen. Sperre Mo–Fr 06:30–20:10 beachten
   (nach 20:10 frei; früher nur mit Peters Wort).
2. **Wächter mit 3.22.6 (regulärer Weg, kein Abschießen):** 3.22.5 hat den Selbst-Neustart schon eingebaut (`Pruefung`): sieht
   der Wächter eine neue EXE an seinem Pfad (Größe/Zeit zweimal gleich, Prüfung jede Minute), startet er sie als Nachfolger
   `--sm-waechter --nachfolger` und endet – nie während eines offenen kp-SpeechMagic-Diktats. An CASWS10 läuft seit 17:22
   pid 12452 (3.22.5). Beleg in rakscribe.log binnen ~2–3 min nach dem Tausch:
   `[SM] Wächter-Prozess endet: neue KaiScribe-EXE liegt bereit` + `[SM] Wächter-Prozess 3.22.6 gestartet (pid …, Nachfolger; …)`;
   danach genau 1 Prozess mit `--sm-waechter` je Sitzung (Get-CimInstance Win32_Process). Kommt kein Nachfolger (z. B. Wächter
   läuft aus einer anderen Kopie als dem getauschten Pfad): Befehlszeile/Pfad von pid 12452 belegen, dann über den regulären
   Weg (Autostart-VBS bzw. nächster KaiScribe-Start) – kein Kill; Lücke als Karte (tun).
3. **Abnahme 451898** (Werkzeuge wie in `senf-ibl-speechmagic-paste-n1` / `tools/sm_probe.ps1`): Senf-Ablage mit einer
   synthetischen Zeile > 300 Zeichen (z. B. 450 Zeichen, endet mit „… stationär. (Verlauf empfohlen)“) → SM-Diktat 451898 öffnen →
   Zeile kommt vollständig an (Länge im Diktat = Länge der Ablage), genau einmal; Diktat zu/wieder auf → nichts doppelt.
   Alles stornieren, nie vidieren. Rot → Rollback auf `.alt`.
4. Geht 3. nicht: Beleg = erster echter kp-Fall mit Senf > 300 Zeichen, der vollständig in SpeechMagic ankommt
   (Länge der Senf-Ablage vs. eingefügte Länge, nur Nummern/Längen ins Log/den Bericht).
5. Bericht ≤ 6 Zeilen in `BERICHT-SM-SENF-LAENGE-N1.md` (Nachtrag „Einspielen“). Meldung an Peter macht die Queue.

## Lücken aus Teil 1
- Selbst-Neustart des Wächters über den EXE-Tausch auf X: ist nur offline getestet (test_sm_waechter_bleibt) und beim
  3.22.5-Tausch nicht als Nachfolger-Zeile belegt (damals lief vorher kein Wächter) → Punkt 2 ist der erste echte Beleg.
- Mac-Offline-Tests: test_cas_auftrag, test_ibl_nur_auffaellig, test_maske_ablauf sind am Mac (Python 3.9) schon auf main rot,
  nicht durch 3.22.6; CI (Python 3.12) ist maßgeblich.
