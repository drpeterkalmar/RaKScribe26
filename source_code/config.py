"""config.ini der EXE robust laden (Umbau Schritt 10, Gutachten P2-4) — ohne Tk/Windows importierbar.

- Jede Einstellung hat einen Standardwert; eine fehlende Zeile ist kein Fehler.
- Unbrauchbarer Wert (z. B. RAG_BEISPIELE = 7s) → Standardwert + Warnung im Log.
- Fehlende Datei → Standardwerte, Datei wird mit den Standardwerten angelegt.
- Nur ein echter Lesefehler (configparser.Error, z. B. fehlender [SETTINGS]-Kopf, doppelte Schlüssel) ist fatal:
  KonfigFehler mit Klartext — RaKScribe.py zeigt ihn als Dialog und beendet sich.
- Nicht mehr ausgewertet (still ignoriert, falls noch in alten Dateien): CHUNK_DURATION, STT_ENGINE,
  GOOGLE_JSON_FILENAME. Schlüssel kommen seit v3.2.3 nur aus dem Praxis-Schlüssel (kaiscribe-praxis-key.json, keys.py).
"""
import configparser
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

import senf_anzeige as _senf

STANDARD_INHALT = (
    "[SETTINGS]\n"
    "# Befund-KI: gemini (Vertex AI, gemini-3.5-flash am EU-Endpoint — Schlüssel aus kaiscribe-praxis-key.json)\n"
    "LLM_PROVIDER = gemini\n"
    "LLM_MODEL = gemini-3.5-flash\n"
    "# Anbieter: anthropic (Standard seit 16.11.2026: Claude Sonnet 5.5, Text maskiert; Schlüssel anthropic_api_key in\n"
    "# kaiscribe-praxis-key.json) | gemini (Handschalter)\n"
    "LLM_ANBIETER = anthropic\n"
    "ANTHROPIC_MODELL = claude-sonnet-5-5\n"
    "ANTHROPIC_FRIST = 45\n"
    "# KI_RUECKFALL = aus (Standard seit 24.11.2026): kein automatischer Gemini-Aufruf; Claude ein zweites Mal, dann\n"
    "# ohne KI (Diktat unformatiert + rote Prüfzeile). an = alter Weg (Problem → Gemini)\n"
    "KI_RUECKFALL = aus\n"
)


class KonfigFehler(Exception):
    """config.ini ist nicht lesbar (Syntaxfehler) — Klartext für den Dialog."""


@dataclass
class Config:
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.5-flash"
    api_key: str = ""           # nur für LLM_PROVIDER = openai/ollama (Gemini: Praxis-Schlüssel)
    # kaiscribe-haiku-ab-n1 (13.11.2026): Befund-KI-Anbieter gemini (Standard) | anthropic (maskiert, Rückfall Gemini);
    # LLM_ANBIETER_KORREKTUR nur für Call 0 (leer = wie LLM_ANBIETER), ANTHROPIC_MODELL, ANTHROPIC_FRIST (s).
    # kaiscribe-sonnet-n2 (Peter 14.11.2026 „go“): Standard anthropic + Claude Sonnet 5.5, Gemini nur noch Rückfall.
    llm_anbieter: str = "anthropic"
    llm_anbieter_korrektur: str = ""
    anthropic_modell: str = "claude-sonnet-5-5"
    anthropic_frist: int = 45   # kaiscribe-ohne-gemini-n1 (24.11.2026): 45 s statt 20 s (kein Gemini mehr dahinter)
    # kaiscribe-ohne-gemini-n1 (Peter 23.11.2026 „no gemini please derzeit“): KI_RUECKFALL = aus (Standard) → nie Gemini
    # automatisch; an = alter Weg (Anthropic-Problem → derselbe Aufruf über Gemini)
    ki_rueckfall: bool = False
    rag_beispiele: int = 0      # v3.2: Praxis-Beispiele aus practice_reports.db, Standard AUS
    # v3.18.5 (Nachtrag RH 99): Lauf-Protokoll je Befund (STT-Text, Vorschlag, Modell, Prompt-Stand), auch ohne EOL;
    # LAUF_ORDNER = aus → nie. Fehlt das Laufwerk, schreibt KaiScribe nichts. kaiscribe-umzug-n1-exe: X:\KaiScribe, solange
    # es den Ordner auf X: noch nicht gibt X:\RaKScribe (umzug.x_pfad beim Schreiben, gilt auch für einen Eintrag in config.ini).
    lauf_ordner: str = "X:\\KaiScribe\\Daten\\laeufe"
    # kaiscribe-frog-einsetzen-n1 (Georg 19.11.2026, RH 127): Ablage des IB-Lab-Abholers – daraus holt KaiScribe den
    # FROG-/HIPPO-Text selbst, wenn eine ältere Brücke (< 2.5.20 bzw. < 2.5.22) ihn nicht mitgibt. IBL_ABLAGE = aus → nie.
    ibl_ablage: str = "X:\\IBL-Vorbefunde"
    # kaiscribe-senf-anzeige-n1 (Peter 20.11.2026): Opus-Senf als schreibgeschützter Hinweis beim Öffnen eines CAS-Diktats,
    # nur für Kürzel in SENF_ANZEIGE (Standard kp; „aus“ = niemand). SENF_ORDNER = Ablage der VM (nur lesend).
    senf_anzeige: List[str] = field(default_factory=lambda: ["kp"])
    senf_ordner: str = _senf.SENF_ORDNER_STANDARD
    # senf-ibl-speechmagic-paste-n1 (Peter 21.11.2026): Senf / auffällige IB-Lab-Sätze automatisch ins SpeechMagic-Fenster,
    # nur für diese Kürzel (Standard kp, „aus“ = niemand); zusätzlich zentrale Freigabe-Datei (sm_einfuegen.py).
    sm_senf: List[str] = field(default_factory=lambda: ["kp"])
    sm_ibl: List[str] = field(default_factory=lambda: ["kp"])
    # chirp-fachwortliste-n1 (Peter 24.11.2026): zusätzliche Fachwortliste aus SpeechMagic-Briefen für chirp_3
    # (phrases.json chirp_sm, stt.CHIRP_SM_BOOST), nur für diese Kürzel. Standard aus (Messung 24.11.: bei kp nicht besser).
    chirp_sm: List[str] = field(default_factory=list)
    # kaiscribe-live-anzeige-aus-kp-n1 (Peter 24.11.2026 „Ja“ auf Vorschlag 1): für diese Kürzel KEINE Live-Anzeige
    # (kein Google-Streaming, keine Abschnitts-Reparatur je SpeechMike-Pause) – der Text kommt erst nach Stopp/INS aus
    # chirp_3. Standard kp; „aus“ = niemand (alle wieder mit Live-Anzeige = Rollback-Schalter). Ohne CAS-Auftrag → Live an.
    live_anzeige_aus: List[str] = field(default_factory=lambda: ["kp"])
    # kaiscribe-stt-tagesdeckel-n1 (Peter 24.11.2026): harter Tagesdeckel Google-Spracherkennung je PC in Minuten Audio
    # (chirp_3 + Live-Anzeige, Wiederholungen mitgezählt; Tageswechsel 00:00 Wien). Normal 15–30 min/Tag → greift nie.
    stt_tagesdeckel_min: int = 240
    sm_uebernehmen_taste: str = "ctrl+alt+s"   # Nachtrag 21.11. 21:13: „Übernehmen“ = [SENF]-Marken weg (aus = keine Taste)
    maske_tasten: Dict[str, str] = field(default_factory=dict)  # v3.15.0: [MASKE] NAECHSTES_FELD = FF … (überschreibt masken.json)
    maske_tasten_ambient: Dict[str, str] = field(default_factory=dict)  # v3.15.4: [MASKE] AMBIENT_UEBERNEHMEN = PLAY …
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


ALT_FRIST = 20   # bis 3.23.x mitgelieferter Standard (darunter lief Gemini) — steht in den config.ini der Ordi-PCs


def _an_aus(sek, name, standard, warnungen):
    roh = sek.get(name, "").strip().lower()
    if not roh:
        return standard
    if roh in ("an", "ein", "ja", "1", "true", "gemini"):
        return True
    if roh in ("aus", "nein", "0", "false"):
        return False
    warnungen.append(f"config.ini: {name} = {roh!r} unbekannt (an|aus) — {'an' if standard else 'aus'} wird verwendet.")
    return standard


ANBIETER = ("gemini", "anthropic")   # später: lokales Modell (VM) als dritter Anbieter


def _anbieter(sek, name, standard, warnungen):
    roh = sek.get(name, "").strip().lower()
    if not roh:
        return standard
    if roh not in ANBIETER:
        warnungen.append(f"config.ini: {name} = {roh!r} unbekannt (gemini|anthropic) — gemini wird verwendet.")
        return "gemini"
    return roh


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
    cfg.llm_anbieter = _anbieter(sek, "LLM_ANBIETER", "anthropic", cfg.warnungen)
    cfg.llm_anbieter_korrektur = _anbieter(sek, "LLM_ANBIETER_KORREKTUR", "", cfg.warnungen)
    cfg.anthropic_modell = (sek.get("ANTHROPIC_MODELL", "") or cfg.anthropic_modell).strip()
    cfg.anthropic_frist = max(3, _int(sek, "ANTHROPIC_FRIST", 45, cfg.warnungen))
    if cfg.anthropic_frist == ALT_FRIST:   # ohne-gemini-n1: alte Standardzeile „ANTHROPIC_FRIST = 20“ der PCs → neuer Standard
        cfg.anthropic_frist = 45
    cfg.ki_rueckfall = _an_aus(sek, "KI_RUECKFALL", False, cfg.warnungen)
    cfg.lauf_ordner = (sek.get("LAUF_ORDNER", "") or cfg.lauf_ordner).strip().strip('"')
    cfg.ibl_ablage = (sek.get("IBL_ABLAGE", "") or cfg.ibl_ablage).strip().strip('"')
    if "SENF_ANZEIGE" in sek:
        cfg.senf_anzeige = _senf.kuerzel_liste(sek.get("SENF_ANZEIGE", ""))  # kp | kp, mh | [kp] | aus
    cfg.senf_ordner = (sek.get("SENF_ORDNER", "") or cfg.senf_ordner).strip().strip('"')
    if "SM_SENF" in sek:
        cfg.sm_senf = _senf.kuerzel_liste(sek.get("SM_SENF", ""))      # kp | kp, mh | aus
    if "SM_IBL" in sek:
        cfg.sm_ibl = _senf.kuerzel_liste(sek.get("SM_IBL", ""))
    if "CHIRP_SM" in sek:
        cfg.chirp_sm = _senf.kuerzel_liste(sek.get("CHIRP_SM", ""), standard=())   # kp | kp, rg | aus
    if "LIVE_ANZEIGE_AUS" in sek:
        cfg.live_anzeige_aus = _senf.kuerzel_liste(sek.get("LIVE_ANZEIGE_AUS", ""), standard=())  # kp | kp, rg | aus
    cfg.stt_tagesdeckel_min = _int(sek, "STT_TAGESDECKEL_MIN", 240, cfg.warnungen)
    if cfg.stt_tagesdeckel_min <= 0:      # tagesdeckel-n1: kein „aus“ – ohne Deckel gäbe es bei chirp_3 keine Grenze
        cfg.warnungen.append(f"config.ini: STT_TAGESDECKEL_MIN = {cfg.stt_tagesdeckel_min} — muss > 0 sein, "
                             "Standardwert 240 wird verwendet.")
        cfg.stt_tagesdeckel_min = 240
    cfg.sm_uebernehmen_taste = (sek.get("SM_UEBERNEHMEN_TASTE", "") or cfg.sm_uebernehmen_taste).strip().lower()
    # v3.15.0 (Peter 14.10., Mammo-Maske): Tastenbelegung der Maske, z. B. [MASKE] NAECHSTES_FELD = FF INSTR
    if parser.has_section("MASKE"):
        for name in ("NAECHSTES_FELD", "VORIGES_FELD", "UEBERNEHMEN", "MASKE_UMSCHALTEN"):
            wert = parser["MASKE"].get(name, "").strip()
            if wert:
                cfg.maske_tasten[name.lower()] = wert
            wert = parser["MASKE"].get("AMBIENT_" + name, "").strip()   # v3.15.4: SpeechMike Ambient (ohne F1–F4)
            if wert:
                cfg.maske_tasten_ambient[name.lower()] = wert
    return cfg


def einmalig(merker_pfad, text):
    """Merker für einmalige Hinweise (Umbau Schritt 24, Gutachten P3-4): True genau beim ersten Mal je Hinweistext.
    Der Merker liegt in %APPDATA%\\KaiScribe (überlebt EXE-Updates). Lesefehler → Hinweis zeigen;
    Schreibfehler → trotzdem zeigen (lieber einmal zu oft als nie)."""
    schluessel = hashlib.sha1((text or "").encode("utf-8")).hexdigest()
    try:
        with open(merker_pfad, encoding="utf-8") as f:
            gesehen = set(json.load(f))
    except (OSError, ValueError, TypeError):
        gesehen = set()
    if schluessel in gesehen:
        return False
    gesehen.add(schluessel)
    try:
        os.makedirs(os.path.dirname(merker_pfad) or ".", exist_ok=True)
        with open(merker_pfad, "w", encoding="utf-8") as f:
            json.dump(sorted(gesehen), f)
    except OSError:
        pass
    return True
