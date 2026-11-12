# Konfabulation RH 38 – Messung 12.11.2026 (Prompt 2026-11-12-v3184-nur-diktiertes)

Anlass: Diktat Knie links nur „Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen unauffällig“.
KaiScribe 3.18.0 schrieb Osteophyten, subchondrale Sklerose und „Mäßiggradige Gonarthrose … (Arthrose Grad 3 nach
Kellgren & Lawrence)“. Richtig wäre KL 1 laut IB Lab KOALA gewesen.

Ursache (zwei Quellen):
1. Gen-Prompt `radiology_prompt.txt`: Der Abschnitt „K&L-Graduierung (PFLICHT)“ verlangte den Grad „aus dem diktierten
   Adjektiv“ (mäßig = Grad 3) und dazu den festen Deskriptor des Grades („… mit multiplen Osteophyten und subchondraler
   Sklerosierung“). Aus einer diktierten Gelenkspaltverschmälerung wurde so eine Gonarthrose Grad 3 samt Osteophyten.
2. Web-Validator (Call 2) Regel 5: „Fehlt die Graduierung, ergänze sie … aus dem diktierten Adjektiv“.
   Die Vorlage `kniegelenk_in_2_ebenen` enthält keine Pathologie. Der Ergebnis-Teil entsteht im selben Aufruf, einen
   eigenen Ergebnis-Aufruf gibt es nicht.

Messung mit echtem Gemini (`tools/verify_konfabulation.py`, synthetische Diktate, keine Patientendaten):

| Fall | alt (3.18.3) | neu |
|---|---|---|
| RH 38, EXE mit CAS-Leistung Knie links, ohne IB Lab | 0/4 grün (Osteophyten, Sklerose, Gonarthrose, Grad 3) | 20/20 |
| RH 38, EXE ohne CAS | 0/4 | 20/20 |
| RH 38, Web-Kette | 4/4 | 20/20 |
| RH 38 + IB-Lab-KOALA KL 1 links | 0/4 (Grad 1 **und** Grad 3) | 20/20 (nur Grad 1) |
| Diktat K&L 2, IB Lab KL 1 | 0/4 (Osteophyten erfunden) | 20/20 (Grad 2, IB-Lab-Grad nicht zusätzlich) |
| Diktat K&L 3, ohne IB Lab | – | 20/20 |
| Erhalt Knie (Gonarthrose, Osteophyten, Sklerose, kein Erguss) EXE | 0/4 (Grad 3 erfunden) | 20/20 |
| Erhalt Knie Web | – | 20/20 |
| Erhalt Schulter („mäßiggradige Omarthrose“) | – | 20/20 (kein Grad, Adjektiv bleibt) |

Bestehende Regression (Endstand): `test_all_regions.py` 20 Fälle 0 FAIL (alt 18 Fälle 0 FAIL), `--cas` 4/4,
`--ibl` 3 Fälle 0 FAIL (LAMA/HIPPO-Warnung wie vorher), verify_georg 8/8, verify_knie, verify_kurzsaetze (54 ✅),
verify_peter_ergebnis, verify_k2k3, verify_widerspruch 8/8, verify_sprunggelenk, verify_flachprofil grün.

Zwei Nebenwirkungen fielen beim Testen auf, beide sind behoben:
- Der Satz „Nicht Diktiertes kommt nur aus der Vorlage“ ließ die KI Vorlagensätze stehen, die laut IB-Lab-Block
  wegfallen sollen (FROG „Fußgewölbe regulär“, 4/4). Behoben mit einer Ausnahme für IB-Lab- und Widerspruchs-Block.
- Wegen der Erhalt-Regel „diktierte Wortwahl“ schrieb der Web-Validator das STT-Unwort „Flachprofile“ zurück (6/6).
  Behoben mit der Ausnahme für Verhörer in Prompt und Validator.

Rohdaten (nicht im Repo, `*.json` ist ignoriert): `docs/benchmarks/konfabulation_20261112_<prompt>.json`.
