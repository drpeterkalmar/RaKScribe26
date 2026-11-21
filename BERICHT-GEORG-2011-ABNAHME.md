# BERICHT kaiscribe-georg-2011-abnahme – Georgs Diktiertag: Merge, Release, Einspielen, Pflicht-Abnahme 451898

Sa 21.11.2026 00:36–05:20, Mac + Büro-PC (Ordi-Hermes) + Automaten-VM. Wochenende = Einspielen erlaubt, keine Ordi-Zeit.

## Für Georg (Kurzfassung)
- **Live seit Sa 21.11.:** KaiScribe **3.20.5** auf X: (04:42), Brücke **2.5.26** (01:44, X: + Büro-PC), Formatierer **2.5.26**
  (VM 01:40, Schreib-PCs per Zeiger 05:15), IB-Lab-Abholer **1.3.15** (VM 01:41, inkl. SQUIRREL-Text + LAMA „/Traglinie des
  Ganzbeines“). Web-App 3.20.5.
- **Am Testpatienten belegt (Text im Brief, echte anonyme IB-Lab-Bausteine):** Fuß mit FROG ohne Diagnose (Werte + rote
  Prüfzeile), Mehrfach LWS + Ganzbein (Titel je Teil, LAMA-Anmerkung, Rho als letzter eigener Befund), Knie beidseits (Stellung
  zuerst, rechts zuerst, kein KI-Hinweis), zurückgestellter Befund (wird gespeichert, keine Zwischenablage), GWS a.p. A/B/C.
- **In der Abnahme gefunden und gleich behoben** (darum 3.20.1 → 3.20.5): FROG-Prüfzeile war nicht rot; Knie: Ergebnis links vor
  rechts, „Im Übrigen sind Rechts …“, Befund begann mit der Pathologie; Spracherkennung „Roskore“ (Rho) und „ganz Aufnahme“ (GWS
  a.p. → falsche Vorlage); GWS a.p.: Beschriftung „Wirbelsäule:“ fehlte, SQUIRREL-Satz stand neben „Normale Stellung.“,
  diktierte Skoliose wurde „Seitausbiegung“.
- **Zurückgerollt:** nichts. **Nur offline belegt:** (e) „Aufnahme starten“ fragt vor dem Löschen (siehe unten).
- Offen (nicht Teil dieses Auftrags): 12 Mammo + Sono trennen, 27 Ergebnis nach F10 neu abgleichen. Mo 23.11. Kontrolle der ersten
  echten Fälle ist eingereiht (`kaiscribe-georg-2011-kontrolle`, ab 11:30, nur lesend).

## 1. Merge + Versionen
- RaKScribe26: `job/kaiscribe-georg-2011-n1` (7 Commits) auf main 3.19.20 zusammengeführt (38a5c9e, als ein Commit, weil der Rebase
  die Konfliktlösung verloren hätte). Konflikte: Fixtures/Regel-Register vereinigt, BEFUND-Kopf (Clear all/Reset/Restructure +
  ↶ Rückgängig), `hat_inhalt` (SQUIRREL + FROG ohne Diagnose), Importe `pipeline.ts`.
  **Abgleich 3.19.16 ↔ RH 7:** seit 3.19.16 ergänzt ein Diktat den stehenden Befund (nichts wird gelöscht). Die Rückfrage aus n1
  kommt deshalb nur noch, wenn der Start wirklich Text verwerfen würde (rechts leer bzw. unberührter Fehlstand, links Text).
- Versionen: 3.20.0 (Merge) → 3.20.1 (FROG-Prüfzeile rot, Log „rot (Prüfzeile): n“) → 3.20.2 (Knie rechts zuerst, Widerspruchs-
  Wächter lässt Sätze der anderen Seite stehen, Fehlhör „Roskore“) → 3.20.3 (Stellung zuerst, „Links degenerative“) → 3.20.4
  (Fehlhör „ganz Aufnahme“) → **3.20.5** (GWS a.p.: „Wirbelsäule:“, SQUIRREL ohne Beschriftung, Skoliose wörtlich). Alles EXE = Web
  (gemeinsame Fixtures `befund_regeln_fixtures.json`/`misheard_tests.json`), Regel-Register +5 Einträge.
- Release **3.20.5 latest**: `KaiScribe.exe` = `rakscribe26.exe`, 56 620 594 Byte, sha256
  `fe2f1b5fda853a1d10bfd10f9871240e488f2b9d054e3b1466843b5f5149703a` (Build 44861827416 aus 428f8ab). Windows-UI-Test für 3.20.5
  44862001736 grün (vorher auch 3.20.0–3.20.4; der rote Lauf 44840223891 hatte nur die veraltete Erwartung „68 chirp_3“ → 79).
  Pages-Deploy 44864319655 grün (der automatische 44862175496 scheiterte an GitHub „Artefakt nicht gefunden“), live = 3.20.5.
- Tests am Mac: alle Offline-Gates aus `test.yml` grün außer `test_cas_auftrag`/`test_maske_ablauf` (Mac-Umgebung, auf main vorher
  gleich rot); Web `tsc`/`eslint`/`pipeline_test` grün.
- ris-mods: Zweig `job/ibl-georg-2011-n1` (lag nur auf dem Server, nicht gepusht) per cherry-pick auf main + Versionen **Brücke/
  Formatierer 2.5.26** (2.5.25 war schon vergeben), **Abholer 1.3.15**, **ibl_einfuegen 1.8.1** (3fc58d2). Windows-Prüfung Büro-PC
  67/67 grün (`windows/buero-pc`), Sauber-Prüfung Mac siehe Abschluss. Dazu Teststrecke `kaiscribe.py` 1.8 (3e8db91).
  Grep „BEGIN PRIVATE KEY“ vor jedem Commit = 0.

## 2. Eingespielt (Ordi-Teile, Wochenende)
| Teil | Stand | Rückweg |
|---|---|---|
| VM-Formatierer (`befund_format.py`, `ibl_bausteine.py`, `ibl_einfuegen.py`) | 2.5.26 / 1.8.1 seit 01:40 | `titel_fmt_vm.py zurueck` |
| IB-Lab-Abholer VM | 1.3.15 seit 01:41 (vorher 1.3.13, damit auch SQUIRREL 1.3.14 neu) | `abholer_vm.py einrichten` mit altem Stand |
| Brücke XQ + Büro-PC | 2.5.26 (bruecke.py 2462a6160a72) seit 01:44 | Sicherung `X:\RaKScribe\_alt\Py-diktat-vor-2.5.26-20261121-014453` |
| Formatierer Schreib-PCs | 2.5.26-3fc58d2 (EXE 84c343a10dce…, 6/6 Proben) abgelegt 05:11, Zeiger 05:15 | `fmt_zip_vm.py zeiger fmt2526 2.5.25-0fe2899` |
| KaiScribe X: | 3.20.5 seit 04:42 (vorher 3.19.15) | `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (`rakscribe26.exe.vor3.20.5-20261121-044243.alt`) |

Andere Befund-PCs ziehen die Brücke 2.5.26 per `KaiScribe-einrichten.cmd` (Montag ohnehin geplant, `kaiscribe-umzug-n2-ordi`).

## 3. Pflicht-Abnahme Testpatient 451898 (Text IM BRIEF = `<Nr>.rakscribe.txt`, den KaiScribe beim EOL an CAS übergibt)
Synthetische Diktate (Mac-Sprachausgabe über das RDP-Mikrofon), echte anonyme IB-Lab-Bausteine (mit Abholer-Code 1.3.15 erzeugt,
`tools/ibl_abnahme_bausteine.py`, Fixtures `tests/offline/abnahme_georg_2011/`). Jeder Eintrag storniert, nichts vidiert, 0 Briefe,
Bausteine wieder entfernt, `roboter_testpatient.txt` blieb aus. Ordi-Antworten: `~/cj/work/kaiscribe-georg-2011-abnahme/`.

**(a) Fuß rechts + FROG ohne Diagnose (RH 30)** – 3.20.1 Testkopie, 20261121001, `ibl_zeilen` 3, 3/3 im Befund,
Log `[IBL] Hinweise: 4 (IB Lab FROG, ⚠ IB Lab FROG), rot (Prüfzeile): 1` („… bitte am KI-Bild prüfen“). ✅
```
## Fuß rechts in 2 Ebenen

## Befund

Das Fußskelett ist nach Form, Größe, Anzahl und Stellung der Phalangen, Ossa metatarsalia und der Fußwurzelknochen normal. Das Fußgewölbe ist regulär ausgebildet bei ordnungsgemäßen Gelenkwinkeln. Mineralgehalt und Knochenstruktur sind regelrecht. Glatte und scharfe Abgrenzbarkeit der normal breiten Kortikalis ohne pathologische Konturunterbrechung. Normale Breite der Kompakta. Die gelenkbildenden Flächen sind regelrecht geformt, glatt und scharf begrenzt und stehen normal weit zueinander. Keine intra- und periartikulären Verkalkungen. Die Weichteile sind unauffällig.

Gemessene Winkel d.p.: Hallux-valgus-Winkel 17°, Intermetatarsalwinkel I/II 7° und Metatarsophalangealwinkel V 10°.
Gemessene Winkel seitlich: Calcaneusneigung 24°, Meary-Winkel 6° und Längsgewölbewinkel 114°.

## Ergebnis
Regelrechte Darstellung des Fußskeletts rechts.

Anmerkung: Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.
```

**(b) Mehrfach LWS + Ganzbein (uex2, LAMA Fall 5, nur LWS diktiert) + „Rho 8“** – 3.20.1, 20261121004. ✅ Titel je Teil,
Ganzbein als eigener Normalbefund mit LAMA, Anmerkung „/Traglinie des Ganzbeines“, kein „Varisierung“, Rho zuletzt.
(Erster Versuch 003 mit „Rho Score 8“: STT „Roskore 8“ → Rho fehlte → Fehlhör-Regel in 3.20.2.)
```
## Lendenwirbelsäule in 2 Ebenen

## Befund
Normale Lordose der Lendenwirbelsäule. Die LWK sind nach Anzahl, Form, Größe und Stellung zueinander regelrecht. Mineralgehalt und Knochenstruktur sind unauffällig. Verschmälerung des Intervertebralraums L5/S1 mit subchondraler Sklerosierung der Abschlussplatten. Im Übrigen sind die kortikalen Randkonturen glatt und scharf abgrenzbar. Die Abgänge der Bogenwurzeln, die Dorn-, Quer- und Gelenkfortsätze sind ordnungsgemäß konfiguriert. Die kleinen Wirbelgelenke sind ohne Auffälligkeiten. Die übrigen Zwischenwirbelräume und der Spinalkanal sind normal weit.

Die paravertebralen Weichteile unauffällig.

## Ergebnis
Osteochondrose L5/S1.


## Ganzbeinaufnahme im Stand

## Befund

Extremität: Regelrechte Form und Stellung des Beines, anatomische und mechanische Achse normal.
Gelenke: Regelrechte Artikulation in Articulatio coxae, Articulatio genus und Articulatio talocruralis.
Lange Röhrenknochen: Normal geformt. Mineralgehalt und Knochenstruktur regelrecht. Kortikalis: glatte und scharfe Kontur, ohne pathologische Unterbrechung oder Stufenbildung.
Hüftgelenk: Unauffällige Darstellung, gute Überdachung des normal gerundeten Hüftkopfes durch das Pfannendach.
Kniegelenk: Kongruenz der Gelenkflächen.
Oberes Sprunggelenk: Regelrecht geformt, normale Abbildung der Malleolengabel.
Gelenkspalten: Allseits regelrechte Weiten. Kein Hinweis auf intra- oder periartikuläre Verkalkungen.
Weichteile: Unauffälliger Weichteilmantel.

## Ergebnis
1. Beinlängendifferenz von 11 mm, links kürzer.
2. Beidseits regelrechte Beinachse (rechts HKA 0,4°, MAD −2,0 mm; links HKA 0,7°, MAD 3,1 mm).

Anmerkung: HKA = Hüft-Knie-Sprunggelenk-Winkel, MAD = mechanische Achsabweichung (Mikulicz-Linie/Traglinie des Ganzbeines). Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.


## Opportunistisches Knochendichtescreening (KI)

## Befund
Opportunistisches Knochendichtescreening mittels CE-zertifizierter, klinisch validierter KI-Software (Rho): Der Score von 8 (Skala 1–10) zeigt eine erhöhte Wahrscheinlichkeit für eine verminderte Knochendichte. Der Score korreliert in Studien eng mit dem DEXA-T-Score, ersetzt diesen jedoch nicht. Da keine Knochendichtemessung aus den letzten 2 Jahren vorliegt, wird eine weiterführende Abklärung mittels DEXA empfohlen.

## Ergebnis
Opportunistisches Knochendichtescreening auffällig. Abklärung mittels DEXA empfohlen.
```

**(c) Knie beidseits (knie2)** – 3.20.3 Testkopie, 20261121009. ✅ Stellung zuerst, rechts zuerst, kein KI-Punkt.
(Vorher 005 mit 3.20.1: links zuerst + „Im Übrigen sind Rechts …“; 008 mit 3.20.2: Befund begann mit der Fibroostose – beides
behoben. STT hörte „Patellaunderpol“ – Sprachausgabe, kein KaiScribe-Fehler.)
```
## Kniegelenke beidseits in 2 Ebenen
## Befund
Normale Form und Stellung der dargestellten Skelettabschnitte. Rechts zarte Fibroostose am Patellaunderpol, im Übrigen glatte und scharfe Kontur der Kortikalis ohne pathologische Konturunterbrechung. Links geringe Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer Randzuschärfung. Patella in regelrechter Position. Mineralgehalt und Knochenstruktur sind regelrecht. Links glatte und scharfe Kontur der Kortikalis ohne pathologische Konturunterbrechung. Normale Breite der Kompakta. Ansonsten die Gelenkflächen normal geformt und kongruent. Rechts sind die Gelenkflächen normal geformt und kongruent, der Gelenkspalt ist normal weit. Kein Hinweis auf freie Gelenkkörper. Keine intra- oder periartikulären Verkalkungen. Unauffällige Weichteile.
## Ergebnis
1. Zarte Fibroostose am Patellaunderpol rechts.
2. Geringe Gonarthrose links (Arthrose Grad 2 nach Kellgren & Lawrence).
```

**(d) Zurückgestellter Befund (Punkt 3)** – **Live 3.20.5**, 20261121017, SpeechMagic-WAV + .doc synthetisch nachgestellt. ✅
Brücke: `[ablage] … zurückgestellt (SpeechMagic-Diktat + Befund da)` → `ok=True … RaKScribe-Text abgelegt (… .wav bleibt
unverändert)`, Merkdatei `korrektur=true`, `zurueckgestellt` {md, zeit}, WAV-SHA gleich, keine Zwischenablage/Meldung.
Das Ersetzen des Befundteils beim Öffnen (Formatierer 2.5.26) ist offline belegt (`test_zurueckgestellt_2525.py`), am Testpatienten
nicht geöffnet (Roboter für 451898 aus).
```
## Lendenwirbelsäule in 2 Ebenen

## Befund

Normale Lordose der Lendenwirbelsäule. Die LWK sind nach Anzahl, Form, Größe und Stellung zueinander regelrecht. Mineralgehalt und Knochenstruktur sind unauffällig. Die kortikalen Randkonturen sind einschließlich der Grund- und Deckplatten glatt und scharf abgrenzbar. Die Abgänge der Bogenwurzeln, die Dorn-, Quer- und Gelenkfortsätze sind ordnungsgemäß konfiguriert. Die kleinen Wirbelgelenke sind ohne Auffälligkeiten. Normale Weite der Zwischenwirbelräume und des Spinalkanals.

Die paravertebralen Weichteile unauffällig.

## Ergebnis
Regelrechte Darstellung der LWS.
```

**GWS a.p. A/B/C (Kanban #459, Nachtrag)** – **Live 3.20.5**, CAS `wsap` (eine reine GWS-a.p.-Leistung gibt es in CAS nicht),
Lauf-Datei `vorlagen` = `["ganzaufnahme_der_wirbelsäule_a-p"]`. ✅ #459 auf „erledigt“ gesetzt.
A (20261121018):
```
## Ganzaufnahme der Wirbelsäule a.-p.

## Befund
Wirbelsäule: Normale Stellung. Alignementlinien regelrecht.

Anzahl, Form, Größe und Stellung der Wirbelkörper zueinander regelrecht. Mineralgehalt und Knochenstruktur unauffällig. Kortikale Randkonturen, einschließlich Platae terminales, glatt und scharf begrenzt. Bogenwurzeln und Querfortsätze regelrecht konfiguriert. Zwischenwirbelräume und Spinalkanal normal weit. Mitdargestellte Anteile der Rippen unauffällig.

Keine radiopaken Fremdkörper.

## Ergebnis
Regelrechte Darstellung der Wirbelsäule.
```
B (20261121019):
```
## Ganzaufnahme der Wirbelsäule a.-p.

## Befund
Wirbelsäule: Flachbogige linkskonvexe Skoliose. Alignementlinien regelrecht. Im Übrigen Anzahl, Form, Größe und Stellung der Wirbelkörper zueinander regelrecht. Mineralgehalt und Knochenstruktur unauffällig. Kortikale Randkonturen, einschließlich Platae terminales, glatt und scharf begrenzt. Bogenwurzeln und Querfortsätze regelrecht konfiguriert. Zwischenwirbelräume und Spinalkanal normal weit. Mitdargestellte Anteile der Rippen unauffällig.

Keine radiopaken Fremdkörper.

## Ergebnis
Flachbogige linkskonvexe Skoliose.
```
C mit SQUIRREL „einzeln“ (20261121020, 3/3 IB-Lab-Zeilen):
```
## Ganzaufnahme der Wirbelsäule a.-p.

## Befund
Wirbelsäule: Rechtskonvexe skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 44°. Alignementlinien regelrecht. Anzahl, Form, Größe und Stellung der Wirbelkörper zueinander regelrecht. Mineralgehalt und Knochenstruktur unauffällig. Kortikale Randkonturen, einschließlich Platae terminales, glatt und scharf begrenzt. Bogenwurzeln und Querfortsätze regelrecht konfiguriert. Zwischenwirbelräume und Spinalkanal normal weit. Mitdargestellte Anteile der Rippen unauffällig.

Keine radiopaken Fremdkörper.

## Ergebnis
Hochgradige rechtskonvexe Skoliose der BWS.

Anmerkung: Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.
```

**(e) „Aufnahme starten“ fragt vor dem Löschen** – nur **offline** belegt (`tests/offline/test_georg_2011_ui.py` „39 …“, echte
Tk-Klasse mit Attrappen; Windows-UI-Test der EXE grün). Am Büro-PC nicht geklickt (dafür hätte jemand Text ins Diktatfeld tippen
müssen; Klicks über die Strecke hinaus waren nicht vorgesehen). Seit 3.19.16 löscht der Start rechts ohnehin nichts.

## 4. Funde am Rand
- **ESET „Anwendung geändert“**: Nach dem Austausch der EXE im selben Testordner sperrte ESET deren Netz (WinError 10013 /
  Timeout zu oauth2.googleapis.com) und wartet am Büro-PC mit einem Dialog. Neuer Ordner = kein Problem; der Tausch auf X: löste
  keinen Dialog aus, Live 3.20.5 hat Netz (Diktate d, A–C). Kanban #461 (Peter: Dialog mit „Regeln beibehalten“ schließen).
- Die Autostart-Verknüpfung am Büro-PC heißt seit dem ersten Start von ≥ 3.19.19 `KaiScribe.lnk` (RaKScribe.lnk weg) und
  `%APPDATA%\KaiScribe` ist angelegt (Umzug 3.19.19) – Nachtrag an `kaiscribe-umzug-n2-ordi`.
- Nachträge an `kaiscribe-squirrel-ergebnistext-n1-einspielen` und `kaiscribe-befundfeld-sicher-n1-einspielen-f1`: kein Tausch
  auf 3.19.18 mehr (3.20.5 enthält alles).
- Teststrecke: `kaiscribe.py` brach ab, weil im gemeinsamen X:-Log eine nie geschlossene Aufnahme vom 20.11. stand → 1.8 zählt nur
  Zeilen seit dem letzten Start.
- Sauber-Prüfung ris-mods: 3fc58d2 und 3e8db91 jeweils alles grün außer 2 Tests in `autark` (Cron-Doktor, nicht geändert).
  Ursache: `os.nice(10)` im Startparameter scheitert, wenn der Prüflauf schon maximal „nett“ läuft → robust gemacht (b371c3e),
  `nice -n 19` 124/124 grün; dritter Lauf siehe Abschluss.
- Knie-Text (KI): „Ansonsten die Gelenkflächen normal geformt und kongruent.“ neben „Rechts sind die Gelenkflächen …“ – inhaltlich
  richtig, sprachlich holprig; Georg bitte beim ersten echten Knie-beidseits-Fall ansehen.
