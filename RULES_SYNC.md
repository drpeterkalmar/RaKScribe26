# RULES_SYNC — Telegram-Befundregeln ↔ RaKScribe (Stand v3.2.0, 05.10.2026)

Quelle der Wahrheit: Hermes-Skill `radiology-shoulder-dictation` (SKILL.md + references/). Diese Tabelle zeigt für jede
Regel, **wo** sie in RaKScribe umgesetzt ist und **welcher Test** sie absichert.

## Seit v3.2: weniger Sync-Punkte

Ordner (Umbau 06.10.2026): Offline-Gates in `tests/offline/` (laufen in CI, `.github/workflows/test.yml`), Live-Harness mit Gemini/Google-Aufrufen (`verify_*`, `test_all_regions`, `diktat_suite`, `prod_pipeline` …) in `tools/`, Messergebnisse in `docs/benchmarks/`. Testnamen in den Tabellen unten beziehen sich auf diese Ordner.

| Baustein | Datei | gilt für |
|---|---|---|
| **Befund-Prompt (eine Quelle)** | `radiology_prompt.txt` (Versionsmarker `<!-- RAKSCRIBE_PROMPT_VERSION: … -->`) | EXE (gebündelt + versionierte Wahl), Web (`?raw`-Import, `PROMPT_VERSION` = Marker), Harness/verify (`tools/prod_pipeline.py`) |
| systemInstruction | `SYS_MSG` in `source_code/gemini.py` = `SYS_MSG` in `web_app/src/gemini.ts` (wortgleich, Test) | EXE + Web |
| Validator (nur Web, Call 2) | `validationPrompt` in `web_app/src/gemini.ts` (Snapshot `tests/offline/snapshots/val_prompt.txt`) | Web; Harness liest ihn aus gemini.ts |
| Deterministische Regeln | `source_code/befund_regeln.py` ≡ `web_app/src/befundRegeln.ts`, Fixtures `befund_regeln_fixtures.json` | EXE + Web |
| Normalbefund-Bypass | `source_code/normalbypass.py` ≡ `web_app/src/normalbypass.ts`, Fixtures `normal_bypass_tests.json` | EXE + Web |
| Fehlhör-Liste | `misheard_words.json` (+ `misheard_tests.json`) | EXE + Web |
| Vorlagen | `templates.json` (eine Datei, inkl. Feld `ergebnis`; Web importiert sie aus dem Root) | EXE + Web |
| Vorlagen-Erkennung | `source_code/detect.py` ≡ `web_app/src/detect.ts` + `vorlagen_vorrang.json`, Parität `detect_fixtures.json` | EXE + Web |
| Phrasenlisten STT | `phrases.json` (`medical_exe`, `medical_web`, `chirp`) | EXE + Web |
| Doppelte Hilfsfunktionen | `sync_fixtures.json` (stitch_overlaps ≡ stitchOverlaps, report_complete ≡ isCompleteReport) | EXE + Web |
| **Regel-Register (18.11.2026)** | `tests/regel_register/regeln.json` – jede freigegebene Regel mit Prüfwortlaut je Datei, Quelle, Datum, Status; Test `tests/offline/test_regel_register.py` (rot, wenn ein Wortlaut oder eine Pflicht-Regel fehlt). Wer einen Wortlaut ändert, ändert das Register im selben Commit. | EXE + Web |

Abkürzungen: **P** = `radiology_prompt.txt` (EXE + Web + Harness), **V** = Web-Validator, **D** = deterministisch (Code, beide Apps), **T** = Vorlage/Liste.

## Konventionen (SKILL.md)

| Regel | Umsetzung | Test |
|---|---|---|
| „Ergebnis“ statt „Beurteilung“ | P Formatregel 1, P Stilbeispiele | verify_georg (Few-Shot-Fall mit „Beurteilung“-Beispielen) |
| Ergebnis: EXAKT diktierte Begriffe (inkl. Grad, Messwert) | P „ERGEBNIS 1:1“, ❌/✅-Paar; V 10 + 11 | verify_georg („Mäßiggradige Tendinosis calcarea“ + „17 mm“), verify_k2k3 (K3) |
| Kanonische Überschrift mit Seite | P Überschrift-Regel (+ Schulter-Beispiel, Wirbelsäule ohne Seite); V 8; D `titel_mit_seite` (Bypass) | verify_georg, verify_knie, verify_sprunggelenk, befund_regeln_test |
| **v3.18.4 Nur Diktiertes (RH 38, Peter 12.11.2026):** krankhafte Einzelbefunde, Diagnosen, Grade/Scores, Messwerte nur aus Diktat oder IB-Lab-Block, nie aus dem Wortlaut („mäßige“ ≠ Grad 3, Gelenkspaltverschmälerung ≠ Gonarthrose); gepaarte Erhalt-Regel (alles Diktierte in Befund UND Ergebnis, Verhörer weiter zum Fachbegriff) | P Abschnitt „NUR DIKTIERTES“ + ❌/✅ RH 38; V 5; D `kl_bereinigen` ≡ `klBereinigen` (nicht gedeckter K&L-Grad weg bzw. auf den einzigen erlaubten) | verify_konfabulation (9 Fälle × 20), test_all_regions (RH 38, K&L diktiert, `--ibl` KOALA KL 1), befund_regeln_test (Fixtures `kl`) |
| K&L-Graduierung nur bei DIKTIERTER Arthrose-Diagnose oder aus IB Lab (KOALA, Seite beachten): diktierter Grad vor IB-Lab-Grad vor Grad zum diktierten Adjektiv (beginnend 1, gering 2, mäßig 3, hochgradig 4; v3.18.5, Nachtrag RH 99); Arthrose ohne Adjektiv ohne Grad; nie AC/ISG/Symphyse; Beispiele nur mit Platzhalter „Grad X“ | P K&L-Abschnitt (Format „(Arthrose Grad X nach Kellgren & Lawrence)“, Befundtext nur diktierte Merkmale bzw. „[Adjektiv] degenerative Veränderungen …“); V 5/11/13; `ibl_bausteine.prompt_block` (KOALA-Grad), `_kl_pruefen`; D `kl_adjektiv_grade` ≡ `klAdjektivGrade`, `kl_bereinigen` (Platzhalter X nie gedeckt) | verify_georg (Grad 3 Schulter, Grad 2 Ellbogen), verify_knie (Grad 3 + 2), verify_konfabulation (erhalt_*, rh99_koxa), test_ibl_bausteine (K&L), befund_regeln_test (`kl.adjektiv`) |
| **v3.18.5 Keine Arthrose ohne Diktat (Nachtrag RH 99, Peter 12.11.2026):** „Gelenkspaltverschmälerung“, „degenerative Veränderungen“ und IB-Lab-Messwerte (HIPPO: LCE/Tönnis/Sharp/CCD, Offsets, Beckenschiefstand, Beinlängendifferenz) sind keine Coxarthrose/Gonarthrose; ohne Arthrose-Wort im Diktat kein „Arthrose“ und kein „Kellgren“ | P „NUR DIKTIERTES“ + ❌/✅ Becken mit IB Lab; V 5; `ibl_bausteine.prompt_block` (Messwerte ≠ Arthrose); D `arthrose_bereinigen` ≡ `arthroseBereinigen` (positive Arthrose-Punkte im Ergebnis weg, Verhörer/Verneinung/IB-Lab/K&L-Klammer bleiben; an ihre Stelle tritt der diktierte degenerative Befund aus dem Katalog `arthrose`, sonst bliebe das Ergebnis leer – kaiscribe-konfab-regress-n1, RH 99 „Beginnende degenerative Veränderungen … Randanbauten“); v3.18.11 (Echttest 14.11.2026): Chirp-3-Marken „{Punkt}“/„{Komma}“ … werden vor dem wörtlichen Übernehmen zu Satzzeichen (D `stt_satzzeichen` ≡ `sttSatzzeichen`, auch für `kurzsaetze_sichern`) | verify_konfabulation (rh99_* × 20, auch ohne Wächter), test_all_regions `--ibl` (HIPPO RH 99), befund_regeln_test (Fixtures `arthrose`, `stt_satzzeichen`) |
| **v3.18.6 AC-Luxation (Peter 12.11.2026: „wenn ich eine Tossy-3-Luxation beschreibe, darf es nicht in der nächsten Zeile schreiben, dass das AC-Gelenk unauffällig ist“):** Tossy/Rockwood ≥ II = Fehlstellung; Normalsatz, der den diktierten Befund ausdrücklich verneint („keine Luxation“), wird gestrichen statt eingeschränkt; Befund-Lage AC-Gelenk verdrängt „Schulter“ (Humeruskopf-Satz bleibt) | D `vorlagen_vorrang.json` widersprueche: Struktur `ac`, `strukturen_vorrang`, Merkmal `luxation_verneint`, Kategorie `fehlstellung.streichen`; `_wid_vorrang` ≡ `widVorrang`, `widersprueche_bereinigen` ≡ `widersprucheBereinigen` (gestrichen); `_satz_aus_phrase` „wie bei“ → „Bild wie bei“ | befund_regeln_test (Fixtures `widerspruch.bereinigen` Tossy ×2, `befunde` Tossy III/I), widerspruch_matrix_test (unverändert 0 ✗) |
| **Schulter-Normalsatz mit Artikel (Georg 16.11.2026: „Der Humeruskopf. Bitte ändern“):** „Der Humeruskopf steht in regelrechter Artikulation.“ statt „Humeruskopf in regelrechter Artikulation.“; die alte Form (alte Briefe/Diktate) zählt in der Abschnittsprüfung weiter als Schulter-Vorlagensatz | T `templates.json` (Röntgen-Schulter; Scapula-Aufzählung unverändert), `taught_blocks.json`; P ❌/✅ Schulter-Arthrose + Marker 2026-11-16-humeruskopf-artikel; D `VORLAGEN_ALTFORMEN` in `befund_regeln.py` ≡ `befundRegeln.ts` (`_vorlagen_saetze` ≡ `vorlagenSaetze`) | befund_regeln_test (Fixtures `abschnitte` alte + neue Form, Tossy), test_pipeline_exe (Schulter-Normalbefund EXE + Web), verify_georg |
| **K&L-Tabelle zurück (Georg 18.11.2026, kaiscribe-kl-tabelle-zurueck-n1; 80a36ae hatte sie gestrichen):** steht ein Grad fest (diktiert / Adjektiv einer diktierten Arthrose-Diagnose / IB Lab), steht im Befundtext der Tabellensatz DIESES Grades (Grad 1–4, Grad 4 mit Zystenbildung; Grad 2 im Wortlaut der Skill-Tabelle); RH 38 bleibt (nur „Gelenkspaltverschmälerung“ → kein Grad, keine Tabelle). Knie: femorotibial/femoropatellar je Satz + Punkt, Kompartiment statt „betont“, „Normale Stellung …“, Erguss-Satz | P Abschnitt ARTHROSE (K&L-TABELLE) + Beispiele Schulter/Ellbogen/Knie mit Grad; V 5/13 (Tabellensatz ist kein Zusatz); D `KL_TABELLE` (`befund_regeln.py` ≡ `befundRegeln.ts`), `kl_deskriptor_neutral` (Tabellensatz zählt für die Widerspruchs-Wächter als Arthrose, nicht als Osteophyt/Zyste), Katalog `einschraenkung` („Lateral normal weiter Gelenkspalt.“ ist schon eingeschränkt), `kl_bereinigen` (IB-Lab-Grad + Adjektiv-Grad einer Femoropatellararthrose) | test_regel_register, befund_regeln_test (`kl.bereinigen` Nr. 50), verify_konfabulation (tabelle_schulter(_web), rh38_* 20×) |
| **IB Lab KOALA → Kniebefund (Georg 18.11.2026, GO):** KL 2–4 → Tabellensatz mit „Medial“/„Lateral“ (engerer Gelenkspalt), anderes Kompartiment „… normal weiter Gelenkspalt.“, „Gelenkflächen …“ weg, „Normale Stellung …“, Ergebnis zuerst „Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 nach Kellgren & Lawrence).“, beidseits zusammengefasst; kein Text bei KL 0/1, < 18 J., Prothese, seitlichem Bild, diktierter Gonarthrose; verschiedene Grade aus mehreren a.p.-Bildern → ⚠-Prüfzeile; keine Messzeilen, keine mm | D `ibl_bausteine` (`_koala_plan`, `_koala_befund`, `_koala_ergebnis`, Gerüst mit Knie-Vorlage), `pipeline._koala_frueh` (vor den Wächtern), Gen-Prompt `KOALA_PROMPT` | test_ibl_koala_text (Fixtures Nr. 34/50 wörtlich, ganze EXE-Kette), verify_konfabulation (koala_nr34/nr50/kl3_re) |
| **Skill-Regeln 3o/3p/3z (18.11.2026 ergänzt):** Dissoziation/Fehlstellung „Ansonsten …“, Terry-Thomas Stellungssatz weg; Hyperostosis „Ansonsten die Schädelkalotte …“, aplastischer Sinus frontalis; Duplex Halsgefäße Pathologie zuerst, dann „Ansonsten kommen die A. carotis …“; dazu 3j (nicht als Zwerchfellhochstand), 3y (Komma-Verschiebung), 3ae (Blockade), 9 (Vergleich oben) | P Konflikt-Regeln / Schreibkonventionen | test_regel_register |
| Modalität aus Diktat (Gelenk allein = Röntgen) | detect_template (EXE + Web) | test_normalbefunde TEIL 2 (EXE + Web) |
| Ultraschall = „Sonographie“, Schulter-Sono-Überschrift | P Schreibkonventionen; Templates | diktat_suite |
| „Nonrezent“, Mid-Portion-Tendinose/Enthesiopathie, transmural ≠ komplett | P Schreibkonventionen | — (Prompt-Regel) |
| ~~Osteophyten-Grad passt zum K&L-Grad~~ (v3.18.4: Osteophyten nur, wenn diktiert) | P Abschnitt „NUR DIKTIERTES“ | verify_konfabulation |
| RA/SpA-Formulierungen (3f/3g) | P Ergebnis-Regeln | — |
| Fußfehlstellung mit Schrägstrich | P Konflikt-Regeln | — |

## Widerspruchs-Checkliste

| Pathologie | Umsetzung | Test |
|---|---|---|
| Osteochondrose/Diskopathie, Spondylose, Unkovertebral-, Facettenarthrose, Listhese, Skoliose, Streckhaltung | P Konflikt-Regeln; V 3 | test_all_regions (HWS/LWS-Fälle), verify_flachprofil, verify_k2k3 |
| Fraktur (ohne Adjektiv-Graduierung, „Ansonsten …“) | P Konflikt-Regeln + ❌/✅ | test_all_regions (Fraktur-Fälle) |
| Arthrose (Gelenk) → K&L-Deskriptor statt Normalsätze, „Normale Form …“ weg | P Konflikt-Regeln + ❌/✅ (Schulter, Ellbogen) | verify_georg, verify_knie |
| Kalk/Tendinosis calcarea → Normalsatz „Keine Kalzifikationen …“ an derselben Stelle ersetzen | P Konflikt-Regeln + ❌/✅ | verify_georg („Keine Kalzifikationen“ ersetzt) |
| Syndesmose (Messwert bleibt im Befund!) | P Konflikt-Regel + ERHALT-REGEL Messwerte | verify_sprunggelenk |
| Kardiomegalie, Atelektase/Pneumonie, Pleuraerguss, Pneumothorax, Hilus/Mediastinum | P Konflikt-Regeln (Thorax) + ❌/✅ Kardiomegalie | verify_peter_ergebnis (Kardiomegalie) |
| Pneumoperitoneum, Obstruktion, Colitis, Aerobilie, Konkremente | P Konflikt-Regeln (Abdomen) | — |
| Umschriebene Skelettbefunde (v3.15.5: Fibroostose/Enthesiopathie/Sporn, Exostose, Osteophyt, Arthrose inkl. AC/ISG/Finger/Zehen/Kiefer, Spondylose, Spondylarthrose, Osteochondrose, Unkovertebralarthrose, Baastrup, DISH, Verkalkung, Chondrokalzinose, Os accessorium, Enostose, Zyste, alte Fraktur, Fehlstellung, Osteopenie, Skoliose, Sklerose) → widersprechende Normalsätze nur im betroffenen Teil einschränken („Im Übrigen …“), Ergebnis nennt den Befund | T Katalog `widersprueche` in `vorlagen_vorrang.json` (Kategorien, Normalsatz-Merkmale, Strukturgruppen); P Konflikt-Regel + ❌/✅ (Calcaneus, Hüfte) + Block `<widersprueche>` an `{examples}`; V 3; D `widersprueche_bereinigen` ≡ `widersprucheBereinigen` nach der KI | widerspruch_matrix_test (alle Skelett-Vorlagen + Bausteine × Kategorien, Gegenproben, EXE = Web → `docs/widerspruch_matrix.md`), befund_regeln_test (Fixtures `widerspruch`) |

## Diktat-Verarbeitungsregeln

| Nr. | Regel | Umsetzung | Test |
|---|---|---|---|
| 1, 3ad | Normalbefund = vollständiges Gerüst, kein eigener Standardtext | P Befund-Abschnitt; V 9 + 13 | verify_georg (Template-Sätze erhalten), verify_k2k3 (K2) |
| 2, 3 | Arthrose: „Normale Form …“ anpassen, Unzutreffendes streichen | P Konflikt-Regeln | verify_georg, verify_knie |
| 3a, 3c, 3d, 3e | Fraktur-Formulierungen, „Ansonsten …“ | P Konflikt-Regeln / Befund-Abschnitt | test_all_regions |
| 3b | Seite in die Überschrift | P; D `titel_mit_seite` (Bypass) | verify_georg, verify_peter (Knie), befund_regeln_test |
| 3g | Diktatkorrektur: nur korrigiertes Wort | P Steuerbefehle | — |
| 3h–3p, 3r, 3y, 3aa, 3af | MCP/MTP, Stauung Grad, Pleuraerguss-Höhe, loco tipico, NOF, Aerobilie, JJ-Katheter, P.M., Plaque-Tiefe, IMT, TVT | P Schreibkonventionen | — |
| 3q, 3af | „vereinbar/kompatibel mit“ → „Bild wie bei“; „Verdacht auf“ bleibt | P Ergebnis-Regeln; V 10; Web `restoreBildWieBei` | verify_k2k3, verify_sprunggelenk |
| 3s–3v | Wirbelsäulen-Reihenfolge, Zusammenfassen, Cobb < 10° | P Konflikt-Regeln | test_all_regions (HWS/LWS) |
| 3w | Diagnose → Deskriptor im Befund | P Konsistenz 4 + Grundregel | test_all_regions |
| **3x** | Steuerbefehle „Punkt“, „neue Zeile“, „also“, „Visa“ | P Steuerbefehle; misheard (Visa); D Trenner nutzt „Punkt“/„neue Zeile“ als Grenzen | verify_georg, befund_regeln_test |
| 3ab, 3ac | Nervensono-Überschrift, CSA nur wenn diktiert | P Ergebnis-Regeln / Schreibkonventionen | verify_k2k3 |
| 3ae | Blockade-Standardtext | Template `ultraschall_gezielte_blockade` | test_normalbefunde |
| 4, 7 | Pathologie an Stelle des Normalsatzes, kein neuer Absatz | P Befund-Abschnitt | verify_georg |
| **5** | **Ergebnis nummeriert** | P Ergebnis-Abschnitt + ❌/✅; V 11; **D `ergebnis_nummerieren`** (einzelner Normalsatz unnummeriert) | befund_regeln_test, verify_georg (auch mit alter v4-Datei + alten Beispielen) |
| 6 | Weichteil-Satz ans Ende | P Befund-Abschnitt; V 12 + 15 | verify_georg (Weichteilmantel) |
| 8 | Römische Zahlen | P Schreibkonventionen | — |
| 9 | Voruntersuchungsvergleich unnummeriert | P; D (Zeile „Vergleich zur Voruntersuchung …“ bleibt unnummeriert) | befund_regeln_test |
| 10 | Zusammengehöriges = ein Punkt („als indirekter Hinweis für …“) | P „ZUSAMMENGEHÖRIG“; V 11 | verify_georg (Extensorensehnen) |
| 11 | kein „unauffällig“ im Ergebnis außer Normalbefund | P Ergebnis-Abschnitt | — |
| **12** | Ellbogen-Kompartimente „Ansonsten die artikulierenden Gelenkflächen …“ | P Konflikt-Regeln + ❌/✅; V 13 | verify_georg |
| **13** | Ellbogen-Tendinose: lateral = Extensoren, medial = Flexoren | P Konflikt-Regeln | verify_georg |
| — | Fließtext statt „Label:“ | P Formatregel 3 + ❌/✅; V 12; T 8 Röntgen-Vorlagen auf Fließtext umgestellt (Ellbogen, Oberarm, Unterarm, Hand, Handgelenk, AC-Gelenk, Oberschenkel, Mittelfuß) | verify_georg (keine Labels) |
| — | Mehrere Regionen in einem Diktat | **D `split_regionen`** (Region + Seite nach Satz-/Befehlsgrenze) + P Formatregel 4 (Fallback) | befund_regeln_test (18 Trenner-Fälle), verify_georg |

## Peters Nachtrag (05.10.2026)

| Regel | Umsetzung | Test |
|---|---|---|
| Ergebnis NIE das Diktat abschreiben | Bypass: D `ergebnis_mit_seite(template.ergebnis)`; LLM: P Ergebnis-Abschnitt + `<normal_ergebnis>`-Block + ❌/✅; V 14 | normal_bypass_test, test_normalbefunde TEIL 3, diktat_suite, verify_peter_ergebnis |
| Bypass nur bei reinem Normalbefund | D `is_pure_normal_finding` (EXE + Web, auch ETA-Schätzung) | normal_bypass_test (31 Fälle, PY + TS) |
| Normal-Ergebnis je Untersuchung | T Feld `ergebnis` (140/142 Vorlagen; 44 aus dem Skill, Rest Praxis-Konvention) | normal_bypass_test |
| Lungenröntgen ≠ Skelett | detect_template: „torax“, „lunge(n)“, „pulmo“, „brustkorb“ (+ Hemithorax vor Thorax); misheard „Torax“→„Thorax“; neutrale `allgemein`-Vorlage + P „REGION NICHT ERKANNT“ | test_normalbefunde TEIL 2 (EXE + Web), verify_peter_ergebnis |

## EXE-only-Quellen (Georgs „anderer Standardtext / nicht nummeriert“)

| Quelle | v3.2-Absicherung | Test |
|---|---|---|
| alte `radiology_prompt_v4.txt` / im Prompt-Editor gespeicherter Alt-Prompt neben der EXE | D `waehle_prompt`: lokale Datei nur, wenn ihr Versionsmarker ≥ eingebautem; sonst eingebauter Prompt + Hinweis-Dialog | befund_regeln_test (4 Fälle), verify_georg (Fall V4), Windows-UI-Test C |
| `practice_reports.db`-Few-Shots | Standard AUS (`RAG_BEISPIELE = 0` in config.ini, einschaltbar); P „STILBEISPIELE nur Wortwahl“; D Nummerierung | verify_georg (Fall FS + `--ab`) |
| `is_normal_finding` ohne Pathologie-Prüfung | ersetzt durch `is_pure_normal_finding` | normal_bypass_test |
| eigene `sys_msg` | `SYS_MSG` = Web-`SYS_MSG` | befund_regeln_test (SYNC) |
| Web-Mock-RAG (3 Spielzeug-Befunde) | entfernt | befund_regeln_test (kein zweiter Prompt) |
