#!/usr/bin/env python3
"""chirp_vm.py (chirp-fachwortliste-n1, 24.11.2026) – am MAC: ein Python-Skript als rakauto auf der Automaten-VM (X:/M:).

  python3 tools/mac/chirp_vm.py <skript.py> [weitere Dateien …] [-- args …]

Lädt die Dateien nach C:\\RaK\\chirp_fw\\prog (rakauto darf lesen), startet das erste als rakauto über
ris-mods automaten_vm/vm_als_konto.ps1 (Kennwort aus Vaultwarden, nur stdin) und gibt seine Ausgabe zurück.
DATENSCHUTZ: Die VM-Skripte geben nur Zähler bzw. die bereits streng gefilterte Fachwortliste aus; Ziffernfolgen
≥ 5 werden hier zusätzlich geschwärzt. Rohlisten, Befundtexte und Audio bleiben auf der VM.
"""
import os
import re
import sys
import tempfile

RIS = os.path.expanduser('~/dev/ris-mods')
sys.path.insert(0, os.path.join(RIS, 'automaten_vm', 'mac'))
import kaiscribe_lernen_vm as kl  # noqa: E402  (hoch, ps, kennwort)

B = 'C:\\RaK\\chirp_fw'
P = B + '\\prog'


def main():
    argv = sys.argv[1:]
    args = []
    if '--' in argv:
        i = argv.index('--')
        argv, args = argv[:i], argv[i + 1:]
    frist = int(os.environ.get('FRIST', '1500'))
    q = RIS
    with tempfile.TemporaryDirectory() as t:
        for d in argv:
            kl.hoch(q, d, P + '\\' + os.path.basename(d))
        # Leserecht für rakauto auf den Programmordner, Datenordner = %LOCALAPPDATA%\chirp_fw von rakauto
        acl = os.path.join(t, 'acl.ps1')
        with open(acl, 'w', encoding='utf-8-sig') as f:
            f.write("icacls '%s' /grant 'rakauto:(OI)(CI)M' | Out-Null; 'ACL ok'\n" % B)
        print(kl.ps(q, acl, '', '', 120)[1][-200:])
        teile = "".join(", '%s'" % a.replace("'", "''") for a in args)
        huelle = ("$ErrorActionPreference = 'Continue'\n[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
                  "$env:PYTHONIOENCODING = 'utf-8'\n"
                  "$a = @('/c', 'C:\\RaK\\laufwerke.cmd', 'C:\\Windows\\py.exe', '-3.12', '-u', '-X', 'utf8', "
                  "'%s\\%s'%s)\n"
                  "& cmd.exe @a 2>&1 | ForEach-Object { \"$_\" }\n'PY_RC=' + $LASTEXITCODE\n"
                  % (P, os.path.basename(argv[0]), teile))
        p = os.path.join(t, 'cfw_lauf.ps1')
        with open(p, 'w', encoding='utf-8-sig') as f:
            f.write(huelle)
        kl.hoch(q, p, B + '\\cfw_lauf.ps1')
        a = "-Skript '%s' -Frist %d" % (B + '\\cfw_lauf.ps1', frist)
        rc, aus = kl.ps(q, os.path.join(q, 'automaten_vm', 'vm_als_konto.ps1'), a, kl.kennwort() + '\n', frist + 120)
    print('\n'.join(re.sub(r'\d{5,}', '<zahl>', z) for z in aus.splitlines() if z.strip())[-30000:])
    sys.exit(0 if 'PY_RC=0' in aus else 1)


if __name__ == '__main__':
    main()
