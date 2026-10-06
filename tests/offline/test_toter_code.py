"""Gate (Umbau Schritt 24, Gutachten P3-1/P3-2/P3-4): toter Code bleibt weg, Prompt-Hinweis nur einmal je Datei.
Aufruf: /usr/bin/python3 tests/offline/test_toter_code.py"""
import pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import config  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
for weg in ("def transcribe_full_chirp3", "def numpy_to_wav_bytes", "import pyperclip", "get_close_matches",
            "engine_label", "prompt_toggle", "ALLGEMEIN_FALLBACK = {", "fallback=ALLGEMEIN_FALLBACK", "import queue",
            "import wave", "import io\n"):
    check(f"EXE: {weg.strip()} entfernt", weg not in exe)
web = (ROOT / "web_app" / "src" / "App.tsx").read_text(encoding="utf-8")
for weg in ("const ALLGEMEIN_FALLBACK", "fallback: ALLGEMEIN_FALLBACK", "system_prompt_version', PROMPT_VERSION", "setSystemPrompt",
            "(window as any)"):
    check(f"Web: {weg} entfernt", weg not in web)
check("leere download.html (2×) entfernt", not (ROOT / "web_app" / "download.html").exists()
      and not (ROOT / "web_app" / "src" / "download.html").exists())
check("requirements.txt ohne pyperclip", "pyperclip" not in (ROOT / "requirements.txt").read_text())

merker = pathlib.Path(tempfile.mkdtemp(prefix="rks_merker_")) / "RaKScribe" / "gezeigte_hinweise.json"
h1 = "Alte Datei radiology_prompt_v4.txt ohne Versionsmarker"
check("Prompt-Hinweis: beim ersten Start zeigen", config.einmalig(str(merker), h1) is True and merker.exists())
check("… beim zweiten Start nicht mehr", config.einmalig(str(merker), h1) is False)
check("… andere Datei/Version → wieder einmal zeigen", config.einmalig(str(merker), h1 + " (2026-11-01-a)") is True)
merker.write_text("kaputt")
check("kaputter Merker → Hinweis zeigen (lieber einmal zu oft)", config.einmalig(str(merker), h1) is True)
check("EXE nutzt den Merker", "_cfg.einmalig(os.path.join(USER_KEY_DIR, \"gezeigte_hinweise.json\"), PROMPT_HINWEIS)" in exe)

print("\n" + ("✅ TOTER CODE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
