# Teil 2 zu kaiscribe-kosten-je-befund-n1: KaiScribe 3.29.2 einspielen + Abnahme an 451898 (Prompt-Cache greift)

Code: GitHub-Release **3.29.2** (main a36474d, enthält alles bis dahin, auch 3.28.3 DEXA-doppelt und 3.29.0 Übungsmodus).
Bericht: `docs/benchmarks/BERICHT-kosten-n1.md`. Kurz: Die EXE bündelte `radiology_prompt.txt` mit CRLF, darum war der
Prompt-Cache im Betrieb nie aktiv. Ein Befund kostete 6–7 ct statt ≈ 1,4 ct. 3.29.2 stellt den Prompt beim Laden auf LF.
Neu im Protokoll: Die Zeile `[KI] gen: Anbieter=anthropic claude-sonnet-5-5 maskiert (… s, n Platzhalter, Cache treffer|neu|ohne)`.
Im Nutzungszähler/Tagesbericht gibt es die neue Zeile „Claude-Token heute … Cache-Treffer a, neu b, ohne c …“.

Regeln: Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am Wochenende, nie in der Ordi-Zeit. 451898 nie vidieren,
alles stornieren. Nie in die CAS-DB schreiben. Keine Patientendaten nach außen. In Bericht und Commits nur RH-Nummern bzw.
Zahlen. Georg unverändert, Maskierung unangetastet. Kein Gemini, kein anderes Modell. Meldungsruhe gilt (nur jobnote/Kanban).
Läuft am selben Abend schon ein anderer KaiScribe-Tausch (z. B. `kaiscribe-dexa-doppelt-rh60-n1-einspielen` mit 3.28.3):
nur einmal tauschen, und zwar mit der neuesten Version (3.29.2 oder neuer). Nie auf eine ältere Version zurücktauschen,
außer als Rollback.

## A. Einspielen
1. Build Windows EXE und Windows UI-Test (EXE) für a36474d müssen grün sein (Release 3.29.2, Asset-SHA aus der API, `digest`;
   beim Bau: sha256 `a32c0f731bd33760975209aa041cece75a390de762d3a27d5c9b6abc1bf6543c`, 56.795.191 B).
2. Tausch wie bisher (Erinnerung release-vom-hetzner): Der Ordi-Hermes lädt das Asset von GitHub und prüft die SHA, dann
   `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.29.2 -Sha <sha>`. Die alte EXE bleibt als `.alt` für den Rollback
   (`-Schritt zurueck`). Laufende Prozesse nicht abschießen. 20 min Ruhe nach der letzten Ablage abwarten.
   Erst die Abnahme (B) mit der KaiScribe-Kopie machen, dann tauschen. Ist B rot: nicht tauschen bzw. Rollback.

## B. Abnahme an 451898 (echter Lauf, außerhalb der Ordi-Zeit)
Werkzeug wie `tools/buero/rho_osteopen_abnahme.py` (ris-mods `e2e/diktat_e2e.py`: KaiScribe-KOPIE 3.29.2 als Gast,
echter CAS-Auftrag 451898, Diktat per `text_ins`, echte KI über Konto A, EOL → `<Nr>.rakscribe.txt`).
1. **Zwei Diktate direkt nacheinander** (≤ 5 min Abstand), z. B. „Lendenwirbelsäule in zwei Ebenen. Geringe Osteochondrose
   L5/S1.“ und „Kniegelenk rechts in zwei Ebenen. Mäßiggradige Gonarthrose medial.“
   Erwartet in `rakscribe.log` (nur diese Statuszeilen lesen): Diktat 1 `Cache neu` oder `Cache treffer`, Diktat 2
   **`Cache treffer`**. Bei `Cache ohne` ist die Abnahme ROT: nicht tauschen, Ursache suchen (Prompt-Quelle in der `[INIT]`-Zeile,
   lokale radiology_prompt*.txt neben der Kopie).
2. Der Befund ist vollständig (Titel/Befund/Ergebnis, Pathologie da) und genau einmal abgelegt. Danach stornieren, nie vidieren.
3. Kosten: Laut Zähler der Kopie (falls im Selbsttest aus: aus den usage-Zahlen der Logzeile bzw. dem Tagesbericht) kostet
   Diktat 2 ≈ 1–2 ct (vorher ≈ 6,7 ct).

## C. Beleg im Betrieb (am nächsten Ordi-Tag nach dem Tausch, z. B. als Kontrolle ab 17:30)
`python3 tools/vm/x_lauf_hetzner.py 'C:\RaK\einrichtung\frogdiag\kaiscribe_nutzung_lesen.py' --tage <Tag>` (vorher den
neuen Leser per scp hochladen). Erwartet je PC mit 3.29.2: `cache_treffer` ≫ `cache_neu`, **`cache_ohne=0`**, `usd/anthropic`
≈ 1,5–2 ct. Ergebnis als Nachtrag in `docs/benchmarks/BERICHT-kosten-n1.md` („Betrieb nach dem Fix“), mit neuer Hochrechnung
für 3.000 Befunde/Monat gegen 200 $.

## Meldung an Peter (macht die Queue, kurz, deutsch)
Ursache: Der Zwischenspeicher für die langen KaiScribe-Regeln war wegen Windows-Zeilenenden nie aktiv. Je Befund kostete das
≈ 6–7 ct statt ≈ 1,4 ct. Hochrechnung: bisher ≈ 180–200 $/Monat, jetzt ≈ 50 $/Monat bei 3.000 Befunden (Guthaben 200 $).
