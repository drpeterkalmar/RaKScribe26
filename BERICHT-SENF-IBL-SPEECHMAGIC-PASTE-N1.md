# Bericht senf-ibl-speechmagic-paste-n1 – Senf + auffällige IB-Lab-Sätze automatisch ins SpeechMagic-Fenster (nur kp), Sa 21.11.2026

- **Live seit 22:37 (KaiScribe 3.22.3 auf X:, Freigabe `X:\KaiScribe\Bruecke\speechmagic_einfuegen_an.txt` liegt):** Öffnet kp ein
  SpeechMagic-Diktat, hängt KaiScribe die auffälligen IB-Lab-Sätze (wörtlich wie im KaiScribe-Befund) und den Senf ans Ende
  an. Der Senf steht befundtauglich da (ohne „RH xx · Untersuchung ·“), davor nur die Marke `[SENF]`. Bei unauffälligem Ergebnis
  steht nur `[SENF] unauffällig` da. Der Cursor bleibt, wo er war, die Zwischenablage kommt zurück, jeder Text höchstens einmal je Diktatnummer.
- **So sieht Peter es:** Die Zeilen stehen unter seinem Diktat. **Übernehmen = Strg+Alt+S**: Die Taste entfernt nur die `[SENF]`-Marken, danach
  ergänzt er frei. Schließt er das Diktat mit stehender Marke, kommt ein rotes KaiScribe-Fenster „SENF-Zeile noch im Diktat“.
  Grund ist nur die Marke, nie der Inhalt.
- **Beleg 451898 (Büro-PC, nie vidiert, alles storniert):** L1 Nr 035: 3 Zeilen eingefügt, kein „RH 0“, Zwischenablage gleich, Warnfenster
  beim Fertigstellen. L2 Nr 037/038 bei schon laufendem SpeechMagic: eingefügt, Diktattext davor unverändert, Warnung. L3 Nr 039: Übernehmen
  hat genau 1 Marke entfernt, der Text blieb sonst gleich, keine Warnung. 0 Fehler im Log. Belege liegen in `~/cj/work/senf-ibl-speechmagic-paste-n1/`.
- **Unterwegs behoben:** L1 zeigte, dass ein schon laufendes SpeechMagic das nächste Diktat übernimmt und der Startprozess mit der neuen Nummer
  nach weniger als 0,5 s weg ist. 3.22.2 prüft deshalb alle 50 ms die Prozessliste. Taste und Marken-Format kamen mit Peters Nachtrag (3.22.1).
- **Schalter:** `SM_SENF` / `SM_IBL` in config.ini (Standard kp, `aus` = niemand), `SM_UEBERNEHMEN_TASTE` (Standard ctrl+alt+s).
  Zentral wirkt es nur mit der Freigabe-Datei. Notaus: `speechmagic_einfuegen_aus.txt` daneben anlegen oder die Freigabe löschen (wirkt in ≤ 30 s).
  rg und alle anderen Kürzel: unverändert, nichts davon.
- **Code/Tests:** `source_code/sm_einfuegen.py`, `tests/offline/test_sm_einfuegen.py` (76 Prüfungen), ganze Offline-Reihe grün,
  Windows-UI-Test (Wächter läuft) 3.22.0–3.22.3 grün. Probe-Skript `tools/sm_probe.ps1`.
- **Offen:** (1) Strg+Alt+S mit echter Tastatur ist noch nicht belegt. Künstlich gesendete Tasten erreichen den Tasten-Hook nicht; belegt ist
  derselbe Ablauf über die Auslöser-Datei. (2) Das Warten während einer echten Aufnahme ist nicht live belegt (am Testplatz gab es keinen Ton).
  Die Windows-Mikrofonanzeige hat dort einen CASSpeechMagic-Eintrag. (3) Die Prüfung auf der Vidierliste bzw. im Brief fehlt noch: Heute warnt
  KaiScribe beim Schließen und merkt sich `senf_offen` → Karte #470. (4) Kontrolle des ersten echten kp-Falls Mo 23.11. → Karte #471.
  (5) Eine freie SpeechMike-Taste kann Peter in SpeechControl auf Strg+Alt+S legen; nicht eingerichtet. Für den Notaus gibt es noch keine Doppelklick-.cmd.
