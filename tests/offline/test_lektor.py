"""Gate (kaiscribe-lektor-einbau-n1, 26.11.2026): KaiScribe-Lektor — Schalter Standard AUS, nur kp/rg, Monatsdeckel,
Aufruf maskiert über Opus 5.5 (Konto A) ohne zweiten Versuch/anderes Modell, Korrekturen nur über den Wächter und nie auf
Arzt-Stellen, Prüfzeilen als rote Hinweiszeile (nie im Befund), Kosten getrennt mit Rolle „lektor“.
Aufruf: python3 tests/offline/test_lektor.py"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import config as cfgmod  # noqa: E402
import lektor as L  # noqa: E402
import lektor_waechter as W  # noqa: E402
import llm_anbieter as la  # noqa: E402
import nutzung  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ── Wächter = Kopie aus ris-mods (Pflicht laut Auftrag) ──
quelle = pathlib.Path.home() / "dev" / "ris-mods" / "kaiscribe_lektor" / "waechter.py"
if quelle.exists():
    check("lektor_waechter.py wortgleich zu ris-mods/kaiscribe_lektor/waechter.py",
          quelle.read_text(encoding="utf-8") == (ROOT / "source_code" / "lektor_waechter.py").read_text(encoding="utf-8"))
else:
    print("ℹ️  ris-mods nicht daneben — Gleichheit von lektor_waechter.py nicht geprüft")

# ── Schalter: Standard AUS, nur kp/rg ──
d = tempfile.mkdtemp(prefix="rks_lektor_")
pf = os.path.join(d, "lektor.json")
s = L.Schalter(pf)
check("Schalter: Datei fehlt → aus (kp, rg)", not s.an_fuer("kp") and not s.an_fuer("rg"))
check("config: LEKTOR_DATEI Standard X:\\KaiScribe\\Daten\\lektor.json", cfgmod.Config().lektor_datei ==
      "X:\\KaiScribe\\Daten\\lektor.json")
ini = os.path.join(d, "config.ini")
with open(ini, "w", encoding="utf-8") as f:
    f.write("[SETTINGS]\nLEKTOR_DATEI = " + pf + "\n")
check("config: LEKTOR_DATEI überschreibbar (Gast-Kopie für 451898)", cfgmod.load_config(ini).lektor_datei == pf)
with open(pf, "w", encoding="utf-8") as f:
    json.dump({"befunder": {"kp": False, "rg": False}, "monatsdeckel_usd": 40}, f)
s = L.Schalter(pf)
check("Schalter: ausgeliefert kp/rg false → aus", not s.an_fuer("kp") and not s.an_fuer("rg"))
with open(pf, "w", encoding="utf-8") as f:
    json.dump({"befunder": {"kp": True, "mh": True}, "monatsdeckel_usd": 12.5}, f)
s = L.Schalter(pf)
check("Schalter: kp an → an für kp/KP, aus für rg", s.an_fuer("kp") and s.an_fuer("KP") and not s.an_fuer("rg"))
check("Schalter: nur kp/rg möglich (mh in der Datei zählt nicht)", not s.an_fuer("mh") and L.ERLAUBT == ("kp", "rg"))
check("Schalter: Monatsdeckel aus der Datei", s.deckel_usd() == 12.5)
check("Schalter: Liste ['rg'] → rg an", L.befunder_an({"befunder": ["rg"]}, "rg") and not L.befunder_an({"befunder": ["rg"]}, "kp"))
with open(pf, "w", encoding="utf-8") as f:
    f.write("{kaputt")
check("Schalter: kaputte Datei → aus (nach Neulesen)", not L.Schalter(pf).an_fuer("kp"))
check("Schalter: LEKTOR_DATEI = aus → aus", not L.Schalter("aus").an_fuer("kp"))
check("Deckel: Standard 40 $", L.deckel_aus({}) == 40.0 and L.deckel_aus({"monatsdeckel_usd": "x"}) == 40.0)
t = [0.0]
with open(pf, "w", encoding="utf-8") as f:
    json.dump({"befunder": {"kp": True}}, f)
s = L.Schalter(pf, jetzt=lambda: t[0])
an1 = s.an_fuer("kp")
with open(pf, "w", encoding="utf-8") as f:
    json.dump({"befunder": {"kp": False}}, f)
t[0] = 5
an2 = s.an_fuer("kp")
t[0] = 40
check("Schalter: wird alle 30 s neu gelesen (Notaus ohne Neustart)", an1 and an2 and not s.an_fuer("kp"))

# ── Aufruf: Body, Maske, kein zweiter Versuch ──
b = L.body("<befund>x</befund>")
check("Body: Opus 5.5, effort medium, Systemprompt 1 h im Cache, kein temperature/thinking",
      b["model"] == "claude-opus-5-5" and b["output_config"] == {"effort": "medium"}
      and b["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"} and "temperature" not in b
      and "thinking" not in b and b["system"][0]["text"] == L.SYSTEM)
check("Prompt lektor-2 (n2: lektor-3 macht Opus zu leise)", L.PROMPT_VERSION == "lektor-2"
      and "[vom Arzt]" not in L.SYSTEM and "Leere Listen, wenn nichts zu tun ist." in L.SYSTEM)
check("kein Gemini/anderes Modell im Lektor", "gemini" not in (ROOT / "source_code" / "lektor.py").read_text(
    encoding="utf-8").lower().replace("kein gemini", "").replace("kein zweiter versuch, kein anderes modell, kein gemini", ""))
check("Opus-Preis in kosten_usd", abs(la.kosten_usd("claude-opus-5-5", {"input_tokens": 1000, "output_tokens": 100})
                                     - (1000 * 4 + 100 * 20) / 1e6) < 1e-12)

BEFUND = ("## Schulter rechts in 2 Ebenen\n\nHumeruskopf steht in regelrechter Artikulation. Geringe osseäre Ausziehung "
          "am AC-Gelenk mit Asymetrie. Keine Luxation. Die Klavikula ist intakt. Sonographie: Zelle Status post CHE.\n\n"
          "## Ergebnis\n1. Geringe AC-Gelenksarthrose rechts (Arthrose Grad 2 nach Kellgren & Lawrence).")
DIKTAT = "Schulter rechts vom 12.03.2026 geringe AC Gelenksarthrose Asymetrie"
gesendet = []


def antwort(korr=(), pruef=(), stop="end_turn"):
    return {"stop_reason": stop, "usage": {"input_tokens": 800, "cache_read_input_tokens": 3900, "output_tokens": 300},
            "content": [{"type": "thinking", "thinking": "…"},
                        {"type": "text", "text": json.dumps({"korrekturen": list(korr), "pruefen": list(pruef)})}]}


def sender_fn(resp):
    def senden(body, frist):
        gesendet.append(body)
        if isinstance(resp, Exception):
            raise resp
        return resp
    return senden


erg, info = L.aufrufen(BEFUND, DIKTAT, sender_fn(antwort([{"alt": "Asymetrie", "neu": "Asymmetrie"}])),
                       kosten_fn=la.kosten_usd)
inhalt = gesendet[-1]["messages"][0]["content"]
check("Aufruf maskiert: Datum des Diktats geht als Platzhalter hinaus", "12.03.2026" not in inhalt and "⟦D1⟧" in inhalt)
check("Aufruf: Antwort gelesen, Kosten berechnet", erg["korrekturen"][0]["neu"] == "Asymmetrie" and info["usd"] > 0)
n0 = len(gesendet)
try:
    L.aufrufen(BEFUND, DIKTAT, sender_fn(la.HttpFehler(529, "overloaded_error")))
    check("HTTP 529 → Ausfall", False)
except L.Ausfall as e:
    check("HTTP 529 → Ausfall ohne zweiten Versuch", len(gesendet) == n0 + 1 and e.grund == "HTTP 529", e.grund)
try:
    L.aufrufen(BEFUND, DIKTAT, sender_fn(antwort(stop="max_tokens")))
    check("abgebrochene Antwort → Ausfall", False)
except L.Ausfall as e:
    check("abgebrochene Antwort → Ausfall mit Kosten (abgerechnet)", e.kosten and e.kosten.get("usage"), e.kosten)
erg, _i = L.aufrufen(BEFUND, DIKTAT, sender_fn(antwort(
    [{"alt": "vom ⟦D1⟧", "neu": "vom ⟦D2⟧"}], [{"zitat": "Asymetrie", "hinweis": "Diktat ⟦D1⟧", "art": "fehlt"},
                                               {"zitat": "x", "hinweis": "⟦D9⟧", "art": "fehlt"}])))
check("Antwort: Korrektur mit Platzhalter fällt weg, Prüfzeile zurückgesetzt, unbekannter Platzhalter → weg",
      erg["korrekturen"] == [] and len(erg["pruefen"]) == 1 and "12.03.2026" in erg["pruefen"][0]["hinweis"], erg)
check("antwort_lesen: zweites JSON (Selbstkorrektur) → letzte gültige",
      L.antwort_lesen('{"korrekturen": [{"alt": "a"}]} Moment {"korrekturen": [], "pruefen": []}') ==
      {"korrekturen": [], "pruefen": []})
check("antwort_lesen: kein JSON → None", L.antwort_lesen("Ich kann das nicht") is None)

# ── Wächter + Arzt-Filter beim Einarbeiten ──
KORR = [{"alt": "Asymetrie", "neu": "Asymmetrie"}, {"alt": "Klavikula", "neu": "Clavicula"},
        {"alt": "Keine Luxation", "neu": "Luxation"}, {"alt": "Zelle", "neu": "Galle"},
        {"alt": "Schulter rechts in 2 Ebenen", "neu": "Schulter links in 2 Ebenen"}]
plan, zeilen, z = L.zusammenfuehren(BEFUND, BEFUND, {"korrekturen": KORR, "pruefen": []})
neu = L.anwenden_auf(BEFUND, plan)
check("Wächter: Rechtschreibung + Fachbegriff übernommen", "Asymmetrie" in neu and "Clavicula" in neu)
check("Wächter: Verneinung bleibt", "Keine Luxation." in neu)
check("Wächter-Zusatz (n2): „Zelle“ → „Galle“ ist kein Hörfehler", "Zelle Status" in neu and z["waechter"] == 3, z)
check("Wächter: Überschrift bleibt", neu.startswith("## Schulter rechts in 2 Ebenen"))
check("Wortwechsel-Regel lässt Hörfehler/Schreibweisen durch",
      not L.wortwechsel("radikarpale", "radiokarpale") and not L.wortwechsel("Sigelenksarthrose", "SI-Gelenksarthrose")
      and not L.wortwechsel("Klavikula", "Clavicula") and L.wortwechsel("Zelle", "Galle"))
reg = ["Humeruskopf steht in regelrechter Artikulation"]
plan, _z, z = L.zusammenfuehren(BEFUND, BEFUND, {"korrekturen": [{"alt": "Humeruskopf steht", "neu": "Der Humeruskopf steht"}]},
                                register=reg)
check("Wächter: Regel-Register-Wortlaut bleibt geschützt", plan == [] and z["waechter"] == 1)
regeln = L.register_saetze_laden(str(ROOT / "tests" / "regel_register" / "regeln.json"))
check("Regel-Register-Wortlaute ladbar (EXE bündelt regeln.json)", len(regeln) > 50, len(regeln))
pool = L.vorlagen_pool({"x": {"body": "Die Weichteile unauffällig. Kein Erguss."}})
t2 = "## LWS\n\nGeringe Spondylose. Die Weichteile unauffällig.\n\n## Ergebnis\n1. Geringe Spondylose."
plan, _z, z = L.zusammenfuehren(t2, t2, {"korrekturen": [{"alt": "Weichteile unauffällig", "neu": "Weichteile sind unauffällig"}]},
                                vorlagen=pool)
check("Wächter: Vorlagensatz bleibt wortgleich", plan == [] and z["waechter"] == 1)

# Arzt hat im Fenster geändert: „Asymetrie“ selbst umgeschrieben, Satz ergänzt
jetzt = BEFUND.replace("mit Asymetrie", "mit deutlicher Asymetrie der Gelenkflächen").replace(
    "Keine Luxation.", "Keine Luxation. Kein Erguss.")
plan, zeilen, z = L.zusammenfuehren(BEFUND, jetzt, {"korrekturen": KORR[:2], "pruefen": [
    {"zitat": "mit deutlicher Asymetrie", "hinweis": "nicht diktiert", "art": "konfabulation"},
    {"zitat": "Kein Erguss.", "hinweis": "nicht diktiert", "art": "konfabulation"},
    {"zitat": "Die Klavikula ist intakt.", "hinweis": "Normalsatz trotz Fraktur", "art": "normalsatz_trotz_pathologie"}]})
neu = L.anwenden_auf(jetzt, plan)
check("Arzt-Stelle: Korrektur dort nicht (Asymetrie bleibt), anderswo schon (Clavicula)",
      "deutlicher Asymetrie der Gelenkflächen" in neu and "Clavicula" in neu and z["arzt"] == 1, (z, neu))
check("Arzt-Stelle: sonst bleibt der Arzt-Text wörtlich", "Keine Luxation. Kein Erguss." in neu)
check("Arzt-Filter: Prüfzeilen auf Arzt-Stellen fallen weg, andere bleiben",
      len(zeilen) == 1 and "Normalsatz trotz Fraktur" in zeilen[0] and z["pruef_arzt"] == 2, zeilen)
check("Prüfzeile: bisheriges Format „…“ … – bitte prüfen (rot)", zeilen[0].startswith("„") and
      zeilen[0].endswith("– bitte prüfen") and "(Lektor)" in zeilen[0])
plan, zeilen, z = L.zusammenfuehren(BEFUND, BEFUND, {"pruefen": [{"zitat": "gibt es nicht", "hinweis": "x"}]})
check("Prüfzeile: Zitat nicht (mehr) im Text → keine Zeile", zeilen == [] and z["pruef_arzt"] == 1)
plan, zeilen, _z = L.zusammenfuehren(BEFUND, BEFUND, {"pruefen": [{"zitat": "Keine Luxation.", "hinweis": f"h{i}"}
                                                               for i in range(9)]})
check(f"Prüfzeilen höchstens {L.MAX_PRUEFZEILEN}", len(zeilen) == L.MAX_PRUEFZEILEN)
# Arzt hat in der Zwischenzeit vorne etwas eingefügt → Positionen verschieben sich richtig
jetzt = BEFUND.replace("Humeruskopf steht", "Zusatz vom Arzt. Humeruskopf steht")
plan, _zl, _z = L.zusammenfuehren(BEFUND, jetzt, {"korrekturen": KORR[:2]})
neu = L.anwenden_auf(jetzt, plan)
check("Arzt-Einschub davor: Korrekturen landen an der richtigen Stelle",
      neu == jetzt.replace("Asymetrie", "Asymmetrie").replace("Klavikula", "Clavicula"), neu)

plan, zeilen, z = L.zusammenfuehren(BEFUND, BEFUND, {"pruefen": [
    {"zitat": "(Arthrose Grad 2 nach Kellgren & Lawrence)", "hinweis": "Grad nicht diktiert", "art": "konfabulation"},
    {"zitat": "Grad 2 nach Kellgren & Lawrence", "hinweis": "gering passt nicht zu Grad 2", "art": "widerspruch"},
    {"zitat": "Humeruskopf steht in regelrechter Artikulation.", "hinweis": "nicht diktiert", "art": "konfabulation"}]},
    register=["Humeruskopf steht in regelrechter Artikulation"])
check("Hausregel (n2 P52): „nicht diktiert“ auf K&L-Grad/Register-Wortlaut fällt weg, Widerspruch bleibt",
      len(zeilen) == 1 and "passt nicht" in zeilen[0] and z["pruef_hausregel"] == 2, (zeilen, z))

# ── Normal-/Bausteinbefund → kein Lektor ──
pool = L.vorlagen_pool({"k": {"body": "Regelrechte Stellung der Skelettabschnitte. Keine Fraktur nachweisbar.",
                              "ergebnis": "Unauffälliger Befund."}})
nb = "## Knie rechts\n\nRegelrechte Stellung der Skelettabschnitte. Keine Fraktur nachweisbar.\n\n## Ergebnis\nUnauffälliger Befund."
check("Normal-/Bausteinbefund → kein Lektor", L.normal_oder_baustein(nb, "Knie rechts", pool))
check("Diktat reiner Normalbefund → kein Lektor", L.normal_oder_baustein(BEFUND, "Schulter unauffällig", pool,
                                                                         lambda dk, t: "unauffällig" in dk))
check("Pathologischer Befund → Lektor", not L.normal_oder_baustein(BEFUND, DIKTAT, pool, lambda dk, t: False))

# ── Lauf: Hintergrund, EOL vorher → verworfen, Ausfall → unverändert ──
gemeldet, fertig = [], []
lauf = L.Lauf(BEFUND, DIKTAT, sender_fn(antwort(KORR[:1])), melden=gemeldet.append, fertig_fn=fertig.append,
              kosten_fn=la.kosten_usd, starten=False)
lauf.laufen()
check("Lauf: fertig → fertig_fn, Kosten mit Rolle lektor gemeldet",
      fertig == [lauf] and gemeldet and gemeldet[0]["rolle"] == "lektor" and gemeldet[0]["usd"] > 0, gemeldet)
gemeldet, fertig = [], []
lauf = L.Lauf(BEFUND, DIKTAT, sender_fn(antwort(KORR[:1])), melden=gemeldet.append, fertig_fn=fertig.append,
              starten=False)
check("Lauf: EOL vor der Antwort → abbrechen meldet „lief noch“", lauf.abbrechen("EOL"))
lauf.laufen()
check("Lauf: Antwort nach EOL → verworfen (kein Einarbeiten), als zu_spaet gezählt",
      fertig == [] and any(g.get("lektor") == "zu_spaet" for g in gemeldet), gemeldet)
gemeldet, fertig = [], []
lauf = L.Lauf(BEFUND, DIKTAT, sender_fn(TimeoutError("timed out")), melden=gemeldet.append, fertig_fn=fertig.append,
              starten=False)
lauf.laufen()
check("Lauf: Ausfall → nichts eingearbeitet, gezählt", fertig == [] and gemeldet[-1].get("lektor") == "ausfall"
      and gemeldet[-1]["grund"] == "Zeitüberschreitung", gemeldet)
ev = []
lauf = L.Lauf(BEFUND, DIKTAT, lambda b, f: (time.sleep(0.2), antwort())[1], fertig_fn=lambda x: ev.append("fertig"))
check("Lauf: läuft im Hintergrund (Aufrufer wartet nicht)", ev == [] and not lauf.fertig)
for _ in range(50):
    if ev:
        break
    time.sleep(0.05)
check("Lauf: Hintergrund-Thread liefert", ev == ["fertig"])

# ── Nutzungszähler: Rolle lektor getrennt ──
T = datetime.datetime(2026, 11, 26, 18, 0)
nbasis = tempfile.mkdtemp(prefix="rks_lektor_nutz_")
nd = os.path.join(nbasis, "nutzung")
zz = nutzung.Zaehler(nd, "CASWS10", jetzt=lambda: T)
zz.ki({"rolle": "gen", "anbieter": "anthropic", "usd": 0.014, "usage": {"input_tokens": 10, "cache_read_input_tokens": 9000}})
zz.ki({"rolle": "lektor", "anbieter": "anthropic", "usd": 0.013, "usage": {"input_tokens": 800,
                                                                             "cache_read_input_tokens": 3900,
                                                                             "output_tokens": 300}})
zz.ki({"rolle": "lektor", "lektor": "uebernommen", "n": 2, "pruefzeilen": 1})
zz.ki({"rolle": "lektor", "lektor": "ausfall", "grund": "HTTP 529"})
dat = json.load(open(os.path.join(nd, "2026-11_CASWS10.json"), encoding="utf-8"))["tage"]["2026-11-26"]
check("Zähler: KaiScribe-Zahlen unverfälscht (1 Aufruf, 1 Befund, 1,4 ct, 1 Cache-Treffer)",
      dat["ki"].get("anthropic") == 1 and dat["befunde"] == 1 and abs(dat["anthropic_usd"] - 0.014) < 1e-9
      and dat["cache"] == {"treffer": 1}, dat)
lk = dat["lektor"]
check("Zähler: Lektor getrennt (Aufruf, $, Token, übernommen, Prüfzeile, Ausfall)",
      lk["aufrufe"] == 1 and abs(lk["usd"] - 0.013) < 1e-9 and lk["token_out"] == 300 and lk["uebernommen"] == 2
      and lk["pruefzeilen"] == 1 and lk["befunde_korrigiert"] == 1 and lk["ausfall"] == 1, lk)
check("Monatsdeckel: Lektor-$ des Monats über alle PCs", abs(nutzung.lektor_monat_usd(nd, "2026-11") - 0.013) < 1e-9)
text, _w = nutzung.tagesbericht(nd, "2026-11-26")
check("Tagesbericht: Zeile „Lektor heute …“", "Lektor heute: Aufrufe 1, Korrekturen übernommen 2 (in 1 Befunden), "
      "Prüfzeilen 1, ausgefallen 1" in text and "≈ 1.4 ct je Aufruf" in text, text)
nd2 = tempfile.mkdtemp(prefix="rks_lektor_nutz2_")
nutzung.Zaehler(nd2, "CASWS10", jetzt=lambda: T).ki({"rolle": "gen", "anbieter": "anthropic", "usd": 0.01})
check("Tagesbericht ohne Lektor: keine Lektor-Zeile", "Lektor" not in nutzung.tagesbericht(nd2, "2026-11-26")[0])
out = subprocess.run([sys.executable, str(ROOT / "tools" / "vm" / "kaiscribe_nutzung_lesen.py"), "--tage", "2026-11-26",
                      "--ordner", nbasis], capture_output=True, text=True, timeout=60).stdout
check("kaiscribe_nutzung_lesen: LEKTOR-Zeile mit Zahlen", "LEKTOR 2026-11 CASWS10 2026-11-26 aufrufe=1 usd=0.0130 "
      "uebernommen=2 befunde_korrigiert=1 pruefzeilen=1 ausfall=1" in out, out[-800:])

# ── Einbau in der EXE (Quelltext) ──
exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
i_voll = exe.find("if not erg.vollstaendig:")
i_start = exe.find("self._lektor_starten(gen, d)")
check("EXE: Lektor startet erst, wenn der Befund vollständig rechts steht (nach „Hermi formt“)",
      0 < i_voll < i_start < exe.find("self._lauf_fertig(gen))", i_start))
i_cas = exe.find("def _cas_senden(self):")
check("EXE: EOL/CAS fragt den Lektor vor dem Senden (eben korrigiert → EOL nochmals, läuft noch → verworfen)",
      i_cas < exe.find("if not self._lektor_eol():", i_cas) < exe.find("ergebnis_schreiben(", i_cas))
check("EXE: Felder leeren bricht den Lektor ab", 'self._lektor_abbrechen("Felder leeren")' in exe)
fertig_src = exe[exe.find("def _lektor_fertig"):exe.find("def _lektor_eol")]
check("EXE: Prüfzeilen nur in die Hinweiszeile, nie in den Befundtext",
      "_cas_hinweise_zeigen(" in fertig_src and "insert(f\"1.0+{pos}c\", neu)" in fertig_src
      and fertig_src.count(".insert(") == 2)
check("EXE: Schalter/Befunder aus dem CAS-Auftrag, ohne CAS kein Lektor",
      'if a is None or LEKTOR_SCHALTER is None' in exe and "LEKTOR_SCHALTER.an_fuer(kz)" in exe)
check("EXE: Monatsdeckel vor dem Aufruf", "_nutz.lektor_monat_usd(" in exe and "Monatsdeckel erreicht" in exe)
check("EXE: Schlüssel = KaiScribe-Schlüssel (Konto A)", "_keys.load_anthropic_key(BASE_DIR, _schluessel_benutzerpfad())"
      in exe[exe.find("def _lektor_sender"):exe.find("def _lektor_sender") + 300])
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("Build: lektor + lektor_waechter + regeln.json gebündelt", "--hidden-import=lektor " in wf
      and "--hidden-import=lektor_waechter" in wf and '--add-data "../tests/regel_register/regeln.json;."' in wf)
log_zeilen = [z for z in (ROOT / "source_code" / "lektor.py").read_text(encoding="utf-8").splitlines() if "self.log(f" in z]
check("Protokoll: Lektor schreibt nur Zahlen/Kategorien (kein basis/diktat/zitat im Log)",
      log_zeilen and not any(w in z for z in log_zeilen for w in ("basis", "diktat", "zitat", "neu}", "alt}")))

print(f"\n{'OK' if not fails else f'{fails} FEHLER'}")
sys.exit(1 if fails else 0)
