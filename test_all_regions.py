#!/usr/bin/env python3
"""
Vollständiger Widerspruchstest für alle Regionen/Modalitäten.
Testet Generierung + Validierung mit pathologischen Diktaten pro Region.
"""

import json
import os
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path

API_KEY = os.environ.get("VERTEX_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
VERTEX_URL = "https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent"

# Templates laden
TEMPLATES_PATH = Path.home() / "RaKScribe26" / "web_app" / "src" / "templates.json"
with open(TEMPLATES_PATH) as f:
    TEMPLATES = json.load(f)

CONFLICT_RULES = """
## KONFLIKT-REGELN (NORMALBEFUND vs. PATHOLOGIE) — STRIKT EINZUHALTEN:
Wenn das Diktat eine Pathologie nennt, MÜSSEN die entsprechenden Normalbefund-Sätze aus dem Template ENTFERNT oder ANGEPASST werden. KEINE WIDERSPRÜCHE im Befundtext!

Spezifische Regeln:
- Osteochondrose/Diskopathie in Segment X: ENTFERNE "Bandscheibenräume normal hoch" / "Kein Nachweis von Discopathien" für dieses Segment. Schreibe stattdessen Deskriptoren: "Verschmälerung des Intervertebralraums [Segment] mit subchondraler Sklerosierung der Abschlussplatten". Schreibe NICHT "Osteochondrose" als Wort in den Befundtext — nur Deskriptoren.
- Spondylosis deformans/Spondylophyten in Segment X: ERGÄNZE "Spondylophytenbildung [Segment]" im Befundtext.
- Unkovertebralgelenksarthrose/Uncovertebralarthrose in Segment X: FÜGE HINZU "Degenerative Veränderungen der Unkovertebralgelenke [Segment]". Die "kleinen Zwischenwirbelgelenke" (Facettengelenke) sind ANDERE Gelenke und bleiben "ohne Auffälligkeiten" wenn nicht genannt.
- Fehlhaltung im Diktat (z.B. "kyphotische Fehlhaltung"): darf NICHT verschwiegen werden — nenne sie im Befundtext (z.B. "Kyphotische Fehlhaltung der HWS.") UND im Ergebnis.
- Facettengelenksarthrose/Spondylarthrose in Segment X: ERSETZE "Kein Nachweis von Facettengelenksarthrosen" / "kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" durch "Degenerative Veränderungen der kleinen Wirbelgelenke [Segment]".
- Anterolisthese/Retrolisthese: Ersetze die normale Achsenverlaufsbeschreibung für das betroffene Segment.
- Skoliose/skoliotische Fehlhaltung: ERSETZE "Normaler Achsenverlauf" / "achsengerechte Stellung" durch die Skoliose-Beschreibung.
- Streckhaltung: ERSETZE "Normaler Achsenverlauf" / "achsengerechte Stellung" durch "Streckhaltung".
- Haltungs-/Achsenbeschreibungen ("Flachbogige Konvexität", "Streckhaltung", "Skoliose") NUR wenn im Diktat genannt. Degenerative Diagnosen (Osteochondrose/Spondylose/Arthrose) rechtfertigen KEINE erfundene Achsenbeschreibung — "Normaler Achsenverlauf" / "achsengerechte Stellung" bleibt dann UNVERÄNDERT.
- Fraktur: ENTFERNE "Alle Wirbelkörper von normaler Form und Höhe" / "Normale Form und Struktur der Gelenkkörper" und ersetze durch Frakturbeschreibung.
- Omarthrose/Coxarthrose/Gonarthrose/Gelenksarthrose etc.: ENTFERNE "Normale Form und Struktur der Gelenkkörper", "Die Gelenkflächen glatt und kongruent", "Die Gelenkränder unauffällig", "Die Gelenksspalten normal weit" — ALLE diese Normalbefund-Sätze MÜSSEN gestrichen werden wenn eine Arthrose vorliegt. Stattdessen arthrotische Deskriptoren (Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophytenbildung). NIEMALS "Normale Form und Struktur der Gelenkkörper" + arthrotische Deskriptoren im selben Satz (kein "bei ansonsten normaler Form").
- Humeruskopfhochstand/Femurkopfhochstand: Ersetze die normale Gelenkpartner-Stellung durch den Hochstand. KEIN "bei ansonsten normaler Form und Struktur" — der Hochstand IST die Abweichung.
- TEP/Prothese: ERSETZE "Normale Form und Struktur der Gelenkkörper" durch Prothesenbeschreibung.
- Knochenzyste/Lyse/Tumor: ERSETZE "Knochenstruktur unauffällig" / "Mineralgehalt und Knochenstruktur regelrecht" durch pathologische Beschreibung.
- Kalzifikation/Tendinosis calcarea: ERGÄNZE Verkalkungsbeschreibung im Befundtext.

GRUNDREGEL: Wenn ein Normalbefund-Satz durch eine Pathologie hinfällig wird, MUSS er gestrichen oder ersetzt werden. Ein Befundtext darf NIEMALS eine Struktur als "normal/unauffällig/ordnungsgemäß" beschreiben UND GLEICHZEITIG als pathologisch verändert einstufen.
BESCHREIBUNGSTEXT = NUR MORPHOLOGIE/DESKRIPTOREN. Diagnosen gehören NUR ins Ergebnis, NICHT in den Befundtext.

## VERBOTENE MUSTER (Anti-Patterns) — diese Fehler macht Gemini Flash oft, sie MÜSSEN vermieden werden:
❌ FALSCH: "Normale Form und Struktur der Gelenkkörper. Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung und Osteophytenbildung." (Widerspruch: erst normal, dann arthrotisch — der erste Satz MUSS WEG)
✅ RICHTIG: "Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung der Gelenkflächen und osteophytärer Randwulstbildung." (nur arthrotische Deskriptoren)
❌ FALSCH: "Die Gelenkflächen glatt und kongruent. Die Gelenkränder unauffällig. Die Gelenksspalten normal weit. Medialbetonte Gelenkspaltverschmälerung." (Widerspruch: 3 Normalbefund-Sätze + 1 arthrotischer Befund — die 3 Normalbefund-Sätze MÜSSEN WEG)
✅ RICHTIG: "Medialbetonte Gelenkspaltverschmälerung. Die periartikuläre Weichteilzone o. B." (nur arthrotische Deskriptoren + Weichteil-Normalbefund, da dieser nicht betroffen ist)
❌ FALSCH: "Hochstand des Humeruskopfes bei ansonsten normaler Form und Struktur der Gelenkkörper." (Widerspruch: Hochstand + normale Form — "bei ansonsten normaler Form" MUSS WEG)
✅ RICHTIG: "Hochstand des Humeruskopfes." (Hochstand ist die Abweichung, kein "bei ansonsten normaler Form")
❌ FALSCH: "Normale Form und Struktur der Gelenkkörper. Dislozierte Kontinuitätsunterbrechung im Bereich des Collum chirurgicum." (Widerspruch: erst normale Form, dann Fraktur — der erste Satz MUSS WEG)
✅ RICHTIG: "Dislozierte Kontinuitätsunterbrechung im Bereich des Collum chirurgicum humeri." (nur Frakturbeschreibung)
❌ FALSCH: "Artikulierende Flächen regelrecht konfiguriert, glatt und scharf begrenzt, allseits normal weit zueinander." (nach Fraktur eines Gelenkpartners — fehlender Qualifikator, impliziert ALLE Flächen normal)
✅ RICHTIG: "Artikulierende Flächen im Übrigen regelrecht konfiguriert, glatt und scharf begrenzt, allseits normal weit zueinander." ("im Übrigen" qualifiziert: der frakturierte Teil ist ausgenommen)
❌ FALSCH: "Mineralgehalt und Knochenstruktur regelrecht. Nicht dislozierte Kontinuitätsunterbrechung im Bereich der Kahnbeintaille." (Widerspruch: Knochenstruktur als regelrecht bezeichnet, dann Fraktur — "und Knochenstruktur" MUSS WEG)
✅ RICHTIG: "Mineralgehalt regelrecht. Nicht dislozierte Kontinuitätsunterbrechung im Bereich der Kahnbeintaille." (Mineralgehalt darf normal bleiben, Knochenstruktur nicht bei Fraktur)
❌ FALSCH: "Flachbogige linkskonvexe Skoliose." oder "Retrolisthese von L4 gegenüber L5." (Befundtext — Diagnosename statt Morphologie)
✅ RICHTIG: "Flachbogige linkskonvexe Seitausbiegung." bzw. "Dorsaler Versatz von L4 gegenüber L5." (Morphologie im Befundtext, Diagnose "Skoliose"/"Retrolisthese" nur im Ergebnis)
❌ FALSCH: "Flachbogige Konvexität." als Befund-Satz, ohne dass das Diktat eine Haltungs-/Achsenabweichung nennt (erfundene Haltungsbeschreibung)
✅ RICHTIG: "Normaler Achsenverlauf." (Template-Satz bleibt stehen, wenn das Diktat nichts zur Achse/Haltung diktiert)

## ERGEBNIS-REGELN:
- Schreibe NUR Diagnosen die im Diktat genannt wurden. Keine ERFUNDENEN Begriffe.
- Verwende EXAKT die Begriffe aus dem Diktat.
- Diagnose-Namen dürfen NICHT umformuliert werden. "Osteochondrose" bleibt "Osteochondrose", nicht "Diskopathie". "Coxarthrose" bleibt "Coxarthrose", nicht "Hüftgelenksarthrose".
- Wenn das Diktat nur Deskriptoren nennt (z.B. "Schleimhautschwellung, Spiegelbildung") schreibe diese als Befund, aber erfinde KEINE Diagnose (z.B. nicht "Sinusitis") für das Ergebnis — nur das Diktat entscheidet ob eine Diagnose gestellt wird.

## ARTHROSE-GRADUIERUNG NACH KELLGREN & LAWRENCE (PFLICHT):
Bei ARTHROSE-Diagnosen im Ergebnis IMMER mit Graduierung: "[Gelenksarthrose-Diagnose] Grad [X] nach Kellgren & Lawrence [Seite]". Die Grad-Zuordnung aus den Deskriptoren: geringe Osteophyten ohne/fragliche Verschmälerung = Grad 1 · geringe Osteophyten + geringe Verschmälerung/Randzuschärfung = Grad 2 · mäßiggradige Verschmälerung + multiple Osteophyten + subchondrale Sklerosierung = Grad 3 · aufgehobener Gelenkspalt + ausgeprägte Sklerosierung/Zysten = Grad 4.
Gilt für: Schulter (Omarthrose), Ellbogen, Hand, Handgelenk, Hüfte (Coxarthrose), Knie (Femorotibial + Patellofemoral getrennt gradieren), Sprunggelenk, Fuß. NICHT für: AC-Gelenk, ISG, Symphyse.
"""

# ─── Testfälle ───
TEST_CASES = [
    # (name, template_key, diktat, erwartete_pathologien)
    ("HWS Streckhaltung+Skoliose+Osteochondrose", "halswirbelsäule_in_2_ebenen",
     "HWS, Röntgen, Streckhaltung, flachbogige Konvexität, Skoliose, degenerative Antelisthese C5 gegenüber C6, bei Osteochondrose, bei Unkovertebralgelenksarthrosen und Spondylosis deformans in diesen Segmenten. Ansonsten unauffällig.",
     ["Streckhaltung", "Skoliose", "Antelisthese", "Osteochondrose", "Unkovertebralgelenksarthrose", "Spondylosis deformans"]),

    ("LWS Osteochondrose+Spondylose+Facettenarthrose", "lendenwirbelsäule_in_2_ebenen",
     "Lendenwirbelsäule, Röntgen, Skoliose, flachbogig linkskonvex, Osteochondrose L4/L5 sowie L5/S1, Spondylosis deformans L3 bis L5, Facettengelenksarthrosen L3 bis S1, Retrolisthese L4 gegenüber L5. Ansonsten unauffällig.",
     ["Skoliose", "Osteochondrose", "Spondylosis deformans", "Facettengelenksarthrose", "Retrolisthese"]),

    ("BWS Morbus Scheuermann", "brustwirbelsäule_in_2_ebenen",
     "Brustwirbelsäule, Röntgen, vermehrte Kyphose, Morbus Scheuermann, Keilwirbel Th7 bis Th9, Schmorl-Knoten Th6 bis Th10. Ansonsten unauffällig.",
     ["Kyphose", "Morbus Scheuermann", "Keilwirbel", "Schmorl"]),

    ("Schulter Omarthrose+Tendinosis calcarea", "schultergelenk_in_2_ebenen",
     "Schulter rechts, Röntgen, Omarthrose, Kalzifikation Supraspinatussehne, Humeruskopfhochstand. Ansonsten unauffällig.",
     ["Omarthrose", "Kalzifikation", "Humeruskopfhochstand"]),

    ("Schulter Fraktur", "schultergelenk_in_2_ebenen",
     "Schulter links, Röntgen, dislozierte Fraktur des Collum chirurgicum humeri. Ansonsten unauffällig.",
     ["Fraktur", "Collum chirurgicum"]),

    ("Hüfte Coxarthrose", "hüftgelenk_in_2_ebenen",
     "Hüfte links, Röntgen, Coxarthrose links, Gelenkspaltverschmälerung, subchondrale Sklerosierung, osteophytäre Randwülste. Ansonsten unauffällig.",
     ["Coxarthrose"]),

    ("Hüfte Schenkelhalsfraktur", "hüftgelenk_in_2_ebenen",
     "Hüfte rechts, Röntgen, nicht dislozierte Schenkelhalsfraktur rechts, Garden I. Ansonsten unauffällig.",
     ["Schenkelhalsfraktur", "Garden"]),

    ("Knie Gonarthrose", "kniegelenk_in_2_ebenen",
     "Knie rechts, Röntgen, Gonarthrose rechts, medialbetonte Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Gonarthrose", "Kellgren"]),

    ("Knie Gonarthrose K&L (Peter 08.09., Screenshot-Case)", "kniegelenk_in_2_ebenen",
     "Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments, geringgradige Retropatellararthrose. Ansonsten unauffällig.",
     ["Gonarthrose", "Kellgren"]),

    ("Ellbogen Fraktur", "ellbogengelenk_in_2_ebenen",
     "Ellbogen rechts, Röntgen, dislozierte Fraktur des Radiusköpfchens. Ansonsten unauffällig.",
     ["Fraktur", "Radiusköpfchen"]),

    ("Hand Fraktur", "hand_in_2_ebenen",
     "Hand links, Röntgen, nicht dislozierte Fraktur der Kahnbeintaille links. Ansonsten unauffällig.",
     ["Fraktur", "Kahnbein"]),

    ("Handgelenk SLAC", "handgelenk_in_2_ebenen",
     "Handgelenk rechts, Röntgen, SLAC wrist, Scapholunäre Dissoziation, Arthrose radioscaphoid. Ansonsten unauffällig.",
     ["SLAC", "Dissoziation", "Arthrose"]),

    ("Beckenübersicht Coxarthrose+Beckenschiefstand", "beckenübersicht_stehend",
     "Beckenübersicht stehend, Röntgen, Beckenschiefstand nach links um 4 mm, Beinlängendifferenz links -4 mm, Coxarthrose links. Ansonsten unauffällig.",
     ["Beckenschiefstand", "Beinlängendifferenz", "Coxarthrose"]),

    ("Sprunggelenk Arthrose", "sprunggelenk_in_2_ebenen",
     "Sprunggelenk links, Röntgen, Arthrose des oberen Sprunggelenkes, Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Arthrose"]),

    ("HWS Discopathiezeichen (Peter 07.09., Regression)", "halswirbelsäule_in_2_ebenen",
     "HWS: Osteochondrose C3/C4, deformierende Spondylose C2–C7, Discopathiezeichen C4–C7.",
     ["Osteochondrose", "Spondylose", "Discopathiezeichen"]),

    ("HWS Flachprofil-STT + kyphotische Fehlhaltung (Peter 07.09., Screenshot-Case)", "halswirbelsäule_in_2_ebenen",
     "HWS: flachprofile nach links, komplexe kyphotische Fehlhaltung. Osteochondrose C2 bis C4. Gelenksarthrose C3 bis C5. Hochgradige Diskopathie C4 bis C7.",
     ["flachbogig", "Fehlhaltung", "Osteochondrose", "Gelenksarthrose", "Diskopathie"]),

    ("Schädel Fraktur", "schädel_in_2_ebenen",
     "Schädel, Röntgen, undislozierte Fraktur des Os parietale links. Ansonsten unauffällig.",
     ["Fraktur", "Os parietale"]),

    ("Nasennebenhöhlen Sinusitis", "nasennebenhöhlen",
     "Nasennebenhöhlen, Röntgen, Schleimhautschwellung und Verlegung des Sinus maxillaris bds., Spiegelbildung links. Ansonsten unauffällig.",
     ["Schleimhautschwellung", "Spiegelbildung"]),
]


def _get_sa_token():
    """Bearer-Fallback: SA-JSON (Hermes-Key, gleiches GCP-Projekt) wenn kein/ungültiger AQ.-Key."""
    global _SA_TOKEN_CACHE
    if _SA_TOKEN_CACHE:
        return _SA_TOKEN_CACHE
    from google.oauth2 import service_account
    import google.auth.transport.requests as _tr
    sa_path = os.environ.get("VERTEX_SA_KEY", str(Path.home() / ".hermes" / "secrets" / "vertex-sa-key.json"))
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(_tr.Request())
    _SA_TOKEN_CACHE = creds.token
    return _SA_TOKEN_CACHE

_SA_TOKEN_CACHE = None

def call_gemini(prompt, token=None, temperature=0.0, timeout=120):
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "thinkingConfig": {"thinkingBudget": 0}}
    }).encode()
    req = urllib.request.Request(VERTEX_URL, data=body, headers=headers, method="POST")
    _retries = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                # Fallback: SA-Bearer (AQ.-Key fehlt/rotiert)
                req = urllib.request.Request(VERTEX_URL, data=body, headers={
                    "Content-Type": "application/json", "Authorization": "Bearer " + _get_sa_token()}, method="POST")
            elif e.code in (429, 500, 503) and _retries < 3:
                _retries += 1
                time.sleep(30 * _retries)
            else:
                raise
    if "error" in data:
        raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()


def build_gen_prompt(raw_text, template_body, region_name=None):
    untersuchung = f"\n<untersuchung>{region_name}</untersuchung>\n" if region_name else ""
    return f"""<role>Radiologie-Assistent der Praxis "Röntgen am Kai" – Dr. P. Kalmar / Dr. G. Riegler</role>

<instructions>
Du bist ein präziser radiologischer Befundungsassistent für die Praxis "Röntgen am Kai" in Graz. Deine Aufgabe ist es, das diktierte Stichwortprotokoll des Arztes in einen formalen, professionellen radiologischen Befund zu strukturieren, der sich EXAKT an den historischen Befundvorlagen der Praxis orientiert.
{untersuchung}

## STRIKTE FORMATREGELN:
1. Erstelle IMMER exakt zwei Hauptabschnitte: '## Befund' und '## Ergebnis'. Kein weiterer Text.
2. Gib NUR den fertigen Befundtext aus – keine Einleitung, kein Schlusswort.

## ABSCHNITT "## Befund":
- UNTERSUCHUNGS-ÜBERSCHRIFT (erste Zeile des Befundtextes): Verwende AUSSCHLIESSLICH die kanonische Untersuchungsbezeichnung aus <untersuchung> bzw. der ersten Template-Zeile — NIE das roh diktierte Wort für die Untersuchung allein. Übernimm die diktierte Seite (links/rechts/beidseits) in die Überschrift (z.B. diktiert "Kniegelenk links" → "Kniegelenk links in 2 Ebenen").
- Nutze das bereitgestellte Normalbefund-Template als genaue strukturelle Basis.
- Passe gezielt die Sätze an, bei denen das Diktat pathologische Befunde nennt.
- Behalte ALLE nicht genannten Regionen und Sätze des Templates UNVERÄNDERT.
- Schreibe im radiologischen Nominalstil.

## ABSCHNITT "## Ergebnis":
- Fasse alle diagnosewesentlichen Pathologien nummeriert zusammen.
- Bei Normalbefund: 'Unauffälliger Befund.'

## KONSISTENZ-REGELN (STRIKT):
1. JEDER pathologische Befund aus dem Diktat MUSS im "## Ergebnis" genannt werden.
2. JEDER pathologische Befund aus dem "## Ergebnis" MUSS auch im "## Befund" beschrieben sein.
3. KEINE WIDERSPRÜCHE: Wenn im Befund eine Pathologie beschrieben wird, darf das Ergebnis nicht "unauffällig" lauten.
4. Keine Diagnose darf ERFUNDEN werden.
5. "ansonsten unauffällig" bezieht sich nur auf nicht genannte Bereiche.
{CONFLICT_RULES}
</instructions>

<normalbefund_template>
{template_body}
</normalbefund_template>

<diktat>
{raw_text}
</diktat>
"""


def build_val_prompt(raw_dictation, generated_report):
    return f"""Du bist ein radiologischer Qualitätskontrolleur. Du erhältst das ursprüngliche Diktat und den daraus generierten Befund. Prüfe STRENG:

1. VOLLSTÄNDIGKEIT: Jede Pathologie/Diagnose aus dem Diktat muss im Befund UND im Ergebnis vorkommen.
2. WIDERSPRUCHSFREIHEIT: Befund und Ergebnis dürfen sich nicht widersprechen.
3. WIDERSPRUCHSFREIHEIT IM BEFUNDTEXT: Ein Normalbefund-Satz darf NICHT bestehen bleiben, wenn die entsprechende Struktur pathologisch verändert ist. Spezifisch:
   - "Bandscheibenräume normal hoch" / "Kein Nachweis von Discopathien" MUSS gestrichen/angepasst werden wenn Osteochondrose/Diskopathie vorliegt.
   - "Gelenkflächen glatt und kongruent" / "Gelenkränder unauffällig" / "Gelenksspalten normal weit" MÜSSEN angepasst werden bei Arthrose.
   - "Normale Form und Struktur der Gelenkkörper" MUSS angepasst werden bei Fraktur, TEP, Tumor.
   - "Normaler Achsenverlauf" / "achsengerechte Stellung" MUSS ersetzt werden bei Skoliose, Streckhaltung, Listhese.
   - "Knochenstruktur unauffällig" / "Mineralgehalt und Knochenstruktur regelrecht" MUSS angepasst werden bei Lyse, Zyste, Tumor.
4. BESCHREIBUNGSTEXT = NUR MORPHOLOGIE: Im "## Befund" dürfen KEINE Diagnosenamen stehen. Stattdessen Deskriptoren. Diagnosen NUR im "## Ergebnis".
5. KEINE ERFUNDENE DIAGNOSE. Umgekehrt MÜSSEN Arthrose-Diagnosen im Ergebnis nach Kellgren & Lawrence graduiert sein ("Grad [1-4] nach Kellgren & Lawrence"), wenn das Gelenk zur K&L-Liste gehört (Schulter/Ellbogen/Hand/Handgelenk/Hüfte/Knie/Sprunggelenk/Fuß — NICHT AC/ISG/Symphyse). Fehlt die Graduierung, ergänze sie aus den Deskriptoren (geringe Osteophyten=1, +geringe Verschmälerung=2, mäßiggradig+multiple Osteophyten+Sklerosierung=3, aufgehobener Spalt=4). Knie: Femorotibial und Patellofemoral getrennt.
6. ZAHLEN UND MESSWERTE: Alle Zahlen aus dem Diktat müssen exakt im Befund stehen.
7. SPRACHERKENNUNGSKORREKTUR: Prüfe nur, ob OFFENSICHTLICHE Spracherkennungsfehler korrekt interpretiert wurden. ERFINDE NIEMALS Beschreibungen, die im Diktat nicht stehen (z.B. "Flachbogige Konvexität" ohne Diktat-Grundlage). Übernimm KEIN STT-Nonsense-Wort in den Befund: "Flachprofil" existiert nicht (korrekt: "flachbogige Skoliose" bzw. "flachbogige Seitausbiegung").
8. UNTERSUCHUNGS-BEZEICHNUNG: Die erste Zeile des Befundtextes muss die kanonische Untersuchungsbezeichnung sein (z.B. "Kniegelenk links in 2 Ebenen") — roh diktierte Kurzformen ohne Formulierungsbestandteile (nur "Kniegelenk") korrigieren, diktierte Seite übernehmen.

Wenn der Befund FEHLERFREI ist, gib ihn UNVERÄNDERT zurück.
Wenn es FEHLER gibt, korrigiere und gib die korrigierte Version zurück.
Gib NUR den fertigen Befundtext aus (mit ## Befund und ## Ergebnis), keine Erklärungen.

<diktat>
{raw_dictation}
</diktat>

<generierter_befund>
{generated_report}
</generierter_befund>

Korrigierter Befund:
"""


def check_contradictions(report, template_body):
    """Checkt ob Normalbefund-Sätze trotz Pathologie im Befund stehen geblieben sind.

    Kontextbewusst: Wörter wie "übrigen", "ansonsten", "übrige" qualifizieren
    eine Phrase als bewusste Einschränkung auf nicht-pathologische Bereiche.
    Solche qualifizierten Phrasen sind KEINE Widersprüche.
    """
    contradictions = []
    befund = report.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in report else ""
    befund_lower = befund.lower()

    # Liste von Normalbefund-Phrasen, die bei Pathologie nicht bleiben dürfen
    contradiction_checks = [
        ("Bandscheibenräume normal hoch", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Discopathien", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Facettengelenksarthrosen", "Facettengelenksarthrose", ["Degenerative Veränderungen", "Facetten"]),
        ("Gelenkflächen glatt und kongruent", "Arthrose", ["Gelenkspaltverschmälerung", "Sklerosierung", "Osteophyt"]),
        ("Gelenkränder unauffällig", "Arthrose", ["Osteophyt", "Sklerosierung", "Randwulst"]),
        ("Gelenksspalten normal weit", "Arthrose", ["Gelenkspaltverschmälerung", "Gelenksspaltenverschmälerung"]),
        ("Normale Form und Struktur der Gelenkkörper", "Fraktur", ["Fraktur", "Frakturlinie", "Dislokation"]),
        ("Normaler Achsenverlauf", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("Normaler Achsenverlauf", "Streckhaltung", ["Streckhaltung"]),
        ("achsengerechte Stellung", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("achsengerechte Stellung", "Streckhaltung", ["Streckhaltung"]),
        ("Knochenstruktur unauffällig", "Fraktur", ["Fraktur"]),
        ("Alle Wirbelkörper von normaler Form", "Fraktur", ["Fraktur"]),
    ]

    # Qualifikatoren, die eine Phrase als bewusste Einschränkung markieren
    qualifiers = ["übrigen", "übrige", "ansonsten", "anderen", "restlichen"]

    def is_qualified(phrase, text_lower):
        """Prüft ob die Phrase durch einen Qualifikator eingeschränkt ist."""
        idx = text_lower.find(phrase.lower())
        if idx == -1:
            return False
        # Schaue 60 Zeichen vor der Phrase nach Qualifikatoren
        window_before = text_lower[max(0, idx - 60):idx]
        # Und 60 Zeichen nach der Phrase (falls der Qualifikator danach kommt)
        window_after = text_lower[idx:idx + len(phrase) + 60]
        combined = window_before + " " + window_after
        return any(q in combined for q in qualifiers)

    for normal_phrase, pathology, expected_descriptors in contradiction_checks:
        if normal_phrase.lower() in befund_lower:
            # Skip wenn qualifiziert (z.B. "die übrigen Bandscheibenräume normal hoch")
            if is_qualified(normal_phrase, befund_lower):
                continue
            # Check if the pathology or its descriptors are also in the befund
            has_pathology = pathology.lower() in befund_lower or \
                           any(d.lower() in befund_lower for d in expected_descriptors)
            if has_pathology:
                contradictions.append(f"❌ '{normal_phrase}' noch im Befund trotz {pathology}")

    return contradictions


def run_test_case(name, template_key, diktat, expected_pathologies, token):
    template_body = TEMPLATES.get(template_key, {}).get("body", "")
    if not template_body:
        return {"name": name, "status": "ERROR", "issues": [f"Template '{template_key}' nicht gefunden"]}

    print(f"\n{'─'*60}")
    print(f"TEST: {name}")
    print(f"{'─'*60}")

    # Call #1: Generation
    try:
        gen_prompt = build_gen_prompt(diktat, template_body, region_name=TEMPLATES[template_key].get("display_name", ""))
        t0 = time.time()
        report = call_gemini(gen_prompt, token, temperature=0.1)
        gen_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Gen call failed: {e}"]}

    # Call #2: Validation
    try:
        val_prompt = build_val_prompt(diktat, report)
        t0 = time.time()
        validated = call_gemini(val_prompt, token, temperature=0.0)
        val_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Val call failed: {e}"]}

    final = validated if validated and "## Befund" in validated else report
    was_corrected = validated.strip() != report.strip()

    # Checks
    issues = []
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""

    # 1. Widerspruchs-Check
    contradictions = check_contradictions(final, template_body)
    issues.extend(contradictions)

    # 2. Vollständigkeit: jede erwartete Pathologie im Ergebnis?
    for exp in expected_pathologies:
        if exp.lower() not in ergebnis.lower():
            issues.append(f"⚠️ '{exp}' fehlt im Ergebnis")

    # 3. Diagnosen im Befundtext?
    diagnosis_words = ["Osteochondrose", "Omarthrose", "Coxarthrose", "Gonarthrose",
                       "Spondylosis deformans", "Facettengelenksarthrose", "Morbus Scheuermann"]
    for dw in diagnosis_words:
        if dw.lower() in befund.lower() and dw.lower() not in template_body.lower():
            issues.append(f"⚠️ Diagnose '{dw}' im Befundtext statt Deskriptor")

    # 4. Erfundene Begriffe? (nur wenn NICHT im Diktat genannt — "Fehlhaltung" kann diktiert sein)
    invented = [inv for inv in ["Fehlhaltung"] if inv.lower() not in diktat.lower()]
    for inv in invented:
        if inv.lower() in ergebnis.lower():
            issues.append(f"⚠️ Erfundener Begriff '{inv}' im Ergebnis")
    # 4b. "Flachprofil" darf NIE im Report stehen (existiert radiologisch nicht)
    if "flachprofil" in final.lower():
        issues.append(f"❌ 'Flachprofil' im Befund — existiert radiologisch nicht (korrekt: flachbogige Skoliose)")

    # 5. Wurde korrigiert?
    if was_corrected:
        issues.append("📝 Call #2 hat korrigiert")

    status = "✅ PASS" if not contradictions and not any("❌" in i for i in issues) else "❌ FAIL"
    if issues and "❌" not in " ".join(issues):
        status = "⚠️ WARN"

    print(f"  Gen: {gen_time:.1f}s | Val: {val_time:.1f}s | Status: {status}")
    if issues:
        for i in issues:
            print(f"  {i}")
    else:
        print("  Keine Widersprüche gefunden ✅")

    # Print final result
    print(f"\n--- {name} FINALES ERGEBNIS ---")
    print(final[:600])

    return {"name": name, "status": status, "issues": issues, "report": final}


def main():
    print("=" * 70)
    print("VOLLSTÄNDIGER WIDERSPRUCHSTEST — Alle Regionen")
    print("=" * 70)

    results = []

    for name, tkey, diktat, expected in TEST_CASES:
        r = run_test_case(name, tkey, diktat, expected, None)
        results.append(r)
        time.sleep(1)  # Rate limit

    # Summary
    print(f"\n{'='*70}")
    print("ZUSAMMENFASSUNG")
    print(f"{'='*70}")
    passes = sum(1 for r in results if r["status"] == "✅ PASS")
    warns = sum(1 for r in results if r["status"] == "⚠️ WARN")
    fails = sum(1 for r in results if r["status"] == "❌ FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\n✅ PASS: {passes} | ⚠️ WARN: {warns} | ❌ FAIL: {fails} | ERROR: {errors}")
    print(f"Total: {len(results)}")

    print(f"\n{'─'*70}")
    for r in results:
        icon = {"✅ PASS": "✅", "⚠️ WARN": "⚠️", "❌ FAIL": "❌", "ERROR": "💥"}.get(r["status"], "?")
        print(f"{icon} {r['name']}")
        for issue in r.get("issues", []):
            print(f"    {issue}")


if __name__ == "__main__":
    main()