# kaiscribe-testkosten-n2-kaitest – Anthropic-Testaufrufe auf Konto B (13.11.2026)

- **Umgestellt:** `tools/testkosten.py` holt den Anthropic-Schlüssel nur noch aus Vaultwarden „Anthropic API KaiTest (Konto B)“
  (oder `KAISCRIBE_GUTACHTER_KEY`). Alle Anthropic-Aufrufe der Tests laufen darüber: Gutachter (`sonnet()`), Modell-Weiche
  (`KAISCRIBE_TEST_ROUTE=…claude…`), `tools/modellvergleich.py`. Andere Testskripte rufen Anthropic nicht direkt auf.
- **Probe:** `testkosten.sonnet_roh("Antworte nur mit OK.")` über KaiTest → „OK“ (claude-sonnet-5-5), gebucht als `anthropic-b`.
- **Kostenbuch:** jede Zeile hat jetzt `konto` (`anthropic-b`, `gcp-test`; Altzeilen ohne Feld = Konto A). Harte Grenze
  Konto B 150 $ je Kalendermonat über alle Jobs (Exit 7, per `KAISCRIBE_TEST_KONTO_B_MONAT_USD` nur senkbar); 5 $/Job und
  15 $/Tag bleiben. `python3 tools/testkosten.py <job>` zeigt die Summen je Konto und den Monatsstand Konto B.
- **Wächter:** `tests/offline/test_testkosten.py` schlägt an, wenn ein Skript unter `tools/`, `tests/` oder im Repo-Wurzelordner
  den KaiFormat-Eintrag, `ANTHROPIC_API_KEY` oder `KAIFORMAT_*KEY` liest oder Anthropic an testkosten vorbei aufruft.
- **Andere Repos (nur gelesen):** ris-mods, KaiMail/kaimail, online-termin (Ordimail) – kein Testskript ruft Anthropic auf,
  nichts umzustellen. Produktion unverändert.
- **Skill:** rakscribe26-pipeline (Verification, `gcp-kosten-budget.md`, `gcp-kosten-und-budgetalarm.md`) mit der Regel
  „Tests = Konto B / KaiTest, Betrieb = Konto A / KaiFormat“.
