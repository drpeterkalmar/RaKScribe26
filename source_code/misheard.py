"""misheard.py — Fehlhör-Liste (misheard_words.json) für die EXE.

Gleiche Semantik wie web_app/src/misheard.ts. Regeln NUR in der JSON pflegen.
  auto-Regeln: deterministische Ersetzung (Unicode-Wortgrenzen, Groß/Klein egal, Leerzeichen
               tolerant) — läuft auf dem chirp_3-Volltranskript VOR Normalbefund-Bypass/LLM.
  llm-Regeln : nur als <stt_hinweise>-Block im Gen-Prompt (kontextabhängig).

Suchreihenfolge der JSON: neben der EXE (editierbar, gewinnt) → PyInstaller-Bundle (_MEIPASS)
→ Repo-Root (Entwicklung). Fehlt alles: keine Ersetzung, kein Absturz.
"""
import json
import os
import re
import sys

_FILE = "misheard_words.json"


def _candidates(base_dir):
    yield os.path.join(base_dir, _FILE)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        yield os.path.join(meipass, _FILE)
    here = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(here, "..", _FILE)
    yield os.path.join(here, _FILE)


def load(base_dir):
    """v3.2.1: Die NEUESTE Liste gewinnt (Feld "version", z. B. "2026-10-05b" — lexikographisch sortierbar).
    Vorher gewann immer die Datei neben der EXE, auch wenn sie aus einem alten Release stammte und das
    Update eine neuere Liste mitbrachte (neue Verhörer kamen dann nie an). Bei Gleichstand gewinnt die
    Datei neben der EXE (= dort editierte Liste)."""
    best = None
    for p in _candidates(base_dir):
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        data["_path"] = p
        if best is None or str(data.get("version", "")) > str(best.get("version", "")):
            best = data
    return best or {"version": "none", "rules": [], "_path": None}


def _escape_literal(s):
    return r"\s+".join(re.escape(tok) for tok in s.strip().split())


def compile_rules(data):
    out = []
    for r in data.get("rules", []):
        if r.get("mode") != "auto":
            continue
        repl = re.sub(r"\$(\d)", r"\\\1", r["mean"])
        for h in r["hear"]:
            core = h if r.get("regex") else _escape_literal(h)
            out.append((re.compile(r"(?<!\w)(?:" + core + r")(?!\w)", re.IGNORECASE), repl))
    return out


def apply(text, compiled):
    for rx, repl in compiled:
        text = rx.sub(repl, text)
    return text


def _fmt(r):
    shown = " / ".join(f'"{h}"' for h in r.get("show") or r["hear"])
    note = f" ({r['note']})" if r.get("note") else ""
    return f"- {shown} → \"{r.get('mean_show') or r['mean']}\"{note}"


def prompt_block_web(data):
    """Exakt der Block, den die Web-App in Call 0 einsetzt (Spiegel von misheardPromptBlock in misheard.ts)."""
    rules = data.get("rules", [])
    stt = [r for r in rules if r.get("group", "stt") != "jargon"]
    jargon = [r for r in rules if r.get("group") == "jargon"]
    return "\n".join(["## BEKANNTE STT-FEHLER (automatisch korrigieren):", *map(_fmt, stt), "",
                      "## PRAXIS-JARGON (Dr. Kalmar / Dr. Riegler Shortcut-Phrasen):", *map(_fmt, jargon)])


def prompt_block(data, only_llm=True):
    """<stt_hinweise> für den Gen-Prompt der EXE (auto-Regeln sind dann schon ersetzt)."""
    rules = [r for r in data.get("rules", []) if not only_llm or r.get("mode") == "llm"]
    if not rules:
        return ""
    lines = ["<stt_hinweise>",
             "Bekannte Spracherkennungs-Verhörer (chirp_3). Korrigiere sie NUR, wenn der Kontext passt; "
             "Zahlen, Seitenangaben und korrekt erkannte Fachbegriffe bleiben unverändert:"]
    lines += [_fmt(r) for r in rules]
    lines.append("</stt_hinweise>")
    return "\n".join(lines)
