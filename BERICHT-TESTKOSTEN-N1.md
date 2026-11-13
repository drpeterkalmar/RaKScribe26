# kaiscribe-testkosten-n1 – Google-Kosten der KaiScribe-Tests gedeckelt (13.11.2026)

- **Umgestellt:** Alle Live-Testskripte (Harness, verify_*, test_diff/test_pipeline, model_ab, diktat_*, STT-Messskripte)
  laufen nur noch über `tools/testkosten.py` im neuen GCP-Projekt **rakscribe-test** (Nr. 396993744763, Dienstkonto
  kaiscribe-test-sa, Schlüssel in `~/.hermes/secrets` + `~/cj/secrets` + Vaultwarden). Kein Praxis-Schlüssel und kein
  `vertex-sa-key.json` mehr in Tests (Offline-Gate `tests/offline/test_testkosten.py` wacht). Produktion unverändert.
- **Deckel:** Kostenbuch je Job (`~/cj/work/testkosten/<job>.jsonl`), Grenze 5 $/Job und 15 $/Tag → Abbruch Exit 7.
  Wiederholungen ≤ 5, 20 nur mit `--release`. `tools/testlauf.py` startet Live nur nach grünen Offline-Gates.
  Google bietet für Gemini keine Anfragen-pro-Tag-Quote (nur 60/Minute gesetzt); Speech 18.000 s Audio/Tag; Budget 20 €/Monat (nur Alarm).
- **Cache:** Fester Gen-Prompt als Vertex-Kontext-Cache (eu geht): Gen-Aufruf 0,023 $ → 0,006 $, Befunde 8/8 wortgleich.
- **Gutachter:** `testkosten.sonnet()` (Sonnet 5.5, KaiFormat-Schlüssel) live getestet; Gemini Pro/Carbon im Modul gesperrt.
  Im Repo nutzte kein Skript Carbon/3.1 Pro – diese Aufrufe kamen aus Agenten-Ad-hoc-Läufen, nicht aus tools/.
- **Gemessen, kompletter Testlauf:** vorher (20 Wdh., ohne Cache, hochgerechnet) ≈ 2.230 Aufrufe ≈ 34 $; 12.11. real 3.913 Aufrufe ≈ 74 $.
  Nachher normal 431 Aufrufe = 2,46 $ (gemessen), `--release` ≈ 967 Aufrufe ≈ 5,5 $ (Grenze dann 8 $).
- **Offen:** verify_konfabulation ibl_kl1 + rh99_degen2 0/5 rot, auch ohne Cache → Befund-Thema seit 3.18.6+, Kanban #261.
  Peter muss nichts tun.
