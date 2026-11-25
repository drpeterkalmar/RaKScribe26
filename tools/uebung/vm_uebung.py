#!/usr/bin/env python3
r"""Am MAC: KaiScribe-Übungsdienst auf der Automaten-VM einspielen und bedienen (kaiscribe-uebung-n1, 25.11.2026).

  python3 tools/uebung/vm_uebung.py lage                     nur lesen (Port, Aufgabe, laufwerke.cmd, Muster)
  python3 tools/uebung/vm_uebung.py einspielen [--konten]    Web-App bauen (Basis /), Paket prog+web hoch, Aufgabe +
                                                             tailscale serve :8555; --konten: neue Kennwörter kp/rg
                                                             erzeugen → Vaultwarden, nur Hashes auf die VM
  python3 tools/uebung/vm_uebung.py spiegeln <JJJJMMTT> [--erkunden] [--max N]   als rakauto (X:, CAS nur SELECT)
  python3 tools/uebung/vm_uebung.py beleg | start | aus      Zustand / Neustart / Rückweg (Aufgabe aus, serve off)

VM-Zugang wie ris-mods (vmssh.py als rakadmin, Einmal-Aufgabe als rakauto mit Kennwort aus Vaultwarden per stdin).
Ausgabe: nur Zustände/Zähler – Patientendaten bleiben auf der VM.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HIER))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.expanduser('~/dev/ris-mods/automaten_vm/mac'))
sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
import abholer_vm as AV  # noqa: E402
import uebung_kern as K  # noqa: E402

E = 'C:\\RaK\\einrichtung\\uebung'
B = 'C:\\RaK\\kaiscribe_uebung'
PROG = ['uebung_kern.py', 'uebung_dienst.py', 'spiegel.py']
URL = 'https://dexa.taild969f0.ts.net:8555/'
VW_NAME = 'KaiScribe-Übung {}'
VW_NACHBAR = 'DEXA-VM rakauto (Automaten-Konto)'


def ps(q, schritt, frist=300):
    rc, aus = AV.ps(q, os.path.join(HIER, 'uebung_vm.ps1'), '-Schritt ' + schritt, '', frist)
    print(re.sub(r'\b\d{9,}\b', '<nr>', aus)[-4000:])
    return rc


def web_bauen(ziel):
    w = os.path.join(REPO, 'web_app')
    env = dict(os.environ)
    r = subprocess.run(['npm', 'run', 'build', '--', '--base=/', '--outDir', ziel, '--emptyOutDir'], cwd=w, env=env,
                       capture_output=True, text=True, timeout=600)
    if r.returncode or not os.path.isfile(os.path.join(ziel, 'index.html')):
        raise SystemExit('UEBUNG_VM FEHLER Web-Bau ' + (r.stdout + r.stderr)[-800:])
    print('WEB gebaut', sum(len(f) for _d, _s, f in os.walk(ziel)), 'Dateien')


def paket(t):
    web = os.path.join(t, 'web')
    web_bauen(web)
    z = os.path.join(t, 'paket.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for n in PROG:
            zf.write(os.path.join(HIER, n), 'prog/' + n)
        zf.write(os.path.join(REPO, 'source_code', 'ki_maske.py'), 'prog/ki_maske.py')
        for d, _s, fs in os.walk(web):
            for f in fs:
                p = os.path.join(d, f)
                zf.write(p, 'web/' + os.path.relpath(p, web).replace(os.sep, '/'))
    return z


def kennwort_neu():
    abc = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'      # SMS-tauglich, ohne 0/O/1/l/I
    return '-'.join(''.join(secrets.choice(abc) for _ in range(5)) for _ in range(4))


def konten_anlegen(t):
    """Kennwörter kp/rg erzeugen, in Vaultwarden (Org/Sammlung wie der rakauto-Eintrag) ablegen, Hash-Datei zurück."""
    import vw_get
    env = vw_get._session()
    hashes = {}
    try:
        items = vw_get._items(env)
        nachbar = next((i for i in items if i.get('name') == VW_NACHBAR), None)
        for k in K.KUERZEL:
            name = VW_NAME.format(k)
            alt = next((i for i in items if i.get('name') == name), None)
            pw = kennwort_neu()
            item = {"type": 1, "name": name, "notes": (
                f"KaiScribe-Übungsmodus (Web), Anmeldung als „{k}“. Link {URL} (nur Tailnet). Angelegt vom Job kaiscribe-uebung-n1 "
                "25.11.2026. Nur für " + ("Peter" if k == 'kp' else "Georg (Weitergabe per Praxis-SMS/Mail an ihn)") + "."),
                "login": {"username": k, "password": pw, "uris": [{"match": None, "uri": URL}]},
                "organizationId": (nachbar or {}).get('organizationId'), "collectionIds": (nachbar or {}).get('collectionIds') or [],
                "favorite": False, "fields": [], "reprompt": 0}
            enc = subprocess.run([vw_get._bw_bin(), 'encode'], input=json.dumps(item), capture_output=True, text=True,
                                 env=env, timeout=60).stdout.strip()
            if alt:
                r = vw_get._bw(['edit', 'item', alt['id'], enc], env)
            else:
                r = vw_get._bw(['create', 'item', enc], env)
            if r.returncode:
                raise SystemExit('UEBUNG_VM FEHLER Vaultwarden ' + name)
            hashes[k] = K.kennwort_hash(pw)
            pw = None
            print('VAULTWARDEN', name, 'geändert' if alt else 'angelegt')
        vw_get._bw(['sync'], env)
    finally:
        vw_get._lock(env)
    p = os.path.join(t, 'konten.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(hashes, f)
    return p


def spiegeln(t, q, tag, extra):
    if not K.TAG_RE.match(tag) or any(not re.fullmatch(r'--erkunden|--max|\d{1,3}', x) for x in extra):
        raise SystemExit('UEBUNG_VM FEHLER Argumente')
    teile = ", ".join("'%s'" % x for x in ['--tag', tag, '--basis', B] + extra)
    huelle = ("$ErrorActionPreference = 'Continue'\n[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
              "$env:PYTHONIOENCODING = 'utf-8'\n"
              "$a = @('/c', 'C:\\RaK\\laufwerke.cmd', 'C:\\Windows\\py.exe', '-3.12', '-X', 'utf8', '%s\\prog\\spiegel.py', %s)\n"
              "& cmd.exe @a 2>&1 | ForEach-Object { \"$_\" }\n'PY_RC=' + $LASTEXITCODE\n" % (B, teile))
    p = os.path.join(t, 'spiegel_lauf.ps1')
    with open(p, 'w', encoding='utf-8-sig') as f:
        f.write(huelle)
    AV.hoch(q, p, E + '\\spiegel_lauf.ps1')
    rc, aus = AV.alskonto(q, E + '\\spiegel_lauf.ps1', int(os.environ.get('VM_FRIST', '1500')))
    zeilen = [z for z in aus.splitlines() if z.lstrip().startswith(('SPIEGEL', 'PY_RC', 'ALSKONTO', 'Traceback', '  File'))
              or re.match(r'^\w*Error', z)]
    print('\n'.join(re.sub(r'\b\d{9,}\b', '<nr>', z) for z in zeilen)[-4000:])
    return 'PY_RC=0' in aus


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('lage', 'einspielen', 'spiegeln', 'beleg', 'start', 'aus'):
        raise SystemExit(__doc__)
    with tempfile.TemporaryDirectory() as t:
        q = AV.quelle(t)
        if a[0] in ('lage', 'beleg', 'start', 'aus'):
            sys.exit(ps(q, a[0]))
        if a[0] == 'spiegeln':
            sys.exit(0 if spiegeln(t, q, a[1], a[2:]) else 1)
        z = paket(t)
        AV.hoch(q, z, E + '\\paket.zip')
        if '--konten' in a:
            k = konten_anlegen(t)
            AV.hoch(q, k, E + '\\konten.json')
            os.remove(k)
        sys.exit(ps(q, 'einrichten', 600))


if __name__ == '__main__':
    main()
