#!/usr/bin/env python3
"""KaiScribe-EXE am Büro-PC bauen + Windows-UI-Test, danach GitHub-Release vom Mac (kaiscribe-privat-n1, 05.11.2026).

Ersatz für build-exe.yml + test-exe-windows.yml, sobald drpeterkalmar/RaKScribe26 privat ist (Peter-Regel: private
Repos ohne Cloud-CI). Muster windows_pruefung.py (ci-ohne-runner-n1):

  kaiscribe_bau.py [--release | --tag T] [--pfad quelle] [--trocken] [--ohne-release] [--ohne-ui-test] [--aus-job NAME]

  ohne --release/--tag  → Testbau, Tag test-<JJMMTThhmm>, Vorabversion (wie früher ein manueller Lauf ohne Tag)
  --release             → Tag = VERSION von main (darf noch kein Release sein), normales Release = „Latest“
  --ohne-ui-test        → nur bauen (Erstprobe), nie ein Release
  --pfad                → Pfad hinter :8451 (Standard quelle = ai.hermes.ordi-quelle auf 9160; Testinstanz z. B. quelle-ks)

Ablauf: Zeitfenster/belegt (windows_pruefung) → Quell-Dienst /kaiscribe/quelle-stand → Auftrag
tools/buero/auftrag_exe_bauen.txt DES GEBAUTEN Commits (Platzhalter gefüllt) → `hermes peer run ordi` → KSBAU=-Zeile →
EXE aus der Ablage (~/.hermes/cache/ordi-quelle/kaiscribe/ablage/<commit>/<tag>/, Prüfsumme) → `gh release create`
(angemeldet; Notizen = report.md des UI-Tests) → Prüfprotokoll + Commit-Status `windows/buero-pc` am Commit.
Mac-Gates (tests/offline) VORHER am Mac laufen lassen (zusammenfuehren --test); dieses Skript baut nur gepushten main.
Exit 0 ok, 1 rot, 3 nicht gelaufen.
"""
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import pruefprotokoll as PP  # noqa: E402
import windows_pruefung as WP  # noqa: E402

HOME = os.path.expanduser("~")
REPO = "drpeterkalmar/RaKScribe26"
ART = "windows/buero-pc"
WORK = os.path.join(HOME, ".hermes/work/kaiscribe_bau")
ABLAGE = os.path.join(HOME, ".hermes/cache/ordi-quelle/kaiscribe/ablage")
PORTS = {"quelle": 9160, "quelle-ks": 9162}
VORLAGE = "tools/buero/auftrag_exe_bauen.txt"
SKRIPT = "tools/buero/kaiscribe_bauen.py"
FRIST_S = 5400
KSBAU_RX = re.compile(r"KSBAU=(\w+)\s+COMMIT=(\S*)\s+TAG=(\S+)\s+SHA256=(\S+)\s+UITEST=(\S+)\s+DAUER=(\d+)(?:\s+GRUND=(.*))?")


def gh(*a, timeout=300, text=True):
    return subprocess.run(["gh", *a], capture_output=True, text=text, timeout=timeout)


def datei(pfad, ref):
    r = gh("api", "-H", "Accept: application/vnd.github.raw", f"repos/{REPO}/contents/{pfad}?ref={ref}", text=False)
    if r.returncode:
        raise RuntimeError(f"{pfad} fehlt im Commit {ref[:8]}")
    return r.stdout


def quelle_stand(pfad):
    if pfad == "quelle":
        WP.quelle_stand()   # startet ai.hermes.ordi-quelle, falls er nicht antwortet (ordi_quelle_sicher)
    with urllib.request.urlopen(f"http://127.0.0.1:{PORTS[pfad]}/{pfad}/kaiscribe/quelle-stand", timeout=600) as r:
        s = json.loads(r.read().decode("utf-8"))
    if not s.get("commit"):
        raise RuntimeError(f"Quell-Dienst ohne KaiScribe-Stand: {s}")
    return s


def auftrag(commit, zip_sha, tag, pfad, ui=True):
    v = datei(VORLAGE, commit).decode("utf-8")
    skript_sha = hashlib.sha256(datei(SKRIPT, commit)).hexdigest()
    return (v.replace("{COMMIT}", commit).replace("{KURZ}", commit[:8]).replace("{SHA_ZIP}", zip_sha)
            .replace("{SHA_SKRIPT}", skript_sha).replace("{TAG}", tag).replace("{PFAD}", pfad)
            .replace("{UI}", "" if ui else " --ohne-ui-test"))


def auswerten(out, commit, tag):
    """Antwort des Ordi-Hermes → (ergebnis ok|fehler|belegt|unklar, sha256, uitest, grund)."""
    t = list(KSBAU_RX.finditer(out or ""))
    if not t:
        return "unklar", "-", "-", "keine KSBAU=-Zeile in der Antwort"
    erg, c, tg, sha, ui, _d, grund = t[-1].groups()
    grund = (grund or "").strip()[:300]
    if erg == "ok" and (not commit.startswith(c[:7] or "x") or tg != tag):
        return "fehler", sha, ui, f"Büro-PC hat {c[:8]}/{tg} statt {commit[:8]}/{tag} gebaut"
    if erg == "ok" and not re.fullmatch(r"[0-9a-f]{64}", sha):
        return "fehler", sha, ui, "keine Prüfsumme der EXE"
    return erg, sha, ui, grund


def release(commit, tag, sha):
    """GitHub-Release aus der Ablage. → (ok, text)"""
    ordner = os.path.join(ABLAGE, commit, tag)
    exe = os.path.join(ordner, "rakscribe26.exe")
    if not os.path.exists(exe):
        return False, "EXE nicht in der Ablage (Abgabe vom Büro-PC fehlt)"
    if hashlib.sha256(open(exe, "rb").read()).hexdigest() != sha:
        return False, "EXE in der Ablage hat eine andere Prüfsumme als gemeldet"
    notiz = os.path.join(ordner, "report.md")
    text = (open(notiz, encoding="utf-8").read() if os.path.exists(notiz) else "Kein UI-Bericht abgegeben.")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(f"Gebaut und getestet am Büro-PC (kaiscribe_bau.py), Commit {commit[:8]}, SHA256 {sha}.\n\n"
                f"<!-- windows-ui-test -->\n{text}\n")
        notes = f.name
    a = ["release", "create", tag, exe, "-R", REPO, "--target", commit, "--title", f"KaiScribe {tag}",
         "--notes-file", notes]
    if tag.startswith("test-"):
        a.append("--prerelease")
    r = gh(*a, timeout=1200)
    os.unlink(notes)
    if r.returncode:
        return False, "gh release create: " + (r.stderr or r.stdout).strip()[:200]
    d = gh("api", f"repos/{REPO}/releases/tags/{tag}", "--jq", '.assets[]|select(.name=="rakscribe26.exe")|.digest')
    if d.stdout.strip() != "sha256:" + sha:
        return False, f"Release-Digest {d.stdout.strip() or '?'} ≠ gebaute EXE"
    return True, f"Release {tag} angelegt"


def bauen(tag=None, mit_release_tag=False, pfad="quelle", trocken=False, ohne_release=False, aus_job=None, ui=True):
    if not ui:
        ohne_release = True   # ohne UI-Test nie ein Release
    if not WP.zeitfenster():
        return {"ergebnis": "nicht_gelaufen", "grund": "außerhalb des Zeitfensters (20:10–06:30 bzw. Wochenende)"}
    os.makedirs(WORK, exist_ok=True)
    fh = open(os.path.join(WORK, ".lock"), "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        wfh = open(os.path.join(WP.WORK, ".lock"), "w") if os.path.isdir(WP.WORK) else None
        if wfh:
            fcntl.flock(wfh, fcntl.LOCK_EX | fcntl.LOCK_NB)   # nie neben einer Windows-Prüfung (ein Peer-Lauf)
    except OSError:
        return {"ergebnis": "nicht_gelaufen", "grund": "ein Bau oder eine Windows-Prüfung läuft schon"}
    try:
        b = WP.belegt(aus_job)
        if b:
            return {"ergebnis": "nicht_gelaufen", "grund": b}
        st = quelle_stand(pfad)
        commit = st["commit"]
        if mit_release_tag:
            tag = datei("VERSION", commit).decode().strip()
            if gh("api", f"repos/{REPO}/releases/tags/{tag}").returncode == 0:
                return {"ergebnis": "nicht_gelaufen", "grund": f"Release {tag} gibt es schon (VERSION erst heben)"}
        tag = tag or "test-" + dt.datetime.now().strftime("%y%m%d%H%M")
        text = auftrag(commit, st["sha256"], tag, pfad, ui)
        if trocken:
            print(text)
            return {"ergebnis": "nicht_gelaufen", "grund": "trocken", "commit": commit}
        PP.commit_status("RaKScribe26", commit, "pending", ART, f"läuft: EXE-Bau + UI-Test am Büro-PC ({tag})")
        t0, d = dt.datetime.now(), {}
        try:
            d = WP.peer(text, f"ksbau-{commit[:8]}-{tag}-{t0:%m%d%H%M}")
            out, status = d.get("output") or "", d.get("status")
        except Exception as ex:  # noqa: BLE001
            out, status = "", f"fehler: {ex}"
        os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
        logpfad = os.path.join(WORK, "logs", f"{commit[:8]}-{tag}-{t0:%Y%m%d-%H%M%S}.txt")
        with open(logpfad, "w") as f:
            f.write(f"status={status} run={d.get('run', '-')}\n{out}")
        erg, sha, ui, grund = auswerten(out, commit, tag)
        if status != "completed" or erg in ("unklar", "belegt"):
            PP.commit_status("RaKScribe26", commit, "error", ART, f"nicht gelaufen: {(grund or str(status))[:100]}")
            return {"ergebnis": "nicht_gelaufen", "grund": f"{status}: {grund}", "commit": commit, "log": logpfad}
        rel = ""
        if erg == "ok" and not ohne_release:
            ok, rel = release(commit, tag, sha)
            if not ok:
                erg, grund = "fehler", rel
        e = {"zeit": PP.jetzt(), "repo": "RaKScribe26", "commit": commit, "art": ART, "ergebnis": erg,
             "dauer_s": round((dt.datetime.now() - t0).total_seconds()), "tag": tag, "sha256": sha, "uitest": ui,
             "grund": grund or rel, "quelle": f"job:{aus_job}" if aus_job else "hand", "log": logpfad,
             "rechner": "CASWS14 (Büro-PC)"}
        ok, _ = PP.commit_status("RaKScribe26", commit, "success" if erg == "ok" else "failure", ART,
                                 (f"grün: EXE {tag} gebaut, UI-Test {ui} am Büro-PC" if erg == "ok"
                                  else f"rot: {grund}")[:139])
        e["status_gesetzt"] = ok
        PP.eintragen(e)
        return e
    finally:
        fh.close()


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    wert = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    e = bauen(tag=wert("--tag"), mit_release_tag="--release" in argv, pfad=wert("--pfad") or "quelle",
              trocken="--trocken" in argv, ohne_release="--ohne-release" in argv, aus_job=wert("--aus-job"),
              ui="--ohne-ui-test" not in argv)
    if e["ergebnis"] == "nicht_gelaufen":
        print(f"nicht gelaufen: {e['grund']}")
        return 3
    print(f"{e['ergebnis']}: {e['tag']} SHA256 {e['sha256'][:12]} UI-Test {e['uitest']} – {e['grund']}\n  Log: {e['log']}")
    return 0 if e["ergebnis"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
