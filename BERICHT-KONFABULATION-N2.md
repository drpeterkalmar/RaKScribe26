# KaiScribe schlägt Coxarthrose ohne Diktat vor (RH 99) – Bericht kaiscribe-konfabulation-n2 (12.11.2026)

**Kurz:** Der Nachtrag ist umgesetzt. **Release 3.18.5** ist veröffentlicht (Latest, Windows-UI-Test grün), die Web-App ist
live (curl: 3.18.5, neuer Prompt-Marker). An die Befund-PCs kommt die EXE mit dem schon wartenden Einspiel-Job
`kaiscribe-nachvollzug-paket-n1`. Der Job hat einen Nachtrag bekommen: 3.18.5 statt 3.18.4, und er soll die neue
Lauf-Datei prüfen.

## a) Quellen
- Nachgestellt mit dem alten Prompt (3.18.3): Becken stehend + HIPPO-Baustein (27 Messwerte, ohne K&L) + Diktat
  „Geringe Gelenkspaltverschmälerung beider Hüftgelenke …“ ergab **4/4** „Coxarthrose + K&L-Grad + Osteophyten“, in der
  Web-Kette auch 4/4. Mit dem Diktat „im Übrigen unauffällig“ kam 0/4: Die HIPPO-Messwerte allein lösen nichts aus.
  Auslöser war die alte K&L-Pflichtregel („Grad aus Adjektiv bzw. Deskriptoren“). 3.18.4 hatte sie schon entschärft.
- Zweites Leck, erst beim Messen mit 3.18.5 gefunden (Wächter aus): „Geringe degenerative Veränderungen beider Hüftgelenke“
  wurde 20/20 zu „Geringe Coxarthrose beidseits (Grad 2)“. Ein Becken-❌/✅-Beispiel behebt das, jetzt 20/20 sauber.
- Feste Grade in den Beispielen: Alle stehen jetzt auf dem Platzhalter „Grad X“. Gibt die KI „Grad X“ wörtlich aus,
  setzt der Wächter den richtigen Grad ein oder streicht ihn.
- Regel jetzt: Ein K&L-Grad steht nur bei **diktierter** Arthrose-Diagnose oder kommt aus IB Lab. Reihenfolge: diktierter
  Grad → IB-Lab-Grad → Grad zum diktierten Adjektiv (beginnend 1, gering 2, mäßig 3, hochgradig 4). Ohne Adjektiv gibt es
  keinen Grad. „Gelenkspaltverschmälerung“, „degenerative Veränderungen“ oder HIPPO-Messwerte ergeben keine Arthrose.
- Wächter nach der KI (EXE ≡ Web): Nennt das Diktat kein Arthrose-Wort (auch nicht als Verhörer), fällt eine positiv
  genannte Arthrose aus dem Ergebnis. Der K&L-Wächter erlaubt jetzt auch den Grad zum Adjektiv.

## b) Regressionsfall (je 20 Läufe, echtes Gemini)
Becken stehend + HIPPO, Diktat ohne Arthrose-Wort (4 Wortlaute + Web): **0× Coxarthrose/Kellgren**, 5 × 20/20. Auch mit
abgeschaltetem Wächter ist es 20/20; das gilt auch für 2 Wortlaute, die nicht im Prompt-Beispiel stehen.
„Mäßige Coxarthrose beidseits“ → **K&L 3 beidseits** 20/20 (EXE und Web). Die n1-Fälle (RH 38, KOALA KL 1, diktierter
Grad, Erhalt) sind alle 20/20. Bestehende Regression ohne FAIL. Zahlen: `docs/benchmarks/konfabulation_rh99_2026-11-12.md`.

## c) Nachvollziehbarkeit ohne EOL
Die EXE schreibt jetzt nach **jedem** Befund-Lauf eine Datei, also auch, wenn das Fenster ohne EOL zugeht:
`X:\RaKScribe\Daten\laeufe\<Nr>_<JJJJMMTT-HHMMSS>.json`. Drin stehen STT-Rohtext, Diktat nach der Fehlhör-Liste,
Ergebnisvorschlag, Modell, Prompt- und Vorlagen-Stand, Vorlage, IB Lab ja/nein samt Modulen, Version, Nr, Benutzer und
Rechner. KaiScribe löscht die Dateien nach 30 Tagen selbst. Mit `LAUF_ORDNER` in config.ini lässt sich der Ordner ändern,
„aus“ schaltet die Dateien ab. Fehlt das Laufwerk, entsteht nichts. Der Inhalt landet nie im Log, dort steht nur der
Dateiname. Am Büro-PC ist geprüft, dass `X:\RaKScribe\Daten` existiert.

## Bewusste Verhaltensänderung gegenüber 3.18.4
„Mäßiggradige Omarthrose“ ergibt wieder „(Arthrose Grad 3 nach Kellgren & Lawrence)“, wie in Georgs Referenzfall vom 05.10.
Der Nachtrag verlangt das ausdrücklich: „KL nur bei DIKTIERTER Arthrose-Diagnose“ und „mäßige Coxarthrose beidseits →
KL 3 bleibt“. Nicht diktierte Osteophyten/Sklerose kommen weiterhin nicht dazu. RH 38 bleibt sauber: Dort war nur
die Gelenkspaltverschmälerung diktiert, also gibt es keinen Grad.

## Offen
- Einspielen an die Befund-PCs + Echttest der Lauf-Datei am Testeintrag: Folgejob `kaiscribe-nachvollzug-paket-n1`
  (wartet, Ordi-Zeit beachten, Nachtrag eingetragen).
- Kein Browser-Check der Web-App (Hetzner). Das Bundle ist nur per curl geprüft.
- Arbeitsdateien: `~/cj/work/kaiscribe-konfabulation-n2/` (Logs, A/B-Skripte, Stand von 3.18.3 für den Vergleich).
