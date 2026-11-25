"""Nutzungszähler der EXE (kaiscribe-sonnet-n2, 16.11.2026) — ohne Tk/Windows importierbar, ohne Patientendaten.

Peter 14.11.2026 („ich will nicht noch extra google zahlen“): Die Befund-KI läuft über Claude Sonnet, Gemini nur noch als
Rückfall. Jeder Rückfall wird gezählt, und die an Chirp (Google-Spracherkennung) geschickten Audiosekunden auch.

- Datei je PC und Monat: <ordner>/<JJJJ-MM>_<PC>.json (jeder PC schreibt nur seine eigene Datei → keine Konflikte auf X:)
  {"pc": …, "tage": {"JJJJ-MM-TT": {"ki": {"anthropic": n, "gemini": n, "rueckfall": n}, "rueckfall_grund": {…},
   "anthropic_usd": x, "stt_s": {"chirp": s, "streaming": s}}}}
  Gezählt werden nur Zahlen und Kategorien (Rolle, Anbieter, Rückfall-Grund ohne Werte) — nie Text, Namen, Nummern.
- tagesbericht(ordner, tag) fasst alle PC-Dateien des Monats zusammen → Text; schreibe_tagesbericht() legt ihn als
  tagesbericht_<JJJJ-MM-TT>.txt daneben. Hochrechnung Chirp (Monat bisher / Tage × Monatstage) > WARN_EUR → Warnzeile
  „WARNUNG“ und warnung_<JJJJ-MM>.txt (seit sonnet-n3-beleg inkl. Live-Anzeige/Streaming, die kostet bei Google auch) (für die Kanban-Karte am Mac, tools/mac/kaiscribe_chirp_warnung.py). Seit
  sonnet-n3-beleg: gezählt ab dem ersten Tag mit Daten im Monat, Warnung erst ab MIN_TAGE gezählten Tagen.
- kaiscribe-ohne-gemini-n1 (24.11.2026): kein Gemini-Rückfall mehr → „ki.ohne_ki“ (je Rolle in „ohne_ki_rolle“, je Grund-
  Kategorie in „ohne_ki_grund“) und „ki.zweitversuch“ (Claude erst im zweiten Versuch). Alte Dateien mit „rueckfall“ werden
  weiter gelesen (KI_RUECKFALL = an zählt wie bisher).
- kaiscribe-stt-tagesdeckel-n1 (24.11.2026): stt_deckel(art, info) – Tagesdeckel der Spracherkennung meldet „warn80“ (80 %
  der Tagesgrenze), „grenze“ (erreicht) bzw. „schleife“ (Schleifenbremse) → td["stt_deckel"] = {art: n, "min": …,
  "limit_min": …} → im Tagesbericht je PC eine Zeile „STT-DECKEL <PC> …“ (die liest die Chirp-Warnung am Mac → Karte für
  Hermes).
- kaiscribe-kosten-je-befund-n1 (25.11.2026): je Anthropic-Antwort die Token-Summen aus usage → td["token"] = {"input",
  "cache_lesen", "cache_schreiben_5m", "cache_schreiben_1h", "output"} und td["cache"] = {"treffer", "neu", "ohne"}
  (Aufrufe mit Cache-Treffer / Neuschreiben / ganz ohne Cache). Verworfene, aber abgerechnete Antworten (Platzhalter
  fehlt, unvollständig …) zählen in td["ki"]["verworfen"] und in $/Token, aber nicht als Aufruf/Befund. Tagesbericht:
  Zeile „Claude-Token …“ (nur Zahlen).
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
STREAM_USD_MIN = 0.024    # Speech-to-Text v1 latest_long (Live-Anzeige, Streaming), Listenpreis ohne Datenprotokoll
USD_EUR = 0.87            # Richtwert für die €-Anzeige (Warnung), kein Abrechnungskurs
WARN_EUR = 6.0            # Peter 14.11.: Google-Guthaben ~9 €/Monat → Warnung ab hochgerechnet 6 €
MIN_TAGE = 3              # Warnung erst ab 3 gezählten Kalendertagen (ein einzelner Tag ist zu zufällig)

_sperre = threading.Lock()


def pc_name(environ=None):
    env = os.environ if environ is None else environ
    roh = env.get("COMPUTERNAME") or env.get("HOSTNAME") or "pc"
    return re.sub(r"[^A-Za-z0-9_-]", "_", roh)[:40] or "pc"


def ordner_aus(lauf_ordner, appdata=None):
    """Zähler-Ordner neben dem Lauf-Protokoll (X:\\KaiScribe\\Daten\\nutzung); LAUF_ORDNER = aus → %APPDATA%\\KaiScribe."""
    lo = (lauf_ordner or "").strip()
    if lo and lo.lower() != "aus":
        import ntpath
        pfad = ntpath if "\\" in lo else os.path       # X:\… auch beim Test am Mac richtig zerlegen
        return pfad.join(pfad.dirname(lo.rstrip("\\/")) or lo, "nutzung")
    return os.path.join(appdata or os.environ.get("APPDATA") or os.path.expanduser("~"), "KaiScribe", "nutzung")


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


TOKEN_FELDER = ("input", "cache_lesen", "cache_schreiben_5m", "cache_schreiben_1h", "output")


def _token_zaehlen(td, u):
    """usage einer Anthropic-Antwort → Tagessummen (nur Zahlen). Ohne Aufschlüsselung 5m/1h zählt das Schreiben als 1h
    (so schickt die EXE cache_control)."""
    def n(k):
        try:
            return max(0, int(u.get(k, 0) or 0))
        except (TypeError, ValueError):
            return 0
    teil = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else None
    cw = n("cache_creation_input_tokens")
    if teil:
        w5 = max(0, int(teil.get("ephemeral_5m_input_tokens", 0) or 0))
        w1 = max(0, int(teil.get("ephemeral_1h_input_tokens", 0) or 0))
    else:
        w5, w1 = 0, cw
    t = td.setdefault("token", {})
    for k, v in (("input", n("input_tokens")), ("cache_lesen", n("cache_read_input_tokens")),
                 ("cache_schreiben_5m", w5), ("cache_schreiben_1h", w1), ("output", n("output_tokens"))):
        t[k] = int(t.get(k, 0) or 0) + v
    c = td.setdefault("cache", {})
    art = "treffer" if n("cache_read_input_tokens") else "neu" if (cw or w5 or w1) else "ohne"
    c[art] = int(c.get(art, 0) or 0) + 1


class Zaehler:
    def __init__(self, ordner, pc=None, jetzt=None):
        """ordner: Pfad oder Funktion, die ihn bei jedem Schreiben liefert (kaiscribe-umzug-n1-exe: X:\\KaiScribe vor
        X:\\RaKScribe erst auflösen, wenn X: verbunden ist)."""
        self._ordner, self.pc = ordner, pc or pc_name()
        self.jetzt = jetzt or datetime.datetime.now

    @property
    def ordner(self):
        return self._ordner() if callable(self._ordner) else self._ordner

    def _aendern(self, fn):
        ordner = self.ordner
        if not ordner:
            return
        t = self.jetzt()
        tag, monat = t.strftime("%Y-%m-%d"), t.strftime("%Y-%m")
        with _sperre:
            try:
                os.makedirs(ordner, exist_ok=True)
                pfad = _datei(ordner, monat, self.pc)
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
            schreibe_tagesbericht(ordner, tag)
        except Exception:
            pass

    def ki(self, info):
        """Beobachter der llm_anbieter.Weiche: je Aufruf {rolle, anbieter, rueckfall, usd, usage, cache, verworfen …}."""
        info = info or {}

        def fn(td):
            ki = td.setdefault("ki", {})
            if isinstance(info.get("usage"), dict):
                _token_zaehlen(td, info["usage"])
            if info.get("verworfen"):       # abgerechnet, aber nicht verwendet → nur Kosten/Token + Zähler
                ki["verworfen"] = ki.get("verworfen", 0) + 1
                if info.get("usd"):
                    td["anthropic_usd"] = round(td.get("anthropic_usd", 0.0) + float(info["usd"]), 6)
                return
            if info.get("zweitversuch"):     # jeder zweite Anthropic-Versuch; _ok = er hat den Text geliefert
                ki["zweitversuch"] = ki.get("zweitversuch", 0) + 1
                if not info.get("ohne_ki"):
                    ki["zweitversuch_ok"] = ki.get("zweitversuch_ok", 0) + 1
            if info.get("ohne_ki"):
                ki["ohne_ki"] = ki.get("ohne_ki", 0) + 1
                ro = td.setdefault("ohne_ki_rolle", {})
                r = str(info.get("rolle") or "?")[:8]
                ro[r] = ro.get(r, 0) + 1
                gr = td.setdefault("ohne_ki_grund", {})
                k = _grund_kategorie(info["ohne_ki"])
                gr[k] = gr.get(k, 0) + 1
            elif info.get("rueckfall"):
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
        """An Google geschickte Audiosekunden (art = chirp: chirp_3-Volltranskript, streaming: Live-Anzeige v1)."""
        if not sekunden or sekunden <= 0:
            return

        def fn(td):
            s = td.setdefault("stt_s", {})
            s[art] = round(s.get(art, 0.0) + float(sekunden), 1)
        self._aendern(fn)


    def stt_deckel(self, art, info=None):
        """Tagesdeckel der Spracherkennung (stt_deckel.Deckel.melden): art = warn80 | grenze | schleife, nur Zahlen."""
        info = info or {}
        art = re.sub(r"[^a-z0-9]", "", str(art or "?"))[:10] or "?"

        def fn(td):
            d = td.setdefault("stt_deckel", {})
            d[art] = int(d.get(art, 0) or 0) + 1
            for k in ("min", "limit_min"):
                if isinstance(info.get(k), (int, float)):
                    d[k] = round(float(info[k]), 1)
        self._aendern(fn)


DECKEL_ARTEN = {"warn80": "80 % der Tagesgrenze erreicht", "grenze": "Tagesgrenze erreicht – keine Spracherkennung mehr",
                "schleife": "Schleifenbremse (dieselbe Aufnahme > 3× an Google)"}


def deckel_zeilen(alle, tag):
    """Tagesbericht-Zeilen „STT-DECKEL <PC> …“ für alle PCs mit Deckel-Meldung an diesem Tag."""
    z = []
    for pc in sorted(alle):
        d = ((alle[pc].get("tage") or {}).get(tag) or {}).get("stt_deckel") or {}
        arten = [a for a in ("grenze", "warn80", "schleife") if d.get(a)]
        if not arten:
            continue
        z.append(f"STT-DECKEL {pc}: " + "; ".join(DECKEL_ARTEN[a] + (f" ({d[a]}×)" if a == "schleife" else "")
                                                for a in arten)
                 + (f" – {d['min']:.0f} von {d['limit_min']:.0f} min Audio" if "min" in d and "limit_min" in d else ""))
    return z


def monat_summen(ordner, monat):
    """Alle PC-Dateien eines Monats → {pc: daten}."""
    aus = {}
    for p in sorted(glob.glob(os.path.join(ordner, f"{monat}_*.json"))):
        d = _lesen(p)
        if d:
            aus[d.get("pc") or os.path.basename(p)[len(monat) + 1:-5]] = d
    return aus


def _summe(tage, nur_tag=None):
    s = {"anthropic": 0, "gemini": 0, "rueckfall": 0, "ohne_ki": 0, "zweitversuch": 0, "zweitversuch_ok": 0, "befunde": 0, "usd": 0.0,
         "chirp_s": 0.0, "stream_s": 0.0, "gruende": {}, "ohne_gruende": {}, "ohne_rollen": {}, "verworfen": 0,
         "token": {k: 0 for k in TOKEN_FELDER}, "cache": {"treffer": 0, "neu": 0, "ohne": 0}}
    for tag, td in (tage or {}).items():
        if nur_tag and tag != nur_tag:
            continue
        ki = td.get("ki", {})
        for k in ("anthropic", "gemini", "rueckfall", "ohne_ki", "zweitversuch", "zweitversuch_ok", "verworfen"):
            s[k] += int(ki.get(k, 0) or 0)
        for k in TOKEN_FELDER:
            s["token"][k] += int((td.get("token") or {}).get(k, 0) or 0)
        for k in ("treffer", "neu", "ohne"):
            s["cache"][k] += int((td.get("cache") or {}).get(k, 0) or 0)
        s["befunde"] += int(td.get("befunde", 0) or 0)
        s["usd"] += float(td.get("anthropic_usd", 0) or 0)
        s["chirp_s"] += float((td.get("stt_s") or {}).get("chirp", 0) or 0)
        s["stream_s"] += float((td.get("stt_s") or {}).get("streaming", 0) or 0)
        for g, n in (td.get("rueckfall_grund") or {}).items():
            s["gruende"][g] = s["gruende"].get(g, 0) + int(n or 0)
        for g, n in (td.get("ohne_ki_grund") or {}).items():
            s["ohne_gruende"][g] = s["ohne_gruende"].get(g, 0) + int(n or 0)
        for g, n in (td.get("ohne_ki_rolle") or {}).items():
            s["ohne_rollen"][g] = s["ohne_rollen"].get(g, 0) + int(n or 0)
    return s


def chirp_eur(sekunden):
    return sekunden / 60.0 * CHIRP_USD_MIN * USD_EUR


def stream_eur(sekunden):
    return sekunden / 60.0 * STREAM_USD_MIN * USD_EUR


def hochrechnung_eur(chirp_s_monat, tag, erster_tag=None, stream_s_monat=0.0):
    """Chirp-€ des Monats bisher, auf den ganzen Monat hochgerechnet (bisher / gezählte Tage × Monatstage).
    Gezählte Tage = ab erster_tag (erster Tag mit Zählerdaten im Monat), sonst ab dem 1. — v3.19.x (sonnet-n3-beleg):
    der Zähler kam am 16.11. dazu, „bisher / 16“ rechnete den November um das 16-Fache zu niedrig."""
    return (chirp_eur(chirp_s_monat) + stream_eur(stream_s_monat)) / gezaehlte_tage(tag, erster_tag) * _monatstage(tag)


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
    def zus(dct, k):
        aus = {}
        for v in dct.values():
            for g, n in v[k].items():
                aus[g] = aus.get(g, 0) + n
        return aus

    def liste(d):
        return " (" + ", ".join(f"{g}: {n}" for g, n in sorted(d.items())) + ")" if d else ""
    gruende = zus(heute, "gruende")
    chirp_m = ges(mon, "chirp_s")
    erster = erster_tag(alle)
    stream_m = ges(mon, "stream_s")
    hoch, n_tage = hochrechnung_eur(chirp_m, tag, erster, stream_m), gezaehlte_tage(tag, erster)
    z = [f"KaiScribe Tagesbericht {tag} (alle PCs, ohne Patientendaten)",
         f"Befund-KI heute: {ges(heute, 'befunde')} Befunde, Aufrufe Claude {ges(heute, 'anthropic')}, "
         f"Rückfälle auf Gemini {h_rf}" + (" (" + ", ".join(f"{g}: {n}" for g, n in sorted(gruende.items())) + ")"
                                           if gruende else "") + f", nur Gemini {ges(heute, 'gemini')}",
         f"Ohne KI (kein Rückfall) heute {ges(heute, 'ohne_ki')}" + liste(zus(heute, "ohne_gruende"))
         + (" je Rolle" + liste(zus(heute, "ohne_rollen")) if ges(heute, "ohne_ki") else "")
         + f", zweite Claude-Versuche {ges(heute, 'zweitversuch')} (davon geklappt {ges(heute, 'zweitversuch_ok')})",
         f"Befund-KI Monat {monat}: Aufrufe Claude {ges(mon, 'anthropic')}, Rückfälle auf Gemini {m_rf}, "
         f"ohne KI {ges(mon, 'ohne_ki')}, zweite Versuche {ges(mon, 'zweitversuch')}, "
         f"Anthropic {ges(mon, 'usd'):.2f} $ (heute {ges(heute, 'usd'):.2f} $)",
         f"Spracherkennung Chirp: heute {ges(heute, 'chirp_s') / 60:.1f} min, Monat {chirp_m / 60:.1f} min "
         f"≈ {chirp_eur(chirp_m):.2f} € (× {CHIRP_USD_MIN} $/min)",
         f"Live-Anzeige (Google-Streaming): heute {ges(heute, 'stream_s') / 60:.1f} min, Monat {stream_m / 60:.1f} min "
         f"≈ {stream_eur(stream_m):.2f} € (× {STREAM_USD_MIN} $/min)",
         f"Google-Spracherkennung gesamt hochgerechnet {hoch:.2f} €/Monat (aus {n_tage} Tag{'en' if n_tage != 1 else ''})"]
    z.append(token_zeile("heute", heute) + "; " + token_zeile("Monat", mon, kurz=True))
    z.extend(deckel_zeilen(alle, tag))          # tagesdeckel-n1 (vor den PC-Zeilen: der VM-Leser nimmt nur 40 Zeilen)
    for pc in sorted(alle):
        h = heute[pc]
        z.append(f"  {pc}: heute Befunde {h['befunde']}, Claude {h['anthropic']}, Rückfall {h['rueckfall']}, "
                 f"ohne KI {h['ohne_ki']}, "
                 f"Gemini {h['gemini']}, Chirp {h['chirp_s'] / 60:.1f} min, Live {h['stream_s'] / 60:.1f} min")
    warnung = warnung_noetig(hoch, tag, erster)
    if warnung:
        z.append(f"WARNUNG: Google-Spracherkennung (Chirp + Live) hochgerechnet {hoch:.2f} €/Monat > {WARN_EUR:.0f} € (Google-Guthaben ~9 €)")
    return "\n".join(z) + "\n", warnung


def token_zeile(wann, dct, kurz=False):
    """„Claude-Token heute: Input … | Cache lesen … | schreiben 1h … (5m …) | Output … | Cache-Treffer a, neu b, ohne c
    | verworfen d | ≈ x ct je Aufruf“ — nur Zahlen (kosten-je-befund-n1)."""
    t = {k: sum(v["token"][k] for v in dct.values()) for k in TOKEN_FELDER}
    c = {k: sum(v["cache"][k] for v in dct.values()) for k in ("treffer", "neu", "ohne")}
    n, usd = sum(v["anthropic"] for v in dct.values()), sum(v["usd"] for v in dct.values())
    verw = sum(v["verworfen"] for v in dct.values())
    je = f", ≈ {usd / n * 100:.1f} ct je Aufruf" if n else ""
    if kurz:
        return (f"{wann}: Cache-Treffer {c['treffer']}, neu {c['neu']}, ohne {c['ohne']}, verworfen {verw}{je}")
    return (f"Claude-Token {wann}: Input {t['input']}, Cache lesen {t['cache_lesen']}, Cache schreiben 1h "
            f"{t['cache_schreiben_1h']} (5m {t['cache_schreiben_5m']}), Output {t['output']}; Cache-Treffer {c['treffer']}, "
            f"neu {c['neu']}, ohne {c['ohne']}, verworfen {verw}{je}")


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
