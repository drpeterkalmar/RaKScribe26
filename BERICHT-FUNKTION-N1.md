# Bericht kaiscribe-funktion-n1 (Di 17.11.2026, Teil 1 = Bau) – Funktionsaufnahmen vergessen (RH 97)

Teil 1 lief auf dem Hetzner-Server, ohne Büro-PC und ohne Befund-PCs: kein Ordi-Auftrag, nichts eingespielt, kein Diktat am
Testpatienten, kein KI- oder Google-Aufruf (kein Gemini). Einspielen und Abnahme sind an den wartenden Abend-Auftrag
`kaiscribe-kniepat-titel-n1-einspielen-f1` angehängt (ein Einspielen und eine Abnahme-Runde für KaiScribe heute Abend).

## Kurz (für Peter)

1. Bei der Leistung „HWS ap u. seitl. incl.Funktion“ (auch „HWS + Funktion“, „LWS mit Funktionaufnahmen“) schreibt KaiScribe jetzt
   zwei Abschnitte: „Halswirbelsäule in 2 Ebenen“ mit dem Diktat und danach „Funktionsaufnahmen der Halswirbelsäule“.
2. Haben Sie zur Funktion nichts diktiert, steht dort der Normaltext der Vorlage (ohne KI). Haben Sie etwas diktiert (z. B.
   „Funktionsaufnahmen: Instabilität C4/5“), kommt genau das in den Funktions-Abschnitt, und der Normaltext entfällt.
3. „Funktionsaufnahmen empfohlen“ im Diktat erzeugt keinen Abschnitt. Es zählt nur die Leistung.
4. Version **3.19.6** (3.19.5 war schon für die Web-App vergeben). Eingespielt wird heute Abend ab 20:15 zusammen mit dem Knie-Fix.

## 1. Ursache

- Die Brücke ordnet `hwsmf` „HWS ap u. seitl. incl.Funktion“ (und `hwsf`, `lwsf`, `lwsmf`) die Vorlage
  `funktionsaufnahmen_der_halswirbelsäule` bzw. `…_lendenwirbelsäule` zu (ris-mods `katalog/kuerzel_vorlage.tsv`).
- Das Diktat „HWS flachbogig …“ erkennt die Vorlage `halswirbelsäule_in_2_ebenen`. `cas_vorlagen.abgleich` behandelt bei gleicher
  Region und gleicher Modalität die Diktat-Vorlage als „die genauere“ und nahm sie. Damit war die Funktions-Leistung „erledigt“,
  und die Funktionsaufnahmen fielen still weg, mit Titel und Befund und ohne Hinweis. Genau so ist RH 97 entstanden
  (CAS hwsmf + kp, KaiScribe 3.19.4).

## 2. Änderung (nur EXE: die Web-App hat keine CAS-Leistungen, also gibt es nichts zu synchronisieren)

`source_code/cas_vorlagen.py`, `source_code/pipeline.py` (`cas_wahlen`):
- `FUNKTION_VORLAGEN` / `funktion_region`: Nennt der Leistungstext „Funktion…“ und HWS oder LWS, und ist die Vorlage der Brücke die
  Grund- oder Funktions-Vorlage dieser Region, dann gilt:
  - **Grund-Untersuchung + Funktion** („HWS ap u. seitl. incl.Funktion“, „HWS + Funktion“, „HWS inkl. Funktion“, „LWS mit
    Funktionaufnahmen“): Daraus werden zwei Untersuchungen, also die Grund-Vorlage (eigener Titel) und die Funktions-Vorlage (eigener Titel).
  - **Nur „Funktionsaufnahmen HWS“** (`fhws`, `flws`): Es gibt nur die Funktions-Vorlage. Ein Diktat „HWS …“ bestätigt sie, wie bei #344
    Patella axial. Es gibt keinen „in 2 Ebenen“-Titel ohne eigene Leistung.
- `funktion_ergaenzen` (nach der Vorlagenwahl): Fehlt der Funktions-Abschnitt, kommt er direkt **nach** den Abschnitt
  der Grund-Untersuchung.
  - Diktierte Funktions-Sätze (funktion/flexion/inklination/reklination/Beugeaufnahme/Bewegungsdiagramm; nach einem Doppelpunkt
    auch der folgende Satz) werden in diesen Abschnitt verschoben und laufen über die KI mit der Funktions-Vorlage. Sie haben also Vorrang vor dem Normaltext.
  - Sonst kommt der Normalbefund der Funktions-Vorlage, Titel + Normaltext + Normal-Ergebnis, ohne KI.
  - Empfehlungssätze (Muster `kurzsaetze.empfehlung` aus `vorlagen_vorrang.json`) zählen nicht als Funktionsbefund (EMPFOHLEN ≠ GEMACHT).
  - Hat der ganze Abschnitt wegen des Worts „Funktionsaufnahmen“ die Funktions-Vorlage bekommen, wird er geteilt: Der Rest geht
    in die Grund-Vorlage, die Funktions-Sätze gehen in den Funktions-Abschnitt.
  - Ist die HWS gar nicht diktiert, entsteht kein Funktions-Abschnitt. Es bleibt ein einziger Hinweis „… laut CAS, nicht diktiert“.
- `wahl`/`aufteilen`: Der Funktions-Teil zählt nicht als eigene Kandidatin. So bleibt „Unauffällig.“ + „HWS + Funktion“ eindeutig
  HWS + Funktion (sonst wäre es „Allgemein“ geworden).
- BWS („Brustwirbelsäule + Funktion“) bleibt unverändert, weil es keine BWS-Funktions-Vorlage gibt.

Beispiel RH 97 (Attrappe statt KI): Die Titel sind jetzt „Schultergelenk … in 2 Ebenen“ · „Halswirbelsäule in 2 Ebenen“ (Skoliose,
Streckhaltung) · „Funktionsaufnahmen der Halswirbelsäule“ (Normaltext „Regelrechte Stellung in maximaler Ante- und Retroflexion …“,
Ergebnis „Regelrechte Darstellung der HWS. Kein Hinweis auf eine segmentale Instabilität.“).

## 3. Tests (offline, ohne KI)

- Regressionsfall maskiert in `tests/offline/test_cas_leistungen.py`, Block „kaiscribe-funktion-n1“ mit 18 Prüfungen: RH 97 wörtlich
  (Diktat aus dem Auftrag, CAS-Texte ohne Patientendaten), HWS/LWS, „+ Funktion“, „inkl. Funktion“, diktierte Funktion
  (Doppelpunkt, Inklination/Reklination), Empfehlung, Leistung ohne Funktion, nur Funktionsaufnahmen, HWS nicht diktiert, BWS.
  Vorher **rot** (11 ❌ auf dem alten Code, RH 97 reproduziert), danach grün.
- Warum nicht `befund_regeln_fixtures` / `vorlagen_vorrang_tests`: Die gelten für die Erkennung ohne CAS (EXE = Web). Der Fehler
  liegt im CAS-Abgleich, den es nur in der EXE gibt. An der Erkennung ohne CAS hat sich nichts geändert.
- Die ganze Python-Offline-Suite wie `.github/workflows/test.yml` (39 Dateien, venv mit Tk) ist grün, darunter Regeln PY+TS 213/213,
  Widerspruch-Matrix 0 ✗, `test_cas_kontext`, `test_pipeline_exe`, `test_maske_ablauf` und „ohne CAS-Datei bit-gleich“. Die Node-Tests
  (`web_app/*.mjs`, tsc, eslint) liefen hier nicht (kein `npm ci` auf dem Server), weil an der Web-App nichts geändert ist. GitHub „Tests“ läuft auf main.
- Formatierer (ris-mods `formatierer`, Kopie unter `~/cj/work/kaiscribe-funktion-n1/fmt`, Word-Attrappe, Linux): `rakscribe_einsetzen`
  mit dem Drei-Abschnitt-Befund und den Leistungen hwsmf + kp setzt drei Titel ein, ohne Warnung und ohne interne Prüfung.
  ris-mods ist unverändert. Am echten Word prüft das die Abnahme.

## 4. Andere „incl./inkl.“-Zusätze (nur gemeldet, nicht ausgeweitet)

Geprüft gegen `kuerzel_vorlage.tsv` und die Vorlagenwahl:
- **Gehaltene Aufnahmen Sprunggelenk (sgrg/sglg/sgbg)**: Hier steckt **derselbe Fehler**. Die Brücke liefert `sprunggelenk_gehaltene_aufnahmen`,
  das Diktat „Sprunggelenk links …“ / „OSG links unauffällig“ setzt aber `sprunggelenk_in_2_ebenen` durch. Dann heißt der Titel
  „Sprunggelenk in 2 Ebenen“, und die gehaltenen Aufnahmen fehlen. Der Fix ginge nach demselben Muster, er ist nicht gemacht (Auftrag: nur melden).
- **Oberschenkel/Unterschenkel „incl.Spezialaufn.“** → `…_in_2_ebenen`. Es gibt keine Vorlage für Spezialaufnahmen, deshalb fehlt der Zusatz still.
- **Rippen „bei Unfall incl.DL“** → `knöcherner_hemithorax`. Die Durchleuchtung steht nicht in der Vorlage.
- **BWS + Funktion (bwsf)**: Es gibt keine Funktions-Vorlage BWS, die Funktion fehlt also wie bisher.
- Unkritisch: „Hand inkl.Mittelhand“ (Mittelhand ist Teil der Hand-Vorlage), „I.v.Pyelographie incl.Nativauf“, „Knochendichte
  inkl.Fettmessung“ (eigene Vorlage bestätigt).

👉 Entscheiden: gehaltene Aufnahmen Sprunggelenk nach demselben Muster beheben (ja/nein)? Bis Fr 20.11. (Kanban-Karte)

## 5. Version, Bau, Einspielen

- **3.19.6** auf main **1c10a4c** (Code 05636b2). GitHub „Tests“ grün (Lauf 44077238918), Build 3.19.6 grün (Lauf 44077280641),
  **Release 3.19.6**: `rakscribe26.exe` 56.817.854 B, sha256 `53ebc44cdd45a0b63af550763f43dc3ac8b5b87b8784b2efdeb9965db3aad4c9`.
  Windows-UI-Test grün (Lauf 44077601302).
- 3.19.6 enthält 3.19.4 (Knie Patella axial) und 3.19.5 (Web-App-Schlüssel, ohne EXE-Änderung). Das Einspielen
  macht `kaiscribe-kniepat-titel-n1-einspielen-f1` (Nachtrag von diesem Job): neuestes grünes Release ≥ 3.19.6 tauschen, Abnahme RH-97-Muster
  am Testpatienten 451898, dann das Ergebnis in `ris-mods/ordi-hermes/ergebnis_kaiscribe_funktion_20261117.md` (OK + Commit + Version).
  Die Ergebnisdatei schreibt Teil 2 erst, wenn der Fix belegt live ist.
- Lücke für Teil 2: In Teil 1 ist nicht geprüft, ob die Teststrecke die Leistung hwsmf am Testpatienten anlegen kann. Ersatzweise
  geht eine cas_leistungen-Datei wie im Kniepat-Brief.
