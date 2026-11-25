# KaiScribe-Übungsmodus (kaiscribe-uebung-n1, 25.11.2026)

Georg 24./25.11.: „Man spiegelt einen Tag … nichts wird irgendwo hin geschickt.“ Peter 25.11.: „1a mit Senf, 2 rg und kp,
auch von zuhause mit der Web-App.“

## Ablauf

1. **Spiegel** (`spiegel.py`, VM, rakauto, nur SELECT): ein vergangener Tag → `C:\RaK\kaiscribe_uebung\daten\<JJJJMMTT>\`
   `anonym.json` (Pseudonym RH<Tageslisten-Nr.>, Alter, Geschlecht, CAS-Leistung, IB Lab, Senf, Vorbefund/Lösung maskiert)
   und `haus.json` (wie CAS; nur für einen ausdrücklich eingeschalteten LAN-Zugang, Standard aus).
2. **Übungsdienst** (`uebung_dienst.py`, VM, Aufgabe `\RaK\RaK KaiScribe Uebung`): liefert die Web-App + `/api/…` auf
   127.0.0.1:18555, im Tailnet über `tailscale serve` als **https://dexa.taild969f0.ts.net:8555/?uebung**.
   Anmeldung je Kürzel (kp/rg, Kennwörter in Vaultwarden „KaiScribe-Übung kp|rg“), über Tailscale immer „anonym“.
3. **Web-App** (`web_app/src/uebung.ts`): roter Dauerbalken, Fallliste links, Fallkarte (Leistung, Alter, IB Lab, Senf,
   Vorbefund), Diktat wie live (Browser-Mikro/Headset/SpeechMike, F10, Befund aus Text), **EOL/F12 = Abgabe** statt
   Kopieren. Danach „Lösung zeigen“ (echter vidierter Befund, maskiert, Unterschiede markiert) und „Word“.
4. **Ablage**: `X:\KaiScribe-Übung\<JJJJMMTT>\<kürzel>\<RH>_<kürzel>.docx` (CAS-Befundlayout, QR-Platzhalter) +
   `.html` (Vergleich, Diktat). Weitere Versuche `_2`, `_3`. Korrekturen im Word → Hermes liest sie später als
   Sammelliste-Kandidaten.

## Harte Sperre (Code, keine Einstellung)

- Web: `sperreEinrichten()` vor dem ersten Render – Zwischenablage, sendBeacon, WebSocket, window.open und jedes
  fetch/XHR-Ziel außer STT/Befund-KI/Drive-Schlüssel/Übungsdienst werden abgefangen und gezählt (`uebung_test.mjs`).
- Dienst: keine ausgehende Verbindung, kein Unterprozess, kein CAS/Brücke/Roboter/Plaza/ELGA/SpeechMagic-Import
  (`tests/offline/test_uebung.py`, 0 Aufrufe abgefangen). Der Spiegel lässt nur `SET TRANSACTION READ ONLY` + SELECT +
  ROLLBACK zu.
- STT-Deckel der Übung: 60 min/Tag je Kürzel (Aufnahme ×2 gebucht: Live-Anzeige + chirp_3), an Ordi-Tagen vor 17:00
  zusammen höchstens 20 min. Das Live-Kontingent der Ordi bleibt unberührt.

## Bedienung (Mac)

```
python3 tools/uebung/vm_uebung.py lage|beleg|start|aus
python3 tools/uebung/vm_uebung.py einspielen [--konten]      # Web bauen, Paket hoch, Aufgabe + serve
python3 tools/uebung/vm_uebung.py spiegeln 20261123          # Tag spiegeln (CAS nur lesen)
/usr/bin/python3 tools/uebung/e2e_uebung_web.py --probe      # Browser-Probe lokal, ohne Geld
```
Rückweg: `vm_uebung.py aus` (Aufgabe aus, `tailscale serve --https=8555 off`). Live-Betrieb (EXE, Brücke, Roboter) ist
nicht berührt.
