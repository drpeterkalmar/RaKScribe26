# Teil 2 zu kaiscribe-nicht-diktiert-streichen-n1: KaiScribe 3.30.0 einspielen + Abnahme an 451898 (Karte #542)

Code: main `2b08a63` = **3.30.0** (enthält alles bis dahin, auch 3.29.2 Prompt-Cache und 3.29.0 DEXA-doppelt – beide sind
noch NICHT live, X: stand am 25.11. auf 3.28.2). Bericht Teil 1: `BERICHT-KAISCRIBE-NICHT-DIKTIERT-STREICHEN-N1.md`.

Neu in 3.30.0 (Georg 26.11.2026 „1b“): Bestellt das CAS mehrere Untersuchungen und wird nur ein Teil diktiert, bekommen die
nicht diktierten Untersuchungen keinen Titel, keinen Normaltext und keinen Befund mehr. Stattdessen steht GENAU EINE rote
Prüfzeile im Befundfenster (nicht im Brief): „<Untersuchungen> bestellt, aber nicht diktiert – bitte prüfen“.
Unverändert: reiner IB-Lab-Teil (Ganzbein mit LAMA, HIPPO usw. behalten ihren Teil), Funktions-Kombis, GWS, DEXA nie.

Regeln: Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am Wochenende, nie in der Ordi-Zeit. 451898 nie vidieren,
alles stornieren. Nie in die CAS-DB schreiben. Keine Patientendaten nach außen; in Bericht/Commits nur RH-Nummern bzw.
Abschnittsnamen. Meldungsruhe gilt (nur jobnote/Kanban). Läuft am selben Abend ein anderer KaiScribe-Tausch: nur EINMAL
tauschen, mit der neuesten Version (3.30.0 oder neuer); nie auf eine ältere Version zurück, außer als Rollback.

## A. Vorbedingung
1. Build Windows EXE und Windows UI-Test (EXE) für `2b08a63` grün (Release 3.30.0, Asset-SHA aus der API, `digest`;
   Stand Teil 1 siehe Bericht). Rot → nicht tauschen, Ursache beheben (Folgejob), nichts melden.

## B. Abnahme an 451898 (echter Lauf, mit der KaiScribe-KOPIE 3.30.0, VOR dem Tausch)
Werkzeug `tools/buero/nicht_diktiert_abnahme.py` (Muster wie `ursula_abnahme.py`/`rho_osteopen_abnahme.py`, ris-mods
`e2e/diktat_e2e.py`: Kopie als Gast, echter CAS-Auftrag, Diktat per `text_ins`, echte KI über Konto A, EOL →
`<Nr>.rakscribe.txt`).
1. CAS-Auftrag am Testpatienten mit **mehreren Leistungen** nehmen, z. B. LWS + Beckenübersicht (wie M8 der Rho-Abnahme,
   20261122004) – nur die LWS wird diktiert. Hat der Auftrag IB-Lab-Bausteine zum Becken (HIPPO), bleibt der Becken-Teil
   absichtlich (IB-Lab-Regel) – dann einen Auftrag ohne HIPPO oder mit anderer Zweit-Leistung (BWS, Hüfte …) wählen.
2. Fall **N1** (nur LWS diktiert) mit `--log <rakscribe.log der Kopie>`: erwartet `NDABN=ok`, `BEFUNDE=1`,
   `PRUEFZEILE=ja` (Logzeile `[CAS] Hinweis: … bestellt, aber nicht diktiert – bitte prüfen`, zusätzlich
   `[CAS] <Leistung>: nicht diktiert → gestrichen (Prüfzeile)`).
3. Gegenprobe Fall **A1** (alle Leistungen diktiert): zwei Befunde, keine solche Prüfzeile.
4. **Seitenbild ohne Patientendaten**: Ausschnitt des KaiScribe-Befundfensters mit der roten Prüfzeile und dem einen
   Befund (Kopfzeile/Name/Nr. abdecken oder nur den Befundbereich zuschneiden). Ablage im Repo
   `docs/einspielen/nicht_diktiert_451898.png`.
5. Beide Läufe stornieren, nie vidieren.
Rot → nicht tauschen bzw. Rollback (`-Schritt zurueck`), Ursache beheben (Folgejob/Karte in „tun“), nichts melden.

## C. Tausch (erst wenn B grün)
Wie bisher (Erinnerung release-vom-hetzner): Ordi-Hermes lädt das Asset von GitHub und prüft die SHA, dann
`kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.30.0 -Sha <sha>`. Die alte EXE bleibt als `.alt` (`-Schritt zurueck`).
Laufende Prozesse nicht abschießen. 20 min Ruhe nach der letzten Ablage abwarten.
**Achtung (25.11.):** Der Tausch 3.29.0 scheiterte 50× an „X:\KaiScribe\Programm\KaiScribe.exe nicht umbenennbar“. Vorher
klären, wer die X:-EXE hält (SM-Wächter `--sm-waechter` am Büro-PC laufen direkt von der X:-EXE; KaiScribe an anderen
PCs). Nichts hart beenden; ggf. Wächter sauber über ihren eigenen Weg stoppen und danach wieder starten. Gelingt der
Tausch nicht: Stand im Bericht, Folgejob, nichts melden.
Beleg je PC: `X:\RaKScribe\Daten\protokolle\bruecke_<PC>.log` bzw. Version im Fenstertitel beim nächsten Start.

## D. Zusätzlich in derselben Runde (ein Einspielen je Programm und Abend)
3.30.0 bringt auch 3.29.2 (Prompt-Cache) und 3.29.0 (DEXA-doppelt) live. Deren Abnahmen sind noch offen:
- `FOLGEJOB-KAISCRIBE-KOSTEN-JE-BEFUND-N1-EINSPIELEN.md` Teil B (zwei Diktate, 2. `Cache treffer`) – N1/A1 oben dürfen
  dafür zählen, wenn sie ≤ 5 min auseinander liegen (Logzeile `[KI] gen: … Cache …`).
- `BERICHT-KAISCRIBE-DEXA-DOPPELT-RH60-N1.md` / `FOLGEJOB-KAISCRIBE-DEXA-DOPPELT-RH60-N1-EINSPIELEN.md`: Abnahme B/C/D,
  soweit am Abend möglich. Ergebnisse jeweils als Nachtrag in deren Bericht.

## E. Bericht + Meldung (erst wenn belegt live)
Nachtrag in `BERICHT-KAISCRIBE-NICHT-DIKTIERT-STREICHEN-N1.md` (≤ 8 Zeilen): Version, was geändert, Probe 451898 (Bild),
ein Satz für Ursula ab wann es gilt. Karte #542 mit Notiz schließen. `## Abschluss` (geht an den Besteller), z. B.:
„Ab <Tag/Uhrzeit> (KaiScribe 3.30.0): Wird nur ein Teil der bestellten Untersuchungen diktiert, schreibt KaiScribe für die
übrigen keine Überschrift und keinen Normaltext mehr. Im Befundfenster steht dann eine rote Zeile, z. B. ‚BWS, LWS
bestellt, aber nicht diktiert – bitte prüfen'.“ Keine Meldung, solange nicht live.
