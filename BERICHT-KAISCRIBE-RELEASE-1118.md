# Bericht kaiscribe-release-1118 (Teil 1, Do 19.11.2026 02:05–02:40, Hetzner-Nachtspur): Sammel-Release KaiScribe 3.19.13

Georg-Go 18.11. ~20:00: „Geh live.“ In Teil 1 gab es nichts am Büro-PC (Queue-Regel). Einspielen und Abnahme macht der Folgeauftrag
`kaiscribe-release-1118-einspielen` (Brief: `FOLGEJOB-KAISCRIBE-RELEASE-1118-EINSPIELEN.md`).

## 1. main geprüft
- Alle drei Vorarbeiten sind auf main:
  - kaiscribe-kl-tabelle-zurueck-n1 = **3.19.11** (`e26cc8c`): K&L-Tabelle zurück, KOALA → Kniebefund, Regel-Register.
  - kaiscribe-panda-knochenalter-n1 = **3.19.12** (`2c0b5f3`): PANDA-Knochenalter als Ergebnisbefund.
  - kaiscribe-hippo-ergebnistext-n1 = **3.19.13** (`34bf5ea`): HIPPO-Becken-/Hüfttext.
- Tests: Alle Python- und TS-Schritte aus `.github/workflows/test.yml` liefen am Server, **0 rot**. Ausgenommen waren tsc und eslint, weil am Server
  `node_modules` fehlt. Der GitHub-Lauf „Tests“ für `34bf5ea` (inkl. tsc/eslint) ist **grün**.
  Enthalten sind Regel-Register, `befund_regeln` PY+TS (inkl. RH 38 Anti-Konfabulation), KOALA (Nr. 34/50), HIPPO, PANDA, FROG, LAMA/FROG ohne Norm und die IB-Lab-Bausteine.
- `grep "BEGIN PRIVATE KEY"` hat keinen Schlüssel gefunden. Es gibt nur drei erlaubte Code-Stellen: die Regex in `web_app/src/stt.ts`, einen Kommentar in `deploy.yml` und den Wächter-Test.

## 2. Version, Web, EXE
- **Eine Version für alles: 3.19.13.** Sie enthält 3.19.11 + 3.19.12 + 3.19.13. Eine weitere Nummer ohne Code-Änderung wäre leer, deshalb gab es keinen neuen Bump.
- Web: https://drpeterkalmar.github.io/RaKScribe26/ zeigt **3.19.13** (Deploy-Run 44433844620 grün).
- EXE: `build-exe.yml` mit 3.19.13 gestartet. Build 44434784025 und Windows-UI-Test 44435064425 sind **grün**.
  Release **3.19.13 = latest**, `rakscribe26.exe` 56 853 396 Byte, sha256 `704549ed1c3aeb692ca7817240a74e7783c5da9aa10bb6a732230e14a1e85469`.

## 3./4. Einspielen + Live-Prüfung → Teil 2
- Auf X: liegt 3.19.12 (aus dem PANDA-Job). Teil 2 tauscht auf 3.19.13 und spielt Abholer 1.3.11 (VM) sowie Brücke/Formatierer 1.7.0 ein (ris-mods `1973a50`).
  Danach belegt Teil 2 die Version für CASWS08/CASWS10/RAKCLIENT04 und macht den Testlauf 451898 mit KOALA-Fixture Nr. 34 (Wortlaut exakt).
- Offline ist Nr. 34 grün (`tests/offline/test_ibl_koala_text.py`, ganze EXE-Kette).
- Lücke für Teil 2: Wie die Teststrecke den KOALA-Baustein für 451898 einspeist, war am Server nicht zu belegen.

## 5. Regel-Audit (aus BERICHT-KL-TABELLE-ZURUECK-N1, Skill-Regeln 1–13/3a–3af)
- **vorhanden:** 1, 3, 3a–3n (ohne 3j), 3r, 3s, 3t, 3u, 3v, 3w (eingeschränkt durch RH 38), 3x, 3aa, 3ab, 3ac, 3ad, 3af, 4,
  5 (mit Peters Einzelpunkt-Ausnahme), 5a, 5b, 6, 7, 8, 10, 11, 12, 13
- **ergänzt:** 2, 3j, 3o, 3p, 3y, 3z, 3ae, 9
- **unklar:** 3q. „‚Wie bei‘ → ‚vereinbar mit‘“ widerspricht „IMMER ‚Bild wie bei [Diagnose]‘“. Georg entscheidet (Kanban #421).

Arbeitsdateien: `~/cj/work/kaiscribe-release-1118/` (gh.py).
