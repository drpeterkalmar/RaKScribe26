# Bericht kaiscribe-frog-einsetzen-n1 (Teil 1, Do 19.11.2026 17:50–19:40, Mac): FROG kam nicht in den Befund (RH 127)

Georg 19.11.: RH 127 „keine Werte“, „Teste das immer ob es funktioniert“. KaiScribe 3.19.13 fand den FROG-Baustein (Fuß beidseits), setzte
aber 0 Zeilen ein. Im Band standen nur Hinweise.

## 1. Ursache (belegt, nur gelesen auf der Automaten-VM als rakauto, Ausgabe ohne Nummer/Namen)
- Seit 12.11. gibt es genau **einen** Lauf mit FROG: Do 19.11. 13:01, PC **CASWS10**, KaiScribe 3.19.13, Vorlage `fuß_in_2_ebenen`,
  `ibl_zeilen=0`. Der Baustein lag schon um 12:34 vollständig in der Ablage (FROG v3, Text „Varusstellung der Kleinzehe beidseits …“).
- An CASWS10 lief um 13:01 noch die **Brücke 2.5.15** (Protokoll `bruecke_CASWS10.log`), erst ab 13:28 die 2.5.22.
  Die Brücke reicht das Feld „befundtext“ erst ab **2.5.20** (FROG) bzw. **2.5.22** (HIPPO) an KaiScribe weiter.
- Ohne die Sätze fiel KaiScribe in den alten Weg (Messzeilen nur mit Treffer). Die Ergebnis-Begriffe verwarf er, weil das Vorlagen-Ergebnis
  „Regelrechte Darstellung des Fußskeletts beidseits.“ unauffällig war. So blieben 0 Zeilen und zwei Hinweise „nicht ins Ergebnis
  übernommen“ – genau Georgs Bild. Mit dem gespeicherten Lauf und demselben Baustein ist der Fehler 1:1 nachgestellt.
- Der Formatierer fasst bei KaiScribe-Diktaten Bausteine nicht an, die älter als das Diktat-Ende sind. Deshalb kam auch im Brief nichts.
- **Zweiter Fehler, der auch mit neuer Brücke geblieben wäre:** Die KI schrieb (Prompt-Regel `cas_beidseits`, „wo nötig beidseits“)
  „Das Fußskelett ist **beidseits** nach Form …“. Dieses Muster erkannte KaiScribe nicht. Der FROG-Satz wäre dann ans Ende gehängt worden,
  und der Normalsatz „… Stellung … normal“ wäre als Widerspruch stehen geblieben.
- HIPPO (RH 16, RH 95) lief an PCs mit Brücke 2.5.22 (z. B. RAKCLIENT04 08:39: `ibl_zeilen=2`, HIPPO-Satz + Schluss da).
- **Brücken-Stände** (letzter Start laut Protokoll): CASWS10 2.5.22, RAKCLIENT04 2.5.22. **CASWS08 2.5.15** (zuletzt 18.11.).
  Für den Büro-PC CASWS14 zeigt das Protokoll noch 2.5.15 vom 18.11.; laut Einspiel-Bericht vom 19.11. 03:49 ist dort 2.5.22 installiert.

## 2. Änderung (KaiScribe 3.19.15, nur EXE – die Web-App hat kein IB Lab)
1. **Text aus der Ablage nachholen** (`ibl_bausteine.text_nachladen`, aufgerufen beim CAS-Takt in `RaKScribe._ibl_holen`):
   - Fehlt bei FROG (mit Ergebnispunkten) oder HIPPO das Feld „befundtext“, liest KaiScribe es aus der Abholer-Datei
     `X:\IBL-Vorbefunde\<AccNo>_<modul>.json`. Das ist dieselbe Datei, aus der die Brücke liest.
   - Nur bei gleicher AccNo **und gleicher Fassung**. Sonst bleibt alles wie geliefert. Eine kaputte oder fehlende Datei oder eine AccNo
     mit Pfadzeichen werden still übergangen.
   - Neu in `config.ini`: `IBL_ABLAGE` (Standard `X:\IBL-Vorbefunde`, `aus` = nie).
   - Hinweis im Band: „FROG: Text aus der IB-Lab-Ablage geholt – Brücke an diesem PC veraltet (KaiScribe-einrichten.cmd)“. Klappt das
     Nachladen nicht: „FROG: Fuß-Text fehlt – Brücke an diesem PC veraltet …, IB-Lab-Werte nicht eingesetzt“. Es wird nie still nichts.
2. **FROG-Vorlagensätze auch mit Seite** (`_FROG_STELLUNG`, `_FROG_GEWOELBE`, `_FROG_PHALANGEN`): „ist beidseits/beidseitig/jeweils …“
   und „Die Fußskelette/Fußgewölbe sind …“. Ein diktierter Seitenbefund („Das Fußgewölbe ist rechts abgeflacht.“) bleibt unberührt.
3. **rakscribe.log** (`protokoll.TeilbareDatei` statt `RotatingFileHandler`):
   - Die Datei liegt auf X: und wird von mehreren PCs zugleich beschrieben. Der alte Handler hielt sie offen. Unter Windows scheitert dann
     das Umbenennen beim Rotieren, und ab 1 MB schrieb niemand mehr (19.11. ab 11:32: 1 000 059 Byte, still).
   - Jetzt ist die Datei nur je Eintrag offen. Scheitert das Rotieren, wird trotzdem angehängt und frühestens nach 60 s erneut rotiert.
     Es bleiben 5 × 1 MB.
   - Alte Instanzen (3.19.13/14) halten die Datei weiter offen, bis sie neu starten.
4. **Regel-Register:** neue Regel `ibl-text-immer` (Pflicht im Wächter). Die FROG-Wortlaut-Regeln (`ibl-frog`, `ibl-ohne-norm`) sind
   unverändert grün. Die Wortlaute selbst kommen unverändert vom Abholer: Latein, keine Normbereiche, 2° Toleranz,
   Hallux valgus gering/mittel/hochgradig, Schlusssatz PACS.

## 3. Tests
- Neu: `tests/offline/test_ibl_frog_einsetzen.py` (in `test.yml`), **46 Prüfungen grün**:
  - **Fall 19.11.:** `snapshots/frog_1911_beidseits.json`, mit ris-mods `53c767e` (Abholer 1.3.13 + Brücke) aus den echten Winkeln erzeugt,
    Nummer erfunden. Alte Brücke → 0 Zeilen (nachgestellt) + Hinweis. Alte Brücke + Ablage = neue Brücke Wort für Wort.
    KI-Satz mit „beidseits“ wird ersetzt. Normalbefund ohne KI. Gate. Keine Normbereiche.
  - **Echte anonyme Fälle:** einseitig (Fall 10, Fuß links), beidseits (Fall 7, Hallux valgus + Pes cavus), Vorfuß (Fall 1, nur d.p.).
    Geprüft: Sätze im Befund, Begriffe als erster Punkt, Schluss zuletzt, Vorlagensatz ersetzt, alte Brücke + Ablage = neu.
  - **Nachladen nur, wenn es passt:** andere Fassung, Datei fehlt, `aus`, Pfadzeichen, halbe Datei, fremde AccNo, schon Text,
    FROG ohne Pathologie, Rho. Dazu HIPPO bei Brücke < 2.5.22.
  - **EXE-Ablauf:** CAS-Takt mit Brücken-Datei ohne Text → nachgeladen → INS → Text im Befund + Hinweis.
- `test_logging.py`: geteilte Datei mit gesperrtem Rotieren → jede Zeile geschrieben, ein Versuch je 60 s, danach Rotation. Datei nur je
  Eintrag offen (Umbenennen von außen klappt).
- Alle 47 Offline-Gates aus `test.yml` am Mac gelaufen: grün außer `test_cas_auftrag.py` und `test_maske_ablauf.py`. Die beiden sind auf
  dem unveränderten main gleich rot (Mac-Umgebung, in GitHub grün). `test_ibl_nur_auffaellig.py` (nicht in CI) ist auf main ebenso rot
  (PANDA-Erwartung von 3.18.7).
- **GitHub „Tests“ 44585270898 für `fa2dcc4`: grün.**

**Prüftext** (Fall 19.11., CAS fuss2 beidseits, KI-Attrappe mit „Das Fußskelett ist beidseits nach Form …“, alte Brücke + Ablage):
```
## Fuß beidseits in 2 Ebenen

## Befund
Varusstellung der Kleinzehe beidseits mit einem Metatarsophalangealwinkel V von rechts 17° und links 13°. Das Fußgewölbe ist regulär
ausgebildet. Mineralgehalt und Knochenstruktur sind regelrecht. … Keine intra- und periartikulären Verkalkungen. Die Weichteile sind
unauffällig.

## Ergebnis
Digitus quintus varus beidseits.
Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.
```
So war es am 19.11. (alte Brücke, 3.19.13): Beschreibung und Ergebnis unverändert die Vorlage („Regelrechte Darstellung des Fußskeletts
beidseits.“), 0 Zeilen.

## 4. Version, Web, EXE
- **3.19.15** auf main (`fa2dcc4`, Fix `4623f50`). Enthält 3.19.14.
- EXE: Build 44585294862 **grün**, Release **3.19.15 = latest**, `rakscribe26.exe` 56 560 416 Byte, sha256
  `9c7a91f8ec2e1105d0b7c05dfb17d4609d6854c3dfbf40ba117b78f29dea71de`. Windows-UI-Test 44585570908: siehe Nachtrag unten.
- Web: Deploy 44585958439 (nur Versionsnummer, kein IB Lab im Web).
- ris-mods (Brücke, Formatierer, Abholer): keine Änderung.

## 5. Werkzeuge
- `tools/ibl_abnahme_bausteine.py`: schreibt einen echten FROG- und HIPPO-Baustein (anonyme Fälle) als Abholer-Datei für die AccNo einer
  Testnummer und gibt den erwarteten Text aus (für die Abnahme am Testpatienten 451898). Mit der ris-mods-Brücke gegengelesen.
- `tools/vm/ibl_laeufe_pruefen.py`: auf der VM als rakauto. Gibt je Lauf mit FROG/HIPPO nur Zähler und Kategorien aus
  (zeilen, Satz da, Schluss da, Brücken-Version des PCs, Urteil OK/LEER/ALT).
  - Weg: hochladen mit ris-mods `automaten_vm/mac/vmssh.py --hochladen`, ausführen mit `abholer_vm.alskonto`.
  - PowerShell-Hülle: `& cmd.exe /c C:\RaK\laufwerke.cmd C:\Windows\py.exe -3.12 -X utf8 <skript> …`.
  - Probelauf 19.11.: HIPPO 08:39 OK, FROG 13:01 ALT.

## 6. Einspielen → Folgeaufträge
- `kaiscribe-frog-einsetzen-n1-einspielen` (Brief `FOLGEJOB-KAISCRIBE-FROG-EINSETZEN-N1-EINSPIELEN.md`):
  - Ressource ordi, ab Do 19.11. 20:15, nach `kaiscribe-mehrfach-seitenlos-n1-einspielen`.
  - **Pflicht-Abnahme vor dem Tausch:** Testpatient 451898 mit fuss2 + bü, echter FROG- und HIPPO-Baustein. Brief-Text belegen
    (Screenshot/Textauszug). Ohne Beleg wird nicht eingespielt.
  - Der wartende 3.19.14-Auftrag bekam einen Nachtrag: Er nimmt 3.19.14, nicht 3.19.15.
- `kaiscribe-frog-einsetzen-n1-kontrolle` (Brief `FOLGEJOB-KAISCRIBE-FROG-EINSETZEN-N1-KONTROLLE.md`): Fr 20.11. ab 13:00 auf der VM.
  Prüft nur lesend den ersten echten FROG-Fall mit 3.19.15 und `rakscribe.log`. Ohne FROG-Fall reiht er sich auf den nächsten Werktag ein
  (bis Mi 25.11.).
- Kanban #422 (Brücke einrichten) ergänzt: CASWS10/RAKCLIENT04 erledigt, CASWS08 offen.

## 7. Grenzen / offen
- Ältere Brücke **und** X: nicht erreichbar → kein Nachladen, sichtbarer Hinweis, Vorlage bleibt (kein falscher Text).
- Der Formatierer (ris-mods `ibl_einfuegen._FROG_VORLAGE`) kennt „… ist beidseits nach Form …“ noch nicht. Er greift nur bei
  Philips-Diktaten bzw. bei nachgekommenen Bausteinen. Bei Bedarf gleich nachziehen (ris-mods, eigener Auftrag).
- 👉 Georg/Peter: an **CASWS08** einmal `X:\RaKScribe\KaiScribe-einrichten.cmd` doppelklicken (Kanban #422), bis Fr 20.11. vor dem ersten
  Diktat. Für FROG/HIPPO ist das ab 3.19.15 nicht mehr nötig, für Rho/LAMA weiter sinnvoll.
