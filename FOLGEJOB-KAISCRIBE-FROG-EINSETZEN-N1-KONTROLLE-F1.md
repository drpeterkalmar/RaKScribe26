# kaiscribe-frog-einsetzen-n1-kontrolle-f1 – erster AUFFÄLLIGER FROG-Fall mit 3.19.15 (nur lesen, Automaten-VM)

Eingereiht von `kaiscribe-frog-einsetzen-n1-kontrolle` (Fr 20.11.2026). Ursprung: `kaiscribe-frog-einsetzen-n1` (Georg 19.11., RH 127: „Teste das immer ob es funktioniert.“).
Ressource: automaten-vm (kein Büro-PC, keine Klicks). Frühestens Mo 23.11. 13:00, nicht nach Mi 25.11.

> **MELDUNGSRUHE:** nichts selbst an Telegram; Peter-Aufgaben → `kanban.py peter …` + „👉 …“.
> **VERBOTEN:** C-MOVE/C-STORE von Patientenbildern, CAS-Datenbank, DICOM-Header. Nur X: lesen (Lauf-Dateien, Protokolle, Ablage).

ZUERST LESEN: `BERICHT-FROG-EINSETZEN-N1.md` und (falls schon da) `docs/einspielen/ergebnis_frog_einsetzen_n1_*.md`.

## Ablauf
1. Stand: Lief `kaiscribe-frog-einsetzen-n1-einspielen` durch (3.19.15 auf X:)? Wenn nein: nur Schritt 2 als Lagebild, Bericht, fertig.
2. `tools/vm/ibl_laeufe_pruefen.py` auf die VM (`C:\RaK\einrichtung\frogdiag\`) und als rakauto laufen lassen – Weg wie in
   `BERICHT-FROG-EINSETZEN-N1.md` (ris-mods `automaten_vm/mac/abholer_vm.py` → `alskonto`, PowerShell-Hülle mit `C:\RaK\laufwerke.cmd`):
   `py -3.12 -X utf8 ibl_laeufe_pruefen.py --von 20261120`. Ausgabe nur Zähler/Kategorien.
3. Bewertung je `IBL_LAUF` mit FROG und `kaiscribe=3.19.15`:
   - `urteil=OK` und `frog_satz=ja` + `schluss=ja` → Fall belegt (pathologischer FROG). Bei FROG ohne Pathologie gibt es keinen Text –
     dann `zeilen=0` und es ist richtig, wenn die Abholer-Datei keinen „befundtext“ hat (mit `diag`-Ansatz aus dem Bericht nachsehen).
   - `urteil=LEER` bei pathologischem FROG → Fehler: mit dem Diagnose-Ansatz aus dem Bericht (Lauf-Bericht neu durch
     `ibl_bausteine.einsetzen`, Ausgabe ohne Nr/Namen) die Ursache finden, Fix-Job `kaiscribe-frog-einsetzen-n2` einreihen bzw. selbst
     fixen (Repo RaKScribe26, eigener Worktree), rote Karte nicht an Peter melden.
   - Läufe an CASWS08 (Brücke zuletzt 2.5.15): hier greift das Nachladen aus der Ablage – OK belegt den Fix für alte Brücken.
4. `X:\RaKScribe\rakscribe.log`: wächst wieder bzw. `rakscribe.log.1` ist neu (Größe/Änderungszeit, kein Inhalt).
5. Noch kein FROG-Fall seit 3.19.15: denselben Brief als `kaiscribe-frog-einsetzen-n1-kontrolle-f1` mit not-before nächster Werktag
   13:00 einreihen (höchstens bis Mi 25.11.), sonst fertig.

## Bericht
`docs/einspielen/kontrolle_frog_einsetzen_n1_<datum>.md` (nur Zähler/Kategorien, keine Nr, keine Namen). Abschlusszeile für die Queue,
z. B. „FROG im echten Betrieb belegt: <n> Fuß-Befunde seit 3.19.15 mit IB-Lab-Text, 0 leer.“

## Nachtrag aus der Kontrolle vom 20.11. (gilt vor dem Ablauf oben)
- Lies zuerst `docs/einspielen/kontrolle_frog_einsetzen_n1_20261120.md`. Am 20.11. gab es 3 echte FROG-Fälle (CASWS10,
  Brücke 2.5.23), **alle ohne Pathologie**. 0 Zeilen war dort richtig. Gesucht ist jetzt der erste Fall mit
  `urteil=OK` **und** `ablage=FROG:patho` (bzw. ein `LEER` mit `ablage=FROG:patho` = Fehler, siehe Schritt 3).
- `ibl_laeufe_pruefen.py` kennt jetzt `ablage=…` und das Urteil `NORMAL` (= FROG ohne Pathologie, richtig). Nimm
  `--von 20261120 --module FROG`. Die Läufe vom 20.11. sind schon bewertet.
- **Weg vom Hetzner:** `python3 tools/vm/x_lauf_hetzner.py 'C:\RaK\einrichtung\frogdiag\ibl_laeufe_pruefen.py' --von 20261120 --module FROG`.
  Vorher `tools/vm/ibl_laeufe_pruefen.py`, `tools/vm/ibl_frog_diag.py` und `tools/vm/x_lauf_huelle.ps1` per
  `scp -q … dexa-rakauto:C:/RaK/einrichtung/frogdiag/` hochladen. Diagnose je FROG-Lauf:
  `… x_lauf_hetzner.py 'C:\RaK\einrichtung\frogdiag\ibl_frog_diag.py' 20261120`. Hängt `bw` (Tresor-Server am Mac), nach
  einigen Minuten erneut versuchen. Fremde hängende `bw`-Prozesse nicht beenden.
  Am Mac geht weiter der Weg aus dem Bericht (`abholer_vm.alskonto`).
- `rakscribe.log` am 20.11.: 300 611 B, 14:52. `.1` = altes 1-MB-Log vom 19.11. Prüfen, ob es weiter wächst bzw. sauber
  rotiert (`.1` neu, `.2` = altes).
- Wieder kein auffälliger FROG-Fall: als `-f2` am nächsten Werktag 13:00 einreihen, höchstens bis Mi 25.11. Danach
  Kanban-Karte (Spalte tun) „FROG auffällig im Betrieb noch unbelegt“ statt weiterer Folgejobs.
- Bericht: `docs/einspielen/kontrolle_frog_einsetzen_n1_<datum>.md`.
