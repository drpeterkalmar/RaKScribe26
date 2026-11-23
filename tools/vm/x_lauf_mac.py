#!/usr/bin/env python3
"""Am Mac: ein Python-Skript aus diesem Repo auf die Automaten-VM laden und als rakauto mit X: laufen lassen (nur lesen).
(kaiscribe-georg-2011-kontrolle, 23.11.2026; Weg wie ris-mods automaten_vm/mac/abholer_vm.py alskonto)

  python3 tools/vm/x_lauf_mac.py tools/vm/georg_kontrolle_pruefen.py --tag 20261123

Lädt nach C:\\RaK\\einrichtung\\frogdiag\\, schreibt eine kleine Hülle (laufwerke.cmd verbindet X: im rakauto-Profil) und
startet sie über vm_als_konto.ps1 (Kennwort aus Vaultwarden per stdin). Ausgabe des Skripts unverändert nach stdout.
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.expanduser('~/dev/ris-mods/automaten_vm/mac'))
sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
import abholer_vm as AV  # noqa: E402

D = 'C:\\RaK\\einrichtung\\frogdiag'


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    skript, args = sys.argv[1], sys.argv[2:]
    if any(not re.fullmatch(r'[\w.:,=+\\-]+', x) for x in args):
        sys.exit('Argumente mit unerlaubten Zeichen')
    with tempfile.TemporaryDirectory() as t:
        q = AV.quelle(t)
        ziel = D + '\\' + os.path.basename(skript)
        AV.hoch(q, os.path.abspath(skript), ziel)
        teile = ", ".join("'%s'" % x for x in args)
        huelle = ("$ErrorActionPreference = 'Continue'\n[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
                  "$env:PYTHONIOENCODING = 'utf-8'\n"
                  "$a = @('/c', 'C:\\RaK\\laufwerke.cmd', 'C:\\Windows\\py.exe', '-3.12', '-X', 'utf8', '%s'%s)\n"
                  "& cmd.exe @a 2>&1 | ForEach-Object { \"$_\" }\n'PY_RC=' + $LASTEXITCODE\n"
                  % (ziel, (', ' + teile) if teile else ''))
        p = os.path.join(t, 'x_lauf.ps1')
        with open(p, 'w', encoding='utf-8-sig') as f:
            f.write(huelle)
        AV.hoch(q, p, D + '\\x_lauf.ps1')
        rc, aus = AV.alskonto(q, D + '\\x_lauf.ps1', int(os.environ.get('VM_FRIST', '300')))
        print(aus)
        sys.exit(0 if 'PY_RC=0' in aus else 1)


if __name__ == '__main__':
    main()
