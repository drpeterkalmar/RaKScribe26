# rho-titel-formatierer-n1 – ris-mods: Rho-Screening-Baustein als eigener Schlussbefund mit Überschrift (Georg Punkt 47)

Von `kaiscribe-rho-titel-nummer-n1` (23.11.2026, Bericht `RaKScribe26/BERICHT-RHO-TITEL-NUMMER-N1.md`). Georg 22.11. (Foto RH 49):
„Die Überschrift bei opp gross machen und mit Punkt 1. Starten“. Der KaiScribe-Weg (diktiertes „Rho“) ist live richtig
(23.11. 1123-059/073: Rho-Titel fett+unterstrichen 11 pt wie die Untersuchungen, Rho-Ergebnis ohne Nummer, Haupt-Ergebnis
1., 2.). **Falsch ist nur noch der Formatierer-Weg** (IB-Lab-Rho ≥ 7 ohne DEXA in 2 J., Rho nicht diktiert):

- `bruecke/ibl_einfuegen.py entscheiden()` (Ende, `i, a_block, e_block = s_i, s_a, s_e`) hängt Block A (`SCREENING_TITEL` +
  `SCREENING_BEFUND`) ans Ende der Beschreibung der LWS-Untersuchung und Block B als **unnummerierte** letzte Zeile unter
  deren „Ergebnis:“ → mitten in der Untersuchung, kein eigener Befund (verletzt Georgs Regel 19 vom 20.11.: Rho immer eigener
  Einzelbefund ganz am Schluss mit eigener Überschrift und eigenem Ergebnis).
- `formatierer/befund_format.py ibl_in_word()` setzt alles schlicht (Arial 11, **nicht fett/unterstrichen**) → die
  Überschrift ist keine Überschrift (= Georgs „gross machen“).
- Zwei Titel-Wortlaute: Formatierer „Opportunistisches Knochendichtescreening auf niedrige Knochenmineraldichte“,
  KaiScribe `RHO_TITEL` „Opportunistisches Knochendichtescreening (KI)“. Brief: nur EIN Wortlaut.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Auftrag (ris-mods)
1. `SCREENING_TITEL = "Opportunistisches Knochendichtescreening (KI)"` (= KaiScribe `RHO_TITEL`). Alter Titel weiter als
   „schon im Befund“/Merkdatei erkennen (`screening_alle_zeilen` + alter Titel; `_SCREENING_DA` trifft ohnehin
   „knochendichtescreening“). Befundtext `SCREENING_BEFUND` (Dr. Rieglers Vorlage 16.11., „Skala 1-10“) bleibt.
2. Screening als **eigener Schlussbefund** nach der letzten Untersuchung (vor Gruß/Unterschrift/DEXA-Teil): 2 Leerzeilen,
   Überschrift (fett + unterstrichen wie `befund_format` „titel“), 1 Leerzeile, Befundtext, 1 Leerzeile, „Ergebnis:“ (fett,
   nur wenn der Brief „Ergebnis:“ kennt), Ergebnissatz **ohne Nummer** (Einzelpunkt). Vorschlag: neuer Plan-Schlüssel
   `plan["schluss"]` (Zeilen) statt `plan["befund"][s_i]`/`plan["ergebnis"][s_i]`; in `ibl_planen` Anker = letzter Absatz der
   letzten Untersuchung (`ergebnis_anker`, sonst `anker()`), Eintrag VOR den übrigen `einfuegen` (gleicher Anker → kommt unter
   die IB-Lab-Ergebnispunkte); `ibl_in_word` art „schluss“ formatiert Titel/„Ergebnis:“; `ibl_auf_liste` dasselbe mit
   fett/unterstrichen (Nachprüfung). Rho-Prüfzeile (`RHO_ZEILE`) bleibt in der LWS-Beschreibung, Osteopen-Ersatz unverändert.
3. Zweites Strg+Alt+B: neuer Abschnitt „… (KI)“ → nichts doppelt (Screening schon da, kein IB-Lab-Baustein ordnet sich ihm zu).
   QR-Block 2.5.29 („letzter Untersuchungsteil ab seiner Überschrift auf die nächste Seite“) mit dem neuen Schlussbefund prüfen.
4. Tests: `bruecke/tests/test_ibl_einfuegen.py` (Z. ~524), `bruecke/tests/test_rho_osteopen.py`, `formatierer/tests/test_ibl_250.py`
   O1–O11 + neue Fälle (eigener Block, Titel fett+unterstrichen, Ergebnis ohne Nummer, Haupt-Ergebnis 1., 2. unberührt,
   zweimal gleich, ohne „Ergebnis:“). `formatierer/tests/osteopen_kopie_echt.py`/`rho_kopie_echt.py` auf den neuen Titel.
5. Version erst beim Zusammenführen (RaK-Befund 2.5.30, `--vorher`), Sauber-Prüfung, **Windows-Prüfung Büro-PC Pflicht** vor
   dem Einspielen (`windows_pruefung.py gruen <commit>`, nur 20:10–06:30/Wochenende). Einspielen VM-Formatierer + Zeiger
   Schreib-PCs wie 2.5.28/2.5.29; Abnahme in echtem Word an 451898 (`osteopen_kopie_echt.py`, Testnummer ohne Lauf-Datei):
   Brief-Struktur mit `RaKScribe26/tools/vm/rho_titel_kontrolle.py <Tag> --nr <NNN>` belegen (Kürzel `Kkifu11 R E r`).
   Rot → nicht einspielen bzw. Rollback auf 2.5.29. 451898 nie vidieren.

VERBOTEN: C-MOVE/C-GET/C-STORE, Header, dcm4chee, CAS-DB schreiben. Keine Patiententexte in Commits/Berichten.
Bericht ≤ 8 Zeilen für Georg.
