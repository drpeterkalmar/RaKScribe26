# kaiscribe-ergaenzung-ohne-ins-n1 – Dazudiktieren rechts ohne INS (Teil 1: Bau, 26.11.2026)

Auslöser: Peter 26.11.2026 ~10:57, Diktat 20261126060 (RH 60), CASWS10, KaiScribe 3.28.2. Er hat rechts eine falsch
autobefundete Stelle markiert und darüber diktiert. Rechts erschien nichts, EOL sagte 15× „Erst INS“, INS traute er sich
nicht. Am Ende hat er abgebrochen, den Text herauskopiert und in SpeechMagic eingefügt. Das Nachdiktat ging verloren.

**Stand:** KaiScribe **3.31.0** ist auf main (`7468767`) und enthält auch 3.30.0. Die Offline-Gates sind grün. Teil 1
spielt nichts ein. Einspielen und Abnahme am Testpatienten 451898 laufen heute Abend mit dem schon wartenden Auftrag
`kaiscribe-nicht-diktiert-streichen-n1-einspielen`, an den ein Nachtrag angehängt ist. Alles Nötige steht in
`FOLGEJOB-KAISCRIBE-ERGAENZUNG-OHNE-INS-N1-EINSPIELEN.md`.

## Ursache (Code 3.28.2/3.30.0 + Log-Strukturzeilen aus dem Auftrag)
- Bis 3.30.0 war eine Pause nur eine Pause. Erkannt und eingefügt wurde erst mit INS bzw. Stopp. Bei kp ist die
  Live-Anzeige aus (live-anzeige-aus-kp-n1), deshalb sah Peter während der Ergänzung gar nichts.
- EOL in der Pause: `jobstate.vorschau("eol")` gibt in RECORDING/PAUSED nichts frei → immer „Erst INS“. Das ist die Sackgasse.
- **Der Widerspruch im Log:** `[EINFÜGEN] Ersetzt markierten Text (84 Zeichen) … (wörtlich, Nur Text an)` und
  `[BEFUNDFELD] Record: cursor` zeigen, dass KaiScribe die Markierung richtig erkannt hatte. INS hätte in diesem Zustand nur
  diese 84 Zeichen ersetzt, ohne Befund-KI und ohne Neuaufbau. Das belegt der alte Ablauftest 6b mit der echten
  RaKScribe-Logik. **Links** wäre aber nach INS das bisherige Diktat mit dem neuen Text dahinter gestanden, wie bei einem
  Nachdiktat. Bei Befundern mit Live-Anzeige erscheint dieser Text schon beim Sprechen. Das sieht aus wie „der ganze Befund
  wird neu gemacht“. Deshalb glaubte Peter, INS würde neu strukturieren. Am Büro-PC bleibt zu belegen, ob am 26.11.
  Live-Anzeige an oder aus war (Logzeile `[GOOGLE] Live-Anzeige aus für …` um 10:53:26) → Teil 2.
- „Nur Text“ war dafür nie nötig. Das Einfügen an der Cursor-Stelle läuft vor dem Nur-Text-Zweig, also ist das Ergebnis
  gleich. Peter hat den Schalter eingeschaltet, weil sonst nichts zu sehen war. Er ist gespeichert und bleibt an, bis
  jemand ihn ausschaltet. Beim **nächsten CAS-Auftrag** schaltet KaiScribe ihn aber selbst aus und zeigt einen Hinweis
  (georg-2011-n1), das ist im Log als `[MODUS] Nur Text beim neuen CAS-Auftrag ausgeschaltet` zu sehen. Der nächste
  CAS-Befund wird also kein „korr“. Ohne CAS (F10) bliebe er an.

## Umsetzung 3.31.0 (EXE `RaKScribe.py` + `befundfeld.py`, Web `App.tsx` + `befundfeld.ts`)
1. **Pause fügt ein:** Mit Cursor oder Markierung rechts erkennt jede Pause den eben gesprochenen Abschnitt sofort
   (chirp_3 nur auf diesem Audio, Fehlhör-Liste und Korrektur wie „Nur Text“, keine Befund-KI). Der Text kommt wörtlich an
   die Stelle bzw. ersetzt die Markierung. Die Abschnitte kommen streng der Reihe nach hinein (eigener Arbeits-Thread je
   Aufnahme). Record = weiter hängt dahinter an. Ein Klick oder eine neue Markierung in der Pause lenkt den nächsten
   Abschnitt dorthin. Links bleibt das bisherige Diktat, es wird nichts angehängt.
2. **INS** danach fügt nur noch den Rest seit der letzten Pause ein. Ein Neuaufbau passiert nie (Test 6d: keine Befund-KI).
3. **EOL** (`befundfeld.eol_aktion` ≡ `eolAktion`, 144 gemeinsame Fälle):
   - In der Pause, wenn alles rechts steht: Die Aufnahme endet und EOL schließt direkt ab.
   - Während der Aufnahme oder wenn noch eingefügt wird: Die Ergänzung wird erst eingefügt. Danach kommt der Hinweis
     „Ergänzung eingefügt – EOL nochmals zum Abschließen“.
   - Ergänzung ohne Cursor: Sie wird erst eingebaut, dann ist EOL nochmals nötig.
   - „Erst INS“ gibt es nur noch, wenn rechts noch kein Befund steht (Neuer Befund, IB-Lab-Gerüst, Maske).
4. **Statuszeile** dauerhaft: „Ergänzung an Cursor-Stelle · Aufnahme läuft · Pause = einfügen – der übrige Befund bleibt“
   bzw. „Ersetzt markierten Text (n Zeichen) · … Pause = ersetzen – der übrige Befund bleibt“. In der Pause steht „… Pause –
   steht rechts · Record: weiter · EOL: abschließen“. Die Hilfezeile im Menü ist angepasst.
5. **Nie still verlieren** (Nachtrag 10:58): Bei offener Ergänzung fragen „Fenster schließen“ und „CAS-Diktat abbrechen“
   nach (Ja = erst einfügen, nichts wird geschlossen). „Befund kopieren“ fügt erst ein und sagt, dass man nochmals kopieren
   soll. Im Web warnt `beforeunload`. Strg+Z holt den Stand vor der **ganzen** Ergänzung zurück und geht auch in der Pause.
6. Unverändert: SpeechMike-Belegung, F10-Ablauf, Mammo-Maske, Nachdiktat ohne Cursor (Pause wie bisher), Regel-Register
   (keine Befundregel berührt).

## Tests (alle grün, Hetzner offline, keine Google-/KI-Kosten)
- Neu: `tests/offline/test_ergaenzung_ohne_ins.py` (31 Prüfungen, in der CI). Es läuft genau Peters Ablauf mit und ohne
  „Nur Text“: Pause → Text rechts, links unverändert, keine Befund-KI → EOL schickt genau den sichtbaren Befund (Strg+V
  einmal). Dazu: Weiter-Diktieren, INS ohne Neuaufbau, Strg+Z über beide Abschnitte, EOL während der Aufnahme (zweimal),
  Ergänzung ohne Cursor, „Erst INS“ nur ohne Befund, Fenster zu und Befund kopieren bei offener Ergänzung, gemeinsame
  EOL-Tabelle.
- Angepasst auf die neue Bedeutung: `test_markierung.py` (RH 156/165, Klick und neue Markierung in der Pause, getippte
  Markierung + Strg+Z in der Pause, IB-Lab-Gerüst), `test_einfuegen.py`, `test_live_anzeige_aus.py` (kp: Pause ersetzt
  mit genau einem chirp_3-Aufruf), `test_speechmike_ablauf.py` (links nichts angehängt).
- Alle 72 Python-Gates aus `test.yml`, die Web-Tests `pipeline_test.mjs` 101/101, speechmike, audio, llm_anbieter und
  uebung sind grün. `tsc --noEmit` und `eslint src --max-warnings=0` sind grün.
- **Am echten Programm:** Der Windows-UI-Test hat einen neuen Fall „k“ (`tests/windows/exe_ui_test.py`). Die echte EXE läuft
  mit CAS-Auftrag: markieren → RECORD → Pause ⇒ steht rechts, links gleich, Status „steht rechts“ → EOL ⇒ „fertig“ an die
  Brücke mit genau diesem Text. Die R-Fälle (RH 156/165) sind auf die neue Bedeutung umgestellt. Ergebnis siehe Nachtrag CI.

## Nachtrag CI (26.11. 13:50)
GitHub für 3.31.0: Tests grün (`7468767`), Build Windows EXE grün (Release 3.31.0), **Windows-UI-Test 123/123 grün**
(Lauf 45821398625, Testskript `17f881f`, gleiche EXE). Am echten Programm: Markierung (22 Zeichen) → Record → Pause ⇒
rechts sofort ersetzt, links „Handgelenk links unauffällig“ unverändert, Zustand Pause; EOL ⇒ „fertig“ an die Brücke mit
genau diesem Text, kein „Erst INS“. Die ersten zwei Läufe waren nur wegen des Tests rot: Die Statuszeile zeigte in der
Pause den Kurzhinweis, und der Markier-Schritt hatte denselben Namen wie ein früherer Schritt, wurde also übersprungen.
Nach der Korrektur ist am Programm nichts mehr rot. Die Web-App ist über GitHub Pages seit 12:20 mit dem neuen Verhalten
online (automatisches Deploy bei main).
- Für den Büro-PC: `tools/buero/ergaenzung_abnahme.py` (K1 markiert, K2 Cursor am Ende) mit echter Spracherkennung über
  ris-mods `diktat_e2e.py`, ohne INS.

## Nebenfunde (nur belegt, keine Regel geändert)
- **5a** Die orange Zeile „… im Diktat genannt, aber KEIN eigener Befund – bitte prüfen“ kommt aus `cas_vorlagen.hinweise`.
  Sie prüft je CAS-Leistung die **Vorlagenwahl der Abschnitte**, nicht die Überschriften im fertigen Befund. Hat der Abschnitt
  eine andere, nicht allgemeine Vorlage als die spezifische CAS-Leistung, kommt die Zeile, obwohl rechts ein eigener
  Abschnitt mit Überschrift steht. Welche Leistung und Vorlage es am 26.11. waren, steht in der Lauf-Datei von 20261126060
  auf X: (`cas_hinweise`, Vorlagen) → Teil 2.
- **5b** „maximal 6 mm“ → „0,6 mm“: Im Code gibt es keine Regel, die Messwerte ändert. Es gibt aber auch keinen
  Messwert-Wächter (diktierte Zahl ≠ Befundzahl → rote Prüfzeile). Die Lauf-Datei enthält STT-Endtext (`stt_roh`),
  korrigierten Text (Call 0) und Befund. Daran sieht man, ob chirp_3, Call 0 oder der Formulierer den Wert geändert hat →
  Teil 2. Ist es der Formulierer oder Call 0, kommt eine Karte „Messwert-Wächter“ in „tun“, die Regel wird nicht still
  geändert.

## Offen / Lücken (→ Teil 2)
- Log am Büro-PC: Live-Anzeige an/aus um 10:53:26; `abgebrochen (fenster_zu)` nach 10:56 und ob die offene Aufnahme dabei
  verworfen wurde; Lauf-Datei 20261126060 für 5a/5b.
- `tools/buero/markierung_abnahme.py` (M156/M165) prüft noch die alte Bedeutung („Markierung bis INS gehalten“). Ab 3.31.0
  gilt dafür K1.

## Arbeitsdateien
`~/cj/work/kaiscribe-ergaenzung-ohne-ins-n1/` (Hetzner): `tests.sh` (Gates) und `version.sh`.

## Abschluss
Gebaut, aber noch nicht in der Ordi: KaiScribe 3.31.0 kommt heute ab 17:35 nach einem Test am Testpatienten.
Bisher kam dein Dazudiktat erst mit INS, und EOL in der Pause sagte „Erst INS“. Deshalb ging nichts.
INS hätte übrigens nur die markierte Stelle ersetzt. Links sah es nur so aus, als würde alles neu gemacht.
So diktierst du ab 3.31.0 dazu: rechts die Stelle markieren oder den Cursor hinsetzen → Record → sprechen → Pause.
Der Text steht sofort rechts an der Stelle, links bleibt alles, wie es war. „Nur Text“ brauchst du nicht.
Weiter sprechen = Record, das kommt dahinter. Danach einfach EOL, ein INS ist nicht nötig.
Drückst du EOL schon während des Sprechens, fügt KaiScribe zuerst ein. Dann EOL noch einmal.
Schließen oder Abbrechen mit offenem Nachdiktat fragt jetzt nach, statt es zu verwerfen.
