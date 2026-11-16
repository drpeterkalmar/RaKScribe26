# Bericht kaiscribe-kniepat-titel-n1 (Mo 16.11.2026, Teil 1 = Bau) – Knie + Patella axial bekommt „mit Patella axial“ im Titel (Kanban #344)

Teil 1 ohne Büro-PC und ohne Befund-PCs: kein Ordi-Auftrag, nichts eingespielt, kein Diktat am Testpatienten, kein LLM-/Google-Aufruf.
Einspielen und Abnahme macht der Folgeauftrag `kaiscribe-kniepat-titel-n1-einspielen` (Brief `FOLGEJOB-KNIEPAT-TITEL-N1-EINSPIELEN.md`).

## Kurz (für Peter)

1. Bei den Leistungen kniepatl, kniepatr und kniepat2 heißt der KaiScribe-Titel jetzt „Kniegelenk links in 2 Ebenen mit Patella axial“
   (rechts bzw. beidseits genauso). Bisher fehlte „mit Patella axial“. Der Wortlaut folgt der Titel-Tabelle in ris-mods
   („Röntgen des linken Kniegelenks in 2 Ebenen mit Patella axial“) in der KaiScribe-Form ohne „Röntgen des …“.
2. Alle anderen Titel bleiben gleich, auch bei kniel/knier/knie2 („Kniegelenk links in 2 Ebenen“).
3. Dafür gibt es eine neue Vorlage „Kniegelenk in 2 Ebenen mit Patella axial“: der Knie-Normalbefund plus ein Satz zur axialen Aufnahme.
4. Der Formatierer am Büro-PC braucht keine Änderung, er übernimmt den neuen Titel so, wie er ist.
5. Version 3.19.4. Eingespielt wird heute Nacht vom Folgeauftrag, abgenommen am Testpatienten.

👉 Bitte den neuen Normalsatz der Vorlage kurz ansehen (Abschnitt 1), bis Fr 20.11. Passt er nicht, schreiben Sie den Wortlaut dazu, er wird 1:1 übernommen.

## 1. Ursache und Änderung

- **Ursache:** Die Brücke ordnet kniepatl/kniepatr/kniepat2 die Vorlage `kniegelenk_in_2_ebenen` zu (ris-mods `katalog/kuerzel_vorlage.tsv`).
  KaiScribe hatte keine Vorlage mit Patella, deshalb bekam die KI `<untersuchung>Kniegelenk in 2 Ebenen</untersuchung>`, und der
  Normalbefund-Weg setzte denselben Titel ein. So entstand im Echtfall 1112-036 der Titel „Kniegelenk links in 2 Ebenen“.
- **Neue Vorlage** `kniegelenk_in_2_ebenen_mit_patella_axial` in `templates.json` (EXE und Web lesen dieselbe Datei):
  Anzeigename „Kniegelenk in 2 Ebenen mit Patella axial“. Der Text ist der Knie-Normalbefund, der Patella-Satz ist erweitert:
  „Patella in regelrechter Position, **in der axialen Aufnahme zentriert im femoralen Gleitlager. Femoropatellarer Gelenkspalt normal weit.**“
  Das Ergebnis lautet wie beim Knie: „Regelrechte Darstellung des Kniegelenkes (links/rechts).“
- **CAS-Weg** (`source_code/cas_vorlagen.py`, nur EXE, die Web-App hat keine CAS-Leistungen):
  - `ZUSATZ_VORLAGEN` / `zusatz_vorlage`: Liefert die Brücke `kniegelenk_in_2_ebenen` und nennt der Leistungstext „Patella ax…/tang…“
    bzw. „axiale Patella“, nimmt KaiScribe die neue Vorlage. Das gilt auch, wenn die Brücke später selbst den neuen Schlüssel liefert.
  - `abgleich`: Ein Diktat „Knie links …“ (erkannt: Grund-Vorlage) bestätigt die erweiterte CAS-Vorlage. Eine genauere Untersuchung im
    Diktat bleibt, z. B. „Knie-TEP links …“ → Knieprothese.
- **Diktat ohne CAS** (`vorlagen_vorrang.json`, EXE und Web gleich): Nennt ein Knie-Diktat irgendwo „Patella axial/tangential“ bzw.
  „axiale Patella“, nimmt KaiScribe die neue Vorlage. Bei Defilee, TEP/Prothese, MR und Sono greift das nicht.
- **Titel** (keine neue Titel-Logik): `titel_mit_seite` setzt die Seite vor „in 2 Ebenen“, `titel_beidseits` macht bei kniepat2 „beidseits“ daraus.
  Bei einem pathologischen Diktat schreibt die KI den Titel nach der Prompt-Regel aus `<untersuchung>`.

| CAS-Leistung (Text der Brücke) | Diktat | Titel vorher | Titel nachher |
|---|---|---|---|
| kniepatl „Knie li mit Patella axial“ | „Kniegelenk links: Erguss …“ (KI) | Kniegelenk links in 2 Ebenen | Kniegelenk links in 2 Ebenen mit Patella axial |
| kniepatl | „Knie links unauffällig“ (ohne KI) | Kniegelenk links in 2 Ebenen | Kniegelenk links in 2 Ebenen mit Patella axial |
| kniepatr „Knie re mit Patella axial“ | „Unauffällig.“ | Kniegelenk rechts in 2 Ebenen | Kniegelenk rechts in 2 Ebenen mit Patella axial |
| kniepat2 „Kniegelenk bds.mit Patella ax.“ | „Knie links geringgradige Gonarthrose …“ | Kniegelenk beidseits in 2 Ebenen | Kniegelenk beidseits in 2 Ebenen mit Patella axial |
| kniel „Kniegelenk links“ | „Knie links unauffällig“ | Kniegelenk links in 2 Ebenen | unverändert |
| kniepatl | „Knie-TEP links: …“ | Knieprothese | unverändert |

Hinweis: „Knie links **mit** Patella axial unauffällig“ läuft wie bisher über die KI und nicht über den Normalbefund-Weg, weil „mit“
dort einen Zusatzbefund ankündigt. Das gilt seit v3.2 für alle Vorlagen und wurde nicht geändert. „Knie links und Patella axial
unauffällig“ läuft ohne KI.

## 2. Formatierer (ris-mods) – keine Änderung nötig

Probe mit dem echten Einsetz-Weg aus `formatierer/tests/test_titel_regel_c.py` (rakscribe_einsetzen + Word-Attrappe, ris-mods main
65d79e1, Python 3.12). Die Basis-Datei war grün (0 Fehler), dazu 6 Zusatzfälle, alle ok, je genau EIN Titel:
- Befund-Modus „## Kniegelenk links in 2 Ebenen mit Patella axial“ + kniepatl → Titel wörtlich so, Text darunter
- Nur Text mit Leerzeile bzw. mit „…:“ + kniepatl → derselbe Titel ohne Doppelpunkt
- rechts + kniepatr, beidseits + kniepat2 → Titel wörtlich
- Gegenprobe „## Kniegelenk links in 2 Ebenen“ + kniepatl → wie bisher

Der Titel entsteht also in KaiScribe. Der Formatierer ersetzt KaiScribe-Titel bewusst nicht durch die Tabelle (Bericht
kaiscribe-titel-regel-n2, Abschnitt 2). In ris-mods ist nichts geändert, deshalb ist dort keine Windows-Prüfung nötig.
Der Testfall steht in den KaiScribe-Tests (Auftrag: „test_titel_regel_c.py bzw. KaiScribe-Tests“).

## 3. Tests (offline, ohne KI)

- `tests/offline/test_cas_leistungen.py`: neuer Block „#344“ mit 14 Prüfungen. Abgedeckt sind die Vorlagenwahl für kniepatl/kniepatr/kniepat2/kniel,
  TEP, Knie + Fuß, die Titel im KI-Weg (Attrappe) und im Normalbefund-Weg, beidseits sowie die Gegenproben.
- `vorlagen_vorrang_tests.json` + `detect_fixtures.json`: 8 Erkennungsfälle (5 neue Vorlage, Gegenproben TEP/MRT/„Patella in regelrechter
  Position“) und die 3 Namens-Diktate der neuen Vorlage. EXE und Web liefern jeweils denselben Wert.
- Ganze Offline-Suite wie `.github/workflows/test.yml` (Python 3.12 mit Tk, Node): alles grün außer `test_maske_ablauf.py`.
  Der ist am Mac auch auf dem unveränderten main rot (dieselben 31 Fehler, Mammo-Maske, Mac-Umgebung) und auf GitHub grün.
  Er berührt nichts von dieser Änderung. Beleg auf GitHub: Lauf „Tests“ zum Commit dieser Version.
- Probe über alle 144 Vorlagen (`vorlagen_erreichbar_test.py`): alle erreichbar, 102 Vorrang-Fälle, EXE und Web liefern dasselbe.

## 4. Version und Einspielen

- Version **3.19.4** (VERSION-Datei, vergeben beim Zusammenführen). Die Release-EXE baut GitHub (`build-exe.yml`), danach läuft der Windows-UI-Test.
- Stand 16.11. 23:00: main **1a3512d** (Code d142156). GitHub „Tests“ grün (Lauf 43962220624), Build 3.19.4 (Lauf 43962992275),
  **Release 3.19.4**: `rakscribe26.exe` 56.811.184 B, sha256 `5e1308dc46a5a7640f7217876b6f82d4a20fc471264da894df7b721cc8a4b2d0`.
  Windows-UI-Test **115/115** (Lauf 43963359467). 3.19.4 enthält auch 3.19.2 (Humeruskopf) und 3.19.3 (Mammo-Vergleichsdatum, bisher ohne
  eigenes Release). Ein Tausch auf 3.19.4 spielt also alle drei ein.
- Einspielen (Teil 2): wie 3.19.1/3.19.2 mit ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1 -Schritt exe` am Büro-PC.
  **Rückweg:** `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste `.alt`, nur außerhalb Mo–Fr 06:30–20:10).
  Ein Rückweg nur für diese Änderung ohne EXE-Tausch geht nicht, weil die Vorlagen in der EXE gebündelt sind.

## Offen (Teil 2 bzw. später)

- Teil 2 ist eingereiht: `kaiscribe-kniepat-titel-n1-einspielen` (ordi + automaten-vm, prio 6, ohne Startzeit, weil es schon nach 20:10 war).
  Es gab keinen wartenden Einspiel-Auftrag für KaiScribe, an den man hätte anhängen können. Kanban #344 hat eine Notiz bekommen, #364 (Peter: Normalsatz) ist angelegt.

- Einspielen und Abnahme am Testpatienten 451898 mit der Leistung kniepatl, danach `kanban.py fertig 344` → Folgeauftrag.
- Lücke aus Teil 1: Es ist nicht belegt, dass die Teststrecke einen Testeintrag mit **kniepatl** anlegen kann. Bisher hat sie nur
  Einzelleistungen wie bü angelegt (siehe Folgeauftrag).
- Nacht-Regression auf der VM (`automaten_vm/titel_n2/faelle.json`, Fall 1112-036): Sie prüft die gespeicherte KaiScribe-Ablage mit dem
  alten Titel und bleibt deshalb grün. Das Soll „Kniegelenk links in 2 Ebenen“ wird erst geändert, wenn ein neuer Echtfall
  mit dem neuen Titel vorliegt. Bis dahin bleibt alles wie es ist.
- Optional: In ris-mods könnte `katalog/kuerzel_vorlage.tsv` den neuen Schlüssel direkt liefern. Das ist nicht nötig, weil KaiScribe ihn selbst ableitet,
  und es würde einen Brücken-Bau bedeuten.
