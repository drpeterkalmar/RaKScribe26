# kaiscribe-rho-osteopen-kontrolle-f1 – Di 24.11.2026 ab 11:30: Rho-≥7-Fälle (v. a. Formatierer-Weg 2.5.28) lesend prüfen

Von `kaiscribe-rho-osteopen-kontrolle` (Mo 23.11.: 2 KaiScribe-„(KI)“-Fälle 1123-059/073 korrekt ersetzt, **kein**
Formatierer-Screening-Fall im Brief). Bericht: `docs/einspielen/kontrolle_rho_osteopen_20261123.md`.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Auftrag (NUR LESEN; nichts ändern, nichts vidieren; VERBOTEN: C-MOVE/C-GET/C-STORE, Header, dcm4chee, CAS-DB ändern)
1. `tools/vm/rho_osteopen_kontrolle.py` per peer `vm` laufen lassen (Base64 + SHA256 im Auftrag, wie
   `~/cj/work/kaiscribe-rho-osteopen-kontrolle/auftrag1.txt`), Tage 20261123 und 20261124. Gibt je Fall Weg (KI/FMT),
   Teile, Teile mit Osteopen-Satz, Normalsätze daneben, Lauf-Datei (diktiert?) und die `[ibl]`-Zeilen der Formatierer-Logs
   samt Formatierer-Version (FMT <PC> v2.5.xx).
2. Bewertung: KaiScribe „(KI)“ → ersetzt, kein Normalsatz. Formatierer „niedrige Knochenmineraldichte“ → ab 23.11. ersetzt,
   sonst **Fehler** – AUSNAHME: FMT-Zeile zeigt eine Version < 2.5.28 (PC hatte 2.5.28 noch nicht geladen), dann nur vermerken.
   Struktur-Kürzel prüfen (T Titel, O Osteopen, N Normalsatz): Titel-Erkennung ist eine Heuristik (Unterstreichung im RTF).
3. Abweichung Formatierer → ris-mods `bruecke/ibl_einfuegen.py osteopen_planen` + `formatierer/befund_format.py
   ibl_ersetzen_ops` (Tests `bruecke/tests/test_rho_osteopen.py`, `formatierer/tests/test_ibl_250.py` O1–O11) oder Folgejob;
   KaiScribe → RaKScribe26 (Fixtures `rho.osteopen`, Register `rho-osteopen`, EXE = Web). Kein Formatierer-Fall bis Di →
   noch einmal Mi 25.11. einreihen. Bericht ≤ 8 Zeilen in `docs/einspielen/kontrolle_rho_osteopen_20261124.md`.
Keine Patientendaten/Texte in Berichte oder Commits (nur Zähler + Diktatnummern).
