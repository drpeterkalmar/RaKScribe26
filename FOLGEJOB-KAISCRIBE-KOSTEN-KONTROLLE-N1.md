# Kontrolle: Kosten je Befund im Betrieb nach KaiScribe 3.31.0 (Prompt-Cache)

Hintergrund: 3.31.0 (Cache-Fix 3.29.2) ist seit Fr 27.11.2026 00:35 auf X: live. Vorher kostete ein Aufruf ≈ 6,7 ct (CASWS10, 26.11., 3 Aufrufe 0,2004 $, 3.28.2, ohne Cache).
Zeitpunkt: erster Ordi-Tag NACH Betrieb mit 3.31.0, frühestens Fr 27.11. ab 13:30 (besser Mo 30.11. ab 17:30, damit ein voller Arbeitstag vorliegt).
Regeln: nur lesen (Ordi-Regeln wie immer: nach Ordi-Schluss), Meldungsruhe, keine Patientendaten.

1. `kaiscribe_nutzung_lesen.py` je PC (Teil C aus `FOLGEJOB-KAISCRIBE-KOSTEN-JE-BEFUND-N1-EINSPIELEN.md`: `python3 tools/vm/x_lauf_hetzner.py 'C:\RaK\einrichtung\frogdiag\kaiscribe_nutzung_lesen.py' --tage <Tag>`, Leser vorher per scp hochladen). Erwartet je PC mit 3.31.0: `cache_ohne=0`, `cache_treffer` ≫ `cache_neu`, ≈ 1,5–2 ct je Aufruf.
2. **Rot:** `cache_ohne > 0` auf Befund-Aufrufen → Ursache suchen (Prompt-Quelle in `[INIT]`, lokale radiology_prompt*.txt), Karte in „tun“.
3. Nachtrag „Betrieb nach dem Fix“ in `docs/benchmarks/BERICHT-kosten-n1.md` mit Hochrechnung für 3.000 Befunde/Monat gegen 200 $. Abschluss kurz: Kosten je Befund vorher/nachher, Monatsschätzung.
