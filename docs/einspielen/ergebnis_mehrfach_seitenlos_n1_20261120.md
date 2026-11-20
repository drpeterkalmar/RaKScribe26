# Ergebnis kaiscribe-mehrfach-seitenlos-n1-einspielen (Fr 20.11.2026, ~04:30, Hetzner-Nachtspur)

**Ergebnis: Kein Tausch nötig und keiner gemacht. Auf X: läuft bereits KaiScribe 3.19.15, und 3.19.15 enthält 3.19.14.
Die Abnahme mit gesprochenem Diktat A/B am Testpatienten 451898 ist von hier aus NICHT gelaufen (offen, siehe 3).**

## 1. Tore (nur gelesen)
- Nachträge: 3.19.15 liegt seit Fr 20.11. 00:27 auf X:, abgenommen im Job kaiscribe-frog-einsetzen-n1-einspielen.
  `git merge-base --is-ancestor bd8a4a1 fa2dcc4` = ja (3.19.15 enthält 3.19.14). Schritt 1 (Tausch) entfällt, ein Tausch auf 3.19.14 wäre ein Rückschritt.
- Live-Stand 04:3x über den Ordi-Hermes (Lauf run_080437e1…, nur lesend): `X:\RaKScribe\rakscribe26.exe` SHA256 beginnt mit **9c7a91f8ec2e**,
  56 560 416 Byte (Dateizeit 19.11. 23:47). Fenstertitel „KaiScribe 3.19.15 - Röntgen am Kai“. `rakscribe.log` wächst (letzter Start 03:25:14, `[INIT]` ohne Fehler).
- Neueste Lauf-Dateien: 20261120005 (03:24), …004 (02:06), …002 (01:55): keine von diesem Job. Eine RDP-Sitzung (cas, die des Ordi-Hermes), Konsole gesperrt.
- Am Büro-PC und an X: wurde nichts verändert.

## 2. Was belegt ist
- Der Prüfstand für 3.19.14/3.19.15 (`tests/offline/test_mehrfach_seitenlos.py`, 38 Prüfungen: Georgs Fall mit Überschriften, Nachtrag-Diktat ohne
  Regionsnennung, bü → Beckenübersicht und Hüfte, HIPPO nur im Becken, K&L-Tabellensatz Grad 2 nur im Beckentext, Prüfzeilen, Rho → LWS) lief am
  Stand `fa2dcc4` (= live) am Server: **ALLE GRÜN**.
- Erwartung A und B steht damit auf Code-Ebene (zwei Befunde „Lendenwirbelsäule in 2 Ebenen“ + „Beckenübersicht stehend“, je eigenes Ergebnis).
  Das ersetzt den Lauf mit echter Stimme **nicht**.

## 3. Offen: Diktat A und B live am 451898
Die Teststrecke spricht die Diktate mit der Mac-Sprachausgabe über das RDP-Mikrofon (`teststrecke/mac/ton.sh`, `audin_tts`). Das gibt es auf dem
Hetzner-Server nicht (kein Mac, kein sdl-freerdp, kein Zugang zum Mac). KaiScribe hat keinen Text-Eingang für Tests. Ich habe deshalb keinen Klick-Lauf
mit erfundenem Ersatz gestartet und nichts als „live abgenommen“ gemeldet. Fehlt noch: Testeintrag 451898 mit `lws,bü`, Diktat A und Diktat B,
EOL, Beleg in `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` (`vorlagen` mit beiden Keys), Storno. Das geht nur am Mac, außerhalb Mo–Fr 06:30–17:20
(also heute Nacht bis 06:30 oder ab Fr 20:10 bzw. Sa/So), als Folgejob `kaiscribe-mehrfach-seitenlos-n1-abnahme` auf dem Mac (Ressource ordi).

## 4. Rückweg
Nicht geändert. Falls je nötig: `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste .alt = 3.19.13), nie auf 3.19.14.

Meldung nach außen: nur „KaiScribe 3.19.15 (mit 3.19.14: zwei Untersuchungen in einem Diktat → zwei Befunde) ist live seit Fr 20.11. 00:27; Live-Abnahme mit
Stimme steht noch aus“. Nicht als abgenommen melden.
