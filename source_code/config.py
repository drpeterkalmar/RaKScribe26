"""config.ini der EXE robust laden (Umbau Schritt 10, Gutachten P2-4) — ohne Tk/Windows importierbar.

- Jede Einstellung hat einen Standardwert; eine fehlende Zeile ist kein Fehler.
- Unbrauchbarer Wert (z. B. RAG_BEISPIELE = 7s) → Standardwert + Warnung im Log.
- Fehlende Datei → Standardwerte, Datei wird mit den Standardwerten angelegt.
- Nur ein echter Lesefehler (configparser.Error, z. B. fehlender [SETTINGS]-Kopf, doppelte Schlüssel) ist fatal:
  KonfigFehler mit Klartext — RaKScribe.py zeigt ihn als Dialog und beendet sich.
- Nicht mehr ausgewertet (still ignoriert, falls noch in alten Dateien): CHUNK_DURATION, STT_ENGINE,
  GOOGLE_JSON_FILENAME. Schlüssel kommen seit v3.2.3 nur aus rakscribe-praxis-key.json.
"""
import configparser
import os
from dataclasses import dataclass, field
from typing import List

STANDARD_INHALT = (
    "[SETTINGS]\n"
    "# Befund-KI: gemini (Vertex AI, gemini-3.5-flash am EU-Endpoint — Schlüssel aus rakscribe-praxis-key.json)\n"
    "LLM_PROVIDER = gemini\n"
    "LLM_MODEL = gemini-3.5-flash\n"
)


class KonfigFehler(Exception):
    """config.ini ist nicht lesbar (Syntaxfehler) — Klartext für den Dialog."""


@dataclass
class Config:
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.5-flash"
    api_key: str = ""           # nur für LLM_PROVIDER = openai/ollama (Gemini: Praxis-Schlüssel)
    rag_beispiele: int = 0      # v3.2: Praxis-Beispiele aus practice_reports.db, Standard AUS
    angelegt: bool = False      # Datei fehlte und wurde mit Standardwerten angelegt
    warnungen: List[str] = field(default_factory=list)


def _int(sek, name, standard, warnungen):
    roh = sek.get(name, "").strip()
    if not roh:
        return standard
    try:
        return int(roh)
    except ValueError:
        warnungen.append(f"config.ini: {name} = {roh!r} ist keine Zahl — Standardwert {standard} wird verwendet.")
        return standard


def load_config(path):
    """Liest config.ini; legt sie an, wenn sie fehlt. Wirft nur KonfigFehler (Syntaxfehler)."""
    cfg = Config()
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(STANDARD_INHALT)
            cfg.angelegt = True
        except OSError as e:
            cfg.warnungen.append(f"config.ini fehlte und konnte nicht angelegt werden ({e}) — Standardwerte aktiv.")
        return cfg

    parser = configparser.ConfigParser()
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            parser.read_file(f)
    except configparser.Error as e:
        raise KonfigFehler(
            "Die Datei 'config.ini' ist fehlerhaft und kann nicht gelesen werden.\n\n"
            f"Pfad: {path}\n\nDetails: {e}\n\n"
            "Bitte die Datei korrigieren oder löschen — beim nächsten Start wird sie neu angelegt.") from e

    if not parser.has_section("SETTINGS"):
        cfg.warnungen.append("config.ini enthält keinen Abschnitt [SETTINGS] — Standardwerte aktiv.")
        return cfg
    sek = parser["SETTINGS"]
    cfg.llm_provider = (sek.get("LLM_PROVIDER", "") or cfg.llm_provider).strip().lower()
    cfg.llm_model = (sek.get("LLM_MODEL", "") or cfg.llm_model).strip()
    cfg.api_key = sek.get("API_KEY", "").strip().replace('"', '')
    cfg.rag_beispiele = _int(sek, "RAG_BEISPIELE", 0, cfg.warnungen)
    return cfg
