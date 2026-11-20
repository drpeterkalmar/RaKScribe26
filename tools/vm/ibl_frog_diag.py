# Nur lesen (X:). Aufruf: tools/vm/x_lauf_hetzner.py C:\RaK\einrichtung\frogdiag\ibl_frog_diag.py 20261120
"""Nur lesen (X:). Je Lauf heute mit FROG: Kategorien aus Lauf-Datei, Abholer-Ablage und Brücken-Protokoll. Keine Nr, keine Namen, kein Befundtext."""
import glob, json, os, re, sys
von = sys.argv[1] if len(sys.argv) > 1 else "20261120"
L = r"X:\RaKScribe\Daten\laeufe"; A = r"X:\IBL-Vorbefunde"; P = r"X:\RaKScribe\Daten\protokolle"
SCHLUSS = "Weitere Winkelmessungen"
schl_gezeigt = False
for p in sorted(glob.glob(os.path.join(L, "*.json"))):
    m = re.match(r"^(\d+)_(\d{8})-(\d{4})", os.path.basename(p))
    if not m or m.group(2) < von:
        continue
    d = json.load(open(p, encoding="utf-8-sig"))
    mods = [str(x) for x in d.get("ibl_module") or []]
    if not any(x.upper().startswith("FROG") for x in mods):
        continue
    nr = m.group(1)
    if not schl_gezeigt:
        print("LAUF_SCHLUESSEL", sorted(d.keys())); schl_gezeigt = True
    rep = str(d.get("ergebnis_vorschlag") or "")
    print(f"\nLAUF {m.group(2)}-{m.group(3)} rechner={d.get('rechner')} ks={d.get('kaiscribe')} module={'+'.join(x.replace(' ','_') for x in mods)} "
          f"ibl_baustein={d.get('ibl_baustein')} ibl_zeilen={d.get('ibl_zeilen')} vorlagen={d.get('vorlagen')} "
          f"vorschlag_len={len(rep)} schluss_im_vorschlag={SCHLUSS in rep} regelrecht_fussskelett={'Regelrechte Darstellung des Fußskeletts' in rep}")
    for k in ("ibl_hinweise", "hinweise", "ibl_text_ablage", "ibl"):
        if k in d:
            v = d[k]
            print(f"  lauf.{k}: typ={type(v).__name__} n={len(v) if hasattr(v,'__len__') else v}",
                  [re.sub(r"\d{6,}", "<nr>", str(h))[:140] for h in (v if isinstance(v, list) else [])][:6])
    for f in sorted(glob.glob(os.path.join(A, nr + "*_frog.json"))):
        try:
            a = json.load(open(f, encoding="utf-8-sig"))
        except Exception as e:
            print("  ABLAGE kaputt", type(e).__name__); continue
        vb = a.get("vorbefund") or {}
        ep = vb.get("ergebnis_punkte") or []
        bt = vb.get("befundtext")
        mt = os.path.getmtime(f)
        import datetime
        print(f"  ABLAGE ziffer={os.path.basename(f)[len(nr):].split('_')[0]} format={a.get('format')} version={a.get('version')} "
              f"aktualisiert={a.get('aktualisiert')} mtime={datetime.datetime.fromtimestamp(mt):%H:%M} "
              f"ergebnis_punkte={len(ep)} davon_patho={sum(1 for e in ep if SCHLUSS not in e)} "
              f"befundtext={'ja:'+','.join(sorted((bt.get('frog') or {}).keys())) if isinstance(bt, dict) and bt.get('frog') else ('leer' if bt is not None else 'fehlt')} "
              f"befundteil_zeilen={len(vb.get('befundteil') or [])} hinweise={len(vb.get('hinweise_fuer_befunder') or [])} "
              f"regeln={vb.get('angewandte_regeln')}")
        if ep:
            print("   ergebnis_punkte(ohne Schluss, nur Fachbegriffe):", [e for e in ep if SCHLUSS not in e][:4])
    for b in glob.glob(os.path.join(P, "bruecke_*.log")):
        pc = os.path.basename(b)[8:-4]
        z = [l.rstrip() for l in open(b, encoding="utf-8", errors="replace") if nr in l]
        if z:
            print(f"  BRUECKE {pc}: {len(z)} Zeilen")
            for l in z[:12]:
                print("   ", re.sub(r"\d{9,}", "<nr>", l)[:200])
