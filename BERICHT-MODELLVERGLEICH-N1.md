# kaiscribe-modellvergleich-n1 – Befund-LLM: Flash 3.5 vs Gemini 4 Hydrogen vs Sonnet 5.5 (13.11.2026, nur gemessen, nichts umgestellt)

| Kandidat (niedrigste Denkstufe) | Gates (synthetisch) | Erfunden (rh99_degen2) · Normalbefund-Treue¹ · Seiten | Latenz EXE Median/P95 · Web | $/Befund EXE mit Cache (heute ohne) | $/Monat 3.000 EXE · Web (ohne Cache) |
|---|---|---|---|---|---|
| **A Flash 3.5 eu** (Budget 0 = heute) | alle grün (Regionen 20/20, CAS, IBL, Widerspruch, Kurzsätze 5×, Georg 8/8) | 0/5 · 90 % (83 %) · ok | 1,7 / 2,4 s · 4,3 s | 0,005 (0,023) | 16 (68) · 53 (105) |
| **B Hydrogen eu** (LOW ≈ 680 Denk-Token; aus/MINIMAL lehnt die API ab) | alle grün², Regionen 20/20 ohne Nachkorrektur | 2/3 · – (78 %) · ok | 6,9 / 29 s · 14 s | 0,013 (0,027) | 39 (83) · 86 (132) |
| **C Sonnet 5.5** (Denken aus) | rot: Kurzsätze Fall 6 4/5 (Satz verloren), „Discopathiezeichen“ fehlt im Ergebnis | 4/5 · 86 % (78 %) · ok | 2,6 / 3,8 s · 6,8 s | 0,011 (0,049) | 32 (148) · 107 (222) |
| Mischung Hydrogen-Gen+Flash · Sonnet-Gen+Flash | EXE = nur Gen → wie B · wie C | – | Web 9,4 s · 5,1 s | – | Web 76 · 69 |

¹ Anteil unberührter Vorlagensätze, alle 18 Konfabulations-Fälle (in Klammern: 6 Kernfälle, gleicher Satz für alle drei). ² Hydrogen ohne expliziten Cache ≈ 3× teurer je Prüflauf → gekürzt: Regionen/CAS/IBL/Widerspruch/Georg/Kurzsätze 1×, Konfabulation 3× auf 6 Kernfällen. ibl_kl1 ist bei allen dreien 0/n → kein Modellthema (#261). Kosten Job: Google 4,78 $ (≤ 5), Anthropic 5,78 $ (≤ 10).
**Empfehlung: bei Flash 3.5 bleiben** – am schnellsten, am billigsten, Gates grün, beste Vorlagentreue. Hydrogen erfindet etwas weniger, ist aber 4× langsamer (Ausreißer bis 30 s) und denkt immer mit; Sonnet verliert vereinzelt Diktiertes, kostet das Doppelte und bräuchte Maskierung.
**Größerer Hebel als ein Modellwechsel:** expliziter Kontext-Cache für den festen Gen-Prompt in der Produktion (Tests 8/8 wortgleich) → EXE ≈ 68 → 16 $/Monat Listenpreis; bräuchte ein Release (gemini.py/gemini.ts, Cache anlegen/erneuern).
Umstellung B: Release mit Modellname + thinkingLevel statt thinkingBudget, kein neuer Datenweg. C: Release + Maskierung nur des Diktattexts (Daten/Namen; CAS- und IB-Lab-Block ohne Personendaten, Vorbefund geht nie an die KI, Mammo-Vergleichsdatum setzt maske.py erst danach) + Datenschutz (USA-Transfer, AVV/SCC).
👉 Peter: Entscheidung a/b (Flash + Prompt-Cache per Release oder alles so lassen), bis 20.11. (Kanban #263).
Werkzeug: `KAISCRIBE_TEST_ROUTE` in tools/testkosten.py (Modell je Aufrufart korr/gen/val), tools/modellvergleich.py; Logs + Auswertung ~/cj/work/kaiscribe-modellvergleich-n1/.
