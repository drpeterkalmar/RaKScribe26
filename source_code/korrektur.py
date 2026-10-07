"""Nur-Text-Modus (v3.4.0, Peter 07.10.): Call 0 = korrigierte Spracherkennung ohne Befund — wie die Web-App.

Ablauf: Fehlhör-Liste (auto) → Gemini-Korrektur mit dem Call-0-Prompt der Web-App → Satz-Bausteine einsetzen.
Der Prompt ist WORTGLEICH zu correctionPrompt in web_app/src/gemini.ts (beide gegen
tests/offline/snapshots/call0_prompt.txt geprüft). Scheitert Gemini oder ist die Antwort abgeschnitten/verkürzt
(< 60 % des Rohtextes), bleibt der Rohtext (nach Fehlhör-Liste) stehen — wie correctTranscriptionWithGemini.
Ohne Tk/Windows importierbar, Netz austauschbar (Tests).
"""
import json
import urllib.request

import gemini as _gem

KORREKTUR_PROMPT = 'Du bist ein medizinischer Lektor für radiologische Diktate. Korrigiere Spracherkennungsfehler.\n\n{MISHEARD_PROMPT_BLOCK}\n\n## WICHTIGE REGELN:\n1. Behalte ALLE Pathologien bei — verliere NIEMALS eine Diagnose\n2. "mit" + unklarer Begriff nach Sehnen-Untersuchung → "mit Begleitbursitis"\n3. VERÄNDERE KEINE ZAHLEN! "18 mm" bleibt "18 mm", nicht "1,8 mm". "15 mm²" bleibt "15 mm²". Messwerte sind heilig.\n4. VERÄNDERE KEINE ANATOMISCHEN LOKALISATIONEN! "axillär" bleibt "axillär", nicht "lateral". \n5. KORRIGIERE NUR ECHTE SPRACHERKENNUNGSFEHLER (Unsinnswörter, falsch gehörte Silben). Ein korrekt erkannter Fachbegriff bleibt WÖRTLICH stehen — NIEMALS durch einen "präziseren" oder anderen Fachbegriff ersetzen ("Gelenksarthrose" bleibt "Gelenksarthrose", NICHT "Uncovertebralarthrose"; "Diskopathie" bleibt "Diskopathie"). NIEMALS zwei diktierte Befunde zusammenziehen ("flachbogige Skoliose nach links, kyphotische Fehlhaltung" bleiben ZWEI Befunde).\n6. Gib NUR den korrigierten Text aus, keine Erklärungen\n7. "Baustein" + Kürzel (z. B. "Baustein Mammo 1", "Baustein Ösophagus 2", "Baustein usob", "Baustein A1") ist ein Textbaustein der Ordination: Wort "Baustein" und Kürzel WÖRTLICH stehen lassen, nicht ausschreiben, nicht übersetzen.\n\n## FEW-SHOT BEISPIELE:\nRoh: "Tendinopathie und den Genusses pinnatus Sehne mit begleitet ist, ansonsten nur noch völlig"\nKorrigiert: "Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis, ansonsten unauffällig"\n\nRoh: "Mammasonographie beidseits, thrombosierte Hautvenen links im axillären Quadranten, auslaufend in die linke Axilla bis 18 mm Durchmesser im Sinne eines Morbus Mondor, ansonsten beidseits unauffällig, Pirates 2"\nKorrigiert: "Mammasonographie beidseits: Thrombosierte Hautvenen links im axillären Quadranten, auslaufend in die linke Axilla bis 18 mm Durchmesser im Sinne eines Morbus Mondor, ansonsten beidseits unauffällig. BI-RADS 2."\n\nRoh: "Röntgen und der Sonographie des linken Schultergelenkes tenosynovitis der langen Bizepssehne tendinopathie und den Genusses pinnatus Sehne mit begleitet ist, ansonsten nur noch völlig"\nKorrigiert: "Röntgen und Sonographie des linken Schultergelenkes: Tenosynovitis der langen Bizepssehne, Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis, ansonsten unauffällig"\n\nRoh: {rawText}\n\nKorrigiert:'


def prompt(misheard_block, roh):
    return KORREKTUR_PROMPT.replace("{MISHEARD_PROMPT_BLOCK}", misheard_block or "").replace("{rawText}", roh)


def korrigieren(roh, key, misheard_block="", endpoint=_gem.VERTEX_ENDPOINT, urlopen=None, log=None):
    """Rohtext (Fehlhör-Liste schon angewandt) → korrigierter Text; bei jedem Problem der Rohtext."""
    urlopen = urlopen or urllib.request.urlopen
    log = log or (lambda *a: None)
    if not roh or not key:
        return roh
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt(misheard_block, roh)}]}],
        "generationConfig": {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    req = urllib.request.Request(endpoint, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        if "error" in result:
            raise Exception(result["error"].get("message", result["error"]))
        cand = result["candidates"][0]
        txt = _gem.strip_fences(_gem.join_text(cand).strip())
    except Exception as e:
        log(f"[KORREKTUR] fehlgeschlagen: {e} — verwende Rohtext")
        return roh
    if not txt or not _gem.finish_ok(cand) or len(txt) < len(roh.strip()) * 0.6:
        log("[KORREKTUR] unvollständig/verkürzt — verwende Rohtext")
        return roh
    return txt
