"""Gate (Umbau Schritt 10, Gutachten P2-4): config.ini robust laden — Standardwerte, nur Syntaxfehler fatal.
Aufruf: /usr/bin/python3 tests/offline/test_config.py"""
import pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import config as c  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_cfg_"))


def datei(inhalt, name="config.ini", enc="utf-8"):
    p = tmp / name
    p.write_text(inhalt, encoding=enc)
    return str(p)


p = tmp / "fehlt.ini"
cfg = c.load_config(str(p))
check("fehlende Datei → Standardwerte", (cfg.llm_provider, cfg.llm_model, cfg.api_key, cfg.rag_beispiele)
      == ("gemini", "gemini-3.5-flash", "", 0) and cfg.angelegt)
check("… und Datei wird angelegt (ohne Schlüssel, ohne CHUNK_DURATION)", p.exists()
      and "LLM_PROVIDER = gemini" in p.read_text() and "CHUNK_DURATION" not in p.read_text() and "API_KEY" not in p.read_text())
check("angelegte Datei lädt wieder fehlerfrei", c.load_config(str(p)).warnungen == [])

cfg = c.load_config(datei("[SETTINGS]\nLLM_PROVIDER = gemini\n"))
check("fehlende Zeile LLM_MODEL → Standard, kein Fehler (früher: Programmende)", cfg.llm_model == "gemini-3.5-flash" and not cfg.warnungen)
cfg = c.load_config(datei("[SETTINGS]\nRAG_BEISPIELE = 7s\nCHUNK_DURATION = 7s\n"))
check("'7s' → Standardwert + Warnung", cfg.rag_beispiele == 0 and len(cfg.warnungen) == 1 and "7s" in cfg.warnungen[0], str(cfg.warnungen))
check("alte Schlüssel CHUNK_DURATION/STT_ENGINE/GOOGLE_JSON_FILENAME werden ignoriert (kein Absturz)",
      c.load_config(datei("[SETTINGS]\nCHUNK_DURATION = sieben\nSTT_ENGINE = whisper\nGOOGLE_JSON_FILENAME = x.json\n")).warnungen == [])
cfg = c.load_config(datei("[SETTINGS]\nLLM_PROVIDER = OpenAI\nLLM_MODEL = gpt-4o-mini\nAPI_KEY = \"sk-test\"\nRAG_BEISPIELE = 2\n"))
check("Werte werden übernommen (Provider klein, Anführungszeichen weg)",
      (cfg.llm_provider, cfg.llm_model, cfg.api_key, cfg.rag_beispiele) == ("openai", "gpt-4o-mini", "sk-test", 2))
cfg = c.load_config(datei("﻿[SETTINGS]\nLLM_MODEL = gemini-3.5-flash\n"))
check("Datei mit BOM (Windows-Editor) wird gelesen", cfg.llm_model == "gemini-3.5-flash" and not cfg.warnungen)

for name, inhalt in [("kein [SETTINGS]-Kopf", "LLM_PROVIDER = gemini\n"),
                     ("doppelter Schlüssel", "[SETTINGS]\nLLM_MODEL = a\nLLM_MODEL = b\n")]:
    try:
        c.load_config(datei(inhalt))
        check(f"{name} → Fehler (Klartext)", False)
    except c.KonfigFehler as e:
        check(f"{name} → Fehler (Klartext)", "config.ini" in str(e) and "löschen" in str(e))
cfg = c.load_config(datei("[ANDERES]\nx = 1\n"))
check("anderer Abschnitt ohne [SETTINGS] → Standardwerte + Warnung", cfg.llm_provider == "gemini" and cfg.warnungen)
check("leere Datei → Standardwerte, Datei bleibt unangetastet", c.load_config(datei("")).llm_provider == "gemini"
      and (tmp / "config.ini").read_text() == "")

src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt config.load_config, kein CHUNK_DURATION/STT_ENGINE mehr",
      "_cfg.load_config(CONFIG_FILE_PATH)" in src and "CHUNK_DURATION" not in src and "STT_ENGINE" not in src
      and "except _cfg.KonfigFehler" in src)

print("\n" + ("✅ KONFIGURATION PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
