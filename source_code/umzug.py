"""Namens-Umzug RaKScribe → KaiScribe (kaiscribe-umzug-n1-exe, Peter 20.11.2026: „bitte nenne mal alle rakscribe sachen in
kaiscribe um“) — ohne Tk/Windows importierbar und testbar (tests/offline/test_umzug.py).

Übergang, damit kein Befund-PC bricht (die EXE liegt gemeinsam auf X:, die Brücken je PC werden erst nach und nach
umgestellt):
  Benutzer-Daten  %APPDATA%\\KaiScribe. Fehlt der Ordner und gibt es %APPDATA%\\RaKScribe, wird er beim Start EINMAL
                  kopiert (nie verschoben, nie gelöscht – der alte Ordner bleibt für den Rückweg auf eine alte EXE).
                  Der Schlüssel heißt in der Kopie kaiscribe-praxis-key.json. Danach liest die EXE nur noch den neuen Ordner.
  X:-Pfade        X:\\KaiScribe\\… vor X:\\RaKScribe\\… (Rückfall, solange der neue Ordner auf X: fehlt).
  Prozess         KaiScribe.exe; rakscribe26.exe (Übergangs-Asset, alte Kopien) zählt überall mit.
Bewusst NICHT umbenannt (Protokoll mit der Brücke bzw. gemeinsame Sperre alter und neuer EXE): %LOCALAPPDATA%\\RaKScribe
(CAS-Auftrag), Mutex Local\\RaKScribe26-Einzelinstanz, Umgebungsvariablen RAKSCRIBE_*.
"""
import os
import re
import shutil

NAME = "KaiScribe"
ALT = "RaKScribe"
# Prozessnamen der EXE (WQL-LIKE-Muster, Groß/klein egal). NICHT einfach „KaiScribe%“: eine künftige „KaiScribe-Bruecke.exe“
# (ris-mods) darf nicht als laufende KaiScribe gelten. Kopien beim Herunterladen heißen „KaiScribe (1).exe“.
PROZESS_MUSTER = ("KaiScribe.exe", "KaiScribe (%", "rakscribe26%")


def ist_kaiscribe_prozess(name):
    """True für KaiScribe.exe, rakscribe26.exe und Kopien wie „rakscribe26 (1).exe“/„KaiScribe (1).exe“."""
    n = (name or "").strip().lower()
    return n in ("kaiscribe.exe", "kaiscribe") or n.startswith(("kaiscribe (", "rakscribe26"))


def benutzer_ordner(environ=None):
    """(neu, alt): %APPDATA%\\KaiScribe und %APPDATA%\\RaKScribe."""
    env = os.environ if environ is None else environ
    basis = env.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(basis, NAME), os.path.join(basis, ALT)


def benutzer_daten_uebernehmen(environ=None, log=None, schluessel_alt="rakscribe-praxis-key.json",
                               schluessel_neu="kaiscribe-praxis-key.json"):
    """Einmalig beim Start: %APPDATA%\\RaKScribe → %APPDATA%\\KaiScribe kopieren, wenn neu fehlt und alt da ist.
    Erst in einen Zwischenordner, dann umbenennen — ein abgebrochener Start hinterlässt keinen halben neuen Ordner.
    Rückgabe: Text fürs Protokoll oder None (nichts zu tun)."""
    log = log or (lambda *a: None)
    neu, alt = benutzer_ordner(environ)
    if os.path.exists(neu) or not os.path.isdir(alt):
        return None
    tmp = f"{neu}.umzug-{os.getpid()}"
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(alt, tmp, ignore=shutil.ignore_patterns(schluessel_alt, "*.tmp"))
        if os.path.isfile(os.path.join(alt, schluessel_alt)):
            shutil.copy2(os.path.join(alt, schluessel_alt), os.path.join(tmp, schluessel_neu))
        os.replace(tmp, neu)
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        text = f"[UMZUG] {alt} nicht nach {neu} kopiert ({type(e).__name__}: {e}) – KaiScribe liest weiter den alten Ordner"
        log(text)
        return text
    text = f"[UMZUG] Benutzer-Daten kopiert: {alt} → {neu} (alter Ordner bleibt unverändert)"
    log(text)
    return text


def benutzer_ordner_aktiv(environ=None):
    """Ordner, den die EXE benutzt: neu — außer die Kopie ist gescheitert (neu fehlt, alt da), dann alt."""
    neu, alt = benutzer_ordner(environ)
    return alt if not os.path.exists(neu) and os.path.isdir(alt) else neu


_X_PFAD = re.compile(r"^([A-Za-z]:[\\/])(" + "|".join((ALT, NAME)) + r")(?=[\\/]|$)(.*)$", re.I)


def x_pfad(pfad, ist_ordner=os.path.isdir):
    """X:\\RaKScribe\\… bzw. X:\\KaiScribe\\… → X:\\KaiScribe\\…, wenn es den neuen Ordner auf dem Laufwerk gibt,
    sonst X:\\RaKScribe\\…, wenn es den alten gibt; sonst unverändert (Laufwerk fehlt → der Aufrufer schreibt nichts).
    Andere Pfade bleiben, wie sie sind."""
    m = _X_PFAD.match(str(pfad or ""))
    if not m:
        return pfad
    lw, _name, rest = m.groups()
    for name in (NAME, ALT):
        if ist_ordner(lw + name):
            return lw + name + rest
    return pfad

