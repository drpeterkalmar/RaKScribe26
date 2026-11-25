# BERICHT kaiscribe-uebung-n1 – KaiScribe-Übungsmodus (Web, auch von zuhause) + Übungsdienst auf der VM

Anlass: Georg 24./25.11.2026 („Man spiegelt einen Tag … nichts wird irgendwo hin geschickt“), Peter 25.11. „Geniale Idee!
… 1a mit Senf, 2 rg und kp“, auch von zuhause über die Web-App. Gebaut am 25.11. ab 17:39, VM-Einrichtung ab 20:15.
Keine Patientendaten in diesem Bericht.

## Bericht für RaK Sonstiges (≤ 10 Zeilen, Georg liest mit)
1. Übungsmodus läuft: **https://dexa.taild969f0.ts.net:8555/?uebung** (nur im Tailnet), roter Balken „ÜBUNG – nichts wird gesendet“.
2. Übungstag **23.11.2026**, anonym: 174 Fälle (kp 127, rg 47) mit Leistung, Alter, Geschlecht, Senf (121), IB Lab (51), Vorbefund (77).
3. Ablauf: anmelden (kp/rg), Fall links wählen, diktieren wie immer (F10/SpeechMike/„Befund aus Text“), **EOL/F12 = Abgabe**, dann „Lösung zeigen“ (damaliger Befund, Unterschiede markiert) und „Word“.
4. Ablage: `X:\KaiScribe-Übung\<Tag>\<kürzel>\<RH>_<kürzel>.docx` (CAS-Layout, QR-Platzhalter) + `.html` (Vergleich). Korrekturen im Word liest Hermes später als Sammelliste-Vorschläge.
5. Probelauf echt (VM, Claude maskiert): kp 3 Fälle – 1 Live-Diktat 21 s, 2 per Text 6–8 s; rg 1 Fall 6 s; jeweils Abgabe, Lösung, Word, Ablage auf X: belegt.
6. Sperrtest grün: kein CAS, keine Brücke, kein Roboter, keine Plaza/ELGA, keine Zwischenablage – 0 Ausgänge (Web 39/39, Dienst 100+ Prüfungen).
7. Kennwörter: Vaultwarden „KaiScribe-Übung kp“ bzw. „… rg“; eigener Spracherkennungs-Deckel 60 min/Tag je Kürzel (Ordi-Tage vor 17:00 zusammen 20 min).
8. Georg: Tailscale-App installieren, Peters Freigabe „dexa“ mit georg.riegler@gmx.net annehmen, Link öffnen, einmal den Praxis-Schlüssel (Drive) laden. Sein Kennwort kommt nach dem Beitritt (Karte #571).
9. Nebenbei behoben: Die Web-App sperrte die Aufnahme, weil im Gemini-Projekt die Ausgabengrenze erreicht ist (KaiScribe nutzt seit 3.24.0 nur Claude) – betraf auch die normale Web-App.

## Technik
- `tools/uebung/spiegel.py` (VM, rakauto): Tagesliste + je Fall die Brücken-Abfrage `casdb.Direkt.fragen` (besuch, leistungen,
  vorbefund, mammo, brief) + Patient (Alter/Geschlecht/Name nur zum Maskieren), Senf-Ablage, IB-Lab-Abholer
  (`X:\IBL-Vorbefunde\<nr><ziffer>_<modul>.txt`). Nur `SET TRANSACTION READ ONLY` + SELECT + ROLLBACK (Prüfung `sql_sicher`).
  Ergebnis `C:\RaK\kaiscribe_uebung\daten\<tag>\anonym.json` + `haus.json`. Unabhängige Prüfung am 23.11.: 0 Namen,
  0 Diktatnummern, 0 Ziffernfolgen ≥ 9 in „anonym“, 94 maskierte Stellen, nichts ausgeblendet.
- `tools/uebung/uebung_dienst.py` (VM, Aufgabe `\RaK\RaK KaiScribe Uebung`, rakauto, bei Anmeldung + alle 5 min, eine
  Instanz): 127.0.0.1:18555, im Tailnet per `tailscale serve --https=8555` (Port laut Karte #571; Peter hat die Policy
  `autogroup:shared → dexa tcp:8555` gespeichert). Liefert die Web-App (gleiche Herkunft) + `/api/`. Lösung erst nach der
  Abgabe; Zähler nur Zahlen (`zaehler.json`); Abgaben `abgaben.json` (nur VM).
- Web (`web_app/src/uebung.ts`, `App.tsx`, `main.tsx`): `?uebung` (App vom Dienst) bzw. `?uebung=https://…` (App von
  Pages, CORS nur für drpeterkalmar.github.io). Sperre vor dem ersten Render. Befund-Kette unverändert.
- Gemini-Schlüsselprüfung (`geminiNoetig`, `llmAnbieter.ts`): sperrt die Aufnahme nur noch, wenn Gemini wirklich gebraucht
  wird (Claude für Befund + Korrektur mit Schlüssel → nein). Grund: „Spend cap breached“ im Vertex-Projekt 895690562186.
- Varianten: über Tailscale immer „anonym“ (Code). „haus“ nur bei LAN-Zugang mit `--lan` (Standard aus; ohne HTTPS im LAN
  kein Mikrofon → kommt mit dem EXE-Schalter, Teil 2). Originaldiktat (.wav) nicht gebaut (Peter: 1a ohne Originaldiktat).
- Senf fehlt bei 53 Fällen des 23.11. (Senf lief an dem Tag nicht für alle Fälle); nachträglich erzeugt wurde nichts, weil
  der Tag genug Fälle mit Senf hat.

## Tests
- `tests/offline/test_uebung.py` (Kern, HTTP-Dienst, Sperre: 0 Verbindungen/Unterprozesse aus dem Dienst, statische
  Import-Sperre, Spiegel-SQL nur lesend), `web_app/uebung_test.mjs` (Sperre am Attrappen-Fenster: 17 Ausgänge abgefangen,
  0 echte Aufrufe; erlaubte Ziele gehen durch; Quelltext-Prüfung App/main), beide in `.github/workflows/test.yml`.
- `tools/uebung/e2e_uebung_web.py --probe` (lokal, Google/Claude abgefangen) 27/27; echt gegen die VM kp 25/25, rg grün.
  Hinweis Test-Mikrofon: Chromiums `--use-file-for-fake-audio-capture` liefert headless nur den Piepton → der Test ersetzt
  `getUserMedia` durch einen Strom aus der WAV (`say -v Anna`, 9 s).

## Rückweg
`python3 tools/uebung/vm_uebung.py aus` (Aufgabe aus, `tailscale serve --https=8555 off`). Live-Betrieb (EXE, Brücke,
Roboter, X:\KaiScribe\Programm) ist nicht berührt. Probelauf-Dateien liegen in `X:\KaiScribe-Übung\_Probelauf_20261125_Job\`.

## Offen
- Georg: Beitritt + Kennwort (Karte #571, Hermes). EXE-Schalter für die Ordi (Teil 2, eigener Job).
- Weitere Übungstage: `python3 tools/uebung/vm_uebung.py spiegeln <JJJJMMTT>` (Senf-Ablage hält 14 Tage).
- Gemini-Ausgabengrenze im Projekt 895690562186: nur relevant, falls je wieder Gemini gebraucht wird.
