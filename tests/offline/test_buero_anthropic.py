"""Gate (kaiscribe-sonnet-n2): Büro-PC-Helfer tools/buero/kaiscribe_anthropic.py — config.ini umstellen (und zurück),
Anthropic-Schlüssel in die Praxis-Schlüsseldatei übernehmen (Sicherung, andere Felder unverändert, nie ausgegeben),
Probe nur mit einer EXE-Kopie. Ohne Windows, ohne Netz. Aufruf: python3 tests/offline/test_buero_anthropic.py"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "buero"), str(ROOT / "source_code")]
import config  # noqa: E402
import kaiscribe_anthropic as ka  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


d = pathlib.Path(tempfile.mkdtemp(prefix="rks_ka_"))
ALT_INI = "[SETTINGS]\r\nLLM_PROVIDER = gemini\r\nLLM_MODEL = gemini-3.5-flash\r\n\r\n[MASKE]\r\nNAECHSTES_FELD = FF\r\n"
neu = ka.config_setzen(ALT_INI, ka.WERTE["anthropic"])
p = d / "config.ini"
p.write_text(neu, encoding="utf-8")
c = config.load_config(str(p))
check("config: X:-Stand (ohne LLM_ANBIETER) → anthropic/Sonnet/20 s", (c.llm_anbieter, c.anthropic_modell, c.anthropic_frist)
      == ("anthropic", "claude-sonnet-5-5", 20) and not c.warnungen, (c.llm_anbieter, c.anthropic_modell, c.warnungen))
check("config: Zeilen landen in [SETTINGS], [MASKE] bleibt", c.maske_tasten.get("naechstes_feld") == "FF"
      and neu.index("LLM_ANBIETER") < neu.index("[MASKE]"), neu)
check("config: zweites Setzen ändert nichts", ka.config_setzen(neu, ka.WERTE["anthropic"]).strip() == neu.strip())
zur = ka.config_setzen(neu, ka.WERTE["gemini"])
p.write_text(zur, encoding="utf-8")
check("config: Notschalter gemini ersetzt die Zeile", config.load_config(str(p)).llm_anbieter == "gemini"
      and zur.count("LLM_ANBIETER") == 1 + neu.count("LLM_ANBIETER = gemini"), zur)
check("config: Ausgabe nur Köpfe + LLM_/ANTHROPIC_", all(z.startswith(("[", "LLM_", "ANTHROPIC_")) for z in ka.config_zeilen(neu)))

k = d / "rakscribe-praxis-key.json"
k.write_bytes(b"\xef\xbb\xbf" + json.dumps({"vertex_api_key": "AQ.x", "stt": {"private_key": "-----"}}).encode())
erg, sich = ka.schluessel_einsetzen(str(k), "sk-ant-test", str(d / "_alt"))
z = ka.lese_json(str(k))
check("Schlüssel eingesetzt, andere Felder gleich, Sicherung da", erg == "ok" and z["anthropic_api_key"] == "sk-ant-test"
      and z["vertex_api_key"] == "AQ.x" and z["stt"] == {"private_key": "-----"} and pathlib.Path(sich).exists(), z)
check("Schlüssel: zweites Mal = schon", ka.schluessel_einsetzen(str(k), "sk-ant-test", str(d / "_alt")) == ("schon", None))
sys.path.insert(0, str(ROOT / "source_code"))
import keys  # noqa: E402
check("EXE liest den Schlüssel aus der Datei neben der EXE", keys.load_anthropic_key(str(d), str(d / "nix")) == "sk-ant-test")


class Antwort:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


gesendet = []
check("Mini-Prüfaufruf: Status 200, max. 5 Token, kein Patiententext",
      ka.anthropic_pruefen("sk", urlopen=lambda req, timeout: (gesendet.append(json.loads(req.data)), Antwort())[1]) == "200"
      and gesendet[0]["max_tokens"] == 5 and gesendet[0]["messages"][0]["content"] == "Antworte nur: OK")

out = io.StringIO()
with contextlib.redirect_stdout(out):
    rc = ka.cmd_probe({"--exe": "x:\\rakscribe\\RAKSCRIBE26.exe"})
check("Probe weigert sich bei der Produktions-EXE auf X:", rc == 1 and "nur_mit_kopie" in out.getvalue(), out.getvalue())
check("… auch die neue EXE X:\\KaiScribe\\KaiScribe.exe (kaiscribe-umzug-n1-exe)",
      ka.ist_produktions_exe("X:\\KaiScribe\\KaiScribe.exe") and ka.ist_produktions_exe("x:\\kaiscribe\\rakscribe26.exe"))
check("Probe mit Kopie erlaubt", not ka.ist_produktions_exe("C:\\Users\\cas\\AppData\\Local\\hermes\\work\\ks_tausch\\v3.19.0\\rakscribe26.exe"))
lang = "## Knie\n\n## Befund\n" + "Normalsatz. " * 60 + "\n\n## Ergebnis\n1. Mäßige Gonarthrose links medial."
check("Probe liest den vollen Befund (result_voll), nicht die ersten 600 Zeichen",
      "Gonarthrose" in ka.befund_aus_zustand({"befund": {"result": lang[:600], "result_voll": lang}}))
quelle = (ROOT / "tools" / "buero" / "kaiscribe_anthropic.py").read_text(encoding="utf-8")
check("Helfer gibt den Schlüssel nie aus (kein print mit key)", "print(key" not in quelle and "len(key" not in quelle)

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
