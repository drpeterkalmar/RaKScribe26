# Ergebnis kaiscribe-befundfeld-sicher-n1-einspielen (Fr 20.11.2026, Start 19:07)

**Ergebnis: Nichts eingespielt, nichts am Büro-PC oder auf X: verändert. 3.19.15 bleibt live.**

Grund: Der Job startete an einem Werktag um 19:07. Die Sperre am Büro-PC gilt bis 20:10, und die Pflicht-Abnahme am
Testpatienten 451898 (Schritt 1) braucht Klicks am Büro-PC. Laut Brief wird dann nichts halb eingespielt, sondern der
Brief als `-f1` eingereiht. Zusätzlich war die Mac-Werkbank laut Queue seit 18:13 nicht erreichbar.

## Was getan wurde
- Folgejob `kaiscribe-befundfeld-sicher-n1-einspielen-f1` eingereiht: derselbe Brief
  (`FOLGEJOB-KAISCRIBE-BEFUNDFELD-SICHER-N1-EINSPIELEN.md`), not-before Fr 20.11. 20:15, Ressource ordi + automaten-vm.
- Schritt 0 (Tore, Log-Lücke aus Teil 1), Schritt 1 (Abnahme), Schritt 2 (Tausch), Schritt 3 (Kontroll-Auftrag) sind
  Sache des `-f1`-Jobs. Den Kontroll-Auftrag `…-kontrolle` (Mo 23.11. 12:30) legt der `-f1`-Job erst nach belegtem Tausch an.
- Mit SQUIRREL abstimmen: unverändert; `-f1` prüft vor dem Tausch, ob eine neuere KaiScribe-Version (≥ 3.19.17) vorliegt,
  und tauscht nie auf eine ältere zurück.

## Rückweg
Nicht nötig (nichts geändert).

Meldung nach außen: keine. 3.19.16 ist noch nicht live.
