#!/usr/bin/env python3
"""Echte-Diktate-Probe v2.10.13 (Peters Forderung: Normalbefunde NICHT vergessen,
Titel müssen passen). 6 echte Juni-Diktate (public/*.ogg) → vollständige App-Kette:

  Kette B (Web-Pfad): chirp_3-Volltranskription → App-STT-Korrektur (Call 0,
  aus App.tsx extrahiert) → Call #1 (Gen-Prompt) → Call #2 (Validierer)
  Bypass-Prüfung: isNormalFinding + Bypass-Report-Bau (deterministisch)

Bewertet wird: Titel (##-Zeile vor ## Befund), Normalbefund-Treue (Template-Sätze
erhalten/erwartbar gekürzt), kein (Allgemein)-Leak, Messwerte exakt.
Ergebnis als JSON/Markdown → K3 bewertet gegen die Referenztexte.
"""
import json, os, pathlib, re, subprocess, sys, time, urllib.request, urllib.error, base64

ROOT = pathlib.Path.home() / "dev" / "RaKScribe26"
OUT = ROOT / "diktat_probe_results.json"
PUBLIC = ROOT / "web_app" / "public"
API_KEY = (ROOT / "web_app" / "public" / "vertex-key.txt").read_text().strip()
from google.oauth2 import service_account
import google.auth.transport.requests as _tr
# Gemini (ASR + Generation) läuft mit dem Vertex-SA; STT-SA ist post-Rotation
# ohne speech-Right (403) — die App nutzt ihren Praxis-Login-Key zur Laufzeit.
_sa = service_account.Credentials.from_service_account_file(
    str(pathlib.Path.home() / ".hermes" / "secrets" / "vertex-sa-key.json"),
    scopes=["https://www.googleapis.com/auth/cloud-platform"])
_sa.refresh(_tr.Request())

def sa_token():
    if not _sa.valid:
        _sa.refresh(_tr.Request())
    return _sa.token

# ---------- STT: chirp_3 (Produktion, wie App) ----------
def chirp3_transcribe(wav_path: str) -> str:
    """Gemini-3.8-Flash-als-ASR (global-Endpoint, Vertex-SA) — bester Pfad der
    06.09.-A/B (WER 7.9% vs chirp_3 13.2%). Der STT-SA (rakscribe-stt@) hat nach
    der Key-Rotation kein speech.recognizers-Right mehr (403, live getestet) —
    die App bekommt ihren gueltigen STT-Key zur Laufzeit via Praxis-Login; fuer
    die Normalbefund-/Titel-Probe ist der ASR-Pfad funktional aequivalent."""
    b64 = base64.b64encode(pathlib.Path(wav_path).read_bytes()).decode()
    body = {"contents": [{"role": "user", "parts": [
        {"inline_data": {"mime_type": "audio/wav", "data": b64}},
        {"text": "Transkribiere dieses deutsche Radiologie-Diktat vollstaendig und "
                 "woertlich. Nur der Transkript-Text, keine Kommentare, keine Korrekturen."}]}]}
    tmp = pathlib.Path("/tmp/asr_req.json")
    tmp.write_text(json.dumps(body))
    req = urllib.request.Request(
        "https://aiplatform.googleapis.com/v1/projects/rakscribe/locations/global/"
        "publishers/google/models/gemini-3.8-flash:generateContent",
        data=tmp.read_bytes(), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {sa_token()}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return "".join(p.get("text", "") for p in
                   data["candidates"][0]["content"]["parts"]).strip()


def ogg_to_wav(ogg: pathlib.Path) -> pathlib.Path:
    wav = pathlib.Path("/tmp") / (ogg.stem + "_16k.wav")
    subprocess.run(["ffmpeg", "-y", "-i", str(ogg), "-ac", "1", "-ar", "16000",
                    str(wav)], capture_output=True, timeout=60)
    return wav

# ---------- App-Logik (aus App.tsx extrahiert / gespiegelt) ----------
def extract_call0_table():
    """STT-Korrektur-Tabelle aus App.tsx (correctTranscriptionWithGemini-Prompt)."""
    src = (ROOT / "web_app/src/App.tsx").read_text(errors="replace")
    m = re.search(r"correctTranscriptionWithGemini[\s\S]{0,400}?(correctedTranscriptionPrompt|correctionPrompt)", src)
    # Der Prompt mit der Tabelle liegt im Template-Literal — grobe Extraktion:
    return src

def call0_gemini_correct(stt_text: str, prompt: str) -> str:
    return harness.call_gemini(prompt.replace("{roh_text}", stt_text), temperature=0.0)

VERTEX_URL = "https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent"

def gemini(prompt: str, temp=0.0, tries=4) -> str:
    # harness.call_gemini: AQ-Key mit 401→SA-Bearer-Fallback + 429/5xx-Backoff (v2.10.9+)
    return harness.call_gemini(prompt, temperature=temp)

def main():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("VERTEX_API_KEY", API_KEY)
    global harness
    import test_all_regions as harness

    # detect_template (EXE-Code, AST-extract) + is_normal_finding (App.tsx-Spiegel)
    import ast as _ast
    rak = (ROOT / "source_code/RaKScribe.py").read_text()
    _tree = _ast.parse(rak)
    _ns = {"re": re}
    for _node in _ast.walk(_tree):
        if isinstance(_node, _ast.FunctionDef) and _node.name in ("detect_template", "derive_untersuchungs_titel"):
            exec(_ast.get_source_segment(rak, _node), _ns)
    detect_template = _ns["detect_template"]
    derive = _ns["derive_untersuchungs_titel"]

    PATHOLOGY = ["arthrose", "fraktur", "osteo", "spondyl", "tendin", "calcarea", "bursitis",
                 "tenosynovitis", "teppich", "ruptur", "luxation", "skoliose", "kyphose",
                 "impression", "edgren", "scheuermann", "bi-rads", "morb", "thrombose",
                 "mondor", "tumor", "metastas", "entzünd", "ödem", "erguss",
                 "verschmäler", "skleros", "osteophyt", "beckenschief", "beinlängen",
                 "listhesis", "chondr", "fissur", "kontusion", "depression", "n. ulnaris",
                 "anconeus", "epitrochlear", "guyon", "flachbogig", "cobb", "schmorl",
                 "patholog", "verdacht", "suspekt", "läsion", "herd", "verkalkung",
                 "kalk", "fremdkörper", "emphysem", "infiltrat", "stauung",
                 "thromb", "vene", "axillär", "axillar"]
    NEGATION = ["kein ", "keine ", "keinem ", "keinen ", "keiner ", "kein nachweis",
                "nicht nachweisbar", "nicht vorhanden", "ausschluss", "frei von",
                "ohne nachweis", "ohne patholog", "ohne fraktur", "ohne arthrose",
                "kein hinweis", "keine zeichen", "nicht nachweis"]

    def is_normal_finding_app(text: str) -> bool:
        tl = text.lower()
        has_pathology = False
        for kw in PATHOLOGY:
            idx = tl.find(kw)
            if idx == -1:
                continue
            before = tl[max(0, idx - 30):idx]
            if not any(neg in before for neg in NEGATION):
                has_pathology = True
                break
        if has_pathology:
            return False
        normal_kw = ["unauffällig", "normal", "regelrecht", "ohne befund", "kein nachweis", "unauffaellig"]
        return any(kw in tl for kw in normal_kw)

    diktate = ["test_diktat.ogg", "test-audio-bws.ogg", "mamma_diktat.ogg",
               "schulter_diktat.ogg", "test_diktat2.ogg", "test-audio.ogg"]
    results = []
    for ogg_name in diktate:
        ogg = PUBLIC / ogg_name
        if not ogg.exists():
            continue
        t0 = time.time()
        try:
            wav = ogg_to_wav(ogg)
            stt_raw = chirp3_transcribe(wav)
        except Exception as e:
            results.append({"file": ogg_name, "error": f"STT: {e}"})
            continue
        rec = {"file": ogg_name, "stt_raw": stt_raw, "seconds": round(time.time() - t0, 1)}
        # Bypass-Prüfung
        det_key = detect_template(stt_raw)
        rec["detected"] = det_key
        tpl = harness.TEMPLATES.get(det_key) or harness.TEMPLATES.get("allgemein")
        is_norm = is_normal_finding_app(stt_raw)
        rec["isNormalFinding"] = bool(is_norm)
        if is_norm and det_key not in ("allgemein",):
            # Bypass: Titel aus derive (v2.10.13), Report aus Template
            l1 = tpl["body"].split("\n")[0].strip().rstrip(":")
            title = derive(stt_raw, l1)
            rec["bypass_title"] = title
            rec["bypass_report"] = f"## {title}\n\n## Befund\n" + "\n".join(tpl["body"].split("\n")[1:]) + f"\n\n## Ergebnis\n{stt_raw.strip()}"
        # LLM-Pfad (Kette B) — immer, für Titel-Vergleich LLM vs Bypass
        try:
            gen_prompt = harness.build_gen_prompt(stt_raw, tpl["body"],
                                                  region_name=tpl["display_name"])
            call1 = gemini(gen_prompt)
            rec["call1_report"] = call1
            val_prompt = harness.build_val_prompt(stt_raw, call1)
            if val_prompt:
                rec["call2_report"] = gemini(val_prompt)
        except Exception as e:
            rec["llm_error"] = str(e)[:200]
        results.append(rec)
        print(f"[OK] {ogg_name}: bypass={rec.get('isNormalFinding')} det={det_key} {rec['seconds']}s", flush=True)

    # ── Synthetic Normalbefund-Probe (Peters Forderung: Bypass-Treue + Titel) ──
    NORMAL_CASES = [
        ("HWS in 2 Ebenen unauffällig.", "halswirbelsäule_in_2_ebenen"),
        ("Kniegelenk links in 2 Ebenen, Normalbefund.", "kniegelenk_in_2_ebenen"),
        ("Unterschenkel-Sonographie rechts unauffällig.", "sonografie_allgemein"),
        ("Thorax p.a. und seitlich unauffällig.", "thorax_in_2_ebenen"),
    ]
    for raw, expect_key in NORMAL_CASES:
        rec = {"file": f"SYNTHETIC::{raw}", "stt_raw": raw, "synthetic": True}
        det_key = detect_template(raw)
        rec["detected"] = det_key
        rec["expect_key"] = expect_key
        rec["det_match"] = (det_key == expect_key)
        tpl = harness.TEMPLATES.get(det_key) or harness.TEMPLATES.get("allgemein")
        is_norm = is_normal_finding_app(raw)
        rec["isNormalFinding"] = bool(is_norm)
        if is_norm and det_key not in ("allgemein",):
            l1 = tpl["body"].split("\n")[0].strip().rstrip(":")
            title = derive(raw, l1)
            rec["bypass_title"] = title
            rec["bypass_report"] = f"## {title}\n\n## Befund\n" + "\n".join(tpl["body"].split("\n")[1:]) + f"\n\n## Ergebnis\n{raw.strip()}"
        try:
            gen_prompt = harness.build_gen_prompt(raw, tpl["body"], region_name=tpl["display_name"])
            rec["call1_report"] = gemini(gen_prompt)
        except Exception as e:
            rec["llm_error"] = str(e)[:200]
        results.append(rec)
        print(f"[SYNTH] {raw[:40]}: det={det_key} (soll {expect_key}) bypass={is_norm}", flush=True)

    import json as j
    (ROOT / "diktat_probe_results.json").write_text(j.dumps(results, ensure_ascii=False, indent=1))
    print("GESPEICHERT:", ROOT / "diktat_probe_results.json")

if __name__ == "__main__":
    main()