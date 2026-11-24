"""Regel-Wächter (kaiscribe-kl-tabelle-zurueck-n1, Georg Riegler 18.11.2026: „Wir haben Regeln definiert beim KaiScribe. Die
müssen sitzen!!“). Anlass: 80a36ae (12.11.) hat die freigegebene K&L-Tabelle still aus radiology_prompt.txt gestrichen.
tests/regel_register/regeln.json führt jede freigegebene Befundregel mit Prüfwortlaut je Datei. Rot, wenn
  - ein Prüfwort in seiner Datei fehlt (Prompt EXE + Web, Web-Validator, Regel-Module, IB-Lab-Bausteine, Fehlhör-Liste),
  - eine Pflicht-Regel aus dem Register verschwindet (Skill-Regeln 1–13 und 3a–3af, K&L-Tabelle 0–4, Ergebnisformate,
    IB-Lab-Sätze) oder ein Eintrag ohne Quelle/Datum/Status ist,
  - die Web-App den Gen-Prompt nicht mehr aus radiology_prompt.txt lädt (dann gälte der Wächter fürs Web nicht).
Ein Commit, der einen Register-Wortlaut entfernt, geht damit nur zusammen mit einer Register-Änderung (Datum + Quelle).
Aufruf: python3 tests/offline/test_regel_register.py"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = json.loads((ROOT / "tests" / "regel_register" / "regeln.json").read_text(encoding="utf-8"))
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += 0 if ok else 1


# Skill radiology-shoulder-dictation, „Diktat-Verarbeitungsregeln“ (Stand 18.11.2026, Z. 66–101) + Erstbefüllung laut Brief
SKILL = ["1", "2", "3"] + [f"3{c}" for c in "abcdefghijklmnopqrstuvwxyz"] + ["3aa", "3ab", "3ac", "3ad", "3ae", "3af"] \
    + ["4", "5", "5a", "5b", "6", "7", "8", "9", "10", "11", "12", "13"]
PFLICHT = SKILL + ["kl-0", "kl-1", "kl-2", "kl-3", "kl-4", "kl-wann", "kl-rh38", "kl-ergebnis", "kl-knie-fp", "kl-knie-betont",
                   "kl-bsp-schulter", "kl-bsp-ellbogen", "kl-bsp-knie", "kl-koala", "ergebnis-format", "ibl-frog", "ibl-text-immer", "ibl-lama",
                   "ibl-panda", "ibl-rho", "ibl-squirrel", "ibl-squirrel-diktat", "ibl-squirrel-achse", "wid-erguss", "wid-ki-pathologie", "val-kl",
                   "mehrfach-untersuchung", "gws-ap-normaltext", "rho-osteopen", "rho-titel-nummer",
                   # kaiscribe-schulter-ergebnis-n1 (Georg 22./23.11.2026, Punkte 48–70)
                   "georg-schulter-reihenfolge", "georg-enthesiopathie", "georg-ueberschriften-fett", "georg-stt-2311", "georg-sono-bursa", "georg-fraktur-kortikalis", "georg-im-uebrigen-nur-nach-patho", "georg-nerv-unauffaellig", "georg-hueft-op-seite", "georg-dunn", "georg-doppelte-teile", "georg-hippo-10mm", "georg-kombi-diktat", "georg-nie-unter-normalvorlage", "georg-koala-aus", "georg-ergebnis-einfuegen", "georg-geruest-bleibt", "georg-unterarm", "georg-verlauf-zuerst", "georg-hippo-stellung", "georg-kl-adjektiv-zeile",
                   # kaiscribe-ohne-gemini-n1 (Peter 23.11.2026): kein Gemini-Rückfall, rote Prüfzeile ohne KI
                   "ohne-ki-pruefzeile"]

regeln = REG["regeln"]
ids = [r["id"] for r in regeln]
check("Register: keine doppelten IDs", len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1])
fehlt = [i for i in PFLICHT if i not in ids]
check(f"Register: alle {len(PFLICHT)} Pflicht-Regeln da (Skill 1–13, 3a–3af, K&L 0–4, Formate, IB Lab)", not fehlt, fehlt)
for r in regeln:
    ok = all(str(r.get(k) or "").strip() for k in ("titel", "quelle", "datum", "status")) \
        and r["status"] in ("vorhanden", "ergänzt", "unklar") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["datum"]) \
        and isinstance(r.get("pruefwort"), dict) and r["pruefwort"]
    if not ok:
        check(f"Regel {r.get('id')}: Titel, Quelle, Datum (JJJJ-MM-TT), Status und Prüfwort", False, r)

texte = {}
for r in regeln:
    for datei, woerter in (r.get("pruefwort") or {}).items():
        if datei not in texte:
            pfad = ROOT / datei
            texte[datei] = pfad.read_text(encoding="utf-8") if pfad.exists() else None
        if texte[datei] is None:
            check(f"Regel {r['id']}: Datei {datei} vorhanden", False)
            continue
        for w in woerter:
            if w not in texte[datei]:
                check(f"Regel {r['id']} ({r['titel'][:50]}): Wortlaut in {datei}", False, f"fehlt: {w[:160]}")
print(f"   {sum(len(w) for r in regeln for w in r['pruefwort'].values())} Prüfwörter in "
      f"{len({d for r in regeln for d in r['pruefwort']})} Dateien geprüft")

# Die Web-App lädt denselben Gen-Prompt (Vite ?raw) – sonst gälte der Wächter fürs Web nicht
web = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "web_app" / "src").glob("*.ts*"))
check("Web-App lädt den Gen-Prompt aus radiology_prompt.txt (?raw)", re.search(r"radiology_prompt\.txt\?raw", web) is not None)

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
