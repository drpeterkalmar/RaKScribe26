#!/usr/bin/env python3
"""tools/testlauf.py — kompletter KaiScribe-Testlauf in der richtigen Reihenfolge (kaiscribe-testkosten-n1, 13.11.2026).

  1. Offline-Gates (tests/offline/*.py + web_app/*_test.mjs) — kosten nichts, laufen IMMER zuerst.
     Grün → Stempel für genau diesen Code-Stand (tools/testkosten.gate_stempel), sonst Abbruch OHNE Live-Aufruf.
  2. Live-Suite (echtes Gemini im Testprojekt rakscribe-test, über tools/testkosten.py): Harness + verify_*.
     Wiederholungen: Standard 5 (verify_konfabulation), mit --release 20. Kosten je Skript + Summe am Ende.
     Gemessen 13.11.2026 (mit Kontext-Cache): normal 431 Aufrufe ≈ 2,5 $, --release ≈ 967 Aufrufe ≈ 5,5 $.

Aufruf:
  python3 tools/testlauf.py                 Offline, dann Live (5 Wiederholungen)
  python3 tools/testlauf.py --release       Offline, dann Live (20 Wiederholungen; Job-Grenze dann 8 $, gemessen ≈ 5,5 $)
  python3 tools/testlauf.py --nur-offline   nur Gates + Stempel
  python3 tools/testlauf.py --nur-live      Live-Suite (Gates müssen für diesen Stand schon grün sein)
  python3 tools/testlauf.py --nur-live verify_knie test_all_regions   nur diese Live-Skripte
Python: das mit tkinter + numpy + google-auth (am Hetzner z. B. ~/cj/work/<job>/venv/bin/python), node für die Web-Tests.
Exit: 0 grün, 1 rot, 7 Kostengrenze erreicht.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import testkosten as tk  # noqa: E402  (nimmt --release aus argv)

WEB_TESTS = ["befund_regeln", "pipeline", "sync", "audio", "misheard", "normalbypass", "speechmike", "llm_anbieter"]  # detect_test.mjs = Hilfsskript der Python-Gates

# (Skript, Argumente normal, Argumente --release) — Reihenfolge = billig/aussagekräftig zuerst
LIVE = [
    ("verify_kurzsaetze.py", ["3"], ["5"]),
    ("test_all_regions.py", [], []),
    ("test_all_regions.py", ["--cas"], ["--cas"]),
    ("test_all_regions.py", ["--ibl"], ["--ibl"]),
    ("verify_widerspruch.py", [], []),
    ("verify_knie.py", ["1"], ["3"]),
    ("verify_sprunggelenk.py", ["1"], ["3"]),
    ("verify_flachprofil.py", ["1"], ["3"]),
    ("verify_k2k3.py", ["3"], ["5"]),
    ("verify_peter_ergebnis.py", ["3"], ["5"]),
    ("verify_georg_schulter_ellbogen.py", [], []),
    ("verify_konfabulation.py", ["5"], ["20"]),
]


def offline(py):
    rot = []
    for f in sorted((ROOT / "tests" / "offline").glob("*.py")):
        if f.name in ("exe_stubs.py", "titel_fixtures.py"):
            continue
        ok = False
        for _ in range(2):   # ein Wiederholversuch (Zeitmessungs-Tests auf belasteter Maschine)
            try:
                ok = subprocess.run([py, str(f)], cwd=ROOT, capture_output=True, timeout=300).returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
            if ok:
                break
        print(("✅" if ok else "❌"), "offline", f.name, flush=True)
        if not ok:
            rot.append(f.name)
    node = shutil.which("node")
    for t in WEB_TESTS:
        datei = ROOT / "web_app" / f"{t}_test.mjs"
        if not datei.exists():
            continue
        if not node:
            print("❌ node fehlt — Web-Tests nicht gelaufen")
            rot.append("node")
            break
        r = subprocess.run([node, "--experimental-strip-types", datei.name], cwd=ROOT / "web_app",
                           capture_output=True, timeout=300)
        print(("✅" if r.returncode == 0 else "❌"), "web", datei.name, flush=True)
        if r.returncode:
            rot.append(datei.name)
    return rot


def live(py, nur):
    env = dict(os.environ, KAISCRIBE_TEST_JOB=tk.job_name())
    if tk.RELEASE:
        env["KAISCRIBE_TEST_RELEASE"] = "1"
    rot, start = [], tk.job_summe()
    for skript, normal, release in LIVE:
        if nur and skript.removesuffix(".py") not in nur:
            continue
        args = release if tk.RELEASE else normal
        vorher, t0 = tk.job_summe(), time.time()
        r = subprocess.run([py, str(ROOT / "tools" / skript)] + args, cwd=ROOT, env=env, capture_output=True,
                           text=True, timeout=3600)
        log = ROOT / "docs" / "benchmarks" / f"testlauf_{skript.removesuffix('.py')}{''.join(args)}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
        usd = tk.job_summe() - vorher
        print(f"{'✅' if r.returncode == 0 else '❌'} live {skript} {' '.join(args):6s} rc={r.returncode} "
              f"{time.time() - t0:5.0f} s {usd:6.3f} $  → {log.relative_to(ROOT)}", flush=True)
        if r.returncode == tk.EXIT_GRENZE:
            print(r.stderr.strip().splitlines()[-2:] if r.stderr.strip() else "")
            return rot + [skript], True
        if r.returncode:
            rot.append(skript)
    print(f"Live gesamt: {tk.job_summe() - start:.3f} $ (Job „{tk.job_name()}“ {tk.job_summe():.2f} $ von "
          f"{tk.grenze_usd():.2f} $; Kostenbuch {tk.BUCH.pfad})")
    return rot, False


def main():
    args = sys.argv[1:]
    nur_offline, nur_live = "--nur-offline" in args, "--nur-live" in args
    nur = [a.removesuffix(".py") for a in args if not a.startswith("--")]
    py = os.environ.get("KAISCRIBE_TEST_PYTHON", sys.executable)
    if tk.RELEASE and "KAISCRIBE_TEST_LIMIT_USD" not in os.environ:
        # gemessen 13.11.2026: kompletter --release-Lauf ≈ 5,5 $ (967 Aufrufe mit Cache) → für diesen Lauf 8 $
        os.environ["KAISCRIBE_TEST_LIMIT_USD"] = "8"
        print("[testlauf] --release: Job-Grenze 8 $ (kompletter Release-Lauf ≈ 5,5 $; KAISCRIBE_TEST_LIMIT_USD überschreibt)")
    if not nur_live:
        rot = offline(py)
        if rot:
            print(f"\n❌ Offline-Gates rot ({', '.join(rot)}) → KEIN Live-Lauf (kostet nichts, erst beheben).")
            return 1
        tk.gate_stempel().write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
        print(f"✅ Offline-Gates grün — Stempel {tk.gate_stempel().name}")
        if nur_offline:
            return 0
    elif not tk.gate_stempel().exists() and os.environ.get("KAISCRIBE_TEST_OHNE_GATE") != "1":
        print("❌ Für diesen Code-Stand gibt es keine grünen Offline-Gates → erst `tools/testlauf.py --nur-offline`.")
        return 1
    rot, grenze = live(py, nur)
    if grenze:
        return tk.EXIT_GRENZE
    print("\n" + ("✅ TESTLAUF GRÜN" if not rot else f"❌ rot: {', '.join(rot)}"))
    return 1 if rot else 0


if __name__ == "__main__":
    sys.exit(main())
