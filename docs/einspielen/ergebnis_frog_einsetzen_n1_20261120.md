# Ergebnis kaiscribe-frog-einsetzen-n1-einspielen – KaiScribe 3.19.15 live (Fr 20.11.2026, 00:27)

**Ergebnis: KaiScribe 3.19.15 ist seit Fr 20.11.2026 00:27 auf X: aktiv.** Eingespielt wurde erst nach der Pflicht-Abnahme
am Testpatienten 451898 (fuss2 + bü, echter FROG- und HIPPO-Baustein). Alle erwarteten Sätze standen wörtlich im Brieftext,
den KaiScribe beim EOL an CAS übergab (11/11 IB-Lab-Zeilen). Nichts vidiert, Testeintrag storniert, Bausteine entfernt.
Büro-PC über den Ordi-Hermes (Aufträge L1/L2, P1, P2, P3), keine Patientendaten, kein C-MOVE/C-STORE, keine DICOM-Header,
von hier aus kein Zugriff auf die CAS-DB (der Ordi prüft am Testpatienten nur per SELECT wie in der Teststrecke).

## 1. Tore (nur gelesen, Do 19.11. 20:40–20:47)
- Release `3.19.15`: Asset `rakscribe26.exe`, 56 560 416 Byte, API-Digest `sha256:9c7a91f8ec2e1105d0b7c05dfb17d4609d6854c3dfbf40ba117b78f29dea71de` (= Brief).
- Läufe für `fa2dcc4`: Tests 44585270898, Build 44585294862, Windows-UI-Test 44585570908 – alle `success`.
- Live vorher: `X:\RaKScribe\rakscribe26.exe` = **3.19.13** (sha `704549ed1c3a`, 56 853 396 B). Der 3.19.14-Job war noch nicht gelaufen.
  `rakscribe.log` 1 000 059 B, still seit 19.11. 11:32:49, kein `rakscribe.log.1`.
- Büro-PC: die einzige RDP-Verbindung kam vom Mac (100.102.201.79, netstat :3389 + Ereignisprotokoll). Das erste „PETER“ des
  Ordi-Hermes (L1) war seine eigene Vorsicht. CAS/Word/MammoDoppel zu, am 451898 nichts offen.

## 2. Abnahme-Weg (ohne X: anzufassen)
KaiScribe liest `config.ini` und den Praxis-Schlüssel neben der EXE (`BASE_DIR = dirname(sys.executable)`). Den CAS-Auftrag
(`%LOCALAPPDATA%\RaKScribe\cas_auftrag.json`), die Lauf-Dateien (`X:\RaKScribe\Daten\laeufe`) und die IB-Lab-Ablage findet
es dagegen unabhängig vom Ort. Deshalb lief 3.19.15 für die Abnahme als **Testkopie** am Büro-PC:
`%LOCALAPPDATA%\hermes\work\kf_abnahme\app\` = EXE vom GitHub-Release (SHA geprüft) + `config.ini` + `rakscribe-praxis-key.json`
(aus `X:\RaKScribe`, nur gelesen). Die Live-Instanz 3.19.13 wurde sanft geschlossen (CloseMainWindow), danach lief die
Testkopie `--minimiert` (Titel „KaiScribe 3.19.15 – Röntgen am Kai“, `BASE_DIR` = Testordner, `[INIT]` ohne Fehler). Nach dem
Test lief wieder 3.19.13 über `RaKScribe.lnk`. Die Testkopie (samt Schlüssel-Kopie) wurde nach dem Tausch gelöscht.
Die Teststrecke `teststrecke/buero/kaiscribe.py` 1.7 findet Fenster und Log der laufenden Instanz selbst, sie blieb unverändert.

| Zeit | Schritt | Beleg |
|---|---|---|
| 23:49 | P1: EXE nach `ks_tausch\v3.19.15`, Testkopie, Abnahme-Skript `tools/ibl_abnahme_bausteine.py` (+2 Testdaten-Dateien, raw.githubusercontent `ec5a673`, SHA geprüft) | Probe ohne X: gibt den erwarteten Text aus |
| 23:53 | Live 3.19.13 sanft geschlossen, Testkopie 3.19.15 gestartet | Titel 3.19.15, `[INIT]` STT/Gemini/SpeechClient ok |
| 00:02 | Testeintrag **20261120001** (wrid 2403753) per `cas_w.ps1` 1.1 `-Codes "fuss2,bü"` | SELECT: fuss2 seqnumb 1, bü seqnumb 2 (bü per „L“ nachgetragen, #299) |
| 00:03 | `ibl_abnahme_bausteine.py X:\IBL-Vorbefunde --frog 202611200011 --hippo 202611200012` | `…0011_frog.json` 3910 B, `…0012_hippo.json` 1960 B |
| 00:03–00:04 | Diktat über die Strecke: Mac-Ton „Fuß beidseits unauffällig. Beckenübersicht unauffällig.“ (RDP-Mikrofon), F10/F10/F12 | `kaiscribe.py` status ok, 40,5 s, EOL 1861 Zeichen |
| 00:05 | Bausteine gelöscht (0 Treffer), Storno | `storno ok`, Status `!`, 0 Briefe, nicht vidiert |
| 00:06 | Testkopie geschlossen, Live 3.19.13 über `RaKScribe.lnk` | Titel 3.19.13, minimiert |

Der Roboter-Schalter `roboter_testpatient.txt` blieb aus: Der Roboter schrieb den Testeintrag nicht (0 Briefe). Belegt ist
der Brieftext deshalb über die Ablage `<Nr>.rakscribe.txt` (genau der Text, den KaiScribe beim EOL an CAS übergibt) und über
die Lauf-Datei (`ergebnis_vorschlag`, zeichengleich).

## 3. Abnahme-Wortlaut (synthetisches Diktat am Testpatienten, wörtlich aus `\\casmed\speech$\diktate\20261120001.rakscribe.txt`)

```
## Fuß beidseits in 2 Ebenen

## Befund

Varusstellung der Kleinzehe beidseits mit einem Metatarsophalangealwinkel V von rechts 17° und links 13°. Das Fußgewölbe ist regulär ausgebildet. Mineralgehalt und Knochenstruktur sind regelrecht. Glatte und scharfe Abgrenzbarkeit der normal breiten Kortikalis ohne pathologische Konturunterbrechung. Normale Breite der Kompakta. Die gelenkbildenden Flächen sind regelrecht geformt, glatt und scharf begrenzt und stehen normal weit zueinander. Keine intra- und periartikulären Verkalkungen. Die Weichteile sind unauffällig.

## Ergebnis
Digitus quintus varus beidseits.
Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.


## Beckenübersicht stehend

## Befund

Geringer Beckenschiefstand von 7 mm, rechts tieferstehend. Beinlängendifferenz von 1 mm, links kürzer. Der LCE-Winkel beträgt rechts 23° und links 22°. Der AI-Winkel beträgt rechts 13°. Der CCD-Winkel beträgt rechts 145° und links 146°. Mineralgehalt und Knochenstruktur sind regelrecht. Die kortikalen Randkonturen sind normal breit, glatt und scharf abgrenzbar ohne pathologische Konturunterbrechungen. Regelrechte Abbildung beider Pfannendächer. Ordnungsgemäße Stellung der normal geformten Hüftköpfe. Normal konfigurierte, glatte Gelenkflächen mit allseits normal weitem Gelenkspalt. Keine intra- oder periartikulären Verkalkungen. Das Iliosakralgelenk und der Symphysenspalt sind normal weit, glatt und scharf begrenzt. Das Os sacrum ist unauffällig. Unauffällige Weichteile.

## Ergebnis
Grenzwertige Überdachung des rechten Hüftkopfes bei steilem Pfannendach. Grenzwertige Überdachung des linken Hüftkopfes. Coxa valga beidseits.
LCE = lateraler Center-Edge-Winkel nach Wiberg, AI = Acetabulumindex nach Tönnis, CCD = Caput-Collum-Diaphysen-Winkel. Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.
```

Abgleich mit dem Brief (Schritt 1.4):
| Erwartet | Befund |
|---|---|
| FROG-Satz „Varusstellung der Kleinzehe beidseits … rechts 17° und links 13°.“ an der Stelle des Fußskelett-Satzes | ✅ erster Befundsatz, kein „Das Fußskelett ist …“ |
| „Das Fußgewölbe ist regulär ausgebildet.“ | ✅ |
| Ergebnis erster Punkt „Digitus quintus varus beidseits.“, kein „Regelrechte Darstellung des Fußskeletts …“ | ✅ / ✅ (nicht enthalten) |
| „Weitere Winkelmessungen …“ ohne Nummer ganz unten | ✅ je Befund einmal |
| HIPPO-Sätze (Beckenschiefstand 7 mm re tiefer, BLD 1 mm li kürzer, LCE/AI/CCD) am Anfang der Beschreibung | ✅ |
| Ergebnis „Grenzwertige Überdachung … Coxa valga beidseits.“ + Schlussanmerkung „LCE = … Weitere Winkelmessungen …“ ohne Nummer | ✅ |
| keine Normbereiche, keine Messzeilen „… (IB Lab FROG/HIPPO).“, keine rote Zeile | ✅ |

Weitere Belege zur Nr:
- Lauf-Datei `X:\RaKScribe\Daten\laeufe\20261120001_20261120-000406.json` (2458 B, 00:04:06): `kaiscribe` „3.19.15“,
  `vorlagen` [fuß_in_2_ebenen, beckenübersicht_stehend], `ibl_module` [FROG beidseits, HIPPO beidseits], `ibl_baustein` true,
  **`ibl_zeilen` 11**, `ergebnis_vorschlag` zeichengleich mit dem Text oben, `stt_roh` 69 Zeichen.
- `20261120001.rakscribe.json`: Block `kaiscribe` mit denselben IBL-Werten.
- rakscribe.log der Testkopie: `[CAS] Leistungen …: fuss2(fuß_in_2_ebenen), bü(beckenübersicht_stehend)` ·
  `[IBL] Bausteine …: FROG v1 (Ziffer 1), HIPPO v1 (Ziffer 2)` · `[IBL] eingesetzt: frog → Fuß beidseits in 2 Ebenen, hippo →
  Beckenübersicht stehend · 11 Zeile(n)` · `[LAUF] protokolliert` (00:04:06) vor `[IBL] EOL: 11/11 IB-Lab-Zeilen wörtlich im
  Befund` und `[CAS] EOL: Befund (1861 Zeichen)` (00:04:08). Kein Traceback, kein Fehler.
- bruecke.log (Büro-PC, Brücke 2.5.22): `[ibl] 20261120001 FROG v1 (…0011), HIPPO v1 (…0012)` · `angenommen von RaKScribe
  3.19.15` · `[nachvollzug] ja … vorlagen=2 ibl=ja` · `[ablage] ok=True` · `[fertig] ok=True JobFinished(2403753)`.
- Screenshot: keiner. Der Ordi-Hermes macht keine Bildschirmaufnahmen (SOUL-Regel 3), das Befundfenster steht nur Sekunden
  bis F12. Als Beleg dienen der wörtliche Brieftext und die Lauf-Datei.
- Nicht prüfbar am Büro-PC (Brief 1.6): der neue Nachlade-Weg „Text aus der Ablage, wenn die Brücke keinen `befundtext`
  liefert“. Der Büro-PC hat Brücke 2.5.22, die den Text selbst liefert (kein `[IBL] Text aus der Ablage nachgeladen`). Das
  prüft `kaiscribe-frog-einsetzen-n1-kontrolle` an CASWS08 (dort lief zuletzt Brücke 2.5.15).

## 4. Tausch (P3, Fr 20.11.)
- `kaiscribe_x_tauschen.ps1` (sha `9e4d1188b0e6`) `-Schritt exe -Tag 3.19.15 -Sha 9c7a91f8…71de`. Das Skript wartete 20 min nach
  der jüngsten Ablage (= unser Testdiktat 00:04), kein `-Trotzdem`.
- `KS_TAUSCH=ok SCHRITT=exe neu=9c7a91f8ec2e alt=704549ed1c3a sicherung=rakscribe26.exe.vor3.19.15-20261120-002659.alt neu_gestartet=True`
- 00:27:01 per Autostart-Verknüpfung neu gestartet: Titel „KaiScribe 3.19.15 – Röntgen am Kai“, `X:\RaKScribe\rakscribe26.exe`,
  minimiert, eine Instanz (+ Zwilling). Kein Dialog der Sicherheitssoftware. EXE auf X: sha `9c7a91f8ec2e`.
- Die anderen Befund-PCs (CASWS08, CASWS10, RAKCLIENT04) starten 3.19.15 beim nächsten KaiScribe-Start von X:.

## 5. Log läuft wieder
- `rakscribe.log.1` = das alte 1-MB-Log (1 000 059 B, 19.11. 11:32:49). Rotiert wurde schon beim Neustart der Live-Instanz um
  00:05 (nachts hielt kein anderer PC die Datei offen).
- Seit dem Start von 3.19.15 wächst `rakscribe.log` (2 263 → 4 526 B, 00:27:24): `Startup (Frozen: True)`, `BASE_DIR: X:\RaKScribe`,
  `[INIT]` (STT, Gemini über Vertex, Befund-KI Claude Sonnet maskiert, Befund-Prompt 2026-11-18-kl-tabelle-koala, 144 Vorlagen),
  `[START] --minimiert`, `[SPEECHMIKE] Verbunden`. 0 Zeilen mit Fehler/WARN/Traceback/WinError. Die Versionsnummer steht
  nicht in den `[INIT]`-Zeilen. 3.19.15 ist über Fenstertitel und EXE-SHA belegt.
- Ältere Instanzen an anderen PCs (3.19.13) schreiben erst nach ihrem Neustart wieder mit.

## 6. Rückweg
- `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste .alt = `rakscribe26.exe.vor3.19.15-20261120-002659.alt` = 3.19.13;
  nur Sa/So oder Mo–Fr 20:10–06:30).

## 7. Hinweise
- **3.19.14-Job:** `kaiscribe-mehrfach-seitenlos-n1-einspielen` stand am Server noch in der Warteschlange. Sein Nachtrag
  („3.19.15 gilt nicht“) hätte X: auf 3.19.14 zurückgedreht und damit den FROG-Fix entfernt. 3.19.15 enthält 3.19.14
  (`bd8a4a1` ist Vorfahre von `fa2dcc4`). Gesetzt ist jetzt ein Nachtrag: kein Tausch, nur die Abnahme lws + bü mit der
  Live-Version 3.19.15.
- Ordi-Hermes: ein Lauf brach mit „model provider nicht erreichbar“ ab, die Wiederholung lief durch. Nach Mitternacht stellte er
  die CAS-Warteliste auf den 20.11. um (sonst bricht `cas_w` ab).
- Werkzeuge und Antworten am Mac: `~/cj/work/kaiscribe-frog-einsetzen-n1-einspielen/` (l1/l2/p1/p2/p3 + Antworten). Büro-PC:
  `%LOCALAPPDATA%\hermes\work\kf_abnahme\` (ergebnis_p2.md, p2_belege.txt, aenderungen.log).

Meldung nach außen (live belegt): „KaiScribe 3.19.15: IB-Lab-FROG-Text kommt wieder in den Befund (auch an PCs mit älterer
Brücke), abgenommen am Testpatienten mit echtem FROG- und HIPPO-Baustein; aktiv seit Fr 20.11.2026 00:27.“
