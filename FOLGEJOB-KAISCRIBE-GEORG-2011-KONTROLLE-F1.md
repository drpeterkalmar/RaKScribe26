# kaiscribe-georg-2011-kontrolle-f1 – Knie beidseits, GWS a.p., FROG ohne Diagnose im echten Betrieb (Di 24.11.2026 ab 13:00)

Von `kaiscribe-georg-2011-kontrolle` (Mo 23.11.). Deutsch, betrieblich. **Nur lesen** – keine Klicks an Befund-PCs, kein CAS,
keine CAS-DB, kein C-MOVE/C-GET/C-STORE, keine DICOM-Header, keine Patientendaten in Bericht/Log (nur Zähler, Kategorien,
Uhrzeiten, Versionen). MELDUNGSRUHE: Peter nur über `kanban.py peter …` bei echtem Fehler.

## Stand
Lies `docs/einspielen/kontrolle_georg_2011_20261123.md`. Am 23.11. alles ok (FROG mit Diagnose 3/3, Mehrfach 17/17, LAMA, Rho),
aber **kein Fall** für: Knie beidseits, GWS a.p., FROG ohne Diagnose.

## Ablauf (am Mac, Konto rakauto auf der VM)
1. `python3 tools/vm/x_lauf_mac.py tools/vm/georg_kontrolle_pruefen.py --tag 20261124 --ab 07:00`.
   Zeilen `kat=KNIE_BDS` (stellung_zuerst=ja, beginnt_im_uebrigen=nein, ergebnis_rechts_vor_links=ja,
   ki_punkt=nein) und `kat=GWS_AP` (beschriftung=ja; normale_stellung=ja ohne Skoliose bzw. skoliose_im_text=ja nur mit
   skoliose_diktiert=ja oder squirrel=ja; seitausbiegung=nein).
2. FROG: `python3 tools/vm/x_lauf_mac.py tools/vm/ibl_laeufe_pruefen.py --von 20261124 --module FROG --ordner X:\KaiScribe\Daten`.
   FROG ohne Diagnose = `ablage=FROG:normal` bzw. Lauf mit Werten ohne Diagnose → im Log `IBL_ROT` zur selben Minute erwartet.
3. Achtung Knie: Kanban #514 (KOALA-Knie-Automatik raus) kann bis dahin eingespielt sein – Knie-Text dann nur aus dem Diktat.
4. Ergebnis ≤ 10 Zeilen in `docs/einspielen/kontrolle_georg_2011_20261124.md`, commit + `claude_job.py zusammenfuehren --keine-tests`.
   Wieder kein Fall einer Kategorie: einmal als `-f2` am Mi 25.11. 13:00; danach Kanban-Karte (Spalte tun)
   „Georg-Kategorie … im Betrieb noch unbelegt“ statt weiterer Folgejobs.
