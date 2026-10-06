"""Gate (Umbau Schritt 11): Schlüssel-Logik der EXE (keys.py) — nur rakscribe-praxis-key.json (v3.2.3),
neben der EXE vor %APPDATA%, Altdateien ignoriert, Windows-Kodierungen, Token-Cache mit UTC-Ablauf (P3-6).
Nur Dummy-Schlüssel. Aufruf: /usr/bin/python3 tests/offline/test_keys.py"""
import base64, json, os, pathlib, sys, tempfile, time
from datetime import datetime, timedelta
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import keys as k  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def praxis(gk, mit_stt=True):
    d = {"vertex_api_key": gk}
    if mit_stt:
        d["stt"] = {"type": "service_account", "client_email": "dummy@example.invalid", "private_key": "-----DUMMY-----"}
    return json.dumps(d)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_keys_"))
base, appdata = tmp / "exe", tmp / "appdata"
base.mkdir()
user_dir, user_path = k.user_key_paths({"APPDATA": str(appdata)})
check("Benutzer-Schlüssel liegt in %APPDATA%\\RaKScribe", user_dir == str(appdata / "RaKScribe")
      and user_path.endswith("rakscribe-praxis-key.json"))
os.makedirs(user_dir)

check("ohne Datei → kein Schlüssel", k.load_praxis_key(str(base), user_path) == ("", None))
# Altdateien (rotiert) werden NICHT gelesen
(base / "vertex-key.b64").write_text(base64.b64encode(b"AQ.alt-b64").decode())
(base / "vertex-key.txt").write_text("AQ.alt-txt")
(base / "rakscribe-stt-key.json").write_text(json.dumps({"type": "service_account", "private_key": "x"}))
check("nur Altdateien (vertex-key.b64/.txt, stt-key.json) → kein Schlüssel (v3.2.3)",
      k.load_vertex_key(str(base), user_path) == "" and k.load_praxis_key(str(base), user_path)[1] is None)

pathlib.Path(user_path).write_text(praxis("AQ.benutzer"))
gk, stt = k.load_praxis_key(str(base), user_path)
check("nur %APPDATA%-Schlüssel → wird genutzt", gk == "AQ.benutzer" and stt["client_email"] == "dummy@example.invalid")
(base / "rakscribe-praxis-key.json").write_text(praxis("AQ.neben-exe"))
check("Datei neben der EXE hat Vorrang vor %APPDATA%", k.load_vertex_key(str(base), user_path) == "AQ.neben-exe"
      and k.praxis_key_path(str(base), user_path) == str(base / "rakscribe-praxis-key.json"))
(base / "rakscribe-praxis-key.json").write_bytes(b"\xff\xfe" + praxis("AQ.utf16").encode("utf-16-le"))
check("UTF-16 mit BOM (Windows-Editor) wird gelesen", k.load_vertex_key(str(base), user_path) == "AQ.utf16")
(base / "rakscribe-praxis-key.json").write_bytes(b"\xef\xbb\xbf" + praxis("AQ.bom").replace("\n", "\r\n").encode())
check("UTF-8 mit BOM + CRLF wird gelesen", k.load_vertex_key(str(base), user_path) == "AQ.bom")
(base / "rakscribe-praxis-key.json").write_text(praxis("AQ.ohne-stt", mit_stt=False))
check("Schlüssel ohne STT-Teil → (Gemini-Key, None)", k.load_praxis_key(str(base), user_path) == ("AQ.ohne-stt", None))
logs = []
(base / "rakscribe-praxis-key.json").write_text("{kaputt")
check("kaputte Datei → kein Schlüssel + Log", k.load_praxis_key(str(base), user_path, log=logs.append) == ("", None)
      and any("nicht verwertbar" in l for l in logs))
check("ist_praxis_schluessel: kombiniert ja, Teilschlüssel nein",
      k.ist_praxis_schluessel(json.loads(praxis("AQ.x"))) and not k.ist_praxis_schluessel(json.loads(praxis("AQ.x", False)))
      and not k.ist_praxis_schluessel({"stt": {"private_key": "x"}}))


class Creds:
    """google-auth-Credentials-Ersatz: expiry = NAIVE UTC wie google-auth."""
    def __init__(self, gueltig_s):
        self.gueltig_s, self.refreshs, self.token, self.expiry = gueltig_s, 0, None, None

    @property
    def valid(self):
        return self.token is not None and self.expiry > datetime.utcnow()

    def refresh(self, _req):
        self.refreshs += 1
        self.token = f"tok{self.refreshs}"
        self.expiry = datetime.utcnow() + timedelta(seconds=self.gueltig_s)


for tz in ("America/New_York", "Europe/Vienna", "Asia/Tokyo"):
    os.environ["TZ"] = tz
    time.tzset()
    c, cache = Creds(3600), k.SttTokenCache()
    t1 = cache.get(c, request_factory=object)
    t2 = cache.get(c, request_factory=object)
    check(f"Token-Cache ({tz}): 2. Aufruf aus dem Cache, Ablauf korrekt als UTC",
          t1 == t2 == "tok1" and c.refreshs == 1 and abs(cache.exp - (time.time() + 3600)) < 5, f"exp-now={cache.exp - time.time():.0f}")
    c2, cache2 = Creds(60), k.SttTokenCache()
    cache2.get(c2, request_factory=object)
    c2.token, c2.expiry = c2.token, datetime.utcnow() - timedelta(seconds=1)  # abgelaufen
    check(f"Token-Cache ({tz}): abgelaufenes Token wird erneuert", cache2.get(c2, request_factory=object) == "tok2")
os.environ.pop("TZ"); time.tzset()
check("ohne Credentials → None", k.SttTokenCache().get(None) is None)
cache = k.SttTokenCache(); cache.token, cache.exp = "x", time.time() + 999
cache.leeren()
check("leeren() verwirft das Token (Schlüsselwechsel)", cache.token is None and cache.exp == 0)

src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt keys.py", "_keys.load_praxis_key(BASE_DIR, USER_KEY_PATH" in src and "_keys.SttTokenCache()" in src
      and "creds.expiry.timestamp()" not in src)

print("\n" + ("✅ SCHLÜSSEL PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
