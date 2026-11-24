# BERICHT kaiscribe-ursula-2011-text-n1 – Ursulas Durchsicht der KaiScribe-Briefe (Text/Struktur)

Di 24.11.2026 03:24–04:00, Hetzner, **Teil 1** (Bau + Offline-Tests, ohne VM/Büro-PC laut Queue-Nachtrag 18:04).
Vorbericht `kaiscribe-sammel-2311` gelesen (3.24.1 live, kein Konflikt). Keine Patiententexte, nur RH-Nr./Abschnitte.

**Wichtig vorab:** Am 20.11. lief noch KaiScribe 3.19.15/3.19.16. Seit 3.20.0 (21.11.) sind mehrere von Ursulas
Punkten durch Georgs Regeln schon gelöst (Rho-Titel, Zehennummer, nicht diktierte CAS-Teile). Die Ursachen unten sind am
**heutigen Code** mit nachgebauten Diktaten belegt (`~/cj/work/kaiscribe-ursula-2011-text-n1/probe.py`). Der Abgleich mit den
echten Läufen (Lauf-JSON/Log der VM) steht als Teil A im Folgeauftrag (`FOLGEJOB-KAISCRIBE-URSULA-2011-TEXT-N1-EINSPIELEN.md`).

## Version
Ein Paket: **KaiScribe 3.25.0** (Version wird beim Zusammenführen gesetzt, siehe Commit „v3.25.0: Ursulas Durchsicht …“ auf
main). Nicht eingespielt: Einspielen + Abnahme 451898 laufen gebündelt im wartenden KaiScribe-Einspielauftrag
(`sm-senf-laenge-n1-einspielen`, Nachtrag).

## Je Punkt
| # | RH | Stand | Ursache / Beleg | Regel (Register) |
|---|----|-------|-----------------|------------------|
| 1 | 31, 119 | **erledigt (KaiScribe-Teil)** | Eine „## …“-Zeile im Ergebnis (KI) blieb Überschrift → Formatierer machte sie fett+unterstrichen; heute auch doppelt (Prüfung setzte das Ergebnis zusätzlich). Jetzt: Satz/„1. …“ mit „## “ im Ergebnis → Text, „## Ergebnis: Text“ → Kopf + Text; Titel mit folgendem „## Befund“ bleibt. Der echte RH-31-Brief vom 23.11. (Schwesterjob-Messung) hat Titel fett+unterstr., „Ergebnis:“ nur fett – ok. | `ursula-ergebnis-kein-titel` |
| 2 | 49 | **schon erledigt (3.20.0/3.22.x)** | RH 49 lief mit 3.19.15 (Rho im Hüft-Teil). Heute eigener Teil „Opportunistisches Knochendichtescreening (KI)“, ein Punkt ohne Nummer, Haupt-Ergebnis ab 2 Punkten 1., 2. Wortlaut bleibt der des Registers (nicht „…messung“). Test `test_ursula_2011.py` Punkt 2. | `rho-titel-nummer` |
| 3 | 41 | **erledigt** | „trochanter(e)“ als Adjektiv → „trochantär(e)“ nach der KI (auch per-/inter-/sub-/peri-). Gegenprobe: „Trochanter major“, „Bursitis trochanterica“, „Trochanterregion“ bleiben. Ob STT oder KI: Teil A. | `ursula-schreibweisen` |
| 4a | 44/92/106 | **erledigt** | Ursache im Code: der Widerspruchs-Wächter schränkt JEDEN widersprechenden Normalsatz einzeln mit „Im Übrigen …“ ein → 3× hintereinander. Jetzt: nur der erste einer Folge behält es (Vorlagensatz zurück); nach einer neuen Pathologie bleibt es (Kortikalis-Satz hinter Fraktur). | `ursula-im-uebrigen-folge` |
| 4b | 44/92/106 | **erledigt** | Zahl + „-prozentig“ → „%ig“ (50%iger, 30%iger, 12,5%igen); „50 %“ bleibt. | `ursula-prozent` |
| 4c | 44/92/106 | **erledigt** | Titel kam mit Seite aus der KI (Diktat „beidseits“). Wirbelsäulen-Titel jetzt nie mit Seite; im Befundsatz bleibt die diktierte Seite; „LWS sowie Hüftgelenk links“ bleibt. | `ursula-ws-ohne-seite` |
| 5 | 47, 68, 120 | **teilweise erledigt, 1 Frage** | Leere Überschrift (RH 120) und loses Regions-Wort (RH 47) blieben bis zum Schluss stehen. Jetzt am Ende der Kette (nach IB Lab): Teil ohne jeden Inhalt weg, loses Wort als letzte Zeile weg. Gegenprobe: kurzer diktierter Teil und reiner IB-Lab-Teil (LAMA) bleiben. **RH 68 nicht gebaut:** seit 3.20.0 bekommt jede nicht diktierte CAS-Untersuchung Titel + Normaltext + rote Prüfzeile (Georgs Regel 20.11., `georg-nicht-diktiert-normal`); Ursulas „streichen“ widerspricht ihr → Frage an Georg, Karte **#542**. | `ursula-schluss` |
| 6 | 120 | **erledigt** | Nachgestellt: CAS „Ganzbein re.“, KI-Titel ohne Seite → blieb ohne Seite, keine Prüfzeile. Jetzt Seite der CAS-Leistung in den Titel (paarige Regionen, nur wenn der Titel keine Seite hat). CAS + Diktat ohne Seite → rote Prüfzeile, jetzt auch beim nicht diktierten Ganzbein-Teil. 3 alte Testerwartungen (Titel ohne Seite trotz CAS-Seite) angepasst. | `ursula-seite-laut-cas` |
| 7 | 55 | **erledigt** | Zehe ohne Nummer → rote Prüfzeile gibt es seit 3.20.0 (`georg-strahl-nummer`, Test Punkt 7). „Verklakung“ → „Verkalkung“ (auch „verklakt“) nach der KI. STT/KI: Teil A. | `ursula-schreibweisen` |
| 8 | 37 | **erledigt (KaiScribe-Teil)** | KaiScribe ließ eine Leerzeile der KI nach „## Ergebnis“ stehen (Nummerierung erhält sie). Jetzt am Ende entfernt, auch vor „1.“. Setzt der Formatierer selbst eine → Schwesterjob. | `ursula-schluss` |
| 9 | 89, 82 | **an Schwesterjob** | KaiScribe schreibt nie eine Dosis (kein „Dosis“/„DAP“ im Code). Die Dosis steht im Brief im CAS-Vorlagenfeld `<do0>…</do0>` → ris-format-ursula-2011-n1. | – |
| 10 | 59 | **erledigt (vorläufig)** | Peter 23.11.: „Th“. Uneinheitlich war: vor der KI schon DH/TH → Th (Fehlhör-Liste), nach der KI nichts; Plexus-Vorlage hat „TH1“. Jetzt nach der KI „TH12“/„Th 12“ → „Th12“ (auch Vorlagentext). „T1-gewichtet“, „BWK 12“ bleiben. Widerspricht Georg, eine Zeile ändern. | `ursula-th-wirbel` |
| 11 | 31, 89, 120 | **an Schwesterjob** | `<bf0>`/`</bf0>`, `<do0>` sind Marken der CAS-Briefvorlage (Befund-/Dosisfeld, im Brief versteckt; Schwesterjob-Messung `tags.py`); KaiScribe erzeugt keine solchen Tags. → ris-format-ursula-2011-n1. | – |

## Tests / Dateien
- `source_code/befund_regeln.py` (`ursula_2011`, `ergebnis_text_sichern`, `befund_schluss`) ≡ `web_app/src/befundRegeln.ts`;
  `pipeline.py` (`_schluss`, Seite laut CAS, Seiten-Prüfzeile auch für nicht diktierte Teile) + `pipeline.ts`;
  `cas_vorlagen.report_seite`. Fixtures `ursula_2011` (27 Fälle, PY + TS je zweimal gleich), neu
  `tests/offline/test_ursula_2011.py` (15 Prüfungen, CI), Regel-Register +8 Pflicht-Regeln.
- Offline-Suite wie CI (alle Python-Tests) grün, Node-Tests (pipeline/speechmike/audio/llm_anbieter + 437 TS-Regelfälle) grün,
  tsc + eslint sauber.
- Arbeitsdateien: `~/cj/work/kaiscribe-ursula-2011-text-n1/` (probe.py, fixtures_bauen.py, tests.sh, version_hoch.sh).

## Rückweg
EXE: `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (.alt-Sicherung, im Einspielauftrag). Code: der Commit
„KaiScribe: Ursulas Durchsicht 20.11.2026 …“ ist einzeln zurücknehmbar; jede Regel hängt an einer Stelle (`ursula_2011` am Ende
von `grundregeln`, `ergebnis_text_sichern` in `nachbearbeiten`, `befund_schluss` am Ende der Kette).

## Abschluss (für Ursula)
Danke für die Liste! In KaiScribe 3.25 ist (sobald heute Abend eingespielt und am Testpatienten geprüft):
- keine leere Überschrift und kein loses Wort („Becken“) mehr am Ende; keine Leerzeile nach „Ergebnis:“;
- das Ergebnis wird nicht mehr als Überschrift gesetzt; Ganzbein bekommt die Seite aus dem Auftrag (fehlt sie: rote Zeile);
- Wirbelsäule ohne „beidseits“ im Titel, „50%iger“, „Im Übrigen“ nicht mehrmals hintereinander, „trochantär“,
  „Verkalkung“, Brustwirbel „Th12“;
- Rho-Überschrift und fehlende Zehennummer waren seit 21.11. schon gelöst (die Briefe vom 20.11. hatten die ältere Version).
- Dosis beim Nervensono und die Zeichen „</bf0>“ kommen aus der Briefvorlage – das richtet der Formatierer-Auftrag.
- Offen: nicht diktierte Untersuchungen aus dem Auftrag – Georg entscheidet (Karte #542).

👉 Georg: nicht diktierte CAS-Untersuchung – Normaltext lassen oder streichen? (Karte #542), bis Fr 27.11.
