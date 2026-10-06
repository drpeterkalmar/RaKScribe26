"""Gate (Umbau Schritt 22, Gutachten P2-11): Der SECURITY-Schritt in deploy.yml bricht den Pages-Deploy ab, sobald
Schlüsselmaterial im Bundle liegt — und lässt ein sauberes Bundle (das den Code zum Lesen von Schlüsseln enthält)
durch. Der Schritt wird wörtlich aus deploy.yml gelesen und gegen Dummy-Ordner ausgeführt (nur erfundene Schlüssel).
Aufruf: /usr/bin/python3 tests/offline/test_deploy_guard.py"""
import pathlib, subprocess, sys, tempfile
import yaml
ROOT = pathlib.Path(__file__).resolve().parents[2]

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


wf = yaml.safe_load((ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8"))
schritte = wf["jobs"]["build-and-deploy"]["steps"]
guard = next(s for s in schritte if s.get("name", "").startswith("SECURITY"))["run"]
check("SECURITY-Schritt steht VOR dem Hochladen des Bundles",
      [s.get("name", "") for s in schritte].index(next(s for s in schritte if s.get("name", "").startswith("SECURITY"))["name"])
      < [s.get("uses", "") for s in schritte].index("actions/upload-pages-artifact@v3"))

SAUBER_JS = ("const r=t.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\\n|\\r/g,'');"
             "if(json.type==='service_account'&&json.private_key){x(json)}if(c.startsWith('AQ.')){y(c)}"
             "const p=localStorage.getItem('praxis_stt_key');")
FALSCH_PEM = "-----BEGIN PRIVATE KEY-----\\n" + "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC" + "DUMMYdummyDUMMYdummy" * 3 + "\\n-----END PRIVATE KEY-----\\n"


def lauf(dateien):
    with tempfile.TemporaryDirectory() as td:
        dist = pathlib.Path(td) / "web_app" / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<title>RaKScribe</title>")
        for name, inhalt in dateien.items():
            (dist / name).write_text(inhalt)
        r = subprocess.run(["bash", "-c", guard], cwd=td, capture_output=True, text=True)
        return r.returncode


check("sauberes Bundle (Code liest Schlüssel, enthält aber keinen) → Deploy läuft", lauf({"assets/index-abc.js": SAUBER_JS}) == 0)
check("Service-Account-JSON im Bundle → Abbruch",
      lauf({"assets/index-abc.js": SAUBER_JS, "assets/x.js": '{"type":"service_account","private_key": "' + FALSCH_PEM + '"}'}) != 0)
check("PEM-Schlüssel im JS → Abbruch", lauf({"assets/index-abc.js": SAUBER_JS + "const k=`" + FALSCH_PEM.replace("\\n", "\n") + "`"}) != 0)
check("Gemini-Schlüssel AQ.… im JS → Abbruch", lauf({"assets/index-abc.js": SAUBER_JS + "const k='AQ.Ab8RN6DummyDummyDummyDummy0123456789'"}) != 0)
check("Schlüssel-Datei im Bundle (stt-key.txt) → Abbruch", lauf({"stt-key.txt": "leer"}) != 0)
check("Schlüssel-Datei im Bundle (rakscribe-praxis-key.json) → Abbruch", lauf({"rakscribe-praxis-key.json": "{}"}) != 0)

pub = ROOT / "web_app" / "public"
check("web_app/public enthält keine Schlüsseldateien", not [p.name for p in pub.iterdir()
                                                          if any(w in p.name.lower() for w in ("key", "cred", "secret"))])

print("\n" + ("✅ DEPLOY-SCHUTZ PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
