"""tools/call0_prompt.py — baut den Call-0-Prompt (STT-Korrektur) EXAKT wie die Web-App.

Seit v3.1 steht im Web-Template `${MISHEARD_PROMPT_BLOCK}` statt der handgepflegten Tabelle (seit Umbau Schritt 18
in web_app/src/gemini.ts correctionPrompt);
Harness-/Verify-Skripte dürfen den Prompt daher nicht mehr per Regex + rawText-Replace allein bauen.

    from call0_prompt import build_call0_prompt
    prompt = build_call0_prompt(roh_text)   # auto-Regeln angewandt + Block eingesetzt + rawText gefüllt
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)
sys.path.insert(0, str(ROOT / "source_code"))
import misheard  # noqa: E402

_DATA = misheard.load(str(ROOT))
_COMPILED = misheard.compile_rules(_DATA)


def call0_template():
    src = (ROOT / "web_app" / "src" / "gemini.ts").read_text()
    m = re.search(r"export const correctionPrompt = \(MISHEARD_PROMPT_BLOCK: string, rawText: string\): string => `(.*?)`;", src, re.S)
    assert m, "correctionPrompt nicht in web_app/src/gemini.ts gefunden"
    tpl = m.group(1)
    assert "${MISHEARD_PROMPT_BLOCK}" in tpl, "App.tsx-Call-0-Prompt ohne ${MISHEARD_PROMPT_BLOCK} — Skript veraltet?"
    return tpl.replace("${MISHEARD_PROMPT_BLOCK}", misheard.prompt_block_web(_DATA))


def apply_auto(raw):
    return misheard.apply(raw, _COMPILED)


def build_call0_prompt(raw):
    tpl = call0_template()
    leftovers = re.findall(r"\$\{[^}]*\}", tpl)
    assert leftovers == ["${rawText}"], f"unerwartete Platzhalter im Call-0-Prompt: {leftovers}"
    return tpl.replace("${rawText}", apply_auto(raw))
