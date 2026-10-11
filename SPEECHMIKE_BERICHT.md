# RaKScribe 3.8.0 – Philips SpeechMike direkt steuern (Bericht, 11.10.2026)

## Kurzfassung

- RaKScribe liest die Tasten des Philips SpeechMike jetzt **selbst** – in Philips SpeechControl muss nichts
  eingerichtet werden. Gilt für die **EXE** (einfach anstecken) und die **Web-App** in Chrome/Edge (einmal im Menü
  ☰ „SpeechMike verbinden“ klicken).
- Grundsatz (Peter, Nachtrag 2/3): **Es wird nie ein Befund weitergeschickt, den Peter nicht gesehen hat.** INS zeigt
  den Befund rechts zur Kontrolle, erst EOL schickt ihn weiter.
- **F10/F9 und die Maus funktionieren exakt wie bisher** (F10-Stopp = Befund + automatisch einfügen). Nur die
  SpeechMike-Bedienung hat den Kontrollschritt.
- Live: Web-App 3.8.0 (GitHub Pages) und EXE 3.8.0 (Release „Latest“, nur `rakscribe26.exe`).
  Windows-Test der echten EXE: **48/48 bestanden**, darunter der komplette SpeechMike-Ablauf.
- Noch offen, nur mit Gerät prüfbar: echte Tasten/LEDs am SpeechMike, Zusammenspiel mit SpeechControl/SpeechMagic,
  Einfügen ins SpeechMagic-Fenster. Dafür gibt es das Prüfskript `tools/speechmike_probe.py` (Hermes führt es am rog17
  mit Peter aus).

## Belegung (endgültig, Nachtrag 3 + 4)

| Taste | Was passiert |
|---|---|
| **Record** | Aufnahme starten · nochmal = **Pause** · nochmal = **weiter diktieren** (dieselbe Aufnahme) |
| … in der **Pause** | Das Mikrofon nimmt nichts auf. Das bisher Diktierte wird **sofort repariert** (Spracherkennung chirp_3 + Fehlhör-Liste) und links angezeigt, Hinweis „✓ bis zur Pause repariert“. **Es entsteht kein Befund.** |
| **INS** (INS/OVR) | „ins rechte Fenster“: Aufnahme beenden → Befund erscheint **rechts zur Kontrolle**, bearbeitbar. **Nichts wird eingefügt oder kopiert.** Ohne laufende Aufnahme: Befund aus dem Text links (z. B. nachdem links ein Wort korrigiert wurde). Während „Befund wird erstellt“: wird ignoriert. |
| **EOL** | „alles fertig“: genau den **sichtbaren, ggf. von Hand geänderten** Befund weiterschicken, danach **alles leeren** (bereit für den nächsten Patienten). EXE: kopieren + Strg+V ins SpeechMagic-/RIS-Fenster – das Fenster, das gerade vorne ist, oder, wenn RaKScribe selbst vorne ist, das zuletzt davor aktive. Ist es nicht sicher vorne: nur kopieren + Hinweis. Web: kopieren, Hinweis „Befund kopiert – im RIS mit Strg+V einfügen“. |
| EOL ohne fertigen Befund | (Aufnahme läuft, Pause, „Befund wird erstellt“, rechts leer) → **nichts**, Hinweis „Erst INS, Befund prüfen, dann EOL“. Kein Doppeldruck nötig. |
| **Stop** / Schieber auf STOP | wie Pause |
| **F1** | Neu (wie F9): alles verwerfen |
| **F2** | „Nur Text“ an/aus. Ein schon erstelltes Ergebnis bleibt unverändert; der Wechsel wirkt beim nächsten INS. |
| Play, Spulen, INSTR, F3, F4, Command | nichts (stehen im Protokoll) |
| **F10 / F9** (Tastatur) | **unverändert**: F10 Start/Stopp → Befund + automatisch einfügen; F9 Neu. F10 in der Pause = Stopp wie gewohnt. |

**Nachdiktat:** Nach INS etwas vergessen? Record → weiterdiktieren → INS: neuer Befund aus dem **Gesamtdiktat**
(bisher + neu; links steht immer alles). Steht der Cursor im Befund (hineingeklickt), wird – wie bei F10 seit v3.5.0 –
**nur das neu Diktierte an dieser Stelle eingefügt**, der übrige (auch von Hand geänderte) Befund bleibt.

**„Nur Text“:** gleiche Tasten, gleicher Kontrollschritt. INS zeigt rechts den korrigierten Fließtext ohne Überschriften
(Fehlhör-Liste → Gemini-Korrektur → Satz-Bausteine), EOL schickt genau diesen (ggf. geänderten) Text weiter.

**EOL nach F10:** Hat F10 (EXE) den Befund schon per Strg+V eingefügt, fügt EOL ihn **nicht ein zweites Mal** ein,
sondern leert nur die Felder (Hinweis „Befund war schon eingefügt – Felder geleert“) – auch wenn er danach in RaKScribe
noch geändert wurde. *Frage an Peter:* Soll EOL in diesem Sonderfall (F10 + danach geändert) die geänderte Fassung
zusätzlich einfügen? Dann stünde der Befund zweimal in SpeechMagic; heute gilt „nie doppelt“. In der Web-App kopiert
EOL immer den sichtbaren Text (Kopieren schadet nicht doppelt).

**LEDs (Record-LED):** Aufnahme **rot** · Pause **rot blinkend** · Befund wird erstellt **gelb (rot+grün) schnell
blinkend** · Befund wartet auf EOL **grün** · sonst aus. Fehler beim LED-Setzen sind nie schlimm (Tasten gehen weiter).
Ob das Gerät „gelb“ mischt, zeigt der Hardware-Test.

Hilfe-Zeilen im Menü (EXE und Web gleich): „F10 Aufnahme · F9 Neu“ · „SpeechMike: Record = Aufnahme/Pause · INS =
Befund erstellen · EOL = fertig & weiter“ · „F1 = Neu · F2 = Nur Text (dann zeigt INS den korrigierten Text)“.

## Pause: bisheriges Diktat sofort reparieren (Nachtrag 1) – Messung und Entscheidung

Gemessen mit den echten Praxis-Diktaten (`web_app/public/*.ogg`, 5 verschiedene, eines war doppelt), je 2–3
Schnittstellen **mitten in Sprechpausen**, 11 Schnitte × 2 Läufe, 258 Wörter, Produktionsfunktion chirp_3
(`tools/pause_segment_ab.py`, Rohdaten `docs/benchmarks/pause_segmente_2026-10-11.txt`):

| | Ergebnis |
|---|---|
| Wörter an den Pausengrenzen verloren | **0** |
| chirp_3 Ganz-Aufnahme, zweimal | identisch (keine Zufallsschwankung) |
| Abschnitte vs. Ganz-Aufnahme | 6 Wörter je Lauf anders: **„Befund Nervus ulnaris“ → „Power Stange Busulnaris“** (4-s-Anfangsabschnitt ohne Zusammenhang – das hätte die Vorlagen-Erkennung zerstört), „als Zeichen“ → „Also Zeichen“; dafür „DH4/DH8“ → „Th4/Th8“ (besser, macht aber die Fehlhör-Liste ohnehin) |
| Zeit bis zum Text | Ganz-Aufnahme 1,1–2,2 s, letzter Abschnitt ~1,0 s → Ersparnis **unter 1 s** |

**Entscheidung:** Beim Pausieren wird das bisher Diktierte sofort repariert und angezeigt (Peter sieht gleich den
sauberen Text). Der **Befund** entsteht beim INS (bzw. F10) wie bisher aus der Transkription der **ganzen** Aufnahme –
kurze Abschnitte ohne Zusammenhang verhören sich sonst gelegentlich gerade bei Fachbegriffen, und der Zeitgewinn wäre
kleiner als eine Sekunde. Die Gemini-Korrektur je Abschnitt ist **nicht** eingebaut (braucht den Gesamtzusammenhang,
kostet extra); sie läuft wie bisher einmal über das ganze Diktat. Der F10-Ablauf ohne Pause ist unverändert.

## Technik (kurz)

- **Eigenes schlankes Modul statt npm-Paket** `dictation_support` (Google/Philips, Apache-2.0), aber genau nach dessen
  Protokoll: Hersteller-Schnittstelle Usage-Page 0xFFA0, Tastenbericht 0x80 mit Bitmaske in Byte 7/8, LED-Befehl 0x02.
  Gründe: (1) die EXE braucht ohnehin Python – so dekodieren EXE und Web **mit derselben Testtabelle**
  (`tests/offline/speechmike_faelle.txt`); (2) das SDK fragt beim Verbinden Gerätedaten ab, deren Antworten auch bei
  SpeechControl landen – RaKScribe liest nur und setzt LEDs; (3) das SDK wirft bei fremden Berichten (z. B. Antworten auf
  SpeechControl-Befehle) Fehler, unser Modul ignoriert sie; (4) keine Zusatz-Abhängigkeit im Web-Bundle.
- **EXE:** `source_code/speechmike.py` (Lese-Thread mit hidapi 0.15.0, im EXE-Bündel), Gerät wird **geteilt** geöffnet,
  An-/Abstecken wird erkannt, ohne Gerät/ohne hidapi nur eine Zeile im Protokoll. Jede Taste steht im Protokoll:
  `[SPEECHMIKE] Taste INS gedrückt (raw 80 00 00 00 00 00 00 00 40)`. Menü ☰ → „SpeechMike-Diagnose…“ zeigt Gerät,
  LED-Zustand und die letzten Tasten. Pause in `aufnahme.py` (Mikrofon bleibt offen → „weiter“ ohne Anlaufzeit, kein
  abgeschnittenes erstes Wort), Zustand „Pause“ in der Zustandsmaschine `jobstate.py`. EOL-Fensterziel
  (`fensterziel.py`): RaKScribe merkt sich alle 0,5 s das letzte fremde Vordergrundfenster; vor Strg+V wird es aktiviert
  und geprüft, dass es **wirklich vorne** ist – sonst nur kopieren + Hinweis (lieber nicht einfügen als ins falsche Fenster).
- **Web:** `web_app/src/speechmike.ts` (WebHID), beim Laden automatisch über eine frühere Freigabe verbunden; oben die
  Anzeige „SpeechMike verbunden“. Ohne WebHID (Safari/iPhone/Firefox) gibt es den Menüpunkt nicht, sonst ändert sich nichts.

## Was ohne Gerät getestet ist

| Test | Ergebnis |
|---|---|
| Tastenberichte → Tasten (alle Tasten, Druck/Loslassen, mehrere gleichzeitig, Entprellung, Schiebeschalter), LED-Bytes, Belegung, Zustandstabelle (6 Zustände × 7 Ereignisse) – **Python und TypeScript gegen dieselbe Tabelle** | grün (`test_speechmike.py`, `speechmike_test.mjs` 159/159) |
| EXE-Ablauf mit Attrappen: Record→Pause (repariert, kein Befund) → Weiter → INS (Befund, nichts eingefügt) → ändern → EOL (genau dieser Text, Strg+V ins zuvor aktive Fenster, alles leer); EOL während Aufnahme/Verarbeitung/ohne Befund; Nachdiktat; Cursor-Einfügen nur des Neuen; Nur Text; F1/F2; F10 in der Pause; Fensterziel scheitert → nur kopiert | grün (`test_speechmike_ablauf.py`, 42 Prüfungen) |
| Pause in der Aufnahme: in der Pause kein Audio, jede Probe genau einmal an die Live-Anzeige, chirp_3 bekommt die ganze Aufnahme | grün (`test_capture.py`) |
| Web-App im Browser mit nachgebautem SpeechMike (WebHID-Attrappe, Google gemockt): kompletter Ablauf inkl. LED-Befehle, Nur Text, Cursor-Einfügen, „SpeechMike verbinden“, ohne WebHID | **31/31** (`tools/e2e_speechmike_web.py`) |
| Echte EXE-Oberfläche am Mac (Windows-Module als Attrappen) | 14/14 (`tools/exe_speechmike_smoke.py`) |
| **Windows-UI-Test der gebauten EXE 3.8.0** (GitHub, echtes Windows): hidapi im Bündel, Leser läuft ohne Gerät, Record ohne Schlüssel startet nichts, kompletter SpeechMike-Ablauf über denselben Handler-Weg, EOL → geänderter Befund in der **echten Windows-Zwischenablage** | **48/48** (Lauf 38159713020) |
| Alle bisherigen Offline-Gates, Diktat-Suite (echtes Gemini), Typprüfung, Lint, Web-Build | grün |
| Live-Web-Bundle: „SpeechMike verbinden“, „EOL = fertig & weiter“, „Erst INS …“, Version 3.8.0 | nachgewiesen |

## Was NUR mit dem Gerät / am Praxis-PC geprüft werden kann

1. **Kommen die Tasten an?** (Modell, Modus, Bits) – Prüfskript am rog17 (siehe unten).
2. **INS/OVR:** normale Taste (Druck + Loslassen) oder schaltet das Bit um? Laut SDK normale Taste; das Prüfskript sagt
   es ausdrücklich. Falls Umschalter: eine Zeile in `speechmike.UMSCHALTER` / `UMSCHALTER` (Web), dann zählt jede Flanke.
3. **LEDs:** Farben/Blinken, ob „gelb“ (rot+grün) sichtbar ist, ob SpeechControl/SpeechMagic die LEDs überschreibt.
4. **Parallel zu SpeechControl/SpeechMagic:** RaKScribe öffnet geteilt (sollte gehen). Ob SpeechMagic auf dieselben
   Tasten selbst reagiert, siehe nächster Abschnitt.
5. **EOL in der EXE:** Aktivieren des SpeechMagic-Fensters und Strg+V (Windows-Fokusregeln am Praxis-PC).
6. **Web-App im Hintergrund:** Laut Chrome-Quellcode kommen WebHID-Tastenberichte **auch an, wenn der Tab/das Fenster
   im Hintergrund ist** (keine Fokus-Prüfung beim `inputreport`). Aber: **Kopieren (EOL) braucht das Browserfenster
   vorne** – sonst Hinweis „Nicht kopiert – Browserfenster anklicken, dann EOL erneut“; in fremde Fenster einfügen kann
   der Browser grundsätzlich nicht (dafür ist die EXE da). Ob **Record die Aufnahme startet, wenn der Browser im
   Hintergrund ist**, ist unsicher (Mikrofonzugriff darf laut Standard auf den Fokus warten) – am Praxis-PC prüfen.
   Pause/Weiter/INS gehen auch im Hintergrund (das Mikrofon bleibt in der Pause offen).
7. **Web-Freigabe dauerhaft?** Chrome merkt sich die Freigabe nur, wenn das SpeechMike eine **USB-Seriennummer** meldet
   (das Prüfskript zeigt „Seriennr.: ja/nein“). Ohne Seriennummer nach Abstecken/Browser-Neustart einmal „SpeechMike
   verbinden“ klicken. Dauerhaft ohne Klick ginge nur per Chrome-Richtlinie `WebHidAllowDevicesForUrls` je PC (nur falls
   gewünscht). Die EXE braucht nichts davon.

## Hardware-Prüfung am rog17 (Hermes mit Peter)

```
pip install hidapi==0.15.0
python tools/speechmike_probe.py            # 60 s Tasten, danach LED-Durchlauf
```

Vorher RaKScribe (EXE und Web-Tab) schließen, SpeechControl darf laufen. Das Skript braucht nichts aus RaKScribe,
listet alle Philips-Schnittstellen (VID/PID/Usage-Page/Pfad/Seriennummer), öffnet geteilt, fragt **Ereignis-Modus und
Modell** ab (nur lesen), schreibt jede Taste mit Rohdaten mit (**bitte Record, Record, INS dreimal, EOL, Stop, F1, F2,
Play, Spulen drücken**), wertet INS aus und schaltet die Record-LED durch (rot, rot blinkend, grün, gelb blinkend, aus).
Alles landet zusätzlich in `speechmike_probe_<Datum>.log` neben dem Skript. Abweichungen bitte als Nachtrag melden.

Hinweis Philips: **EOL + INS gleichzeitig 3 s halten** schaltet am Gerät den Tasten-Modus um (danach F1 = Event-Modus,
F2 = Tastatur-Modus …). RaKScribe braucht den **Event-Modus** (Philips-Standard, das Prüfskript zeigt ihn als „HID“).

## SpeechControl / SpeechMagic: mögliche Doppelreaktion

RaKScribe öffnet das SpeechMike **geteilt** – SpeechControl bekommt dieselben Tasten weiterhin. Wenn SpeechMagic gerade
zum Diktieren bereit ist, kann es deshalb auf Record (und INS/EOL) **selbst** reagieren, z. B. parallel aufnehmen.

So prüfen: SpeechMagic offen (Befund geöffnet), RaKScribe offen, Record drücken. Nimmt SpeechMagic **auch** auf?
Falls ja: in **Philips SpeechControl** (Tastenbelegung des Geräts – laut Philips „welche Befehle beim Drücken oder
Loslassen einer Taste ausgeführt werden“) für SpeechMagic den Tasten **Record, INS/OVR, EOL, F1, F2** keinen Befehl
zuweisen („keine Aktion“). Achtung: Dann diktiert man in SpeechMagic nicht mehr mit diesen Tasten – das ist bei
RaKScribe-Betrieb gewollt. Die genaue Menübezeichnung hängt von der SpeechControl-Version ab; das klären wir beim
Test am Praxis-PC.

## 5-Punkte-Testanleitung für Peter

1. **Starten:** EXE 3.8.0 laden (Titel „RaKScribe 3.8.0“), SpeechMike anstecken → oben „SpeechMike verbunden“.
   Web: Seite neu laden (F5), Menü ☰ → „SpeechMike verbinden“ → SpeechMike auswählen.
2. **Diktieren mit Pause:** Record → LED rot, sprechen. Record → Pause (LED blinkt), links wird der Text repariert
   (grünes „✓ bis zur Pause repariert“), rechts bleibt leer. Record → weitersprechen.
3. **Kontrolle:** INS → Befund erscheint rechts, nichts wird eingefügt (LED grün). Ein Wort im Befund ändern.
4. **Weiterschicken:** SpeechMagic-Fenster einmal anklicken, zurück zu RaKScribe, EOL → genau der geänderte Befund
   steht in SpeechMagic, RaKScribe ist leer. (Web: Befund ist kopiert → im RIS Strg+V.)
5. **Gegenproben:** EOL während der Aufnahme oder ohne Befund → nichts passiert, Hinweis „Erst INS …“. F2 → „Nur Text“,
   Record + INS zeigt den korrigierten Text. F10/F9 wie gewohnt. Bei Auffälligkeiten: Menü → „SpeechMike-Diagnose…“
   bzw. `rakscribe.log` (Zeilen `[SPEECHMIKE]`) an Hermes.

## Ausblick: EOL → Formatierung → Vidierliste

EOL läuft in EXE und Web über **eine zentrale Funktion**: `befund_fertig()` in `source_code/RaKScribe.py` bzw.
`befundFertig` in `web_app/src/App.tsx` (beide mit Kommentar „ZENTRALE STELLE“). Heute: sichtbaren Befund kopieren und
(EXE) ins SpeechMagic-Fenster einfügen, danach alles leeren. Später kommt genau dort „Formatierung → Vidierliste“
hinein – Tasten, Kontrollschritt und Zustände bleiben gleich.

## Dateien

- Neu: `source_code/speechmike.py`, `source_code/segmente.py`, `source_code/fensterziel.py`,
  `web_app/src/speechmike.ts`, `web_app/src/segmente.ts`
- Geändert: `source_code/RaKScribe.py`, `source_code/aufnahme.py`, `source_code/jobstate.py`, `web_app/src/App.tsx`,
  `web_app/src/lauf.ts`, `web_app/src/index.css`, `requirements.txt` (hidapi 0.15.0), `build-exe.yml`, `test.yml`
- Tests/Werkzeuge: `tests/offline/speechmike_faelle.txt`, `test_speechmike.py`, `test_speechmike_ablauf.py`,
  `web_app/speechmike_test.mjs`, Windows-UI-Test Fall E, `tools/e2e_speechmike_web.py`, `tools/exe_speechmike_smoke.py`,
  `tools/pause_segment_ab.py`, `tools/speechmike_probe.py`

Quellen: Google/Philips-SDK [dictation_support](https://github.com/GoogleChromeLabs/dictation_support)
(`src/speechmike_hid_device.ts`, `src/dictation_device_manager.ts`); Chromium
[`hid_device.cc`](https://chromium.googlesource.com/chromium/src/+/HEAD/third_party/blink/renderer/modules/hid/hid_device.cc)
(inputreport ohne Fokus-Prüfung) und
[`hid_chooser_context.cc`](https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/browser/hid/hid_chooser_context.cc)
(dauerhafte Freigabe nur mit Seriennummer); Philips
[SpeechMike Premium – Tasten-Modi](https://www.dictation.philips.com/fileadmin/Products/lfh3500/ifu/en/button-modes.html).
