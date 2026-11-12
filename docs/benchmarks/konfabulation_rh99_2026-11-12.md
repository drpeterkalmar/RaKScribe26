# Konfabulation RH 99 (Nachtrag) – Messung 12.11.2026 (Prompt 2026-11-12-v3185-kl-nur-diagnose)

Anlass: Beckenübersicht stehend (Vorlage `beckenübersicht_stehend`), KaiScribe 3.18.0 an CASWS08. Dazu kam ein HIPPO-Baustein
mit 26 Messwerten (LCE, Tönnis, Sharp, Offsets, Kopfdurchmesser, CCD, Beckenschiefstand, Beinlängendifferenz), aber
**ohne** K&L-Grad und **ohne** „Arthrose“. KaiScribe schlug „Coxarthrose (Kellgren & Lawrence Grad 3) beidseits“ vor.
Peter hat das Fenster ohne EOL geschlossen. Deshalb ist der Diktattext unbekannt; die Fälle unten sind nachgestellt.

## Ursache (mit dem Prompt von 3.18.0–3.18.3 nachgestellt, je 4 Läufe)

| Diktat (synthetisch) + HIPPO-Baustein (27 Werte, ris-mods Fixture) | 3.18.3 |
|---|---|
| „… Hüftgelenke altersentsprechend, kein Beckenschiefstand, im Übrigen unauffällig“ | 4/4 sauber |
| „Geringe Gelenkspaltverschmälerung beider Hüftgelenke kranial betont …“ | 0/4: jedes Mal Coxarthrose + K&L-Grad + Osteophyten, die Gelenkspaltverschmälerung fehlt im Ergebnis |
| dasselbe in der Web-Kette | 0/4 |
| „Mäßige Coxarthrose beidseits“ | Osteophyten und Sklerose erfunden (alte K&L-Deskriptor-Tabelle) |

Die HIPPO-Messwerte allein lösen nichts aus. Auslöser ist die alte K&L-Pflichtregel: Sie leitete den Grad aus dem Adjektiv
bzw. den Deskriptoren ab und machte so aus einem diktierten Deskriptor eine Arthrose-Diagnose. 3.18.4 (n1) behebt das schon.
Mit 3.18.4 entsteht dafür bei der diktierten „mäßigen Coxarthrose“ kein Grad mehr (0/4). Der Nachtrag verlangt dort aber K&L 3.

Ein weiteres Leck kam beim Messen von 3.18.5 heraus (ohne Wächter, 20 Läufe): Aus „Geringe degenerative Veränderungen beider
Hüftgelenke“ wurde 20/20 „Geringe Coxarthrose beidseits (Grad 2)“. Das ist mit dem Becken-❌/✅-Beispiel behoben.

## Fix 3.18.5
- Prompt: Alle Beispiele nutzen den Platzhalter „Grad X“, kein festes „Grad 3“ mehr. Ein K&L-Grad steht nur bei
  **diktierter** Arthrose-Diagnose (Reihenfolge: diktierter Grad → IB-Lab-Grad → Grad zum diktierten Adjektiv: beginnend 1,
  gering 2, mäßig 3, hochgradig 4). Ohne Adjektiv gibt es keinen Grad. Bei „Gelenkspaltverschmälerung“, „degenerative
  Veränderungen“ oder nur Messwerten gibt es weder Arthrose noch Grad. HIPPO-Messwerte sind ausdrücklich kein Hinweis auf
  Arthrose (Prompt + IB-Lab-Block). Dazu ein ❌/✅-Beispiel Becken mit IB Lab.
- Web-Validator Regel 5/11 entsprechend. Die Fassung ist per A/B-Test gewählt: Ein längerer Text ließ den Validator
  Georgs Vorlagensatz „Unauffällige Darstellung der übrigen …“ umschreiben (0/8).
- Wächter nach der KI (py ≡ ts): `kl_adjektiv_grade` (Grad zum Adjektiv als erlaubter Wert in `kl_bereinigen`, Platzhalter „X“
  nie gedeckt) und `arthrose_bereinigen` (ohne Arthrose-Wort im Diktat, auch als Verhörer, fallen positive Arthrose-Punkte
  im Ergebnis weg; Verneinung, IB-Lab-Zeilen und K&L-Klammer bleiben). Fixtures `kl.adjektiv`, `arthrose`.
- Lauf-Protokoll (Punkt c): je Befund-Lauf `X:\RaKScribe\Daten\laeufe\<Nr>_<JJJJMMTT-HHMMSS>.json`, auch ohne EOL.

## Messung 3.18.5 (echtes Gemini, `tools/verify_konfabulation.py`, je 20 Läufe)

| Fall | mit Wächter | nur Prompt (Wächter aus) |
|---|---|---|
| rh99_normal (Becken + HIPPO, Diktat ohne Befund) | 20/20 | 20/20 |
| rh99_spalt („Geringe Gelenkspaltverschmälerung beider Hüftgelenke …“) | 20/20 | 20/20 |
| rh99_spalt2 (andere Wortwahl, nicht im Prompt-Beispiel) | 20/20 | 20/20 |
| rh99_degen („Geringe degenerative Veränderungen …“) | 20/20 | 20/20 (vorher 0/20) |
| rh99_degen2 (andere Wortwahl, nicht im Prompt-Beispiel) | – | 20/20 |
| rh99_web (Web-Kette) | 20/20 | – |
| rh99_koxa („Mäßige Coxarthrose beidseits“ → K&L 3 beidseits) | 20/20 | 20/20 |
| rh99_koxa_web | 20/20 | – |
| erhalt_schulter („mäßiggradige Omarthrose“ → K&L 3) | 20/20 | 20/20 |
| erhalt_ohne_adj („Coxarthrose“ → kein Grad) | 20/20 | 20/20 |
| n1-Fälle rh38_cas/exe/web, ibl_kl1, diktat_kl, diktat_kl_ohne, erhalt_knie (jetzt K&L 3), erhalt_web | je 20/20 | – |

„0× Coxarthrose/Kellgren“ heißt hier: kein „arthros“ und kein „Kellgren“ außerhalb der IB-Lab-Zeilen.

Bestehende Regression: `test_all_regions.py` 0 FAIL (die WARN sind nur „Call #2 hat korrigiert“), `--cas` 4/4, `--ibl` 4/4
(neu: HIPPO RH 99). verify_georg 8/8 (wieder Grad 3 Schulter / Grad 2 Ellbogen wie Georgs Soll vom 05.10.), verify_knie
(Grad 3 + 2), verify_kurzsaetze, verify_peter_ergebnis, verify_k2k3, verify_widerspruch 8/8, verify_sprunggelenk und
verify_flachprofil grün. Alle Offline-Gates grün.

Ein Fehler kam bei der Messung heraus und ist behoben: Der erste Arthrose-Wächter hielt die erlaubte IB-Lab-Klammer
„(Arthrose Grad 1 nach Kellgren & Lawrence)“ hinter einer diktierten Gelenkspaltverschmälerung für eine Diagnose. Er hat
dann das Ergebnis geleert (ibl_kl1 0/20). Jetzt 20/20, mit eigener Fixture.
