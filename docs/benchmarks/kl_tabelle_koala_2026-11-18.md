# K&L-Tabelle zurück + IB Lab KOALA → Kniebefund (kaiscribe-kl-tabelle-zurueck-n1, 18.11.2026)

Prompt-Stand `2026-11-18-kl-tabelle-koala`. Live-Läufe mit `tools/verify_konfabulation.py`, Produktionsmodell Claude Sonnet 5.5
(`KAISCRIBE_TEST_ROUTE=alle=claude-sonnet-5-5`, Konto B; Google-Tests sind seit 14.11. gesperrt), Kosten gesamt ≈ 3,00 $.
Rohdaten: `~/cj/work/kaiscribe-kl-tabelle-zurueck-n1/konfabulation_20261118_2026-11-18-kl-tabelle-koala.json` (Hetzner).

## Endstand (nach den letzten Fixes)

| Fall | Ergebnis | Inhalt |
|---|---|---|
| rh38_cas (RH 38, CAS Knie links, nur „Gelenkspaltverschmälerung“) | **20/20** (+ 3/3 + 5/5 + 1/1) | nichts erfunden: kein Grad, keine Gonarthrose, keine Osteophyten |
| rh38_exe / rh38_web | 5/5 / 8/8 | dto. EXE ohne CAS, Web-Kette mit Validator |
| tabelle_schulter / _web („mäßiggradige Omarthrose“) | 9/9 / 9/9 | Befund „Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung.“, Ergebnis „… (Arthrose Grad 3 nach Kellgren & Lawrence)“ |
| koala_nr34 (Georg Nr. 34, KL 3 links, Diktat FP-Arthrose + Erguss) | **5/5** wortgleich mit Georgs Fixture (letzte zwei Runden 10/10) | Befund + Ergebnis exakt |
| koala_nr50 (Georg Nr. 50, KL 2 beidseits) | **5/5** wortgleich (letzte Runde) | „Beidseits medial …“, „Lateral beidseits …“, FP Grad 3 neben KOALA 2 |
| koala_kl3_re (Brief Punkt 4, KL 3 rechts) | 19/19 | „Medial mäßiggradige Gelenksspaltverschmälerung …“, „(Arthrose Grad 3 nach Kellgren & Lawrence)“ |
| erhalt_* / diktat_kl_ohne / rh99_spalt / rh99_degen / rh99_koxa | alle grün | Erhalt, kein Grad ohne Adjektiv, keine Coxarthrose aus HIPPO |
| diktat_kl (Grad 2 diktiert) | 7/8 | 1× schrieb die KI den Tabellensatz Grad 2 abgewandelt („Medial betonte Osteophytenbildung mit geringer Gelenkspaltverschmälerung …“) – kein Erfinden (Grad diktiert), aber nicht der wörtliche Tabellensatz |
| ibl_kl1 (KOALA KL 1 + nur Gelenkspaltverschmälerung) | 3/5 | bekannter Altfall (Kanban #261, schon auf main rot); KL 1 bekommt keinen KOALA-Text, betrifft nur die IB-Lab-K&L-Klammer |

Frühere Runden derselben Fälle (vor den Fixes) mit Fehlern – jeder als Offline-Fall in `tests/offline/test_ibl_koala_text.py`
festgehalten und deterministisch abgefangen: „Normale Stellung … beidseits.“, „Mäßige patellofemorale Arthrose“ im Ergebnis,
Femoropatellar-Satz vor dem Gelenkspalt-Satz, „… im Übrigen allseits / femorotibial allseits normal weit“, Weichteilsatz
als eigener Absatz, „Im Übrigen sind die Gelenkflächen …“, „Beidseits femoropatellar …“.
