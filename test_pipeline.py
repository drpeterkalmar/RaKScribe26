#!/usr/bin/env python3
"""
Test-Skript: Simuliert die RaKScribe26 Web App Pipeline (Call #1 + Call #2)
mit Peters letztem Diktat. Testet ob die Konfliktregeln greifen.

Nutzt Google Service Account für Gemini Flash (wie die Web App).
"""

import json
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path
import google.auth.transport.requests as grequests
from google.oauth2.service_account import Credentials

# ─── Config ───
KEY_PATH = Path.home() / ".hermes" / "rakscribe-google-key.json"
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Peters Roh-Diktat (mit STT-Fehlern, wie es aus der Spracherkennung kommt)
RAW_DICTATION = (
    "HWS, Röntgen, Streckhaltung, Flachbügelingskonvexe, Skoliose, "
    "degenerative Antibiotik, C5 gegenüber C6, bei Osteochondrose, "
    "bei Strichunkelvertebalatosen und Spondylosis deformans in diesen Segmenten. "
    "Ansonsten unauffällig."
)

# HWS Template aus der Web App (templates.json)
HWS_TEMPLATE = (
    "HWS ap/seitlich\n\n"
    "Normaler Achsenverlauf. Alle Wirbelkörper von normaler Form und Höhe. "
    "Die Knochenstruktur unauffällig. Die Bandscheibenräume normal hoch. "
    "Die kleinen Zwischenwirbelgelenke ohne Auffälligkeiten. Die Dornfortsätze o. B.. "
    "Der Cervicalkanal normal weit. Der Dens median, die Kopfgelenke o. B."
)

# ─── Konfliktregeln aus dem Skill ───
CONFLICT_RULES = """
## KONFLIKT-REGELN (NORMALBEFUND vs. PATHOLOGIE) — STRIKT EINZUHALTEN:
Wenn das Diktat eine Pathologie nennt, MÜSSEN die entsprechenden Normalbefund-Sätze aus dem Template ENTFERNT oder ANGEPASST werden. KEINE WIDERSPRÜCHE im Befundtext!

Spezifische Regeln:
- Osteochondrose/Diskopathie in Segment X: ENTFERNE "Bandscheibenräume normal hoch" für dieses Segment. Ersetze durch "Verschmälerung des Intervertebralraums [Segment] mit subchondraler Sklerosierung der Abschlussplatten".
- Spondylosis deformans/Spondylophyten in Segment X: ERGÄNZE "Spondylophytenbildung [Segment]" im Befundtext.
- Unkovertebralgelenksarthrose/Uncovertebralarthrose in Segment X: ENTFERNE "kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" NICHT (das sind Facettengelenke), aber FÜGE HINZU "Degenerative Veränderungen der Unkovertebralgelenke [Segment] mit Gelenkspaltverschmälerung, subchondraler Sklerosierung und Osteophytenbildung".
- Facettengelenksarthrose/Spondylarthrose in Segment X: ERSETZE "kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" durch "Degenerative Veränderungen der kleinen Wirbelgelenke [Segment]".
- Anterolisthese/Retrolisthese: ERSETZE "Normaler Achsenverlauf" und "Alle Wirbelkörper von normaler Form und Höhe" (nur für das betroffene Segment) durch die Listhese-Beschreibung.
- Skoliose/skoliotische Fehlhaltung: ERSETZE "Normaler Achsenverlauf" durch die Skoliose-Beschreibung.
- Streckhaltung: ERSETZE "Normaler Achsenverlauf" durch "Streckhaltung der HWS".
- Fraktur: ENTFERNE "Alle Wirbelkörper von normaler Form und Höhe" und ersetze durch Frakturbeschreibung.

GRUNDPREGEL: Wenn ein Normalbefund-Satz durch eine Pathologie hinfällig wird, MUSS er gestrichen oder ersetzt werden. Ein Befundtext darf NIEMALS eine Struktur als "normal/unauffällig/ordnungsgemäß" beschreiben UND GLEICHZEITIG als pathologisch verändert einstufen.

## ERGEBNIS-REGELN:
- Schreibe NUR Diagnosen die im Diktat genannt wurden. Keine ERFUNDENEN Begriffe wie "Fehlhaltung" wenn das Diktat "Streckhaltung" sagt.
- Verwende EXAKT die Begriffe aus dem Diktat. Wenn das Diktat "Streckhaltung" sagt, schreibe "Streckhaltung" — nicht "Fehlhaltung".
- BESCHREIBUNGSTEXT = NUR MORPHOLOGIE/DESKRIPTOREN. Diagnosen, Differentialdiagnosen und Diagnose-Namen gehören NUR ins Ergebnis, NICHT in den Befundtext.
"""

# ─── Prompts ───

def build_generation_prompt(raw_text, template_body, use_conflict_rules=False):
    rules = CONFLICT_RULES if use_conflict_rules else ""
    return f"""<role>Radiologie-Assistent der Praxis "Röntgen am Kai" – Dr. P. Kalmar / Dr. G. Riegler</role>

<instructions>
Du bist ein präziser radiologischer Befundungsassistent für die Praxis "Röntgen am Kai" in Graz. Deine Aufgabe ist es, das diktierte Stichwortprotokoll des Arztes in einen formalen, professionellen radiologischen Befund zu strukturieren, der sich EXAKT an den historischen Befundvorlagen der Praxis orientiert.

## STRIKTE FORMATREGELN:
1. Erstelle IMMER exakt zwei Hauptabschnitte: '## Befund' und '## Ergebnis'. Kein weiterer Text, keine Kommentare, keine Erklärungen außerhalb dieser Abschnitte.
2. Gib NUR den fertigen Befundtext aus – keine Einleitung, kein Schlusswort.

## ABSCHNITT "## Befund":
- Nutze das bereitgestellte Normalbefund-Template als genaue strukturelle Basis.
- Passe gezielt die Sätze an, bei denen das Diktat pathologische Befunde nennt (z.B. Arthrose, Fraktur, TEP, Spondylarthrose, Osteochondrose, Beckenschiefstand, Skoliose, Anterolisthese, Spondylosis deformans).
- Behalte ALLE nicht genannten Regionen und Sätze des Templates UNVERÄNDERT.
- Übernimm Messwerte exakt aus dem Diktat.
- Schreibe im radiologischen Nominalstil.
- SPRACHERKENNUNGSKORREKTUR: Das Diktat kann Spracherkennungsfehler enthalten. Korrigiere offensichtliche Fehler anhand des medizinischen Kontexts (z.B. "Antibiotik" → "Antelisthese", "Strichunkelvertebalatosen" → "Unkovertebralgelenksarthrosen", "Flachbügelingskonvexe" → "flachbogige Konvexität").

## ABSCHNITT "## Ergebnis":
- Fasse alle diagnosewesentlichen Pathologien kurz und stichpunktartig zusammen (nummeriert: 1. 2. 3.).
- Schreibe präzise Diagnosen im Stil der Praxis.
- Bei Normalbefund: 'Unauffälliger Befund.' oder der entsprechende Kurztext.

## KONSISTENZ-REGELN (STRIKT):
1. JEDER pathologische Befund aus dem Diktat MUSS im "## Ergebnis" genannt werden. Keine Diagnose darf fehlen.
2. JEDER pathologische Befund aus dem "## Ergebnis" MUSS auch im "## Befund" beschrieben sein.
3. KEINE WIDERSPRÜCHE: Wenn im Befund eine Pathologie beschrieben wird, darf das Ergebnis nicht "unauffällig" lauten.
4. KEINE WIDERSPRÜCHE: Wenn das Ergebnis eine Diagnose nennt, muss der Befund die entsprechenden morphologischen Kriterien beschreiben.
5. Keine Diagnose darf ERFUNDEN werden, die nicht im Diktat genannt wurde.
6. "ansonsten unauffällig" bezieht sich nur auf nicht genannte Bereiche.
{rules}
</instructions>

<normalbefund_template>
{template_body}
</normalbefund_template>

<diktat>
{raw_text}
</diktat>
"""


def build_validation_prompt(raw_dictation, generated_report, use_conflict_rules=False):
    rules = CONFLICT_RULES if use_conflict_rules else ""
    return f"""Du bist ein radiologischer Qualitätskontrolleur. Du erhältst das ursprüngliche Diktat und den daraus generierten Befund. Prüfe STRENG:

1. VOLLSTÄNDIGKEIT: Jede Pathologie/Diagnose aus dem Diktat muss im Befund (## Befund) UND im Ergebnis (## Ergebnis) vorkommen. Liste fehlende Diagnosen auf.
2. WIDERSPRUCHSFREIHEIT: Befund und Ergebnis dürfen sich nicht widersprechen. Wenn Befund eine Pathologie beschreibt, darf Ergebnis nicht "unauffällig" sein.
3. WIDERSPRUCHSFREIHEIT IM BEFUNDTEXT: Ein Normalbefund-Satz darf NICHT bestehen bleiben, wenn die entsprechende Struktur pathologisch verändert ist. Beispiel: "Bandscheibenräume normal hoch" MUSS gestrichen werden wenn Osteochondrose in einem Segment vorliegt. "Kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" MUSS angepasst werden wenn eine Gelenksarthrose vorliegt.
4. KEINE ERFUNDENE DIAGNOSE: Der Befund darf keine Diagnosen enthalten, die im Diktat nicht erwähnt wurden.
5. ZAHLEN UND MESSWERTE: Alle Zahlen aus dem Diktat müssen exakt im Befund stehen.
6. SPRACHERKENNUNGSKORREKTUR: Prüfe ob offensichtliche Spracherkennungsfehler im Diktat korrekt interpretiert wurden (z.B. "Antibiotik" → "Antelisthese").
{rules}
Wenn der Befund FEHLERFREI ist, gib ihn UNVERÄNDERT zurück.
Wenn es FEHLER gibt, korrigiere den Befund und gib die korrigierte Version zurück.
Gib NUR den fertigen Befundtext aus (mit ## Befund und ## Ergebnis), keine Erklärungen.

<diktat>
{raw_dictation}
</diktat>

<generierter_befund>
{generated_report}
</generierter_befund>

Korrigierter Befund:
"""


def get_bearer_token(key_path):
    creds = Credentials.from_service_account_file(
        str(key_path),
        scopes=["https://www.googleapis.com/auth/generative-language"]
    )
    creds.refresh(grequests.Request())
    return creds.token


def call_gemini(prompt, token, temperature=0.0, timeout=120):
    url = GEMINI_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature}
    }).encode()

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    return text.strip()


def run_test(label, use_conflict_rules_gen=False, use_conflict_rules_val=False):
    print(f"\n{'='*70}")
    print(f"TEST: {label}")
    print(f"{'='*70}")

    # Get token
    token = get_bearer_token(KEY_PATH)

    # Call #1: Generation
    print("\n[CALL #1] Generiere Befund...")
    gen_prompt = build_generation_prompt(RAW_DICTATION, HWS_TEMPLATE, use_conflict_rules=use_conflict_rules_gen)
    t0 = time.time()
    report = call_gemini(gen_prompt, token, temperature=0.1)
    print(f"  Zeit: {time.time()-t0:.1f}s")
    print(f"\n--- Befund nach Call #1 ---")
    print(report)

    # Call #2: Validation
    print("\n[CALL #2] Validiere Befund...")
    val_prompt = build_validation_prompt(RAW_DICTATION, report, use_conflict_rules=use_conflict_rules_val)
    t0 = time.time()
    validated = call_gemini(val_prompt, token, temperature=0.0)
    print(f"  Zeit: {time.time()-t0:.1f}s")

    if validated.strip() == report.strip():
        print("\n✅ Befund war bereits fehlerfrei (keine Korrektur nötig)")
    else:
        print("\n⚠️ Befund wurde korrigiert:")
        print(f"\n--- Befund nach Call #2 (korrigiert) ---")
        print(validated)

    return validated


if __name__ == "__main__":
    # Test 1: Aktueller Stand (ohne Konfliktregeln)
    result1 = run_test(
        "AKTUELL (ohne Konfliktregeln)",
        use_conflict_rules_gen=False,
        use_conflict_rules_val=False
    )

    # Test 2: Mit Konfliktregeln in BOTH prompts
    result2 = run_test(
        "MIT KONFLIKTREGELN (Gen + Val)",
        use_conflict_rules_gen=True,
        use_conflict_rules_val=True
    )

    print(f"\n{'='*70}")
    print("VERGLEICH")
    print(f"{'='*70}")
    print("\n--- Ohne Konfliktregeln ---")
    print(result1[:500])
    print("\n--- Mit Konfliktregeln ---")
    print(result2[:500])