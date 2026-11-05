# KaiScribe privat stellen – Bericht Teil 1 (kaiscribe-privat-n1, 05.11.2026)

**Kurz:** Alles für den Umzug ist vorbereitet und am Mac getestet. **Umgestellt ist noch nichts.** Das Repo ist
weiter öffentlich, kein Befund-PC ist betroffen. Privat stelle ich erst, wenn die Web-App einen neuen Ort hat
(netcup-Webspace erst ab 07.11.) und der EXE-Bau am Büro-PC einmal mit UI-Test grün war. Der Bau am Büro-PC selbst
lief heute schon grün. Der Folgeauftrag ist geschrieben, aber **noch nicht eingereiht**:
`~/.hermes/claude-jobs/briefs/kaiscribe-privat-n2.md`. Einreihen, sobald der netcup-Webspace steht (Ressource Ordi,
Leicht-Spur).

## 1. Inventur: wer holt KaiScribe heute anonym von GitHub?

| Stelle | Was | Nach Teil 1 |
|---|---|---|
| ris-mods `bau/RaK-Befund-bauen.cmd` (Büro-PC baut das RaK-Befund-Paket) | `templates.json` (raw) für die Tests, `rakscribe26.exe` + Digest über die Releases-API | **zuerst vom Mac** (`/quelle/kaiscribe/…`), GitHub nur noch Rückfall |
| ris-mods `ordi-hermes/qr246_bau.ps1`, `rob246_bau.ps1`, `t1_248_bau.ps1` (alte Hotfix-Bauten) | `templates.json` (raw) | zuerst vom Mac, GitHub Rückfall |
| ris-mods `.azure-pipelines/bruecke-windows.yml` (steht auf `trigger: none`) und `.github/workflows/bruecke-windows.yml` (abgeschaltet) | Vorlagen + EXE | unverändert, laufen nie. Die Cloud kommt ohnehin nicht ins Praxisnetz. Bleiben als Vorlage stehen. |
| ris-mods `ordi-hermes/auftrag_*_t*.txt` (alte, erledigte Ordi-Aufträge) | Release-EXE/raw-Dateien mit fester Version | Archiv, nicht mehr in Gebrauch. Neue Aufträge nehmen `/quelle/kaiscribe/rakscribe26.exe?tag=…` bzw. `/quelle/kaiscribe/datei?pfad=…&ref=…` |
| ris-mods `dist/Bruecke-Paket*/KURZANLEITUNG.txt` | nennt den Download-Link | nicht im Git, alte Pakete, kein Abruf |
| Web-App-Kopf (Menü „Windows-App herunterladen“) | `releases/latest/download/rakscribe26.exe` | Ziel jetzt beim Bau einstellbar (`VITE_EXE_DOWNLOAD`); netcup-Bau → `./download/rakscribe26.exe` neben der Web-App |
| Web-App selbst (Peter/Georg im Browser) | `drpeterkalmar.github.io/RaKScribe26/` | **hängt an Pages**, siehe 5 |
| EXE, Menü/Hilfe (`source_code/RaKScribe.py:1885`) | Link auf die github.io-Web-App | nur ein Link, kein Abruf. Bei der nächsten EXE-Version nach dem Umzug auf die neue Adresse ändern (Teil 2) |
| Einspiel-Wächter `~/.hermes/scripts/rak_auto_einspielen.py` | `gh api …/releases/latest` | **angemeldet**, geht auch privat |
| Mac-Skripte/Skills (`claude_job.py`, Credit-Burn-Berichte, Skill rakscribe26-pipeline) | Doku/`gh` angemeldet | geht auch privat; Skill `desktop-exe-build.md` beschreibt noch GitHub Actions → Teil 2 |
| `X:\RaKScribe\…`, Update.ps1 im Paket, Brücke, geplante Aufgaben am Büro-PC | bekommen die EXE **nur aus dem Paket** (paket.py legt sie hinein, Update.cmd kopiert nach X:) | kein eigener GitHub-Abruf gefunden (Code in ris-mods `bruecke/`, `bau/`, `mac/` durchsucht). Am Büro-PC selbst habe ich nichts nachgesehen (Ordi-Zeit). Ein Nur-Lese-Blick gehört zu Teil 2. |
| install.md / readme.md | Releases-Tab | umgeschrieben (Praxis-Update statt Download) |

## 2. Neuer Verteilweg der EXE (ohne neuen Updater)

Der Weg zu den Befund-PCs bleibt genau der bisherige: **RaK-Befund-Paket → Update.cmd → `X:\RaKScribe\rakscribe26.exe`**.
Neu ist nur, woher der Büro-PC beim Paketbau die EXE holt. Sie kommt vom **Mac-Quell-Dienst**. Den gibt es schon für
den ris-mods-Quellstand (`https://mac-mini.taild969f0.ts.net:8451/quelle`, nur im Tailnet). Der Mac lädt die EXE
angemeldet per `gh`. Er prüft sie gegen den Digest des Releases und hält sie im Cache
(`~/.hermes/cache/ordi-quelle/kaiscribe/`). **Am Büro-PC liegt kein Token.**

Neue Endpunkte in `~/.hermes/scripts/ordi_quelle.py` (Sicherung `ordi_quelle.py.bak_20261105_kaiscribe`, Kopie in
ris-mods `mac/ordi_quelle.py`):
`/kaiscribe/stand[?tag=]`, `/kaiscribe/rakscribe26.exe[?tag=]`, `/kaiscribe/templates.json[?ref=]`,
`/kaiscribe/datei?pfad=&ref=`, `/kaiscribe/quelle-stand`, `/kaiscribe/quelle.zip`, `POST /kaiscribe/ablage`.

**Wichtig:** Der laufende Dienst auf 9160 (PID 87171, seit 17.10., läuft nicht unter launchd) hat den neuen Code noch
nicht geladen. Ein Claude-Job beendet ihn nicht. Deshalb nehmen die ris-mods-Bauskripte bis dahin automatisch den alten
GitHub-Weg. Heute fällt also nichts aus. Den Neustart macht Hermes (Teil 2, Punkt 1).

## 3. ris-mods-Bauskripte

Commit `32b5ad6` (ris-mods main): `bau/RaK-Befund-bauen.cmd` holt `templates.json` und die EXE (Stand, Tag, SHA256)
vom Mac. `paket.py` bekommt den Digest vom Mac. Fallen die Mac-Endpunkte aus, greift der alte anonyme Weg. Der
fällt nach dem Privatstellen von selbst weg (404) und wird dann in Teil 2 gelöscht. Ebenso in den drei
`ordi-hermes/*_bau.ps1`.

## 4. EXE-Bau + Windows-UI-Test ohne GitHub Actions

- `tools/buero/kaiscribe_bauen.py` (läuft am Büro-PC, `py -3.12`, nur Standardbibliothek): legt die eigene Bau-venv an
  (`%LOCALAPPDATA%\KaiScribe-Bau\venv`, getrennt von der RaK-Bau-venv) und installiert `requirements.txt`. PyInstaller
  läuft mit **genau den Argumenten aus `build-exe.yml`**: Die Zeile wird gelesen, nicht abgeschrieben, also kein zweites
  Rezept. Danach `tests/windows/exe_ui_test.py` gegen die gebaute EXE, dann die Abgabe von EXE und report.md an den Mac
  (POST, Tailnet).
- `tools/buero/auftrag_exe_bauen.txt` = Auftrag an den Ordi-Hermes (Muster windows_pruefung: Zeitfenster
  20:10–06:30/Wochenende, nichts sonst anfassen, Prüfsummen von Quelle und Skript).
- `~/.hermes/scripts/kaiscribe_bau.py` (Kopie `tools/buero/kaiscribe_bau_mac.py`): Mac-Seite. Prüft Zeitfenster und
  „belegt“ (gleiche Regeln und Sperre wie windows_pruefung, nie zwei Peer-Läufe) und schickt den Auftrag per
  `hermes peer run ordi`. Wertet die `KSBAU=`-Zeile aus, legt das **GitHub-Release angemeldet vom Mac** an (Testbau =
  Vorabversion `test-…`, `--release` = Version aus VERSION) und prüft den Digest des Releases. Ergebnis kommt als
  Commit-Status `windows/buero-pc` ins Prüfprotokoll.
- Mac-Gates bleiben am Mac: alle `tests/offline` aus test.yml (neu: `test_buero_bau.py`). Er prüft, dass die
  PyInstaller-Argumente identisch sind, alle EXE-Module als hidden-import drin sind, der Auftrag alle Platzhalter hat
  und unter `tools/buero` kein anonymer GitHub-Abruf steht.
- **Gefundenes Risiko:** Der UI-Test (Fall G) legt die **echte** Autostart-Verknüpfung `RaKScribe.lnk` an und löscht
  sie wieder. Außerdem teilt die Test-EXE den Einzelinstanz-Mutex mit einer laufenden echten KaiScribe. Auf dem
  GitHub-Rechner war das egal, am Büro-PC nicht. Deshalb bricht das Skript vorher mit `KSBAU=belegt` ab, wenn eine
  `rakscribe26.exe` läuft oder die Verknüpfung liegt. Es meldet beides immer in einer INFO-Zeile.

Probe-Bau am 05.11. abends: Der Bau ist grün, der UI-Test am Büro-PC ist noch gesperrt (siehe Abschnitt 8).

## 5. Web-App: neuer Ort

- **GitHub-Konto:** Der Plan ist per Token nicht lesbar. `plan`, `total_private_repos` und `disk_usage` kommen alle als
  `null`, weil dem Token der Scope `user` fehlt. Es spricht alles für das **Gratis-Konto**: Keines der 12 privaten Repos
  hat Pages, und die Skill-Notizen zu den Actions-Minuten gehen vom Free-Kontingent (2.000 Min.) aus. Dann gilt: **privat
  = keine Pages**, die github.io-Adresse ist sofort weg. Deshalb zuerst umziehen, dann privat stellen.
- **Empfehlung (wie im Brief):** statisch bei netcup (Webhosting 1000, Konto 450039), eigene Subdomain, empfohlen
  `kaiscribe.roentgen-am-kai.at`. Das Key-Gate bleibt, weil die App ohne Praxis-Schlüssel gesperrt ist. Dazu
  `robots.txt` Disallow + `X-Robots-Tag noindex`, kein Verzeichnis-Listing.
- Vorbereitet (main `deae397`): `vite.config.ts` liest `KAISCRIBE_BASE` (netcup `/`, Pages weiter `/RaKScribe26/`),
  `App.tsx` liest `VITE_EXE_DOWNLOAD`. Ohne Angabe bleibt alles wie bisher, live geprüft: Pages-Deploy grün, Bundle hat
  weiter den Release-Link. `tools/web_netcup_bauen.sh` macht die Gates und den Build. Den Schlüssel-Schutz nimmt es
  wörtlich aus deploy.yml. Dann legt es die EXE nach `dist/download/` (Digest geprüft, optional mit Passwort per
  `KAISCRIBE_HTPASSWD`), ergänzt robots/.htaccess und lädt per rsync hoch. Zum Schluss prüft es live, ob die Seite das
  richtige `index-*.js` lädt.
- **CORS:** Die Vorabprüfung (OPTIONS mit `Origin: https://kaiscribe.roentgen-am-kai.at`) ist am 05.11. erfolgreich
  gelaufen, und zwar für Gemini EU (`aiplatform.eu.rep.googleapis.com`), STT EU (`eu-speech.googleapis.com`) und
  `oauth2.googleapis.com/token`. Alle drei antworten mit 200 und geben die Herkunft samt den nötigen Kopfzeilen zurück.
  **Nicht geprüft:** ein echter STT-/Gemini-Aufruf vom neuen Ort. Dafür muss die Seite dort liegen und der
  Praxis-Schlüssel geladen sein. Das kommt in Teil 2, mit Browser.
- **Nicht gemacht:** Build und Upload. In der Leicht-Spur sind keine Builds erlaubt, und der netcup-Webspace und der
  Zugang dazu fehlen noch (Domain-Umzug ab Sa 07.11., Webspace ab 07./09.11.).
- **Termin für den Umzug:** frühestens Mo 09.11. abends, sobald der Webspace steht (Teil 2, Punkt 3).

## 6. Umstellung

**Noch nicht gemacht.** Es fehlen der neue Ort der Web-App (5), der Neustart des Quell-Dienstes (2) und ein
Büro-PC-Testbau mit UI-Test (4). Würde ich jetzt umstellen, wären die Web-App für Peter/Georg und künftige EXE-Releases
weg. Der Ablauf steht in Teil 2:

- nachts 22:00–06:30: `gh repo edit drpeterkalmar/RaKScribe26 --visibility private --accept-visibility-change-consequences`
- danach prüfen: anonym 404 auf Repo und Release
  (`curl -sI https://github.com/drpeterkalmar/RaKScribe26/releases/latest/download/rakscribe26.exe`), Mac-Endpunkte
  liefern weiter (`/quelle/kaiscribe/stand`), ein Befund-PC-Update über den Paket-Weg, Web-App am neuen Ort, Brücke läuft
- danach `gh workflow disable` für build-exe.yml, deploy.yml, test-exe-windows.yml, test.yml (nicht löschen),
  Repo-Beschreibung bleibt
- **Rückweg** bei jedem Fehler vor 06:30:
  `gh repo edit drpeterkalmar/RaKScribe26 --visibility public --accept-visibility-change-consequences`. Achtung: Pages
  muss danach eventuell neu eingeschaltet werden (`gh api -X POST repos/drpeterkalmar/RaKScribe26/pages -f build_type=workflow`)
  und deploy.yml einmal laufen. Sterne/Beobachter gehen beim Privatstellen verloren.

**Option mit Kosten (nicht abgeschlossen, nur zur Info):** GitHub Pro (ca. 4 $/Monat) hätte Pages auch für private
Repos. Die Web-App wäre dann aber weiter öffentlich erreichbar, und die Actions-Minuten blieben begrenzt. Der netcup-Weg
ist ohnehin geplant. Ich empfehle Pro deshalb nicht.

## 7. Testbelege (am Mac)

- Mac-Quell-Dienst, Probe-Instanz auf 127.0.0.1:9169:
  - `/kaiscribe/stand` → 3.18.2, SHA256 `3a794fb8…4635` = Release-Digest
  - EXE 56.725.722 B mit derselben Prüfsumme
  - `?tag=3.18.1` → richtiges Release
  - `templates.json` → 143 Vorlagen
  - `datei?pfad=VERSION` → 3.18.2
  - `quelle.zip` (Commit f903bac) enthält VERSION, RaKScribe.py, exe_ui_test.py
  - `../x` → 404, `tag=../a` → 400
  - POST `ablage`: richtig → 200, falsche Prüfsumme/Tag/Dateiname → 400
  - der ris-mods-Stand `/stand` unverändert
- Über das Tailnet (`https://mac-mini…:8451/quelle-ks/…`, Probe-Instanz 9162): `quelle-stand` und POST `ablage` gehen.
- `kaiscribe_bau.py`: Auswertung ok/falscher Commit/belegt/ohne Zeile richtig. Außerhalb des Zeitfensters → „nicht
  gelaufen“. Der Trockenlauf mit der Probe-Instanz baut den Auftrag mit Commit, Zip- und Skript-Prüfsumme.
- RaKScribe26: alle 38 Offline-Gates aus test.yml grün (vor jedem Zusammenführen). GitHub „Tests“ + „Deploy“ für
  `deae397` grün, Live-Seite unverändert („KaiScribe 3.18.2“, Release-Link im Bundle).
- ris-mods: nur Skripttext geändert, kein Mac-Test betroffen. Die Sauber-Prüfung startet die Queue nach dem Job. Die
  Windows-Prüfung läuft vor dem nächsten Einspielen wie immer (`bau/` gehört zu ihren Code-Pfaden).

## 8. Probe-Bau am Büro-PC (05.11. abends)

Probe über eine eigene Mac-Instanz (Port 9162, Tailnet-Pfad `/quelle-ks`). Danach beendet und den Pfad entfernt. Der
laufende Dienst auf 9160 blieb unberührt.

1. **20:11 Bau ohne UI-Test** (`kaiscribe_bau.py --pfad quelle-ks --ohne-ui-test`, Commit 96c011c, Tag
   `test-2611052011`, kein Release):
   - Ergebnis `KSBAU=ok`, Bau 160 s.
   - Der Büro-PC hat Quelle und Zip vom Mac geholt und die Prüfsummen von Zip und Skript geprüft. Dann hat er die venv
     angelegt, `pip install` gemacht und die PyInstaller-EXE gebaut.
   - Die Abgabe an den Mac kam an: 56.247.118 B, SHA256 `12bb077f…3f81` gleich in Meldung und Ablage.
   - Prüfprotokoll und Commit-Status `windows/buero-pc` sind gesetzt.
   - Gefunden: `tasklist` gibt cp850 aus, und mit `PYTHONUTF8=1` brach das Dekodieren ab. Der Ordi-Hermes hat den Lauf
     mit `chcp 65001` wiederholt. Behoben in `5569edf`: Die Ausgabe wird jetzt als Bytes gelesen.
2. **20:19 mit UI-Test** (Commit 5569edf): `KSBAU=belegt`, wie vorgesehen.
   - INFO `rakscribe_laeuft=nein autostart_lnk=ja`: Am Büro-PC liegt die echte `Startup\RaKScribe.lnk` (seit 15.10.).
   - Nichts gebaut, nichts angefasst. Der tasklist-Fix greift.
   - **Der UI-Test am Büro-PC braucht noch eine sichere Lösung.** Empfohlen: Im Selbsttest-Modus bekommt der Test einen
     eigenen Autostart-Ordner. Das braucht eine EXE-Version und kommt in Teil 2, Punkt 2.

Einen Befund-PC hat keiner der Läufe berührt: kein Release, kein Paket, nichts auf X:.

## Offene Punkte

1. Quell-Dienst 9160 neu starten (Hermes, Teil 2/1). Bis dahin GitHub-Rückfall in den Bauskripten.
2. Büro-PC-Bau mit UI-Test abnehmen. Der Bau selbst ist grün. Die echte `RaKScribe.lnk` am Büro-PC sperrt den UI-Test.
   Empfohlen: eigener Autostart-Ordner im Selbsttest-Modus, mit einer EXE-Version (Teil 2/2).
3. netcup-Subdomain + Zugang, Web-App-Umzug, echter STT/Gemini-Test vom neuen Ort (Browser), neuen Link an Peter/Georg (Teil 2/3).
4. Umstellung nachts, Workflows abschalten, GitHub-Rückfall löschen, Skill `desktop-exe-build.md` + `test_produktname.py` nachziehen, EXE-Hilfelink (Teil 2/4).
5. Ein Nur-Lese-Blick am Büro-PC, ob dort noch etwas anderes (geplante Aufgabe, eigenes Skript) GitHub anfragt.
