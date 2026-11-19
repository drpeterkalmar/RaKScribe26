# Bericht kaiscribe-mehrfach-seitenlos-n1 (Teil 1, Do 19.11.2026 17:38–18:45, Mac): zwei Untersuchungen in einem Diktat

Georg 19.11. (Foto): CAS-Auftrag **lws + bü**, ein Diktat → KaiScribe machte nur den Befund „Lendenwirbelsäule in 2 Ebenen“. Die Becken-
Befunde (Coxarthrose, Fibroostosen SIAS/Trochanter) standen im LWS-Text, die Hüftbeschreibung fehlte, die HIPPO-Zeile hing als eigener Absatz
am Ende. Nachtrag Georg 09:26: beide Befunde sofort im Befundfenster, und das auch fließend diktiert ohne Regionsnennung.

## 1. Ursache
- `befund_regeln.split_regionen` (EXE) bzw. `splitRegionen` (Web) trennten nur Regionen **mit Seite** aus einer Liste von Extremitäten.
  LWS, Becken/BÜ, Thorax, Schädel usw. trennten nie. Dadurch blieb LWS + Becken ein Abschnitt mit nur einer Vorlage.
- Mit CAS teilte die EXE zwar an Satzanfängen, die eine andere CAS-Untersuchung nennen (`cas_vorlagen.aufteilen`). Ein Diktat ohne
  Regionsnennung blieb aber ein Abschnitt. IB-Lab-HIPPO fand dann keinen Beckenbefund und landete „am Ende“.

## 2. Änderung (3.19.14, EXE + Web gleich)
1. **Regionen ohne Seite trennen** (`REGIONEN_OHNE_SEITE` in `befund_regeln.py` und `befundRegeln.ts`): Becken/Beckenübersicht/BÜ/Hüften bds.,
   LWS, BWS, HWS, GWS/gesamte Wirbelsäule, Thorax/Lunge, Schädel, NNH, Abdomen, Kreuzbein/Sakrum, Steißbein.
   - Das gilt nur am Diktat- oder Satzanfang (nach Punkt, „Punkt“, „neue Zeile“, Doppelpunkt), nicht nach Komma.
   - Das Wort muss allein stehen. „Fibroostosen am Becken“ und „Beckenschiefstand“ trennen nicht.
   - Empfehlungen („Beckenübersicht empfohlen“) trennen nicht.
   - **Kombi-Vorlagen bleiben ein Befund:** HWS + LWS (`hws_und_lws`), Becken + Hüfte (`beckenübersicht_und_hüfte`, RH 99/128),
     Kreuzbein + Steißbein. Mit CAS teilt `aufteilen` HWS/LWS weiter, wenn beide als eigene Leistungen bestellt sind (wie bisher).
   - 12 neue Fixtures in `befund_regeln_fixtures.json` („split“). Sie laufen durch die Python- und die TS-Engine.
2. **Mit CAS: Sätze nach Inhalt zuordnen** (`cas_vorlagen.inhalt_zuordnen`, aufgerufen in `pipeline.cas_wahlen`). Das greift nur bei ≥ 2 CAS-
   Untersuchungen mit Vorlage. Jeder Satz und Teilsatz (bis Komma) geht über seine Anatomie-Begriffe zu genau einer Untersuchung:
   - **LWS:** L1–L5/S1, LWK.
   - **BWS:** Th1–12. **HWS:** C1–7.
   - **Die Wirbelsäulen-Untersuchung des Auftrags:** Spondylose/-phyten, Osteochondrose, Lordose, Wirbelkörper, Bandscheibe …
   - **Becken/Hüfte:** Coxarthrose, Hüftkopf, Pfannendach, ISG, Symphyse, Trochanter, Spina iliaca/SIAS, Beckenschaufel, Beckenschiefstand …
   - **Knie:** Kniegelenk, Patella, femoropatellar, Gonarthrose …
   - **Rho:** zur Wirbelsäule.

   Regeln dazu:
   - Regionsnennung im Diktat hat Vorrang. Ein Satz ohne Begriff (Osteopenie, „rechts tiefer“) gehört zum Satz davor.
   - **Rote Prüfzeile statt Raten:** bei einem Satz mit Begriffen zweier CAS-Untersuchungen („Osteochondrose L5/S1 und ISG-Arthrose“) und bei
     einem Begriff einer Region, die im CAS-Auftrag fehlt („Kniegelenk mit Erguss“ bei lws + bü). Der Satz bleibt dann, wo er war.
   - Ist alles klar getrennt diktiert, bleiben die Abschnitte unverändert.
   - Jede Untersuchung bekommt die Vorlage ihrer CAS-Leistung. Die genauere Vorlage aus dem Diktat gilt nur, wenn der Satzanfang die
     Untersuchung nennt („Hüftgelenk links: …“), nicht wenn ein Befundwort nur darauf zeigt.
3. **IB Lab:** HIPPO landet so im Beckenbefund (Zuordnung über die Region, `ibl_bausteine.zuordnen`/`fuer_abschnitt` unverändert). Rho
   (diktiert) landet im LWS-Befund. KOALA → Knie, LAMA → Ganzbein und FROG → Fuß sind unverändert regionsgebunden.
4. **Anzeige (Nachtrag 1):** Beide Befunde stehen nach INS untereinander im Befundfenster, je mit eigener Überschrift und eigenem Ergebnis, und
   sind bis EOL editierbar. EOL schickt beide wie bisherige Mehrregionen-Befunde (`assemble_regions`/`befunde_zusammenfuegen`).
   - Prüfzeilen im CAS-Band sind jetzt **rot** („… – bitte prüfen“, „… nicht in den CAS-Leistungen“). Die übrigen Hinweise bleiben amber.
   - Prüfzeilen mit Diktat-Wortlaut gehen nur als Zahl ins Protokoll (Umbau Schritt 23).
5. **Regel-Register:** neue Regel `mehrfach-untersuchung` („Mehrere Untersuchungen in einem Diktat → je Untersuchung eigener Befund mit eigener
   Vorlage“, Georg 05.10./18.11./19.11.) mit Prüfwörtern in EXE, Web, `cas_vorlagen` und `pipeline`. Sie ist Pflicht-Regel im Wächter.

## 3. Tests
- Neues Gate `tests/offline/test_mehrfach_seitenlos.py` (in `test.yml`) mit 38 Prüfungen, alle grün:
  - Georgs Fall maskiert, mit Überschriften und ohne Satzzeichen.
  - Nachtrag-Fixture ohne Regionsnennung.
  - Variante bü → „Beckenübersicht und Hüfte“.
  - HIPPO-Baustein (Beckenschiefstand 1 mm rechts tiefer, BLD 1 mm rechts kürzer): HIPPO-Sätze + Schlusssatz **nur** im Beckenbefund.
  - Coxarthrose mit **K&L-Tabellensatz Grad 2 links nur im Beckentext**, die LWS ohne Becken-Befunde.
  - Prüfzeilen (unklar/fremd), Rho → LWS, ohne CAS zwei Befunde.
- `test_cas_leistungen.py`, EXE-Ablauf mit Attrappen:
  - Diktat ohne Regionsnennung → beide Befunde im Befundfenster, Prompts je nur mit „ihren“ Sätzen.
  - EOL-Bestätigung „Beckenübersicht stehend · Lendenwirbelsäule in 2 Ebenen“.
  - Rote Prüfzeile im Band.
- **Bestehende Mehrfachregion-Fixtures** (Schulter + Ellbogen, Knie re/li, drei Regionen …) **bleiben grün**.
- GitHub „Tests“ 44574396135 für `bd8a4a1` ist **grün** (alle Python-Gates inkl. tsc/eslint). tsc und eslint liefen zusätzlich am Mac in einer
  Kopie mit `npm ci`: 0 Fehler.
- Am Mac sind `test_cas_auftrag.py` und `test_maske_ablauf.py` mit `/usr/bin/python3` (3.9, einziges Python mit tkinter) auch auf dem
  unveränderten main rot bzw. wechselhaft. Das liegt an der Umgebung, nicht an der Änderung: In GitHub sind beide grün.

**Prüftext** (Georgs Diktat mit Überschriften + HIPPO, CAS lws + bü). Er entstand mit der KI-Attrappe des Tests: Die Gliederung, die Wächter,
die HIPPO-Sätze und der K&L-Satz sind echt, den Wortlaut der Befundsätze schreibt live die KI.
```
## Lendenwirbelsäule in 2 Ebenen

## Befund
Geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung der Grund- und Deckplatten.
Geringe ventrale Spondylophyten L3 bis L5.
Normale Lordose der Lendenwirbelsäule. … Im Übrigen normale Weite der Zwischenwirbelräume und des Spinalkanals.

Die paravertebralen Weichteile unauffällig.

## Ergebnis
1. Geringe Osteochondrose L2 bis L4.
2. Geringe Spondylose L3 bis L5.


## Beckenübersicht stehend

## Befund
Beckenschiefstand von 1 mm, rechts tieferstehend. Beinlängendifferenz von 1 mm, rechts kürzer. Linkes Hüftgelenk: Geringe Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer Randzuschärfung.
Geringe Fibroostosen an der Spina iliaca anterior superior und am Trochanter major beidseits.
Im Übrigen anatomisch normale und symmetrische Form des Beckenskeletts. … Das Os sacrum ist unauffällig. Unauffällige Weichteile.

## Ergebnis
1. Geringgradige Coxarthrose links (Arthrose Grad 2 nach Kellgren & Lawrence).
2. Geringe Fibroostosen beidseits.
Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.
```
Nachtrag-Fixture „geringe Coxarthrose links, Osteochondrose L5/S1, Fibroostosen am Trochanter major beidseits, Spondylophyten L3 bis L5“
(CAS lws + bü) wird so aufgeteilt:
- **Beckenübersicht stehend:** „geringe Coxarthrose links, Fibroostosen am Trochanter major beidseits“
- **Lendenwirbelsäule in 2 Ebenen:** „Osteochondrose L5/S1, Spondylophyten L3 bis L5“

## 4. Version, Web, EXE
- **3.19.14** auf main (`bd8a4a1`).
- Web: https://drpeterkalmar.github.io/RaKScribe26/ zeigt **3.19.14**. Der Deploy-Run 44575137195 brach zuerst an einem GitHub-Artefakt-
  Aussetzer ab und war nach dem Neustart grün.
- EXE: Build 44575168613 und Windows-UI-Test 44575606706 sind **grün**. Release **3.19.14 = latest**, `rakscribe26.exe` 56 868 662 Byte,
  sha256 `3aec0b8d3cc5190e568468ee639f1c0d5af05a9a905b655a47671760dd17ca1f`.
- ris-mods (Brücke/Formatierer/Abholer): keine Änderung nötig.

## 5. Einspielen → Folgeauftrag
`kaiscribe-mehrfach-seitenlos-n1-einspielen` ist eingereiht: frühestens Do 19.11. 20:15, Ressource ordi, verfällt Fr 20.11. 06:30.
Der Brief liegt in `FOLGEJOB-KAISCRIBE-MEHRFACH-SEITENLOS-N1-EINSPIELEN.md`: Tausch 3.19.13 → 3.19.14, Abnahme 451898 mit lws + bü,
Diktat A (Nachtrag) und B (Georgs Fall).

## 6. Grenzen / offen
- **Web** hat keine CAS-Leistungen. Dort trennen nur Regionsnennungen am Satzanfang (Punkt 1). Die Zuordnung nach Inhalt (Punkt 2) gibt es
  nur in der EXE mit CAS-Auftrag.
- Ein „Becken unauffällig.“ als eigener Satz im LWS-Diktat ergibt jetzt einen eigenen Beckenbefund. Ohne Becken im CAS-Auftrag kommt dazu
  die rote Zeile „nicht in den CAS-Leistungen“. „Miterfasstes Becken …“ trennt nicht.
- Mehrdeutige Sätze ohne Begriff (Osteopenie, „unauffällige Weichteile“) gehen zum vorangehenden Abschnitt und werden nicht kopiert.
- Rho aus IB Lab bleibt Anzeige (Regel `ibl-rho`). Nur der diktierte Rho-Baustein geht in den LWS-Befund.
