# kaiscribe-nur-auffaellig-n2 – FROG, HIPPO, KOALA: nur pathologische Messwerte in den Befund (13.11.2026)

**Für Peter:** KaiScribe 3.18.8 schreibt bei FROG, HIPPO und KOALA nur noch die Messwerte in den Befund, aus denen eine
Regel eine Schlussfolgerung gemacht hat. Bei deinem Fuß-Foto sind das nur noch Hallux-valgus-Winkel und
Intermetatarsalwinkel I/II je Seite statt aller 26 Zeilen. Die Ergebnispunkte bleiben genau wie bisher. Ohne Treffer
kommt kein Messwert und auch kein erfundener „alles normal“-Satz in den Befund. Alle Werte stehen weiter in den
IB-Lab-Details (Klick auf die IB-Lab-Zeile). Diktierst du für einen weggelassenen Wert eine andere Zahl, erscheint
weiterhin ein Prüf-Hinweis. SQUIRREL, Rho, LAMA und PANDA bleiben bit-gleich. 3.18.8 liegt seit 13.11. 01:38 auf X:,
und der Büro-PC läuft damit. CASWS08 und CASWS10 holen es beim nächsten KaiScribe-Start. Der Beleg dort und der
Echttest stehen noch aus.

## Umsetzung (RaKScribe26 7778a56, Release 3.18.8)
- `ibl_bausteine.BEFUND_NUR_AUFFAELLIG = {"frog", "hippo", "koala"}` schaltet den Filter, `befund_zeilen(b)` liefert die Zeilen für den Befund.
  „Pathologisch“ heißt: Messgröße + Wert (numerisch, 10° = 10,0°) + passende Seite stehen in einem Ergebnispunkt
  desselben Bausteins. Das deckt auch den Abholer-Stil „… beidseits (X rechts 10°, links 10°)“ ab und „Hallux valgus links (HVA 24°)“.
  Bei mehreren Aufnahmen zählt die Beschriftung („Fuß d.p.: …“). IB Labs „Abnormally High/Low“ wird nicht benutzt.
- Gerüst (`geruest`) und Einsetzen nach der KI (`einsetzen`/`_befund_pruefen`) nutzen beide `befund_zeilen`. Eine Beschriftung
  bleibt nur, wenn darunter noch eine Zeile steht. Weggelassene Zeilen lösen keinen „schon im Befund“-Hinweis aus.
  Ein abweichender diktierter Wert (bzw. K&L-Grad) gibt einen Prüf-Hinweis.
- Gen-Prompt (`prompt_block`): Er nennt nur die eingesetzten Messgrößen, ohne den Satz „ersetzt Vorlagen-Sätze zu <Thema>“, denn die übrigen
  Werte sind unauffällig. KOALA ohne Treffer: kurzer Block, der nur den K&L-Grad nennt (Regel ab 3.18.5: Grad nur zu einer diktierten Arthrose).
- EXE: `_ibl_offen` meldet einen Baustein ohne Treffer nicht als „neu, nicht im Befund“. Die hervorgehobenen Zeilen erkennt jetzt dieselbe Logik.
- Web-App: Sie hat keine IB-Lab-Bausteine, deshalb gibt es keinen Paritätsteil.

## Tests
- Neu `tests/offline/test_ibl_nur_auffaellig.py` (31 Prüfungen). Fälle: Peters Foto (Gerüst, nach der KI, Diktat-Abgleich, Prompt),
  die ris-mods-Beispiele frog_beidseits/frog_pes_planus, die Hersteller-Fixture FROG d.p., Seite und Aufnahme, FROG ohne Treffer (0 Zeilen),
  HIPPO und KOALA je mit und ohne Treffer. Dazu ein Bit-gleich-Vergleich mit 3.18.7 für SQUIRREL/Rho/LAMA/PANDA
  (Schnappschuss `tests/offline/snapshots/ibl_ohne_filter.json`, erzeugt mit dem Code von 3.18.7).
- An das neue Soll angepasst: `test_ibl_bausteine.py` (K&L-Fälle mit Regeltreffer, EXE-Ablauf FROG ohne Treffer) und `test_cas_kontext.py` (Gerüst).
- Alle Offline-Gates sind grün (39 Python-Dateien + 7 Web-Suiten), ebenso GitHub Tests, Build und Windows-UI-Test.
  Live `tools/test_all_regions.py --ibl` ergab 5/5 PASS, darunter neu Peters Fuß-Fall. KOALA-KL1 verhält sich wie in 3.18.7.

## Verteilung
- Ordi-Schritt A1 (01:37, nur lesen) hat die EXE vom GitHub-Release direkt am Büro-PC in den Ordner `ks_tausch\v3.18.8` geholt, SHA geprüft (45ff7af9…).
- Schritt A2 (01:38) lief `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.18.8` mit `KS_TAUSCH=ok`. Die alte EXE liegt als
  `rakscribe26.exe.vor3.18.8-20261113-013849.alt` daneben. Titel „KaiScribe 3.18.8 - Röntgen am Kai“, kein Netzfehler im Log.
- CASWS08 (12.11. 11:05) und CASWS10 (12.11. 17:37) liefen zuletzt mit 3.18.0. Sie bekommen 3.18.8 beim nächsten Start.
- Rückweg: `kaiscribe_x_tauschen.ps1 -Schritt zurueck`, das stellt 3.18.7 wieder her.

## Offen
- Beleg 3.18.8 an CASWS08/CASWS10 und ein Blick auf einen echten FROG/HIPPO/KOALA-Fall: Beides steht als Notiz an Kanban #199
  (Prüfung Fr nach Ordi-Ende). #229 deshalb noch nicht „läuft“.
- Echttest am Testpatienten 451898: nicht von hier aus möglich (braucht Mac-Ton über RDP und eine IB-Lab-Studie). Der wartende
  Job kaiscribe-3187-echttest-n1 trifft jetzt 3.18.8 an (Hinweis an #199).
- Bekannt, nicht Teil dieses Auftrags: Ist das Ergebnis eine reine Normalaussage („Regelrechte Darstellung …“), übernimmt
  KaiScribe IB-Lab-Punkte nicht und meldet „bitte prüfen“. Das ist so seit 3.13.

Arbeitsdateien: `~/cj/work/kaiscribe-nur-auffaellig-n2/` (Ordi-Aufträge, Schnappschuss-Generator, Live-Log).
