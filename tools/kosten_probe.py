"""Kosten je Befund-Aufruf vorher/nachher (kaiscribe-kosten-je-befund-n1, 25.11.2026) — nur synthetische Diktate,
Anthropic Testkonto B über tools/testkosten.py (Kostengrenze je Job/Tag).

  python3 tools/kosten_probe.py [--laeufe 2] [--faelle 4] [--aus ~/cj/work/kaiscribe-kosten-je-befund-n1/probe.json]

Je Fall läuft die EXE-Kette (pipeline.befund_aus_diktat wie RaKScribe.py) mit Claude Sonnet 5.5 maskiert, und zwar
  vorher  = Gen-Prompt mit Windows-Zeilenenden (CRLF), so wie er in der EXE steckt (Windows-Checkout, * text=auto),
            aber OHNE die Korrektur aus diesem Job (fester_anfang findet die Marke nicht → kein Cache),
  nachher = derselbe Prompt mit LF (= nach br.prompt_normalisieren beim Laden).
Gemessen: usage (input, cache lesen/schreiben 5m/1h, output), Inhaltstypen der Antwort (thinking-Blöcke?), $ je Aufruf,
Endtext je Lauf. Ausgabe: Tabelle + JSON-Datei (Texte nur synthetisch).
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "source_code"))
import prod_pipeline as pp  # noqa: E402
import test_all_regions as H  # noqa: E402
import testkosten as tk  # noqa: E402
import llm_anbieter as la  # noqa: E402
import gemini as _g  # noqa: E402

DATUM_FALL = ("Thorax mit Vergleich", None, "Thorax p.a. und seitlich, im Vergleich zur Voraufnahme vom 12.3.2025 "
              "unverändert kleine Plattenatelektase basal rechts, kein Infiltrat, kein Erguss. Ansonsten unauffällig.", [])


def fester_anfang_alt(prompt):
    """fester_anfang() im Stand VOR diesem Job (nur LF-Marke) — damit „vorher“ auch nach dem Fix messbar bleibt."""
    marke = "<normalbefund_template>\n"
    i = prompt.find(marke)
    if i > 0 and "<diktat>" not in prompt[:i] and "<diktat>" in prompt[i:]:
        return prompt[:i + len(marke)]
    return ""


def lauf(diktat, prompt, alt):
    aufrufe = []
    roh_sender = tk._anthropic_test_sender("gen")

    def sender(body, frist):
        data = roh_sender(body, frist)
        aufrufe.append({"usage": data.get("usage", {}), "typen": [b.get("type") for b in data.get("content", [])],
                        "cache_control": any("cache_control" in t for t in body["messages"][0]["content"]),
                        "stop": data.get("stop_reason")})
        return data
    infos = []
    w = la.Weiche("anthropic", la.ANTHROPIC_MODELL, sender=sender, log=lambda *a: None, beobachter=infos.append,
                  gemini_fn=lambda p, s: tk.RUECKFALL_GESPERRT)
    llm = lambda p: w(p, pp.SYS_MSG, pruefen=_g.report_complete, rolle="gen", strip=_g.strip_fences)  # noqa: E731
    fa = la.fester_anfang
    if alt:
        la.fester_anfang = fester_anfang_alt
    try:
        text = pp.exe_kette(diktat, prompt=prompt, llm=llm)
    finally:
        la.fester_anfang = fa
    return text, aufrufe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laeufe", type=int, default=2)
    ap.add_argument("--faelle", type=int, default=4)
    ap.add_argument("--aus", default=str(pathlib.Path.home() / "cj/work/kaiscribe-kosten-je-befund-n1/probe.json"))
    a = ap.parse_args()
    tk._anthropic_key()
    faelle = [H.TEST_CASES[i] for i in range(a.faelle - 1)] + [DATUM_FALL]
    lf = pp.GEN_PROMPT_RAW.replace("\r\n", "\n")
    crlf = lf.replace("\n", "\r\n")
    erg = []
    for art, prompt, alt in (("vorher", crlf, True), ("nachher", lf, False)):
        for n in range(a.laeufe):
            for name, _k, diktat, _e in faelle:
                text, aufrufe = lauf(diktat, prompt, alt)
                usd = sum(la.kosten_usd(la.ANTHROPIC_MODELL, x["usage"]) for x in aufrufe)
                erg.append({"art": art, "lauf": n, "fall": name, "text": text, "aufrufe": aufrufe, "usd": usd})
                u = aufrufe[-1]["usage"] if aufrufe else {}
                cc = u.get("cache_creation") or {}
                print(f"{art:7s} {n} {name[:34]:34s} aufrufe={len(aufrufe)} usd={usd:.4f} in={u.get('input_tokens')} "
                      f"cr={u.get('cache_read_input_tokens')} cw1h={cc.get('ephemeral_1h_input_tokens')} "
                      f"cw5m={cc.get('ephemeral_5m_input_tokens')} out={u.get('output_tokens')} "
                      f"typen={aufrufe[-1]['typen'] if aufrufe else '-'} cc={aufrufe[-1]['cache_control'] if aufrufe else '-'}",
                      flush=True)
    pathlib.Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.aus).write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    for art in ("vorher", "nachher"):
        z = [e for e in erg if e["art"] == art]
        n = sum(len(e["aufrufe"]) for e in z)
        print(f"SUMME {art}: {n} Aufrufe, {sum(e['usd'] for e in z):.4f} $, {sum(e['usd'] for e in z) / max(n, 1) * 100:.2f} ct je Aufruf")
    gleich = 0
    for name, *_ in faelle:
        texte = {e["art"] + str(e["lauf"]): e["text"] for e in erg if e["fall"] == name}
        alle = set(texte.values())
        gleich += len(alle) == 1
        print(f"TEXT {name[:40]:40s} verschiedene Texte={len(alle)} "
              + " ".join(f"{k}={sorted(alle).index(v)}" for k, v in sorted(texte.items())))
    print(f"TEXTGLEICH {gleich}/{len(faelle)} Fälle; Datei {a.aus}")


if __name__ == "__main__":
    main()
