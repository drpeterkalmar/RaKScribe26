"""Nutzungszähler der EXE (kaiscribe-sonnet-n2, 16.11.2026) — ohne Tk/Windows importierbar, ohne Patientendaten.

Peter 14.11.2026 („ich will nicht noch extra google zahlen“): Die Befund-KI läuft über Claude Sonnet, Gemini nur noch als
Rückfall. Jeder Rückfall wird gezählt, und die an Chirp (Google-Spracherkennung) geschickten Audiosekunden auch.

- Datei je PC und Monat: <ordner>/<JJJJ-MM>_<PC>.json (jeder PC schreibt nur seine eigene Datei → keine Konflikte auf X:)
  {"pc": …, "tage": {"JJJJ-MM-TT": {"ki": {"anthropic": n, "gemini": n, "rueckfall": n}, "rueckfall_grund": {…},
   "anthropic_usd": x, "stt_s": {"chirp": s}}}}
  Gezählt werden nur Zahlen und Kategorien (Rolle, Anbieter, Rückfall-Grund ohne Werte) — nie Text, Namen, Nummern.
- tagesbericht(ordner, tag) fasst alle PC-Dateien des Monats zusammen → Text; schreibe_tagesbericht() legt ihn als
  tagesbericht_<JJJJ-MM-TT>.txt daneben. Hochrechnung Chirp (Monat bisher / Tage × Monatstage) > WARN_EUR → Warnzeile
  „WARNUNG“ und warnung_<JJJJ-MM>.txt (für die Kanban-Karte am Mac, tools/mac/kaiscribe_chirp_warnung.py). Seit
  sonnet-n3-beleg: gezählt ab dem ersten Tag mit Daten im Monat, Warnung erst ab MIN_TAGE gezählten Tagen.
- Fehler beim Schreiben sind nie fatal (Laufwerk weg → still nichts).
"""
import calendar
import datetime
import glob
import json
import os
import re
import threading

CHIRP_USD_MIN = 0.016     # Speech-to-Text v2 Standard (chirp_3), Listenpreis $ je Audiominute
USD_EUR = 0.87            # Richtwert für die €-Anzeige (Warnung), kein Abrechnungskurs
WARN_EUR = 6.0            # Peter 14.11.: Google-Guthaben ~9 €/Monat → Warnung ab hochgerechnet 6 €
MIN_TAGE = 3              # Warnung erst ab 3 gezählten Kalendertagen (ein einzelner Tag ist zu zufällig)

_sperre = threading.Lock()


def pc_name(environ=None):
    env = os.environ if environ is None else environ
    roh = env.get("COMPUTERNAME") or env.get("HOSTNAME") or "pc"
    return re.sub(r"[^A-Za-z0-9_-]", "_", roh)[:40] or "pc"


def ordner_aus(lauf_ordner, appdata=None):
    """Zähler-Ordner neben dem Lauf-Protokoll (X:\\RaKScribe\\Daten\\nutzung); LAUF_ORDNER = aus → %APPDATA%\\RaKScribe."""
    lo = (lauf_ordner or "").strip()
    if lo and lo.lower() != "aus":
        import ntpath
        pfad = ntpath if "\\" in lo else os.path       # X:\… auch beim Test am Mac richtig zerlegen
        return pfad.join(pfad.dirname(lo.rstrip("\\/")) or lo, "nutzung")
    return os.path.join(appdata or os.environ.get("APPDATA") or os.path.expanduser("~"), "RaKScribe", "nutzung")


def _datei(ordner, monat, pc):
    return os.path.join(ordner, f"{monat}_{pc}.json")


def _lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _grund_kategorie(grund):
    """Rückfall-Grund ohne Zahlen/Werte, kurz (z. B. „Anthropic-Ausfall (timeout)“, „Platzhalter fehlt …“)."""
    g = re.sub(r"\(\d+ von \d+\)", "", str(grund or "?"))
    return re.sub(r"\s+", " ", g).strip()[:60] or "?"


class Zaehler:
    def __init__(self, ordner, pc=None, jetzt=None):
        self.ordner, self.pc = ordner, pc or pc_name()
        self.jetzt = jetzt or datetime.datetime.now

    def _aendern(self, fn):
        if not self.ordner:
            return
        t = self.jetzt()
        tag, monat = t.strftime("%Y-%m-%d"), t.strftime("%Y-%m")
        with _sperre:
            try:
                os.makedirs(self.ordner, exist_ok=True)
                pfad = _datei(self.ordner, monat, self.pc)
                d = _lesen(pfad)
                d["pc"] = self.pc
                td = d.setdefault("tage", {}).setdefault(tag, {})
                fn(td)
                tmp = pfad + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
                os.replace(tmp, pfad)
            except Exception:
                return
        try:
            schreibe_tagesbericht(self.ordner, tag)
        except Exception:
            pass

    def ki(self, info):
        """Beobachter der llm_anbieter.Weiche: je Aufruf {rolle, anbieter, rueckfall, usd …}."""
        info = info or {}

        def fn(td):
            ki = td.setdefault("ki", {})
            if info.get("rueckfall"):
                ki["rueckfall"] = ki.get("rueckfall", 0) + 1
                gr = td.setdefault("rueckfall_grund", {})
                k = _grund_kategorie(info["rueckfall"])
                gr[k] = gr.get(k, 0) + 1
            else:
                a = info.get("anbieter") or "?"
                ki[a] = ki.get(a, 0) + 1
            if info.get("rolle") == "gen":
                td["befunde"] = td.get("befunde", 0) + 1
            if info.get("usd"):
                td["anthropic_usd"] = round(td.get("anthropic_usd", 0.0) + float(info["usd"]), 6)
        self._aendern(fn)

    def stt(self, sekunden, art="chirp"):
        """An Google geschickte Audiosekunden (art = chirp: chirp_3-Volltranskript)."""
        if not sekunden or sekunden <= 0:
            return

        def fn(td):
            s = td.setdefault("stt_s", {})
            s[art] = round(s.get(art, 0.0) + float(sekunden), 1)
        self._aendern(fn)


def monat_summen(ordner, monat):
    """Alle PC-Dateien eines Monats → {pc: daten}."""
    aus = {}
    for p in sorted(glob.glob(os.path.join(ordner, f"{monat}_*.json"))):
        d = _lesen(p)
        if d:
            aus[d.get("pc") or os.path.basename(p)[len(monat) + 1:-5]] = d
    return aus


def _summe(tage, nur_tag=None):
    s = {"anthropic": 0, "gemini": 0, "rueckfall": 0, "befunde": 0, "usd": 0.0, "chirp_s": 0.0, "gruende": {}}
    for tag, td in (tage or {}).items():
        if nur_tag and tag != nur_tag:
            continue
        ki = td.get("ki", {})
        for k in ("anthropic", "gemini", "rueckfall"):
            s[k] += int(ki.get(k, 0) or 0)
        s["befunde"] += int(td.get("befunde", 0) or 0)
        s["usd"] += float(td.get("anthropic_usd", 0) or 0)
        s["chirp_s"] += float((td.get("stt_s") or {}).get("chirp", 0) or 0)
        for g, n in (td.get("rueckfall_grund") or {}).items():
            s["gruende"][g] = s["gruende"].get(g, 0) + int(n or 0)
    return s


def chirp_eur(sekunden):
    return sekunden / 60.0 * CHIRP_USD_MIN * USD_EUR


def hochrechnung_eur(chirp_s_monat, tag, erster_tag=None):
    """Chirp-€ des Monats bisher, auf den ganzen Monat hochgerechnet (bisher / gezählte Tage × Monatstage).
    Gezählte Tage = ab erster_tag (erster Tag mit Zählerdaten im Monat), sonst ab dem 1. — v3.19.x (sonnet-n3-beleg):
    der Zähler kam am 16.11. dazu, „bisher / 16“ rechnete den November um das 16-Fache zu niedrig."""
    return chirp_eur(chirp_s_monat) / gezaehlte_tage(tag, erster_tag) * _monatstage(tag)


def _monatstage(tag):
    t = datetime.date.fromisoformat(tag)
    return calendar.monthrange(t.year, t.month)[1]


def gezaehlte_tage(tag, erster_tag=None):
    t = datetime.date.fromisoformat(tag)
    start = t.replace(day=1)
    try:
        e = datetime.date.fromisoformat(erster_tag) if erster_tag else start
    except ValueError:
        e = start
    if e.year == t.year and e.month == t.month and start <= e <= t:
        start = e
    return (t - start).days + 1


def erster_tag(alle):
    """Frühester Tag mit Zählerdaten über alle PC-Dateien eines Monats (oder None)."""
    tage = [k for d in (alle or {}).values() for k in (d.get("tage") or {}) if re.match(r"^\d{4}-\d\d-\d\d$", str(k))]
    return min(tage) if tage else None


def warnung_noetig(hoch_eur, tag, erster=None):
    return hoch_eur > WARN_EUR and gezaehlte_tage(tag, erster) >= MIN_TAGE


def tagesbericht(ordner, tag):
    """Text des Tagesberichts (alle PCs) → (text, warnung: bool)."""
    monat = tag[:7]
    alle = monat_summen(ordner, monat)
    heute = {pc: _summe(d.get("tage"), tag) for pc, d in alle.items()}
    mon = {pc: _summe(d.get("tage")) for pc, d in alle.items()}

    def ges(dct, k):
        return sum(v[k] for v in dct.values())
    h_rf, m_rf = ges(heute, "rueckfall"), ges(mon, "rueckfall")
    gruende = {}
    for v in heute.values():
        for g, n in v["gruende"].items():
            gruende[g] = gruende.get(g, 0) + n
    chirp_m = ges(mon, "chirp_s")
    erster = erster_tag(alle)
    hoch, n_tage = hochrechnung_eur(chirp_m, tag, erster), gezaehlte_tage(tag, erster)
    z = [f"KaiScribe Tagesbericht {tag} (alle PCs, ohne Patientendaten)",
         f"Befund-KI heute: {ges(heute, 'befunde')} Befunde, Aufrufe Claude {ges(heute, 'anthropic')}, "
         f"Rückfälle auf Gemini {h_rf}" + (" (" + ", ".join(f"{g}: {n}" for g, n in sorted(gruende.items())) + ")"
                                           if gruende else "") + f", nur Gemini {ges(heute, 'gemini')}",
         f"Befund-KI Monat {monat}: Aufrufe Claude {ges(mon, 'anthropic')}, Rückfälle auf Gemini {m_rf}, "
         f"Anthropic {ges(mon, 'usd'):.2f} $ (heute {ges(heute, 'usd'):.2f} $)",
         f"Spracherkennung Chirp: heute {ges(heute, 'chirp_s') / 60:.1f} min, Monat {chirp_m / 60:.1f} min "
         f"≈ {chirp_eur(chirp_m):.2f} € (× {CHIRP_USD_MIN} $/min), hochgerechnet {hoch:.2f} €/Monat "
         f"(aus {n_tage} Tag{'en' if n_tage != 1 else ''})"]
    for pc in sorted(alle):
        h = heute[pc]
        z.append(f"  {pc}: heute Befunde {h['befunde']}, Claude {h['anthropic']}, Rückfall {h['rueckfall']}, "
                 f"Gemini {h['gemini']}, Chirp {h['chirp_s'] / 60:.1f} min")
    warnung = warnung_noetig(hoch, tag, erster)
    if warnung:
        z.append(f"WARNUNG: Chirp hochgerechnet {hoch:.2f} €/Monat > {WARN_EUR:.0f} € (Google-Guthaben ~9 €)")
    return "\n".join(z) + "\n", warnung


def schreibe_tagesbericht(ordner, tag):
    text, warnung = tagesbericht(ordner, tag)
    pfad = os.path.join(ordner, f"tagesbericht_{tag}.txt")
    tmp = pfad + f".{pc_name()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, pfad)
    if warnung:
        w = os.path.join(ordner, f"warnung_{tag[:7]}.txt")
        if not os.path.exists(w):
            with open(w, "w", encoding="utf-8") as f:
                f.write(text)
    return pfad
