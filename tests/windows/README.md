# Windows-UI-Test der EXE

Automatischer Oberflächen-Test der echten `rakscribe26.exe` auf einem frischen Windows-Rechner von GitHub Actions
(kostenlos für dieses öffentliche Repo). Läuft **automatisch nach jedem erfolgreichen EXE-Build**
(Workflow „Windows UI-Test (EXE)“, `.github/workflows/test-exe-windows.yml`) oder manuell:

```bash
gh workflow run test-exe-windows.yml -f tag=3.0.2   # leer = neuester Release
```

## Was geprüft wird

| Fall | Ablauf | Erwartung |
|---|---|---|
| A – gesperrt | EXE ohne Schlüssel starten | Fenster erscheint, Sperre „Praxis-Schlüssel laden“, Aufnahme-Button gesperrt, Status „Gesperrt“ |
| B – F10 | F10 drücken ohne Schlüssel | keine Aufnahme, Status bleibt „Gesperrt“ |
| C – entsperrt | EXE mit **Dummy**-Schlüssel im Benutzerprofil + Demo-Befund | Sperre weg, Aufnahme aktiv, 3 Überschriften formatiert, `##` ausgeblendet, Kopiertext bleibt Markdown |

Die EXE hat dafür einen **Selbsttest-Modus**, der nur aktiv ist, wenn die Umgebungsvariable `RAKSCRIBE_SELFTEST`
gesetzt ist (im Praxisbetrieb wirkungslos): Sie schreibt ihren UI-Zustand als JSON, das Testskript vergleicht und
macht Screenshots.

## Wo das Ergebnis steht

- **Release-Seite**: Ergebnis-Tabelle + Screenshots in den Release-Notizen, dazu `windows-ui-*.png` und
  `windows-ui-test-report.md` als Assets
- **Actions-Lauf**: Job-Zusammenfassung + Artefakt `windows-ui-test-<tag>`

## Grenzen

- Windows **Server** (GitHub-Runner), nicht Windows 11 — für Start/Oberfläche praktisch gleich.
- **Kein Mikrofon, kein Praxis-Schlüssel, keine Google-Aufrufe**: Der Test-Schlüssel wird bei jedem Lauf frisch als
  wertloser Dummy erzeugt (Sicherheitsregel: echte Schlüssel nie auf GitHub). Spracherkennung und Befundung werden
  separat getestet (`verify_*.py`, `diktat_suite.py`, `e2e_v3_web.py`) bzw. am Praxis-PC.
