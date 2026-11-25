r"""KaiScribe-Übungsdienst (kaiscribe-uebung-n1, 25.11.2026) – läuft NUR auf der Automaten-VM (Konto rakauto).

Web-Server (Stdlib) auf 127.0.0.1:<port>; von außen nur über `tailscale serve` (HTTPS im Tailnet). Liefert
  /            die KaiScribe-Web-App (gebaut mit Basis /, Ordner web\)  → gleiche Herkunft, kein CORS nötig
  /api/…       Übungsdaten aus den gespiegelten Tagesdateien (spiegel.py), Anmeldung je Kürzel (kp/rg)
Ablage: X:\KaiScribe-Übung\<JJJJMMTT>\<kürzel>\<RH>_<kürzel>.docx + .html (Vergleich); ohne X: → <basis>\ablage\….

HARTE SPERRE: kein CAS, keine Brücke, kein Roboter, keine Plaza/ELGA/marc/Teleimage, kein SpeechMagic – dieser Prozess
öffnet keine einzige ausgehende Verbindung und startet keinen Unterprozess (Test: tests/offline/test_uebung.py).
Variante: über Tailscale immer „anonym“ (erzwungen); „haus“ nur über einen ausdrücklich eingeschalteten LAN-Zugang.
Protokoll: nur Zähler (zaehler.json), nie Inhalte.

  py -3.12 -X utf8 uebung_dienst.py [--basis C:\RaK\kaiscribe_uebung] [--port 8473]
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import uebung_kern as K  # noqa: E402

PORT_STANDARD = 8473
X_ABLAGE = "X:\\KaiScribe-Übung"
MAX_KOERPER = 400_000
PAGES_HERKUNFT = "https://drpeterkalmar.github.io"     # Web-App auf GitHub Pages darf (mit Anmeldung) auch fragen


class Dienst:
    def __init__(self, basis, ablage=None, uhr=None, lan=False):
        self.basis = basis
        self.daten = os.path.join(basis, "daten")
        self.web = os.path.join(basis, "web")
        self.ablage_wurzel = ablage
        self.lan = lan
        try:
            with open(os.path.join(basis, "konten.json"), encoding="utf-8") as f:
                konten = json.load(f)
        except (OSError, ValueError):
            konten = {}
        self.sitzungen = K.Sitzungen(konten)
        self.zaehler = K.Zaehler(os.path.join(basis, "zaehler.json"), **({"uhr": uhr} if uhr else {}))
        self.abgaben_pfad = os.path.join(basis, "abgaben.json")   # (kürzel, tag, id) → {"befund", "datei"} (nur VM)
        self.abgaben = {}
        try:
            with open(self.abgaben_pfad, encoding="utf-8") as f:
                for z in json.load(f):
                    self.abgaben[(z["k"], z["tag"], z["id"])] = {"befund": z["befund"], "datei": z["datei"]}
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.lock = threading.Lock()
        self._cache = {}

    def abgaben_sichern(self):
        tmp = self.abgaben_pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([{"k": k, "tag": t, "id": i, **v} for (k, t, i), v in self.abgaben.items()], f, ensure_ascii=False)
        os.replace(tmp, self.abgaben_pfad)

    # ── Ablage ──
    def ablage_ordner(self, tag, kuerzel):
        for w in ([self.ablage_wurzel] if self.ablage_wurzel else [X_ABLAGE, os.path.join(self.basis, "ablage")]):
            p = os.path.join(w, tag, kuerzel)
            try:
                os.makedirs(p, exist_ok=True)
                return p
            except OSError:
                continue
        raise OSError("keine Ablage")

    def spiegel(self, tag, variante):
        k = (tag, variante)
        p = os.path.join(self.daten, tag, variante + ".json")
        try:
            mt = os.path.getmtime(p)
        except OSError:
            return None
        if k not in self._cache or self._cache[k][0] != mt:
            d = K.spiegel_lesen(self.daten, tag, variante)
            if d is None:
                return None
            self._cache[k] = (mt, d)
        return self._cache[k][1]

    def fall(self, tag, variante, fid, kuerzel):
        s = self.spiegel(tag, variante)
        if not s:
            return None
        for f in s.get("faelle") or []:
            if f.get("id") == fid and f.get("kuerzel") == kuerzel:
                return f
        return None


def herkunft(handler, lan_an):
    """tailscale serve leitet über 127.0.0.1 weiter und setzt Tailscale-User-Login → 'tailscale'. LAN nur, wenn der
    LAN-Zugang ausdrücklich an ist UND die Gegenstelle im Ordi-Netz liegt. Alles andere zählt wie Tailscale (anonym)."""
    ip = handler.client_address[0]
    if lan_an and ip.startswith("10.168.110.") and not handler.headers.get("Tailscale-User-Login"):
        return "lan"
    return "tailscale"


class Handler(BaseHTTPRequestHandler):
    server_version = "KaiScribeUebung/" + K.VERSION
    dienst: Dienst = None  # type: ignore[assignment]

    def log_message(self, *a):        # kein Zugriffsprotokoll mit Inhalten/Pfaden
        return

    # ── Antworten ──
    def _kopf_sicher(self):
        o = self.headers.get("Origin") or ""
        if o == PAGES_HERKUNFT:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self._kopf_sicher()
        self.end_headers()
        self.wfile.write(b)

    def _bytes(self, code, b, typ, name=None):
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(b)))
        if name:
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self._kopf_sicher()
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._kopf_sicher()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _koerper(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_KOERPER:
            return {}
        try:
            d = json.loads(self.rfile.read(n).decode("utf-8"))
            return d if isinstance(d, dict) else {}
        except (ValueError, UnicodeDecodeError):
            return {}

    def _wer(self):
        a = self.headers.get("Authorization") or ""
        return self.dienst.sitzungen.wer(a[7:] if a.startswith("Bearer ") else "")

    def _variante(self, q):
        return K.variante_fuer(herkunft(self, self.dienst.lan), (q.get("variante") or ["anonym"])[0])

    # ── GET ──
    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path.startswith("/api/"):
            return self._api_get(u.path, q)
        return self._statisch(u.path)

    def _statisch(self, pfad):
        rel = urllib.parse.unquote(pfad).lstrip("/") or "index.html"
        voll = os.path.realpath(os.path.join(self.dienst.web, rel))
        wurzel = os.path.realpath(self.dienst.web)
        if not voll.startswith(wurzel + os.sep) and voll != wurzel:
            return self._json(404, {"fehler": "nicht da"})
        if not os.path.isfile(voll):
            voll = os.path.join(wurzel, "index.html")
        try:
            with open(voll, "rb") as f:
                b = f.read()
        except OSError:
            return self._json(404, {"fehler": "nicht da"})
        typ = mimetypes.guess_type(voll)[0] or "application/octet-stream"
        if typ.startswith("text/") or typ in ("application/javascript", "application/json"):
            typ += "; charset=utf-8"
        self._bytes(200, b, typ)

    def _api_get(self, pfad, q):
        d = self.dienst
        if pfad == "/api/status":
            return self._json(200, {"dienst": "kaiscribe-uebung", "version": K.VERSION, "variante": self._variante(q),
                                    "kuerzel": list(K.KUERZEL)})
        k = self._wer()
        if not k:
            return self._json(401, {"fehler": "anmelden"})
        tag = (q.get("tag") or [""])[0]
        var = self._variante(q)
        if pfad == "/api/tage":
            return self._json(200, {"tage": K.tage(d.daten), "variante": var, "kuerzel": k,
                                    "stt_rest_s": d.zaehler.stt_rest_s(k)})
        if not K.TAG_RE.match(tag):
            return self._json(400, {"fehler": "tag"})
        if pfad == "/api/faelle":
            s = d.spiegel(tag, var)
            if not s:
                return self._json(404, {"fehler": "tag nicht gespiegelt"})
            faelle = [{"id": f["id"], "zeit": f.get("zeit"), "untersuchungen": f.get("untersuchungen"),
                       "alter": f.get("alter"), "geschlecht": f.get("geschlecht"),
                       "abgegeben": (k, tag, f["id"]) in d.abgaben or self._abgabe_datei(tag, k, f["id"]) is not None}
                      for f in s.get("faelle") or [] if f.get("kuerzel") == k]
            return self._json(200, {"tag": tag, "variante": var, "faelle": faelle, "senf_fehlt": s.get("senf_fehlt", 0)})
        fid = (q.get("id") or [""])[0]
        if not K.FALL_RE.match(fid):
            return self._json(400, {"fehler": "id"})
        f = d.fall(tag, var, fid, k)
        if not f:
            return self._json(404, {"fehler": "fall"})
        if pfad == "/api/fall":
            d.zaehler.zaehlen(k, "fall")
            return self._json(200, {"tag": tag, "variante": var, "fall": K.fall_ohne_loesung(f)})
        if pfad == "/api/loesung":
            ab = d.abgaben.get((k, tag, fid))
            if not ab:
                return self._json(403, {"fehler": "erst abgeben"})
            d.zaehler.zaehlen(k, "loesung")
            ops = K.wort_diff(ab["befund"], f.get("loesung") or "")
            return self._json(200, {"loesung": f.get("loesung") or "", "diff": ops, "zahlen": K.diff_zahlen(ops)})
        if pfad == "/api/word":
            p = self._abgabe_datei(tag, k, fid)
            if not p:
                return self._json(404, {"fehler": "keine abgabe"})
            with open(p, "rb") as fh:
                b = fh.read()
            d.zaehler.zaehlen(k, "word")
            return self._bytes(200, b, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               os.path.basename(p))
        return self._json(404, {"fehler": "pfad"})

    def _abgabe_datei(self, tag, k, fid):
        ab = self.dienst.abgaben.get((k, tag, fid))
        if ab and os.path.isfile(ab["datei"]):
            return ab["datei"]
        return None

    # ── POST ──
    def do_POST(self):  # noqa: N802
        d = self.dienst
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        body = self._koerper()
        if u.path == "/api/anmelden":
            t, fehler = d.sitzungen.anmelden(body.get("kuerzel"), body.get("kennwort") or "")
            if not t:
                return self._json(403 if fehler == "falsch" else 429, {"fehler": fehler})
            k = d.sitzungen.wer(t)
            d.zaehler.zaehlen(k, "anmeldung")
            return self._json(200, {"token": t, "kuerzel": k, "variante": self._variante(q),
                                    "stt_rest_s": d.zaehler.stt_rest_s(k)})
        k = self._wer()
        if not k:
            return self._json(401, {"fehler": "anmelden"})
        if u.path == "/api/abmelden":
            a = self.headers.get("Authorization") or ""
            d.sitzungen.abmelden(a[7:])
            return self._json(200, {"ok": True})
        if u.path == "/api/stt":
            # Vor jeder Aufnahme: Rest abfragen ("sekunden": 0) bzw. nach der Aufnahme buchen ("sekunden": Audio-s)
            s = body.get("sekunden")
            try:
                s = max(0, min(3600, int(float(s or 0))))
            except (TypeError, ValueError):
                s = 0
            if s:
                d.zaehler.zaehlen(k, "stt_s", s * K.STT_FAKTOR)
            return self._json(200, {"stt_rest_s": d.zaehler.stt_rest_s(k), "faktor": K.STT_FAKTOR})
        if u.path == "/api/abgabe":
            tag, fid = str(body.get("tag") or ""), str(body.get("id") or "")
            befund, diktat = str(body.get("befund") or "")[:60000], str(body.get("diktat") or "")[:60000]
            if not K.TAG_RE.match(tag) or not K.FALL_RE.match(fid) or not befund.strip():
                return self._json(400, {"fehler": "eingabe"})
            var = self._variante(q)
            f = d.fall(tag, var, fid, k)
            if not f:
                return self._json(404, {"fehler": "fall"})
            try:
                ordner = d.ablage_ordner(tag, k)
            except OSError:
                return self._json(500, {"fehler": "ablage"})
            name = K.ablage_name(fid, k)
            with d.lock:
                n = 1
                while os.path.exists(os.path.join(ordner, name + ("" if n == 1 else f"_{n}") + ".docx")):
                    n += 1
                stamm = os.path.join(ordner, name + ("" if n == 1 else f"_{n}"))
                docx = K.docx_cas(f, befund, k, tag)
                with open(stamm + ".docx", "xb") as fh:
                    fh.write(docx)
                ops = K.wort_diff(befund, f.get("loesung") or "")
                kopf = f"{fid} · {'; '.join(f.get('untersuchungen') or [])} · Übung {k} · Tag {tag}"
                with open(stamm + ".html", "x", encoding="utf-8") as fh:
                    fh.write(K.diff_html(ops, kopf, befund, f.get("loesung") or "", diktat))
                d.abgaben[(k, tag, fid)] = {"befund": befund, "datei": stamm + ".docx"}
                d.abgaben_sichern()
            d.zaehler.zaehlen(k, "abgabe")
            return self._json(200, {"ok": True, "ablage": os.path.basename(stamm) + ".docx", "versuch": n,
                                    "zahlen": K.diff_zahlen(ops)})
        return self._json(404, {"fehler": "pfad"})


def server(dienst, host, port):
    h = type("H", (Handler,), {"dienst": dienst})
    return ThreadingHTTPServer((host, port), h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", default=r"C:\RaK\kaiscribe_uebung")
    ap.add_argument("--port", type=int, default=PORT_STANDARD)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--ablage", default=None)
    ap.add_argument("--lan", action="store_true", help="Variante haus für Anfragen aus 10.168.110.x zulassen")
    a = ap.parse_args()
    if not re.fullmatch(r"127\.0\.0\.1|10\.168\.110\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3}", a.host):
        sys.exit("nur 127.0.0.1, Ordi-LAN oder Tailnet")
    d = Dienst(a.basis, a.ablage, lan=a.lan)
    s = server(d, a.host, a.port)
    print(f"UEBUNG {K.VERSION} {a.host}:{a.port} konten={len(d.sitzungen.konten)} tage={len(K.tage(d.daten))}", flush=True)
    s.serve_forever()


if __name__ == "__main__":
    main()
