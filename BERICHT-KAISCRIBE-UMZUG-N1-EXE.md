# Bericht kaiscribe-umzug-n1-exe – KaiScribe heißt auch technisch KaiScribe (Teil 1 von 2)

Peter 20.11.2026: „bitte nenne mal alle rakscribe sachen in kaiscribe um und räum ein bisschen auf“. Teil 1 betrifft die
EXE im Repo RaKScribe26. **Auf X: ist noch nichts eingespielt.** Das Einspielen macht Teil 2 (`kaiscribe-umzug-n2-ordi`)
zusammen mit dem Ordner-Umzug auf X:, damit es nur einen Einspielvorgang und einen Rückweg gibt.

## Ergebnis

- **KaiScribe 3.19.19** = RaKScribe26 `9e681ab` (Änderung `6f4b2d4`). Das Release „KaiScribe 3.19.19“ ist **Latest**.
- Das Release enthält **zwei Dateien mit gleichem Inhalt**: `KaiScribe.exe` und `rakscribe26.exe` (Übergang), jeweils
  56 596 584 Byte, **sha256 `b20c947ebe6c0b64005932463e504ba53d0a108f198ac929a954421dde1c7040`**.
  - `curl -IL …/releases/latest/download/KaiScribe.exe` und `…/rakscribe26.exe` liefern beide 302 → 3.19.19 → 200.
    Beide heruntergeladen, die Prüfsumme ist bei beiden gleich.
- **Windows-UI-Test 118/118 grün** (Lauf 44815483961). Der Test startet `KaiScribe.exe`, und der Workflow prüft mit
  `cmp`, dass beide Dateien gleich sind. Der Fenstertitel lautet „KaiScribe 3.19.19 – Röntgen am Kai“. Neu geprüft wird
  in C, E und M: Der Schlüssel liegt wie auf den Befund-PCs noch im alten Ordner `%APPDATA%\RaKScribe`. KaiScribe kopiert
  ihn beim Start nach `%APPDATA%\KaiScribe`, der alte Ordner bleibt, und die App ist entsperrt („Schlüssel aktiv“). Fall G
  legt jetzt `Startup\KaiScribe.lnk` an.
  Die Screenshots liegen in `~/.hermes/work/kaiscribe-umzug-n1/ui/windows-ui-test-3.19.19/` (z. B. `C_entsperrt.png`).
- Mac-Gates: Alle `tests/offline/*.py` sind grün, darunter das neue `test_umzug.py`. Ausnahme sind `test_cas_auftrag`,
  `test_maske_ablauf` und `test_ibl_nur_auffaellig`: Sie sind am Mac auf dem unveränderten main genauso rot
  (Python 3.9 bzw. fehlendes Tk) und im GitHub-Workflow „Tests“ grün (Lauf 44815213143). Die Web-Tests (audio,
  befund_regeln, misheard, normalbypass, pipeline, sync) sowie `tsc -b` und `npm run build` sind grün.
- Die Web-App 3.19.19 ist live (Pages). Der Menüpunkt „Windows-App herunterladen“ zeigt jetzt auf
  `releases/latest/download/KaiScribe.exe`.

## Was sich in der EXE ändert

| Bereich | neu | Übergang / Rückfall |
|---|---|---|
| Programmdatei | `KaiScribe.exe` (Icon `kaiscribe.ico`) | Das Release enthält zusätzlich `rakscribe26.exe` (gleiche Datei) |
| Benutzer-Daten | `%APPDATA%\KaiScribe` | Fehlt der Ordner und gibt es `%APPDATA%\RaKScribe`, wird er beim Start **einmal kopiert**, nie verschoben oder gelöscht. Die Kopie läuft erst in einen Zwischenordner und wird dann umbenannt. Danach liest die EXE nur noch neu. Scheitert die Kopie, liest sie weiter alt. |
| Schlüssel | `kaiscribe-praxis-key.json` | `rakscribe-praxis-key.json` wird weiter gelesen, neben der EXE und im Benutzer-Ordner, aber nachrangig. „Schlüssel entfernen“ löscht beide Namen im Benutzer-Ordner. |
| X:-Pfade (Lauf-Protokoll `Daten\laeufe`, Nutzungszähler `Daten\nutzung`) | `X:\KaiScribe\…` | Solange es `X:\KaiScribe` nicht gibt, gilt `X:\RaKScribe\…`. Der Pfad wird erst beim Schreiben bestimmt, weil X: beim Start oft fehlt. Das gilt auch, wenn in config.ini noch `LAUF_ORDNER = X:\RaKScribe\…` steht. |
| Autostart | `KaiScribe.lnk`, Starter `%APPDATA%\KaiScribe\warte_auf_x.vbs` („KaiScribe-Starter 3“) | Eine vorhandene `RaKScribe.lnk` gilt weiter als „an“. Beim Start wird sie durch `KaiScribe.lnk` ersetzt, die gemerkte EXE bleibt Ziel, solange es sie gibt. Scheitert das, bleibt die alte Verknüpfung. |
| Prozess-Erkennung (Starter) | `KaiScribe.exe`, `KaiScribe (1).exe` | weiter `rakscribe26*`. **Kein** Präfix „KaiScribe%“, sonst gälte eine künftige `KaiScribe-Bruecke.exe` als laufende KaiScribe |
| Texte | Schlüssel-Dialoge/Sperre: „kaiscribe-praxis-key.json (früher rakscribe-praxis-key.json)“, Praxis-Drive statt „Drive-Ordner RaKScribe“; Starter-Protokoll, Log-Zeilen `[START]`/`[PASTE]` sagen KaiScribe | – |
| Bau | `build-exe.yml` (`--name=KaiScribe`, beide Assets, `cmp`), Büro-PC-Bau `tools/buero/kaiscribe_bauen.py` (baut `dist\KaiScribe.exe`; Ablage-Transportname bleibt `rakscribe26.exe`, weil `ordi_quelle.py` nur diesen annimmt), `kaiscribe_bau_mac.py` und Hermes-Kopie `~/.hermes/scripts/kaiscribe_bau.py` (Release mit beiden Assets, Prüfsumme je Asset; Sicherung `~/.hermes/work/kaiscribe-umzug-n1/kaiscribe_bau.py.vor-umzug`), `tools/web_netcup_bauen.sh` (KaiScribe.exe) | – |

Gate `tests/offline/test_produktname.py`: In der Liste ERLAUBT stehen nur noch `RaKScribe26` (Repo/Pages/Mutex),
`"RaKScribe.lnk"` (alte Verknüpfung, wird ersetzt), `"RaKScribe"` (Ordnername für Rückfall bzw. Brücken-Austausch) und
der Testbefund-Kopf der Brücke. Neues Gate: `tests/offline/test_umzug.py` (in test.yml).
Aufgeräumt: `start rakscribe.bat` heißt jetzt `start kaiscribe.bat`. readme.md, install.md und config.ini nennen die neuen
Namen.

## Bewusst gelassen (mit Grund)

- **Repo-Name `RaKScribe26`, Pages-Pfad `/RaKScribe26/`**: Ein Umbenennen bräche Links und Lesezeichen der Web-App
  (Auftrag Punkt 4).
- **localStorage-Schlüssel der Web-App** (`rakscribe_debug` u. a.): Peter sieht sie nicht. Ein Umbenennen würde in jedem
  Browser die gespeicherten Einstellungen verlieren (Auftrag Punkt 4).
- **`%LOCALAPPDATA%\RaKScribe`** (Austausch-Ordner mit der Brücke: `cas_auftrag.json`, `nach_vorne.json`): Die EXE liegt
  gemeinsam auf X:, die Brücken laufen je PC und werden erst mit dem Doppelklick am Montag umgestellt. EXE und alle Brücken
  müssen denselben Ordner benutzen. Ein Wechsel geht erst, wenn jede Brücke neu ist, und auch dann nur mit EXE-seitigem
  Lesen beider Ordner.
- **Mutex `Local\RaKScribe26-Einzelinstanz`**: Alte und neue EXE teilen ihn. So laufen in einer Windows-Sitzung nie
  `rakscribe26.exe` und `KaiScribe.exe` gleichzeitig. Das ist während des Übergangs gewollt.
- **`rakscribe.log`** (neben der EXE): Die Abnahme-Werkzeuge in ris-mods (Teststrecke `buero/kaiscribe.py`,
  `e2e/diktat_e2e.py`, `kp_abend.py`, `ordi-hermes/mammo_probe.py`) lesen genau diesen Namen. Ein Umbenennen geht erst
  zusammen mit ihnen.
- **Testbefund-Kopf „TEST RaKScribe-Brücke …“**: Er steht wortgleich in ris-mods `bruecke/bruecke.py` und im
  Windows-E2E. Ändern lässt er sich nur zusammen mit der Brücke.
- **Umgebungsvariablen `RAKSCRIBE_*`** (Selbsttest, WAV-Modus, Debug): Ordi-Proben und Teststrecke setzen sie.
- **Modul-/Klassennamen** (`RaKScribe.py`, `RaKScribeApp`), **Schlüsseldatei im Drive** (`rakscribe-praxis-key.json`):
  Die Web-App holt sie per Name (`llmAnbieter.ts DRIVE_SCHLUESSEL_DATEI`). Im Drive wird nichts umbenannt oder gelöscht.

## Für Teil 2 (kaiscribe-umzug-n2-ordi) – was die EXE 3.19.19 erwartet

1. **Einspielen**: Release 3.19.19 (oder neuer, sofern es `9e681ab` enthält), Datei `KaiScribe.exe`, sha256 siehe oben.
   Ziel ist `X:\KaiScribe\KaiScribe.exe`. Den Schlüssel neben die EXE legen (`X:\KaiScribe\kaiscribe-praxis-key.json`;
   der alte Name geht auch), ebenso config.ini. Die Abnahme an Testpatient 451898 wie immer.
2. **Sobald `X:\KaiScribe` existiert**, schreibt eine EXE ab 3.19.19 Lauf-Dateien und Nutzungszähler dorthin
   (`X:\KaiScribe\Daten\laeufe|nutzung`), auch wenn in config.ini noch X:\RaKScribe steht. Eine ältere EXE schreibt
   weiter nach X:\RaKScribe. Darum den Ordner erst anlegen, wenn eingespielt wird, oder vorher die Daten übernehmen.
3. **Brücke (ris-mods)**: `bruecke.py:207 windows.prozesse("rakscribe26")` muss auch `KaiScribe.exe` erkennen, und zwar
   mit genauem Namen bzw. „KaiScribe (n).exe“, **nicht** mit dem Präfix „kaiscribe“. Sonst träfe es eine umbenannte
   `KaiScribe-Bruecke.exe`. Ebenso `zentral.py RAKSCRIBE = "rakscribe26.exe"`, `konfig.py rakscribe_exe`
   (Standardpfad der EXE) und `paket.py` (holt `rakscribe26.exe` aus dem Release; besser jetzt `KaiScribe.exe`). Der
   Austausch-Ordner `%LOCALAPPDATA%\RaKScribe` bleibt (siehe oben).
4. **Update.ps1, `kaiscribe_x_tauschen.ps1`, Einspiel-Wächter `~/.hermes/scripts/rak_auto_einspielen.py`, Teststrecke**:
   Diese Teile suchen bzw. tauschen `X:\RaKScribe\rakscribe26.exe` und erkennen den Prozess `rakscribe26`. Sie brauchen
   jetzt beide Namen und den neuen Pfad. Das Release-Asset `rakscribe26.exe` gibt es weiter, alte Wege lösen also auf.
5. **Autostart**: Startet ein Benutzer 3.19.19 mit der alten `RaKScribe.lnk`, ersetzt die EXE sie durch `KaiScribe.lnk`.
   **Rückweg auf ≤ 3.19.18**: Die alte EXE sieht dann keine `RaKScribe.lnk` mehr, der Autostart wirkt aus. Der Rückweg
   muss `RaKScribe.lnk` wieder anlegen, oder der Haken wird neu gesetzt. Sie liest dann wieder `%APPDATA%\RaKScribe`, das
   unverändert ist; Änderungen seit dem Umzug fehlen dort.
6. **Ablage-Server** `~/.hermes/scripts/ordi_quelle.py`: Er nimmt als `X-Datei` nur `rakscribe26.exe|report.md` an. Der
   Büro-PC-Bau schickt deshalb weiter unter diesem Namen, der Mac lädt beide Assets hoch. Den Namen später nachzuziehen,
   ist optional.
7. Weiter offen aus 3.17.0: Die Regex in ris-mods `ordi-hermes/mammo_probe.py:142` lautet noch „RaKScribe 3.x“ und
   sollte `(Kai|RaK)` erlauben.

## Grenzen eingehalten

Kein Ordi-Peer-Lauf, nichts auf X: eingespielt, keine Schlüssel committet (vor dem Commit nach PEM gesucht), keine
Normbereiche oder Regeltexte angefasst.
