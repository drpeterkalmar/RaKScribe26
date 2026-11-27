# Bericht kaiscribe-lektor-einspielen-tausch-n2: Tausch weiter blockiert, Abmeldung braucht Peter

Stand Fr 27.11.2026 20:30. Live bleibt **3.31.0**, `lektor.json` nicht angelegt (fehlt = Lektor aus). Belege: `~/cj/work/kaiscribe-lektor-einspielen-tausch-n2/` (r1_auftrag.txt, w1.txt).

## 1. Ursache (nur gelesen, Büro-PC 20:27)
- Nur der SM-Wächter 3.31.0 läuft (PID 28828 Bootloader + 37636 Kind, `--sm-waechter --nachfolger`, seit 00:37, Sitzung 2 = RDP `cas` vom Mac-mini). Beide sind laut Restart Manager die einzigen Halter von `X:\KaiScribe\Programm\KaiScribe.exe`. Bootloader läuft direkt aus X:, entpackt nach %TEMP%\_MEI….
- Andere PCs: Get-SmbOpenFile nicht prüfbar (Zugriff verweigert / WinRM). Laut RL laufen dort Wächter aus derselben EXE, enden aber bei Abmeldung.
- Es gibt keinen Stopp-Weg: weder Stopp-/Freigabe-Datei noch Neustart-Auftrag. Der Wächter endet nur bei neuer EXE (setzt Umbenennen voraus → Henne-Ei, `Pruefung.pruefen` in sm_einfuegen.py), bei SM_SENF/SM_IBL aus oder bei Windows-Abmeldung. Der Tausch-Skript-`Close-Ks` schließt per CloseMainWindow, der Wächter hat kein Fenster.
- Tausch-Versuch 20:28: `KS_TAUSCH=belegt … nicht umbenennbar`. Nichts erzwungen, keine Restdatei, SHA live weiter b1262bd7b655.

## 2. Lösungswahl
(a) Halter nicht weg. (c) Abmeldung der Sitzung `cas`: CasMed und CASSpeechMagic sind offen → laut Auftrag nicht ohne Peter. Kanban-Karte #531 `--grund vorort` angelegt.
(b) Stopp-Datei im Wächter (3.32.1) hilft erst ab dem übernächsten Tausch, weil 3.32.0 den Wächter noch ohne Stopp-Weg enthält; als Vorschlag im Folgejob.

## 👉 Peter: am Büro-PC in der Nachtzeit die Sitzung `cas` einmal abmelden (CasMed zuerst schließen), bis 02.12.

## Folgejob
`FOLGEJOB-KAISCRIBE-LEKTOR-TAUSCH-N3.md`: nach Peters Abmeldung sofort Tausch 3.32.0 + Schalter AUS; vor Scharf-n2 nötig.

## Abschluss
Der Wechsel auf KaiScribe 3.32.0 ist wieder nicht gelungen: Ein unsichtbarer Hintergrunddienst von 3.31.0 am Büro-PC hält die Programmdatei fest und lässt sich nicht sauber anhalten. Nichts wurde verändert, es läuft weiter 3.31.0, der Lektor ist aus. Weil dafür die Büro-Sitzung mit offenem CAS abgemeldet werden müsste, brauche ich dich: 👉 am Büro-PC einmal in der Nachtzeit die Sitzung „cas“ abmelden, bis 02.12. Danach tauscht ein Folgejob sofort.
