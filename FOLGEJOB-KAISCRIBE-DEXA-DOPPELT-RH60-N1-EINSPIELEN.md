# Teil 2 zu kaiscribe-dexa-doppelt-rh60-n1: Einspielen + Abnahme an 451898 (Kombi Rö + DEXA)

Code: Die Version steht im Commit „v3.28.3: Nie eine DEXA-Vorlage …“ auf origin/main (`git log --oneline -1 --grep dexa-doppelt`).
Die Änderung beschreibt `BERICHT-KAISCRIBE-DEXA-DOPPELT-RH60-N1.md`. Die Version enthält alles, was vorher auf main war.
Läuft heute Abend schon ein anderer KaiScribe-Tausch, dann nur einmal tauschen, und zwar mit der neuesten Version.

Regeln: Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am Wochenende. 451898 nie vidieren. Keine Patientendaten auf
Mac oder Server, in Bericht und Commits nur RH-Nummern. Meldungsruhe gilt.

## A. Einspielen
1. Build Windows EXE (`gh workflow run build-exe.yml`, Release mit VERSION) und Windows-UI-Test (test-exe-windows.yml) müssen grün sein.
2. Tausch: `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag <Version>`. SHA256 der X:-EXE muss gleich dem Release-Asset sein.
3. Web-App: Pages-Deploy grün, die Live-Seite zeigt die Version. **Achtung:** Seit 24.11. 22:24 scheitert der Deploy an GitHub
   („No artifacts named github-pages“, der Build ist grün; Läufe 45500511449, 45569199889, 45569403893). Live steht noch **3.28.1**.
   Mit `gh workflow run deploy.yml --ref main` neu starten, bis https://drpeterkalmar.github.io/RaKScribe26/ 3.28.3 (oder neuer)
   zeigt. Scheitert es weiter: Kanban-Karte in Spalte tun „RaKScribe26 Pages-Deploy hängt“, keine Schleife.

## B. Abnahme an 451898 (Kombi Rö + DEXA)
1. Am Testpatienten 451898 eine Kombi anlegen bzw. nutzen: eine Röntgen-Leistung (z. B. LWS 2 Ebenen) **plus** eine
   DEXA-Leistung (od/dexa). Diktat nur zum Röntgen-Teil, z. B. „LWS in 2 Ebenen: Osteochondrose L5/S1.“ → INS.
   Erwartet:
   - Im Befund steht nur „Lendenwirbelsäule in 2 Ebenen“. Es gibt keine Überschrift „Knochendichtemessung (DEXA)“,
     kein „ODM – LWS“ und keinen Text in eckigen Klammern.
   - Es gibt keinen Hinweis „Osteodensitometrie laut CAS, nicht diktiert …“.
   - Im Log `[CAS] Leistungen …` steht od(knochendichtemessung_dexa), aber KEINE Zeile `Normalbefund der Vorlage knochendichtemessung_dexa`
     und kein `Abschnitt …: Vorlage knochendichtemessung_dexa`.
2. Gegenprobe Rho (nur wenn ohne Zusatzaufwand möglich): dieselbe Kombi mit „… Rho Score 8“ im Diktat. Es darf kein
   Rho-Text kommen, Hinweis „Rho: kein Rho-Text – Knochendichte in den letzten 2 Jahren“. Damit ist belegt, dass die DEXA-Sperre bleibt.
3. Seitenbild des Befunds **ohne Patientendaten** als Beleg nach `docs/screenshots/` (Name `dexa-doppelt-451898-<Datum>.png`).
4. Diktat stornieren, nicht vidieren.

**Rot → Rückweg:** `-Schritt zurueck` auf die vorige EXE, Karte in Spalte tun.

## C. Lücken aus Teil 1 (nur lesend auf der VM)
- **Betroffene Briefe zählen:** seit 3.20.5 live (Sa 21.11.2026 04:42) bis zum Tausch. In den KaiScribe-Logs (X:/Daten bzw.
  `%APPDATA%\KaiScribe` der Schreib-PCs) nach Zeilen `[CAS] Osteodensitometrie: nicht diktiert → Normalbefund der Vorlage
  knochendichtemessung_dexa` bzw. `…: nicht diktiert → Normalbefund der Vorlage knochendichtemessung_dexa` suchen
  (alle DEXA-Kürzel: dexa, dexaneu, dxf, od, odh). Dazu Abschnitte mit `Vorlage knochendichtemessung_dexa (diktat` (zweiter Weg:
  „Knochendichte“ im Rö-Diktat). Nur Anzahl + RH-Nr. in den Bericht.
- **RH 60 nachlesen:** Diktat `20261123060` (.doc in M:\Diktate, sonst Nachbartage mit RH 60) – bestätigen, dass der leere
  DEXA-Teil aus KaiScribe kam (Überschrift „Knochendichtemessung (DEXA)“, „ODM – LWS“ mit `[Wert_LWS]`). Ursula schrieb
  „g/cm³“, die Vorlage hat g/cm². Bitte nur bestätigen, nichts am Brief ändern.

## D. Meldungen (erst wenn belegt live)
- Bericht `BERICHT-KAISCRIBE-DEXA-DOPPELT-RH60-N1.md` ergänzen: Version live, Probe 451898, Anzahl betroffener Briefe (RH-Nr.).
- Satz für Ursula (über die Queue, nicht selbst senden): „Seit <Datum/Uhrzeit> fügt KaiScribe bei DEXA in Kombination
  mit Röntgen oder Ultraschall keine DEXA-Vorlage mehr ein. Den DEXA-Teil fügen wie früher Sie ein, bei reiner DEXA der Roboter.
  Briefe vom 23.11. bis heute mit doppelter DEXA-Überschrift (RH …) bitte den oberen, leeren Teil löschen.“
