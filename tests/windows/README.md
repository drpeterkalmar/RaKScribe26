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
| D – Verarbeitung | „Befund wird erstellt“ simuliert, dann F10/F9 über denselben Handler | F10 ignoriert, F9 bricht ab → Bereit |
| E – SpeechMike (v3.8.0) | Tastenberichte über die Selbsttest-Phase `sm_<Taste>#n` (gleicher Weg wie vom Gerät), Mikrofon/Google/chirp_3 als Attrappen (`RAKSCRIBE_SELFTEST_FAKEAUDIO=1`) | hidapi im Bündel; Record → Pause (repariert, kein Befund) → EOL nichts → Weiter → INS (Befund zur Kontrolle, nichts eingefügt) → von Hand ändern → EOL (genau dieser Text in der Windows-Zwischenablage, alles leer); Nur Text, F1, Play |
| G – Bereitschaft (v3.11.0) | Start mit `--minimiert`; Leerlauf 30 s messen (psutil); zweiter Start ohne/mit `--minimiert`; CAS-Auftrag wie die Brücke; Menü-Haken „Mit Windows starten“ (Selbsttest-Phase `autostart_an`); Verknüpfung öffnen wie bei der Anmeldung, die EXE erst nach 30 s hinlegen („X: kommt mit dem CAS-Login“); Starter bei laufender RaKScribe; Haken aus; Starter mit 12 s Frist für eine nie erreichbare EXE | nur Taskleisten-Symbol, nicht vorne; < 2 % eines CPU-Kerns (Zahlen im Bericht); keine zweite Instanz, laufende kommt nach vorne (mit `--minimiert`: still); Annahme < 1 s, Fenster vorne, nach EOL wieder minimiert; Verknüpfung → wscript.exe → `warte_auf_x.vbs` → diese EXE; Starter wartet unsichtbar, startet dann minimiert und endet; endet still; alles entfernt; endet nach der Frist |

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
  separat getestet (`tools/verify_*.py`, `tools/diktat_suite.py`, `tools/e2e_v3_web.py`) bzw. am Praxis-PC.
