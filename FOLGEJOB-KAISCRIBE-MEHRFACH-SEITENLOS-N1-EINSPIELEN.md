# kaiscribe-mehrfach-seitenlos-n1-einspielen – KaiScribe 3.19.14 einspielen (LWS + Becken in einem Diktat), Abnahme 451898

Eingereiht von `kaiscribe-mehrfach-seitenlos-n1` (Teil 1, Do 19.11.2026 ~18:30, Mac). Repo RaKScribe26, Ordi-Werkzeuge in ris-mods.
Ressource: ordi. Georg 19.11. hat das Ziel vorgegeben („Wie funktioniert es, wenn ich 2 Untersuchungen habe?“) und Go für Fix + Einspielen
gegeben, wenn alle Tests grün sind. **Live bis Fr 20.11. 06:30.**

**Zeitfenster:** EXE-Tausch nur Mo–Fr 20:10–06:30 (Sperre im Skript). Klicks am Büro-PC Mo–Fr 06:30–17:20 nie. Startet dieser Job an
einem Werktag nach 05:30: nichts halb einspielen, denselben Brief als `kaiscribe-mehrfach-seitenlos-n1-einspielen-f1` mit not-before
20:15 desselben Tages einreihen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

ZUERST LESEN: `BERICHT-MEHRFACH-SEITENLOS-N1.md` (Teil 1: Ursache, Änderung, Tests, Prüftext). Ablauf-Vorlage für Tausch/Abnahme:
`FOLGEJOB-KAISCRIBE-RELEASE-1118-EINSPIELEN.md` und `BERICHT-KAISCRIBE-RELEASE-1118-EINSPIELEN.md`.

## Was eingespielt wird
- **KaiScribe 3.19.14** (RaKScribe26 `bd8a4a1`), Release-Tag `3.19.14` (latest), Asset `rakscribe26.exe`, 56 868 662 Byte,
  **sha256 `3aec0b8d3cc5190e568468ee639f1c0d5af05a9a905b655a47671760dd17ca1f`**. Tests 44574396135, Build 44575168613 und Windows-UI-Test
  44575606706 (Stand siehe Bericht Teil 1) – Tor: alle drei grün.
- Auf X: liegt 3.19.13 (Job kaiscribe-release-1118-einspielen, 19.11. 03:51). Tausch 3.19.13 → 3.19.14. Liegt schon ein neueres grünes
  Release mit `bd8a4a1` (`git merge-base --is-ancestor bd8a4a1 <tag>`): das nehmen. Nie zurück auf ein älteres.
- ris-mods (Brücke, Formatierer, Abholer): **keine Änderung** – EOL schickt beide Befunde wie bisherige Mehrregionen-Befunde.

## Schritt 0 – Tore (nur lesen)
1. Release + Digest per API, Tests/Build/UI-Test für `bd8a4a1` grün.
2. Live-Stand: SHA/Version von `X:\RaKScribe\rakscribe26.exe`, letzte `[INIT]`-Zeilen in `X:\RaKScribe\rakscribe.log`.
3. Niemand arbeitet am Büro-PC (die eigene RDP-Sitzung des Macs zählt nicht).

## Schritt 1 – Tausch
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.14\rakscribe26.exe`,
  SHA prüfen, dann `-Schritt exe -Tag 3.19.14 -Sha 3aec0b8d…ca1f`. **NICHT** `-Schritt holen`.
- Beleg: `KS_TAUSCH=ok neu=… alt=…`, Sicherung `rakscribe26.exe.vor3.19.14-….alt`, Titel „KaiScribe 3.19.14 – Röntgen am Kai“.
- Rückweg: `-Schritt zurueck` (jüngste .alt = 3.19.13). Bei Rot: alte Version bleibt bzw. zurück, Grund in den Bericht.

## Schritt 2 – Abnahme am Testpatienten 451898 (nie vidieren)
- Testeintrag 451898 mit **zwei Leistungen: lws + bü** (Teststrecke KS, ris-mods `ordi-hermes/teststrecke/ks.py` bzw. `buero/kaiscribe.py diktat`).
  Geht das Anlegen zweier Leistungen nicht: KaiScribe mit einer cas_leistungen-Datei
  `[{"kurz":"lws","text":"LWS","vorlage":"lendenwirbelsäule_in_2_ebenen"},{"kurz":"bü","text":"Becken","vorlage":"beckenübersicht_stehend"}]`
  (ohne CAS-Schreiben) und das im Bericht klar sagen.
- **Diktat A (Georgs Nachtrag, ohne Regionsnennung):** „geringe Coxarthrose links, Osteochondrose L5/S1, Fibroostosen am Trochanter major
  beidseits, Spondylophyten L3 bis L5“.
  Erwartet: sofort nach INS **zwei Befunde untereinander** im Befundfenster: „## Beckenübersicht stehend“ (Coxarthrose links mit
  „(Arthrose Grad 2 nach Kellgren & Lawrence)“ + K&L-Tabellensatz Grad 2, Fibroostosen Trochanter) und „## Lendenwirbelsäule in 2 Ebenen“
  (Osteochondrose L5/S1, Spondylophyten L3–L5), je eigenes Ergebnis, keine Becken-Befunde im LWS-Text und umgekehrt, keine rote Prüfzeile.
- **Diktat B (Georgs Fall mit Überschriften):** „LWS in 2 Ebenen: Geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung.
  Geringe Spondylophyten L3 bis L5. Beckenübersicht: Geringgradige Coxarthrose links. Geringe Fibroostosen an der SIAS und am Trochanter
  major beidseits.“ → „Lendenwirbelsäule in 2 Ebenen“ + „Beckenübersicht stehend“.
- Optional (nur wenn die Teststrecke einen HIPPO-Baustein für 451898 einspeisen kann): HIPPO-Sätze + Schlusssatz „Weitere Winkelmessungen …“
  nur im Beckenbefund. Sonst im Bericht als offen nennen (kein echter Fall nötig).
- EOL: beide Befunde gehen an CAS (Bestätigung „✓ An CAS übergeben: … · Beckenübersicht stehend · Lendenwirbelsäule in 2 Ebenen“),
  Formatierer: zwei Titel fett/unterstrichen. Belegen (nur lesend): Lauf-Datei `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` (`vorlagen` mit
  beiden Keys). Danach stornieren wie in der Teststrecke üblich.

## Schritt 3 – Bericht
`docs/einspielen/ergebnis_mehrfach_seitenlos_n1_<datum>.md` (Tore, Stände vorher/nachher, Tausch, Abnahme-Wortlaut A/B, Rückweg), keine
Patientendaten. Meldung nach außen nur über den Queue-Abschluss und nur, wenn live belegt, z. B.: „KaiScribe 3.19.14: Zwei Untersuchungen in
einem Diktat (z. B. LWS + Becken) ergeben jetzt zwei eigene Befunde – auch ohne Regionsnennung, aktiv seit <Datum Uhrzeit>.“
