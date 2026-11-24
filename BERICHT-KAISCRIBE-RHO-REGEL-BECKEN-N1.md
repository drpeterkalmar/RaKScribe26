# kaiscribe-rho-regel-becken-n1 – Teil 1 (Code + Offline-Tests), 24.11.2026 – Kanban #533

**Version: KaiScribe 3.26.0 = origin/main 2a51626** (Code 00b3d3a). Nichts am Büro-PC, an den Befund-PCs oder der VM
geändert. Einspielen + Abnahme → Folgeauftrag **kaiscribe-rho-regel-becken-n1-einspielen** (ab 17:35, Ressource
ordi + automaten-vm, Brief `FOLGEJOB-KAISCRIBE-RHO-REGEL-BECKEN-N1-EINSPIELEN.md`).

## Ursache
- **Rho:** KaiScribe prüfte beim diktierten „Rho N“ nur den Score (< 7 → nichts). Region und DEXA prüfte es nicht. Ein
  Rho-Diktat an Hand, Thorax oder Becken ergab deshalb einen Rho-Schlussbefund und „Osteopenischer Knochenaspekt“. Die
  Hinweise des IB-Lab-Rho-Bausteins („Regel rho-score-N“, RH 124 Hand Score 9) zeigte KaiScribe immer an.
  Die Regel stand verteilt in `rho_einfuegen` (RHO_AB) und dem Kommentar bei NUR_ANZEIGE.
- **HIPPO ≥ 10 mm:** Der Abholer liefert seit cce497c (1.3.18) `befundtext.ergebnis_becken`. KaiScribe las das Feld
  nicht. Den Beckenschiefstand setzte nur die Rückfall-Regel georg-hippo-10mm (befund_regeln.georg_2311) aus dem
  Befundtext ins Ergebnis, die Beinlängendifferenz nie.

## Gebaut
| Teil | Änderung |
|---|---|
| `befund_regeln.py` ≡ `befundRegeln.ts` | `rho_regel(score, lws, dexa)` = ris-mods `rho_regel.pruefen` (Score ≥ 7 UND LWS UND DEXA frei); `rho_regel_anwenden(report, dexa)`: Rho-Teil fällt weg, wenn die Regel nicht erfüllt ist (Region = eine Untersuchung des Befunds ist LWS; „Rho“ ohne Zahl = ≥ 7 nach Georg 13.10.) |
| `pipeline.py` / `pipeline.ts` | vor dem Osteopen-Schritt die Rho-Regel; DEXA: DEXA-Leistung im CAS-Auftrag → gesperrt, sonst gilt das Diktat als Arzt-Auskunft (Web ohne CAS: frei); Hinweis „Rho: kein Rho-Text – <Grund> (Rho-Regel …)“ in der Anzeige, Logzeile `[RHO] kein Rho-Text – …` |
| `ibl_bausteine.py` | Rho-Baustein-Anzeige nach derselben Regel (`_rho_anzeigen`: Score < 7 oder „Rho analysierte: <nicht LWS>“ → Baustein fällt weg) |
| `ibl_bausteine.py` HIPPO | `ergebnis_becken` gelesen (Kinder nie); `_hippo_becken_punkte`: eigene Ergebnispunkte nach dem Begriff-Punkt, ersetzen das Normal-Ergebnis, nicht doppelt (diktiertes Thema → Hinweis); Gerüst ebenso; HIPPO_PROMPT nennt die Punkte (unterdrückt sie nicht) |
| Register | `rho-eine-regel` (Register „Rho-Ausgänge“ → ris-mods ibl/RHO_REGEL.md), `hippo-ergebnis-becken`; Notizen an `ibl-rho`, `georg-hippo-10mm` |

Tests: Fixtures `rho.regel` (10 Fälle: LWS 8 bleibt, ohne Zahl bleibt, **RH 124 Hand 9 → nichts**, Thorax 8 → nichts,
**Score 6 → nichts**, DEXA gesperrt/unklar → nichts, Becken+LWS bleibt, Becken+Hand → nichts) und `rho.regel_score`
(PY + TS gleich, 457/457 TS). test_ibl_hippo_text: RH 101 (Hüftdysplasie + 13 mm + 20 mm), RH 30 (12 mm statt
Normal-Ergebnis, mit Diktat), diktierter Beckenschiefstand, 9 mm nur Beschreibung, Kind, Gerüst, Prompt.
test_ibl_bausteine k2 (Anzeige Hand 9 / LWS 6 weg, LWS 9 bleibt). Zusammenspiel mit georg_2311 geprüft (kein doppelter
Punkt). Absichtlich geänderte alte Erwartungen: Rho bei Becken/Hüfte ohne LWS → kein Rho-Teil (test_rho_titel_nummer
jetzt mit LWS, test_ursula_2011 Beleg 2 an der LWS), IB-Lab-Rho Score 6/Thorax → keine Anzeige.
Gates (test.yml, /usr/bin/python3 + node/tsc/eslint): alle grün außer test_cas_auftrag und test_maske_ablauf. Die
beiden sind auch auf dem unveränderten Stand 00f02d1 rot (Mac-Python 3.9: ris-mods roboter.py braucht ≥ 3.12; Maske-Ablauf
30 FAIL ohne meine Änderung) → nicht von diesem Job, in GitHub Actions eigener Lauf. Kerntests nach dem Rebase grün.
grep „BEGIN PRIVATE KEY“ in den Änderungen = 0.

## Entscheidungen (selbst getroffen)
- KaiScribe kennt die DEXA der letzten 2 Jahre nicht. Gesperrt wird bei einer DEXA-Leistung im selben CAS-Auftrag, sonst
  gilt das diktierte „Rho“ als Auskunft des Arztes. Georgs Rho-Wortlaut sagt selbst „Da keine Knochendichtemessung aus
  den letzten 2 Jahren vorliegt …“. Die DEXA-Prüfung aus dem CAS macht der Formatierer weiter.
- „Rho“ ohne Zahl bleibt ≥ 7 (Georg 13.10.); mit Zahl < 7 nichts.
- Region: eine der Untersuchungen im Befund ist die LWS (Titel „Lendenwirbel…“, „LWS“, „lumbal“). Rho darf in einem
  Mehrfach-Befund im Becken-Teil diktiert sein, wenn die LWS dabei ist. Gesamte WS zählt nicht als LWS (wie ris-mods).

## Lücken → Teil 2
- Kein Live-Beleg: Ist der Abholer 1.3.18 auf der VM (Einspielen in ibl-rho-sc-ab7-weiche-bue-n1-einspielen) und steht
  `ergebnis_becken` in den Ablage-Dateien von RH 101/RH 30? → Teil 2 A.
- Der im Brief genannte Job kaiscribe-schulter-ergebnis-n1-abnahme stand nicht in der Queue → eigener Einspielauftrag.
- ris-mods `ibl/RHO_REGEL.md`: Querverweis auf den KaiScribe-Ausgang nachtragen → Teil 2 D.

👉 nichts für Peter aus Teil 1.

## Teil 2 – Abnahme + Einspielen (in kaiscribe-schulter-ergebnis-n1-abnahme, 24.11.2026)
- Eingespielt als **3.28.1** (enthält 3.26.0) auf X: 23:43, Release Latest. Ein eigener Auftrag `…-einspielen` existierte nicht; die Arbeit lief in derselben Abnahme-Runde.
- Abnahme 451898 (echte KI, Brief): **R1** Handgelenk Rho 9 → kein Rho-Text (`[RHO] kein Rho-Text – Rho-Region nicht LWS`). **R2** LWS Rho 8 → eigener Teil „Opportunistisches Knochendichtescreening (KI)“ (Score 8, Ergebnis ohne Nummer) + „Osteopenischer Knochenaspekt.“. **R3** Rho 6 → nichts, Normalsatz bleibt.
- **HIPPO:** Mit 3.27.1 war M13 (13 mm re tiefer, BLD 20 mm) rot. Die Brücke 2.5.35 reicht `befundtext.hippo.ergebnis_becken` nicht an KaiScribe durch, deshalb kam nur die Rückfall-Regel (13 mm) ins Ergebnis, die BLD fehlte. Fix **3.28.1**: `ibl_bausteine.text_nachladen` ergänzt das Feld aus der Abholer-Datei (gleiche AccNo/Fassung, nie bei Kind). Mit 3.28.1 grün: „1. Beckenschiefstand von 13 mm, rechts tieferstehend. 2. Beinlängendifferenz von 20 mm.“ + Anmerkung, kein „Regelrechte Darstellung“. Gegenprobe M9 (9 mm) → nur Beschreibung, Normal-Ergebnis bleibt.
- Die Abholer-Version auf der VM wurde nicht gelesen (vom Büro-PC aus nicht lesbar). Der Baustein war für die Abnahme nachgestellt (`tools/ibl_abnahme_bausteine.py --hippo-becken`) und ist wieder entfernt. Brücken-Fix: Karte #565. D (ris-mods RHO_REGEL.md Querverweis) nicht gemacht.
- Kanban #533 → fertig.

## Teil 2 – Nachprüfung 25.11.2026 00:30 (Job kaiscribe-rho-regel-becken-n1-einspielen, Hetzner)
- Einspielen und Abnahme R1–R3/H1 waren schon in der Abend-Runde erledigt (siehe oben, 3.28.1 live, enthält 3.26.0 und 3.27.0). Kein zweiter Tausch, kein zweiter Abnahmelauf nötig (Ordi nachts nicht angefasst).
- Live-Anzeige kp (Nachtrag 3.27.0): Abnahme B steht in BERICHT-KAISCRIBE-LIVE-ANZEIGE-AUS-KP-N1.md (Messwert 2,8 s). Teil C (Kostenrechnung aus nutzung-JSON/rakscribe.log 17.–23.11.) und B4 (rg-Log lesen) sind dort als offen an `kaiscribe-stt-tagesdeckel-n1-einspielen` weitergegeben.
- **Offen: D** (ris-mods `ibl/RHO_REGEL.md` Querverweis „seit 3.26.0 umgesetzt: befund_regeln.rho_regel/rho_regel_anwenden (+ befundRegeln.ts), Register rho-eine-regel; Ausgänge: diktierter Schlussbefund, Osteopen, Anzeige des IB-Lab-Rho-Bausteins“). Dieser Job hat nur eine RaKScribe26-Arbeitskopie, ris-mods ist hier nur Lese-Spiegel. Nur Doku, `--keine-tests`; Folgejob/Karte nötig.
- Offen: Abholer-Version auf der VM (≥ 1.3.18) nicht gelesen.
