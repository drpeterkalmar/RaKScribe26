#!/usr/bin/env python3
"""Vom Hetzner-Server: ein Python-Skript auf der Automaten-VM als rakauto mit X: laufen lassen (nur lesen).
(kaiscribe-frog-einsetzen-n1-kontrolle, 20.11.2026)

  python3 tools/vm/x_lauf_hetzner.py <skript-auf-der-VM> [argumente …]
  z. B. … 'C:\\RaK\\einrichtung\\frogdiag\\ibl_laeufe_pruefen.py' --von 20261120

Warum so: Per SSH-Schlüssel (Host dexa-rakauto) fehlt rakauto die gespeicherte Anmeldung für \\\\casmed\\casmed$
(laufwerke.cmd verbindet X: dann nicht), und der Hetzner-Tresor hat das rakauto-Kennwort für abholer_vm.alskonto
nicht. Daher: Laufwerks-Anmeldung „Laufwerk X: CASMED-Konto dexa (Rottmann)“ aus Vaultwarden (ohne bw sync – der Server
am Mac ist zeitweise nicht erreichbar, dann hängt sync), per stdin an x_lauf_huelle.ps1, die X: nur für diese Sitzung
verbindet (New-PSDrive; New-SmbMapping ist über SSH gesperrt) und danach trennt. Kennwort nie als Argument.
Vorher hochladen: scp x_lauf_huelle.ps1 + Skript nach dexa-rakauto:C:/RaK/einrichtung/frogdiag/.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
import vw_get  # noqa: E402

NAME = 'Laufwerk X: CASMED-Konto dexa (Rottmann)'
HUELLE = r'C:\RaK\einrichtung\frogdiag\x_lauf_huelle.ps1'


def anmeldung():
    env = vw_get._env()
    env['BW_PASSWORD'] = open(vw_get.MASTER_DATEI).read().strip()
    s = subprocess.run([vw_get._bw_bin(), 'unlock', '--passwordenv', 'BW_PASSWORD', '--raw'], env=env,
                       capture_output=True, text=True, timeout=60).stdout.strip()
    env.pop('BW_PASSWORD')
    env['BW_SESSION'] = s
    try:
        o = subprocess.run([vw_get._bw_bin(), 'list', 'items'], env=env, capture_output=True, text=True, timeout=60).stdout
    finally:
        try:  # nur Aufräumen; hängt, wenn der Tresor-Server am Mac nicht erreichbar ist
            subprocess.run([vw_get._bw_bin(), 'lock'], env=env, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            pass
    lg = next(it['login'] for it in json.loads(o[o.find('['):]) if it.get('name') == NAME)
    return lg['username'], lg['password']


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    skript, args = sys.argv[1], ' '.join(sys.argv[2:])
    if "'" in skript + args or '"' in skript + args:
        sys.exit('keine Anführungszeichen in Skript/Argumenten')
    u, p = anmeldung()
    cmd = ("powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"$env:KF_SKRIPT='%s'; "
           "$env:KF_ARGS='%s'; & %s\"" % (skript, args, HUELLE))
    r = subprocess.run(['ssh', 'dexa-rakauto', cmd], input=u + '\n' + p + '\n', capture_output=True, text=True,
                       timeout=int(os.environ.get('VM_TIMEOUT', '400')))
    sys.stdout.write(r.stdout)
    err = '\n'.join(z for z in r.stderr.splitlines() if 'CLIXML' not in z and '<Objs' not in z)
    sys.stderr.write(err[-1500:])
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
