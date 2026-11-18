# Bericht kaiscribe-kl-tabelle-zurueck-n1 (Mi 18.11.2026) – K&L-Tabelle zurück, KOALA-Kniebefund, Regel-Register

**Stand: auf main als v3.19.11 (e26cc8c), CI „Tests“ grün, Web-Deploy (GitHub Pages) grün.** Die EXE habe ich nicht gebaut und
nicht verteilt; das übernimmt laut Georgs GO der Sammel-Release-Job kaiscribe-release-1118.

## Was jetzt gilt

1. **K&L-Tabelle wieder im Prompt** (`radiology_prompt.txt`, alle Gen-Calls EXE + Web, Marker `2026-11-18-kl-tabelle-koala`).
   Sobald ein Grad feststeht (diktierter Grad, diktierte Arthrose-Diagnose mit Adjektiv, IB-Lab-Grad), steht im Befundtext
   genau der Tabellensatz dieses Grades an Stelle des Gelenkspalt-Normalsatzes. Grad 4 mit Zystenbildung. Tabelle zusätzlich
   als `KL_TABELLE` in `befund_regeln.py` ≡ `befundRegeln.ts`.
   - Abweichung von 80a36ae^: **Grad 2** steht im Wortlaut der Skill-Tabelle und von Georgs Fixture Nr. 50 („Geringe
     Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer Randzuschärfung.“). Der alte Prompt hatte
     „Geringe Gelenksspaltverschmälerung mit beginnender Osteophytenbildung …“.
   - Adjektiv→Grad (beginnend 1, gering 2, mäßig/mittelgradig 3, hochgradig 4) bleibt; Peters Option a vom 12.11.
   - Beispiele wieder mit Tabellensatz und echtem Grad: Schulter mäßiggradige Omarthrose (Grad 3), Ellbogen geringe Arthrose +
     Extensorensehnenplatte (Grad 2), Knie „Mäßige Gonarthrose … medial betont (Arthrose Grad 3 nach Kellgren & Lawrence)“.
   - **RH 38 bleibt**: Wird nur „Gelenkspaltverschmälerung“ ohne Arthrose-Diagnose diktiert, kommt kein Grad und kein
     Tabellensatz. „Coxarthrose“ ohne Adjektiv bekommt keinen Grad.
   - Knie: femorotibial und femoropatellar je ein Satz und ein Ergebnispunkt. Das Kompartiment wird genannt, nie „betont“
     (außer es ist so diktiert). „Normale Form und Stellung …“ wird zu „Normale Stellung …“. Erguss-Satz am Ende. Eine von
     der KI gezeigte Pathologie gleicht die Vorlage genauso an wie eine diktierte.
   - Web-Prüfer (Regel 5/13): Der Tabellensatz bei feststehendem Grad zählt nicht als Zusatz. Ohne diese Änderung hätte der
     Web-Prüfer ihn gestrichen.
2. **IB Lab KOALA → Kniebefund** (EXE, `ibl_bausteine.py`), genau nach Georgs Nachtrag:
   - Bei KL 2–4 bekommt das Kompartiment mit dem engeren Gelenkspalt „Medial …“/„Lateral …“ + Tabellensatz, das andere
     „… normal weiter Gelenkspalt.“. „Die Gelenkflächen …“ fällt weg, „Normale Stellung …“.
   - Erster Ergebnispunkt „Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 nach Kellgren & Lawrence).“; das
     Normal-Ergebnis entfällt; beide Seiten gleich werden zusammengefasst.
   - Keine Messzeilen und keine mm-Werte. Der Abholer-Punkt „Mittelgradige Gonarthrose …“ wird nicht übernommen.
   - Kein Text bei KL 0/1, Alter < 18, Prothese (Vorlage/Überschrift/Diktat), seitlichem Bild oder diktierter Gonarthrose
     (das Diktat geht vor; bei anderem Grad kommt ein Prüf-Hinweis).
   - Mehrere a.p.-Bilder mit verschiedenen Graden ergeben eine ⚠-Prüfzeile und keinen Text.
   - Die Femoropatellararthrose (diktiert) schreibt die KI nach Prompt; KaiScribe bringt Reihenfolge und Form fest auf
     Georgs Wortlaut.
   - Eingesetzt wird **vor** den Wächtern (`pipeline._koala_frueh`). Das Gerüst vor dem Diktat ist die ganze Knie-Vorlage mit
     KOALA-Text, d. h. sofort EOL ergibt einen fertigen Befund.
3. **Wächter-Fixes (EXE ≡ Web)**, nötig, damit Georgs Wortlaut die echte Kette übersteht:
   - Die Widerspruchs-Wächter haben „Lateral normal weiter Gelenkspalt.“ zu „Im Übrigen Lateral …“ gemacht und Befundsätze
     umgestellt; jetzt gilt der Satz im Katalog als schon eingeschränkt.
   - Der Kortikalis-Satz bekam „Im Übrigen“, weil im Tabellensatz „Osteophyten“ steht; jetzt zählt der Tabellensatz als
     Arthrose (`kl_deskriptor_neutral`).
   - `kl_bereinigen` hätte bei Nr. 50 den Femoropatellar-Grad 3 auf den KOALA-Grad 2 gesetzt; jetzt gelten der IB-Lab-Grad
     und der Adjektiv-Grad einer Femoropatellararthrose nebeneinander.
   - `arthrose_bereinigen` lässt KOALA-Punkte stehen.
4. **Regel-Register** `tests/regel_register/regeln.json` (70 Regeln, 102 Prüfwörter in 6 Dateien) +
   `tests/offline/test_regel_register.py` (in CI).
   - Der Test wird rot, wenn ein freigegebener Wortlaut fehlt oder eine Pflicht-Regel aus dem Register verschwindet.
     Gegenprobe: Tabellensatz Grad 3 gestrichen → rot mit Meldung.
   - Wer einen Wortlaut ändert, muss das Register im selben Commit ändern. Achtung: Die Datei ist durch `*.json` in
     `.gitignore` verdeckt, also `git add -f`.

## Tests

- Offline: alle Gates aus `.github/workflows/test.yml` grün, auch Typprüfung und Lint (Hetzner, nach `npm ci`). Neu
  `test_ibl_koala_text.py`: Nr. 34 und Nr. 50 wortgleich, deterministisch und durch die ganze EXE-Kette mit KI-Attrappe,
  dazu jede Live-Abweichung als eigener Fall.
- Live über `tools/verify_konfabulation.py` mit Claude Sonnet 5.5 (= Produktionsmodell, Konto B; Google-Tests sind seit
  14.11. gesperrt), Kosten 3,00 $ von 5 $. Messnotiz: `docs/benchmarks/kl_tabelle_koala_2026-11-18.md`.
  - **RH 38: 20/20 grün** (dazu 9/9 weitere Läufe), nichts erfunden.
  - Schulter „mäßiggradige Omarthrose“ → Tabelle Grad 3: EXE 9/9, Web 9/9.
  - **KOALA Nr. 34 und Nr. 50 je 5/5 wortgleich** mit Georgs Fixture (Endstand nach den Fixes). KL 3 rechts: 19/19.
  - Erhalt- und RH-99-Fälle grün.
  - `diktat_kl` 7/8: Einmal hat die KI den Grad-2-Satz abgewandelt („Medial betonte Osteophytenbildung …“). Das ist kein
    Erfinden, aber nicht der wörtliche Tabellensatz.
  - `ibl_kl1` 3/5: bekannter Altfall (Kanban #261), nicht von hier.

## Prüfung der Skill-Regeln 1–13, 3a–3af (Nachtrag C, jede inhaltlich gegen den Prompt geprüft)

| Status | Regeln |
|---|---|
| **vorhanden** | 1, 3, 3a, 3b, 3c, 3d, 3e, 3f, 3g, 3h, 3i, 3k, 3l, 3m, 3n, 3r, 3s, 3t, 3u, 3v, 3w (eingeschränkt durch RH 38), 3x, 3aa, 3ab, 3ac, 3ad, 3af, 4, 5 (mit Peters Einzelpunkt-Ausnahme), 5a (Fehlhör-Liste), 5b (Rho-Baustein bei diktiertem „Rho“), 6, 7, 8, 10, 11, 12, 13 |
| **ergänzt** | 2 (Form + Stellung → „Normale Stellung …“), **3o**, **3p**, **3z** (Wortlaut Skill-Zeile 95), 3j („NICHT als Zwerchfellhochstand“ fehlte), 3y (Komma-Verschiebung 26 → 2,6 mm fehlte), 3ae (Lokalanästhetika, Carbostesin/Volon A, Ergebnis-Konvention fehlten – nur die Vorlage war da), 9 („Vergleich zur Voruntersuchung vom …:“ oben im Befundtext fehlte) |
| **unklar** | 3q: Der Teil „‚Wie bei‘ → ‚vereinbar mit‘“ widerspricht „IMMER ‚Bild wie bei [Diagnose]‘“. KaiScribe hat nur „Bild wie bei“; Georg muss entscheiden (Kanban #421). |

## Offen

- ris-mods (Kanban #420):
  - Der Formatierer (`bruecke/ibl_einfuegen`) setzt KOALA bei klassischem Diktat bzw. nachgereichtem Baustein noch als alte
    Messzeilen + „Mittelgradige Gonarthrose …“ ein.
  - Die Brücke liefert noch kein Patientenalter (Feld `alter`), deshalb greift „< 18 → kein Text“ in KaiScribe erst danach;
    unbekanntes Alter = Text kommt.
  - `regeln/koala.toml` schreibt „Mittelgradige“.
- Kein Browser-/Windows-Check von hier (Hetzner). Der Windows-UI-Test läuft mit dem Sammel-Release.

👉 Georg: Regel 3q entscheiden, bis 25.11. (Kanban #421)

Arbeitsdateien: `~/cj/work/kaiscribe-kl-tabelle-zurueck-n1/` (tests.sh, version.sh, register_bauen.py, Live-Rohdaten JSON).
