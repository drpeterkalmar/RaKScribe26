# RaKScribe 3.2.0 — Telegram-Befundregeln in EXE und Web (05.10.2026)

Für Dr. Georg Riegler und Dr. Peter Kalmar. Anlass: Georg (Telegram „RaKScribe26 dev“): „Die Befunde in der
Telegramgruppe sind korrekt und sehr gut. Leider funktioniert es nicht in der exe … anderer Standardtext … nummeriert im
Ergebnis nicht.“ Dazu Peters Nachtrag: „Mein Diktat wird eins zu eins in das Ergebnis übernommen“ und „Ein unauffälliges
Lungenröntgen wurde als unauffälliges Skelettröntgen beschrieben.“

## Kurz: Was ist jetzt anders?

1. **Mehrere Regionen in einem Diktat** („Schulter rechts … Ellbogen rechts …“) werden erkannt und als **eigene Befunde
   untereinander** geschrieben — jeder mit eigener Vorlage, eigener Überschrift und eigenem Ergebnis. Bisher fiel eine
   Region komplett weg.
2. **Ergebnis immer nummeriert** (1. 2. 3.) — das macht RaKScribe jetzt zusätzlich selbst (unabhängig von Gemini), in EXE
   und Web. Ein reiner Normalbefund bleibt ein einzelner unnummerierter Satz.
3. **Ergebnis mit den diktierten Begriffen 1:1**, inklusive Grad und Messwert („Mäßiggradige Tendinosis calcarea mit 17 mm
   messendem Kalkdepot“), Arthrose immer mit „(Arthrose Grad X nach Kellgren & Lawrence)“.
4. **Überschrift kanonisch mit Seite**: „Schultergelenk rechts in 2 Ebenen“ statt „Schulter rechts in 2 Ebenen“.
   Wirbelsäule/Thorax bekommen keine Seite („nach links“ bei Skoliose ist eine Richtung).
5. **Fließtext statt „Knochenstruktur: / Gelenkflächen: / Weichteile:“** — acht Röntgen-Vorlagen (Ellbogen, Oberarm,
   Unterarm, Hand, Handgelenk, AC-Gelenk, Oberschenkel, Mittelfuß) sind auf Fließtext umgestellt, und der Prompt verbietet
   die Labels.
6. **Der Standardtext kommt immer aus der Praxis-Vorlage** — Gemini muss jeden nicht betroffenen Vorlagen-Satz wörtlich
   übernehmen und darf keinen eigenen Standardtext schreiben.
7. **EXE und Web haben jetzt denselben Befund-Prompt** (eine Datei `radiology_prompt.txt` statt zwei getrennt gepflegter
   Texte) und dieselbe Nachbearbeitung. Alle Regeln aus dem Telegram-Skill sind eingebaut; die Zuordnung Regel → Stelle →
   Test steht in `RULES_SYNC.md`.
8. **Peters Punkte** (siehe eigener Abschnitt): Bei unauffälligem Diktat steht im Ergebnis ein zur Untersuchung passender
   Satz statt des Diktats; ein Lungenröntgen wird als Thorax befundet.

## Warum schrieb die EXE bei Georg anders?

Gefunden und behoben (alle Ursachen, weil Georgs Ordner nicht einsehbar ist):

| Ursache | Wirkung | Lösung in 3.2 |
|---|---|---|
| Die Vorlagen-Erkennung nahm bei zwei Regionen nur **eine** Vorlage | Schulter fehlte komplett | Regionen-Trenner (EXE + Web), je Region ein Befund |
| **Alte Prompt-Datei neben der EXE** (`radiology_prompt_v4.txt` oder ein im Prompt-Editor gespeicherter Prompt) gewann still gegen jedes Update | alter Stil, alter Standardtext | Prompt trägt eine Versionsnummer; eine ältere Datei wird ignoriert, beim Start kommt ein Hinweis |
| **Alte Praxisbefunde als Beispiele** (`practice_reports.db`) | gemessen: mit alten unnummerierten Beispielen schrieb Gemini 3 von 3 Mal wieder „Knochenstruktur:“-Labels und verlor „geringgradig“ im Ergebnis | Beispiele **standardmäßig aus** (Telegram arbeitet auch ohne); bei Bedarf `RAG_BEISPIELE = 1` in config.ini. Mit dem neuen Prompt schaden sie nicht mehr (3/3 korrekt), nützen aber auch nichts messbar |
| EXE-Prompt verlangte keine Nummerierung, eigener System-Text | unnummeriert möglich | Prompt-Regel + automatische Nummerierung |
| EXE-Normalbefund-Abkürzung prüfte keine Pathologien | „Knie Gonarthrose sonst unauffällig“ konnte als Normalbefund durchrutschen | strenger Normalbefund-Check (siehe Peters Punkte) |
| Ellbogen-Vorlage mit Labels | „Knochenstruktur:“ im Befund | Vorlage als Fließtext |

## Referenzfall Georg — Vorher / Nachher

Diktat (Spracherkennung roh): „Schulter rechts Punkt neue Zeile mäßig gradige Ommatrose Punkt mäßig gradige Tenenosis
kakaria mit 17 mm Messing am Kack Depot Punkt neue Zeile Ellbogen rechts Punkt … geringgradige Ellbogengelenksarthrose …
kortikale Unregelmäßigkeiten im Bereich der Extensorensehnenplatte rechts das ist indirekter Hinweis für Tendenose der
Extensorensehnen Punkt“

**Vorher (EXE 3.1, nachgestellt):** nur der Ellbogen, Schulter fehlt komplett:

```
## Ellbogengelenk rechts in 2 Ebenen
## Befund
**Knochenstruktur:** Mineralgehalt regelrecht. Kompakta und Kortikalis nach Breite und Kontur regelrecht. Kortikale Unregelmäßigkeiten im Bereich der Extensorensehnenplatte rechts.
**Gelenkflächen:** Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung der Gelenkflächen und osteophytärer Randwulstbildung. Keine intra- oder periartikulären Verkalkungen.
**Weichteile:** Unauffällige Darstellung des Weichteilmantels.
## Ergebnis
1. Geringgradige Ellbogengelenksarthrose rechts, Grad 2 nach Kellgren & Lawrence.
2. Kortikale Unregelmäßigkeiten im Bereich der Extensorensehnenplatte rechts als indirekter Hinweis für eine Tendinose der Extensorensehnen.
```

**Nachher (EXE 3.2, echter Lauf; Web liefert dasselbe):**

```
## Schultergelenk rechts in 2 Ebenen
## Befund
Humeruskopf in regelrechter Artikulation. Mineralgehalt und Knochenstruktur sind normal. Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung. AC-Gelenk altersentsprechend, keine Luxation.

Unauffällige Darstellung der übrigen angrenzenden Skelettanteile des Schultergürtels und des oberen Thoraxskeletts. Periartikuläre Verkalkung im Bereich der Rotatorenmanschette mit einer Ausdehnung von 17 mm.

Normale Weichteile.
## Ergebnis
1. Mäßiggradige Omarthrose rechts (Arthrose Grad 3 nach Kellgren & Lawrence).
2. Mäßiggradige Tendinosis calcarea mit 17 mm messendem Kalkdepot rechts.

## Ellbogengelenk rechts in 2 Ebenen
## Befund
Mineralgehalt und Knochenstruktur regelrecht. Geringe Gelenksspaltverschmälerung mit beginnender Osteophytenbildung und geringer Randzuschärfung. Ansonsten die artikulierenden Gelenkflächen regelrecht konfiguriert, glatt und scharf begrenzt, allseits normal weit zueinander. Keine intra- oder periartikulären Verkalkungen. Kortikale Unregelmäßigkeiten im Bereich der Extensorensehnenplatte. Ansonsten Kompakta und Kortikalis nach Breite und Kontur regelrecht.

Unauffällige Darstellung des Weichteilmantels.
## Ergebnis
1. Geringgradige Ellbogengelenksarthrose rechts (Arthrose Grad 2 nach Kellgren & Lawrence).
2. Kortikale Unregelmäßigkeiten im Bereich der Extensorensehnenplatte als indirekter Hinweis für eine Tendinose der Extensorensehnen rechts.
```

Bis auf Kleinigkeiten (Seite „rechts“ zusätzlich im Kalk-Punkt, „allseits normal weit zueinander“ aus der Praxis-Vorlage)
deckungsgleich mit dem Telegram-Befund. Die Verhörer („Ommatrose“, „Tenenosis kakaria“, „Messing am Kack Depot“,
„Tendenose“, „mäßig gradige“) korrigiert RaKScribe jetzt automatisch über die Fehlhör-Liste.

## Peters Punkte 1 + 2 — Vorher / Nachher

**Punkt 1 — „Mein Diktat wird eins zu eins in das Ergebnis übernommen.“** Ursache: Bei Diktaten, die RaKScribe als
Normalbefund erkannte, wurde der Befund ohne KI gebaut und das Diktat als Ergebnis eingesetzt. Die Erkennung war zudem zu
großzügig („Thorax: Kardiomegalie, sonst unauffällig“ galt als Normalbefund → Befundtext komplett normal, die Kardiomegalie
stand nur als Diktat-Kopie im Ergebnis).

| Diktat | Vorher | Nachher |
|---|---|---|
| „Knie rechts unauffällig“ | Ergebnis „Knie rechts unauffällig.“ | Ergebnis „Regelrechte Darstellung des Kniegelenkes rechts.“, Überschrift „Kniegelenk rechts in 2 Ebenen“ |
| „Thorax: Kardiomegalie, sonst unauffällig.“ | Normalbefund-Text + Ergebnis = Diktat | Befund „… Der Herz-Gefäßschatten verbreitert. …“, Ergebnis „1. Kardiomegalie.“ |
| „Lungenröntgen unauffällig.“ | Ergebnis = Diktat | Ergebnis „Unauffälliger Befund.“ |

Jede Vorlage hat jetzt einen eigenen Normal-Ergebnis-Satz (140 von 142; 44 wörtlich aus den beigebrachten
Normalbefunden, der Rest nach Praxis-Konvention „Regelrechte Darstellung des/der …“; Knochendichtemessung und Blockade
haben keinen). Die Abkürzung ohne KI greift nur noch, wenn das Diktat ausschließlich aus Untersuchung + „unauffällig/
regelrecht/o. B.“ besteht — jedes weitere Wort („sonst“, eine Diagnose, eine Beschreibung) geht durch Gemini.
**Bitte prüfen:** die Vorschläge für Mammographie/Mamma-Sono („Unauffälliger Befund. BI-RADS 1 beidseits.“) und
Beinvenen-Sono („Kein Hinweis auf eine Thrombose.“) stammen nicht aus dem Skill.

**Punkt 2 — „Unauffälliges Lungenröntgen als Skelettröntgen beschrieben.“** Ursache: Wurde die Region nicht erkannt
(z. B. „Torax“, „Brustkorb“), nahm RaKScribe die Allgemein-Vorlage mit Skelett-Sätzen („Mineralgehalt und
Knochenstruktur …“). Jetzt: „Torax“ wird zu „Thorax“ korrigiert, „Lunge(n)“, „Brustkorb“, „Pulmo“ erkennen die
Thorax-Vorlage (EXE und Web, getestet), und die Allgemein-Vorlage enthält keine Skelett-Sätze mehr. Messung mit
erzwungener Allgemein-Vorlage: alter Text → Skelett-Sätze in 4 von 9 Nicht-Skelett-Läufen (Abdomen 3/3), neuer Text → 0
von 9. Preis: eine unbekannte *Skelett*-Untersuchung wird knapper (nur die diktierten Inhalte).

| Diktat | Vorher | Nachher |
|---|---|---|
| „Torax p.a. und seitlich unauffällig.“ | „## Thorax p.a. und seitlich“ + Skelett-Text | „## Thorax in 2 Ebenen“ + Thorax-Vorlage, „Unauffälliger Befund.“ |

## Was Georg in seinem EXE-Ordner tun muss

1. Neue `rakscribe26.exe` 3.2.0 herunterladen (Link wie immer, „latest“) und die alte ersetzen.
2. **Nichts löschen nötig:** Liegt noch eine alte `radiology_prompt_v4.txt` oder `radiology_prompt.txt` daneben, ignoriert
   RaKScribe sie jetzt automatisch und zeigt einmal beim Start „Befund-Prompt aktualisiert“. Danach kann die alte Datei
   gelöscht werden, dann kommt der Hinweis nicht mehr.
3. Wer den Prompt im Prompt-Editor anpasst: Die gespeicherte Datei gilt, bis eine neuere RaKScribe-Version erscheint —
   dann gewinnt wieder der mitgelieferte Prompt (mit Hinweis).
4. Praxisbeispiele aus `practice_reports.db` sind aus. Wer sie wieder will: in `config.ini` die Zeile
   `RAG_BEISPIELE = 1` ergänzen.

## Geprüft (alle grün)

- Referenzfall Georg (`verify_georg_schulter_ellbogen.py`): EXE 3/3, Web 3/3, plus alte v4-Prompt-Datei und alte
  unnummerierte Beispiele — 8/8.
- Peters Punkte (`verify_peter_ergebnis.py`): 4 Diktate × 2 Wege × 3 Läufe = 24/24.
- Bestehende Prüfungen: Knie, Sprunggelenk, Flachprofil (je 3× beide Wege), K2/K3 (9/9), Normalbefund-Treue,
  Fehlhör-Liste (34 Fälle), Regel-Modul EXE ≡ Web (51 Fälle), Normalbefund-Abkürzung (31 Fälle), Teilantworten (28/28),
  Diktat-Suite mit 6 echten Diktaten, Gesamt-Harness 18 Fälle: 4 PASS / 14 WARN / **0 FAIL** (vorher 2/16/0; WARN =
  „Validierer hat formuliert“).
- Unterwegs gefunden und behoben: neue Syndesmosen-Regel verdrängte den diktierten Messwert „12 mm“ aus dem Befund;
  „Verdacht auf“ wurde im Web einmal zu „Bild wie bei“; der Web-Validierer verlor in 5/8 Läufen den Weichteil-Satz
  (nach Präzisierung 0/8); „## Befund“ fehlte gelegentlich (wird jetzt automatisch ergänzt).

## Offen

- Kein Browser-Test der Web-Oberfläche in diesem Lauf (Leicht-Spur); die Web-Logik ist über TypeScript-Prüfung,
  Fixture-Tests der echten Web-Funktionen und die Gemini-Ketten geprüft, der Live-Stand über das ausgelieferte Bundle.
- `practice_reports.db` liegt nur auf dem Praxis-PC — ob dort Beispiele mit anderem Stil stehen, ist ungeprüft (daher
  standardmäßig aus).
- Unbekannte Skelett-Untersuchungen (keine Vorlage) bekommen nur noch die diktierten Inhalte.
