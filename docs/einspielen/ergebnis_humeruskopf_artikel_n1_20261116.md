# Bericht kaiscribe-humeruskopf-artikel-n1-einspielen (Mo 16.11.2026, Hetzner + Büro-PC lesend)

## Kurz
1. **Der Schulter-Satz ist auf X: eingespielt, aber nicht live belegt.** Auf X: läuft seit 23:07 KaiScribe **3.19.4**. Das Release enthält die Änderung aus 3.19.2 (e84b617 ist Vorgänger, `git merge-base --is-ancestor` ja). Beleg: `[INIT] Befund-Prompt 2026-11-16-humeruskopf-artikel aus eingebaut`. Der Tausch lief im Job kaiscribe-mammo-vergleichsdatum-n1-einspielen, ich habe NICHT nochmals getauscht (Brief: nie doppelt, nie zurück).
2. **Abnahme am Testpatienten 451898: nicht gemacht.** Die Teststrecke KS braucht den Mac (Sprachausgabe + RDP-Mikrofon). Von Hetzner aus gibt es dorthin nur den eingeschränkten Werkbank-Zugang (kein ton.sh). Ein getipptes Ersatzdiktat per Bildschirmsteuerung am Büro-PC mit offenem CAS wollte ich nachts nicht riskieren.
3. **Keine Meldung an Georg** (nicht live belegt). Kontroll-Job als Kanban-Karte #366 (tun, Frist 17.11.): nur lesend Lauf-Dateien echter Schulter-Normalbefunde ab 23:07 auf „Der Humeruskopf steht“ prüfen. Alternativ später die Abnahme am 451898 vom Mac aus.

## Tore (nur lesen)
- Release 3.19.4: SHA256 5e1308dc46a5…b2d0, 56.811.184 B, Windows-UI-Test grün (siehe BERICHT-mammo-vergleichsdatum-n1-einspielen.md). Enthält 3.19.2.
- Ordi-Lesejob HK1 (23:12, `docs/einspielen/humeruskopf_artikel_einspielen/a1.txt`, `a1_antwort.txt`): Titel „KaiScribe 3.19.4 - Röntgen am Kai“, SHA/Größe stimmen, keine Aufnahme, nur der Mac-Client verbunden.

## Stände
- Vorher: 3.19.1 (Prompt noch ohne Artikel). Nachher: 3.19.4 seit 23:07:26 am Büro-PC CASWS14; CASWS08/CASWS10 beim nächsten Start von X:. Sicherung `rakscribe26.exe.vor3.19.4-20261116-230725.alt`, Rückweg `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (nur außerhalb 06:30–20:10).

## Lücke aus Teil 1 (Herkunft von Georgs Foto)
Der alte Satz „Humeruskopf in regelrechter Artikulation“ (ohne Artikel) steht auf X: in nur einer Textdatei: `Bruecke\original\20261108014.json` (2 Treffer, Original-Diktat vom 8.11., kein Baustein). Der neue Satz steckt fest in der EXE (Prompt/Vorlage), in keiner Textdatei. Kein zweiter Textbaustein auf X: gefunden. Läufe mit „Humeruskopf“ gibt es nur vor dem Tausch (3.18.11/3.19.1, alter Satz); seit 23:07 keinen.

## Offen
- Live-Beleg (Lauf-Datei `ergebnis_vorschlag` enthält „Der Humeruskopf steht“, `kaiscribe` ≥ 3.19.4) – Kanban #366.
- Teil „Georg informieren“ erst danach: „Schulter-Normalbefund in KaiScribe geändert: jetzt ‚Der Humeruskopf steht in regelrechter Artikulation.‘ Aktiv seit 16.11. 23:07 (Version 3.19.4), an allen Befund-PCs ab dem nächsten Start von KaiScribe.“
