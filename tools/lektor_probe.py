#!/usr/bin/env python3
"""Lektor-Probe (kaiscribe-lektor-einbau-n1, 26.11.2026): der EINGEBAUTE Weg (source_code/lektor.py: Body, Antwort-Leser,
Wächter, Arzt-Filter) an den 64 maskierten Paaren aus ris-mods kaiscribe-lektor-messlauf-n1 — Testschlüssel Konto B über
tools/testkosten.py (Kostenbuch + Grenze), nie Konto A, nie Patientendaten (die Paare sind schon maskiert).

  python3 tools/lektor_probe.py <paare.json> [--max N] [--aus lauf.jsonl]

Simuliert den ungünstigsten Fall im Betrieb: Der Lektor bekommt die KaiScribe-Erstfassung („erst“), der Arzt hat bis
zur Antwort schon alles geändert, was er bis EOL geändert hat („eol“). Gezählt: Aufrufe, reine Normal-/Bausteinbefunde
(kein Aufruf), Korrekturen (übernommen / Wächter / Arzt-Stelle), Prüfzeilen (gezeigt / auf Arzt-Stellen verworfen),
übernommene Korrekturen, die der Arzt selbst genauso gemacht hat, Dauer p50/p90, $ je Aufruf und hochgerechnet auf 3.000
Befunde/Monat. Ausgabe nur Zahlen (Rohantworten maskiert in --aus).
"""
import argparse
import json
import os
import pathlib
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("KAISCRIBE_TEST_JOB", os.environ.get("CLAUDE_JOB_NAME") or "kaiscribe-lektor-einbau-n1")
import lektor as L  # noqa: E402
import normalbypass  # noqa: E402
import bausteine  # noqa: E402
import testkosten as tk  # noqa: E402


class OhneMaske:
    """Die Paare sind schon maskiert (⟦…⟧) – der echte Maskierer würde sie ablehnen; hier unverändert durchreichen."""
    def __init__(self, *_a):
        self.zu_wert = {}

    def maskieren(self, t):
        return t

    def restpruefung(self, _t):
        return None

    def zuruecksetzen(self, t):
        return t


def sender(body, frist):
    import urllib.request
    p_in, _pc, p_out, _ = tk.preis(L.MODELL, "anthropic")
    tk.BUCH.pruefen((len(json.dumps(body)) / 3.5 * p_in * 1.25 + 1500 * p_out) / 1e6, konto=tk.KONTO_ANTHROPIC_B)
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": tk._anthropic_key(), "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=frist) as r:
        data = json.loads(r.read())
    u = data.get("usage", {})
    d_usd, tin, tc, tout = tk.kosten_anthropic(L.MODELL, u)
    tk.BUCH.buchen("anthropic", L.MODELL, d_usd, tin, tc, tout, rolle="lektor-einbau", konto=tk.KONTO_ANTHROPIC_B,
                   cache_schreiben=int(u.get("cache_creation_input_tokens", 0) or 0))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paare")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--aus", default="")
    a = ap.parse_args()
    paare = json.load(open(a.paare, encoding="utf-8"))
    with open(ROOT / "templates.json", encoding="utf-8") as f:
        tpl = json.load(f)
    pool = L.vorlagen_pool(tpl, bausteine.laden(str(ROOT / "ordi_bausteine.json")))
    reg = L.register_saetze_laden(str(ROOT / "tests" / "regel_register" / "regeln.json"))
    L.ki_maske.Maske = OhneMaske
    rein = [p for p in paare if L.normal_oder_baustein(p["erst"], p.get("stt") or "", pool,
                                                         lambda d, t: normalbypass.is_pure_normal_finding(d, t))]
    offen = [p for p in paare if p not in rein]
    if a.max:
        offen = offen[:a.max]

    def eins(p):
        try:
            erg, info = L.aufrufen(p["erst"], p.get("stt") or "", sender, kosten_fn=L_kosten)
            return p, erg, info, None
        except L.Ausfall as e:
            return p, None, e.kosten or {}, e.grund
    z = {k: 0 for k in ("korrekturen", "uebernommen", "waechter", "arzt", "pruefen", "pruefzeilen", "pruef_arzt")}
    s, usd, ausfall, wie_arzt, mit_pz, mit_korr = [], 0.0, [], 0, 0, 0
    aus = open(a.aus, "w", encoding="utf-8") if a.aus else None
    with ThreadPoolExecutor(4) as ex:
        for p, erg, info, fehler in ex.map(eins, offen):
            usd += float(info.get("usd") or 0)
            if info.get("s"):
                s.append(info["s"])
            if fehler:
                ausfall.append(fehler)
                continue
            jetzt = p.get("eol") or p["erst"]
            plan, zeilen, zz = L.zusammenfuehren(p["erst"], jetzt, erg, reg, pool)
            for k in z:
                z[k] += zz[k]
            mit_pz += bool(zeilen)
            mit_korr += bool(plan)
            final = L.anwenden_auf(L.W._nfc(jetzt), plan)
            for pos, n, neu in plan:
                if neu in (p.get("final") or p.get("eol") or ""):
                    wie_arzt += 1
            if aus:
                aus.write(json.dumps({"id": p["id"], "antwort": erg, "plan": plan, "zeilen": zeilen, "z": zz,
                                      "s": info.get("s"), "usd": info.get("usd")}, ensure_ascii=False) + "\n")
            del final
    n = len(offen) - len(ausfall)
    print(f"PROBE befunde={len(paare)} normal_baustein={len(rein)} aufrufe={len(offen)} ausfall={len(ausfall)} "
          f"({', '.join(sorted(set(ausfall))) or '-'})")
    print("PROBE " + " ".join(f"{k}={v}" for k, v in z.items()) + f" befunde_mit_korrektur={mit_korr} "
          f"befunde_mit_pruefzeile={mit_pz} korrektur_wie_arzt={wie_arzt}")
    if s:
        q = sorted(s)
        print(f"PROBE dauer_p50={statistics.median(q):.1f}s dauer_p90={q[int(len(q) * 0.9) - 1]:.1f}s")
    je_aufruf = usd / max(1, len(offen))
    je_befund = je_aufruf * (len(paare) - len(rein)) / max(1, len(paare))   # nur Nicht-Normalbefunde rufen auf
    print(f"PROBE usd={usd:.4f} je_aufruf={je_aufruf * 100:.2f}ct je_befund={je_befund * 100:.2f}ct "
          f"monat_3000={je_befund * 3000:.1f}$ (n={n})")


def L_kosten(modell, u):
    """Preis wie in der EXE (llm_anbieter.kosten_usd, Cache-Schreiben 1 h = 2 × Input); das Kostenbuch rechnet vorsichtiger."""
    import llm_anbieter
    return llm_anbieter.kosten_usd(modell, u)


if __name__ == "__main__":
    main()
