#!/usr/bin/env python3
"""tools/speechmike_probe.py — Hardware-Prüfung SpeechMike (v3.8.0, Peter 11.10., Nachtrag 1/3). EIGENSTÄNDIG: braucht nur
Python 3 + hidapi, nichts aus RaKScribe.

    pip install hidapi==0.15.0
    python speechmike_probe.py                 # 60 s Tasten mitschreiben, danach LEDs durchschalten
    python speechmike_probe.py --sekunden 120  --ohne-led  --ohne-abfrage

Vorher RaKScribe (EXE und Web-App-Tab) schließen — sonst reagiert RaKScribe auf die Tasten. Philips SpeechControl darf
laufen (das Skript öffnet das Gerät GETEILT wie RaKScribe; so sieht man auch, ob beides parallel geht).

Was es tut:
  1. listet alle Philips-/Nuance-HID-Schnittstellen (Hersteller 0911/0554: VID:PID, Usage-Page, Usage, Pfad)
  2. öffnet die Hersteller-Schnittstelle (Usage-Page 0xFFA0) geteilt, fragt Ereignis-Modus und Modell ab (wie das
     Google/Philips-SDK dictation_support; nur Lesen, es wird NICHTS am Gerät umgestellt)
  3. schreibt <Sekunden> lang jede Taste mit: „Taste RECORD gedrückt (raw 80 00 …)“ / „losgelassen“ — bitte nacheinander
     Record, Record, INS (3× hintereinander!), EOL, Stop/Schieber, F1, F2, Play, Spulen, INSTR drücken
  4. schaltet die Record-LED durch: rot, rot blinkend, grün, gelb blinkend (rot+grün), aus — bitte notieren, was zu sehen war
Alles steht zusätzlich in speechmike_probe_<Datum>.log neben dem Skript (für Hermes/Peter).
Exit: 0 ok, 2 kein Gerät, 3 Öffnen fehlgeschlagen, 4 hidapi fehlt.
"""
import argparse, os, platform, sys, threading, time

VENDOREN = {0x0911: "Philips", 0x0554: "Nuance"}
PRODUKTE = {0x0C1C: "SpeechMike (verkabelt, HID-Modus)", 0x0C1D: "SpeechMike Premium Air", 0x0C1E: "SpeechOne/Ambient",
            0x0FA0: "SpeechMike im Browser-Modus", 0x0064: "PowerMic 4", 0x1001: "PowerMic III",
            0x1844: "Fußschalter ACC2310/2320", 0x091A: "Fußschalter ACC2330"}
USAGE_PAGE = 0xFFA0
TASTEN = (("F1", 1 << 1), ("F2", 1 << 2), ("F3", 1 << 3), ("F4", 1 << 4), ("COMMAND", 1 << 5), ("RECORD", 1 << 8),
          ("STOP", 1 << 9), ("PLAY", 1 << 10), ("FF", 1 << 11), ("REW", 1 << 12), ("EOL", 1 << 13), ("INS", 1 << 14),
          ("INSTR", 1 << 15))
MODI = {0: "HID (Standard für Philips-Software, RaKScribe braucht diesen)", 1: "Tastatur", 2: "Browser/Gamepad",
        3: "Windows-Spracherkennung", 4: "Dragon für Mac", 5: "Dragon für Windows"}
MODELLE = {3200: "LFH3200", 3210: "LFH3210 (Schieber)", 3220: "LFH3220 (Schieber)", 3300: "LFH3300", 3310: "LFH3310 (Schieber)",
           3500: "SpeechMike Premium LFH3500 (Druckknöpfe)", 3510: "SpeechMike Premium LFH3510 (Schiebeschalter)",
           3520: "SpeechMike Premium LFH3520 (Schiebeschalter, Philips-Belegung)", 3600: "LFH3600 (Druckknöpfe)",
           3610: "LFH3610 (Schiebeschalter)", 3700: "SpeechMike Premium Touch SMP3700 (Druckknöpfe)",
           3710: "SMP3710 (Schiebeschalter)", 3720: "SMP3720 (Schiebeschalter, Philips-Belegung)", 3800: "SMP3800",
           3810: "SMP3810 (Schiebeschalter)", 4000: "SpeechMike Premium Air SMP4000", 4010: "SMP4010 (Schiebeschalter)",
           5000: "SpeechMike Ambient PSM5000", 6001: "SpeechOne PSM6000"}
LED = [("Record-LED ROT (Aufnahme)", 0x0C, 3), ("Record-LED ROT LANGSAM BLINKEND (Pause)", 0x04, 4),
       ("Record-LED GRÜN (Befund bereit)", 0x03, 3), ("Record-LED GELB/ROT+GRÜN SCHNELL BLINKEND (Befund wird erstellt)", 0x0A, 4),
       ("alle LEDs AUS", 0x00, 1)]

_log = None
T0 = time.time()


def out(text=""):
    print(text, flush=True)
    if _log:
        _log.write(text + "\n")
        _log.flush()


def hx(daten):
    return " ".join(f"{b:02x}" for b in daten)


def warten_auf_antwort(dev, cmd, sek=1.5):
    ende = time.time() + sek
    while time.time() < ende:
        d = dev.read(64, 100)
        if d and d[0] == cmd:
            return d
        if d:
            out(f"    (während der Abfrage: Bericht {hx(d)})")
    return None


def befehl(dev, cmd):
    dev.write([0x00, cmd, 0, 0, 0, 0, 0, 0, 0, 0])
    return warten_auf_antwort(dev, cmd)


def abfragen(dev):
    try:
        r = befehl(dev, 0x8D)
        out(f"  Ereignis-Modus: {MODI.get(r[8], r[8]) if r and len(r) > 8 else 'keine Antwort'}"
            + (f"   (raw {hx(r)})" if r else ""))
        code = None
        r = befehl(dev, 0x83)
        if r and len(r) > 8:
            if r[8] & 0x80:
                r2 = befehl(dev, 0x8B)
                if r2 and len(r2) > 8 and r2[1]:
                    r3 = befehl(dev, 0x96)
                    code = (r3[7] << 8 | r3[8]) if r3 and len(r3) > 8 else None
                elif r2 and len(r2) > 7:
                    code = max(r2[2] << 8 | r2[3], r2[4] << 8 | r2[5], r2[6] << 8 | r2[7])
            else:
                r2 = befehl(dev, 0x87)
                code = (r2[7] << 8 | r2[8]) if r2 and len(r2) > 8 else None
        out(f"  Modell: {MODELLE.get(code, 'unbekannt')} (Gerätecode {code})" if code else "  Modell: keine Antwort")
    except Exception as e:
        out(f"  Abfrage nicht möglich: {e}")


def mitlesen(dev, sekunden, nebenstellen):
    out(f"\n== {sekunden} s Tasten mitschreiben. Bitte nacheinander drücken: Record, Record, INS (3× hintereinander), EOL,")
    out("   Stop bzw. Schieber auf STOP, F1, F2, Play, Spulen vor/zurück, INSTR. Gerät auch einmal hinlegen/aufnehmen.")
    maske, ins_druecke, ende = 0, [], time.time() + sekunden
    halt = threading.Event()
    for name, d in nebenstellen:  # andere Schnittstellen (Browser-/Tastatur-Modus) roh mitlesen
        def lauf(name=name, d=d):
            while not halt.is_set():
                try:
                    x = d.read(64, 200)
                except Exception:
                    return
                if x:
                    out(f"  [{time.time() - T0:6.2f}s] Schnittstelle {name}: Bericht {hx(x)}")
        threading.Thread(target=lauf, daemon=True).start()
    while time.time() < ende:
        d = dev.read(64, 200)
        if not d:
            continue
        t = time.time() - T0
        if d[0] == 0x80 and len(d) >= 9:
            neu = d[7] | d[8] << 8
            for name, bit in TASTEN:
                if (neu & bit) != (maske & bit):
                    gedrueckt = bool(neu & bit)
                    out(f"  [{t:6.2f}s] Taste {name} {'gedrückt' if gedrueckt else 'losgelassen'} (raw {hx(d)})")
                    if name == "INS":
                        ins_druecke.append((t, gedrueckt))
            unbekannt = neu & ~sum(b for _, b in TASTEN)
            if unbekannt:
                out(f"  [{t:6.2f}s] unbekannte Bits 0x{unbekannt:04x} (raw {hx(d)})")
            maske = neu
        elif d[0] == 0x9E:
            out(f"  [{t:6.2f}s] Bewegung: {'abgelegt' if len(d) > 8 and d[8] == 1 else 'aufgenommen'} (raw {hx(d)})")
        elif d[0] == 0x94:
            out(f"  [{t:6.2f}s] Funkstatus (raw {hx(d)})")
        else:
            out(f"  [{t:6.2f}s] Bericht 0x{d[0]:02x} (raw {hx(d)})")
    halt.set()
    druecke = [x for x in ins_druecke if x[1]]
    los = [x for x in ins_druecke if not x[1]]
    out(f"\n== INS/OVR: {len(druecke)}× gedrückt, {len(los)}× losgelassen gemeldet.")
    if druecke and len(los) >= len(druecke) and all(l[0] - p[0] < 1.5 for p, l in zip(druecke, los)):
        out("   → normale Taste (Druck + Loslassen je Druck) — passt zu RaKScribe.")
    elif druecke:
        out("   → AUFFÄLLIG: Bit bleibt nach dem Druck stehen (Umschalter?). Bitte so an Hermes melden — RaKScribe kann dann")
        out("     jede Flanke als Druck werten (speechmike.UMSCHALTER).")
    else:
        out("   → INS wurde nicht gedrückt oder kam nicht an.")


def leds(dev):
    out("\n== LED-Test (Record-LED). Bitte jeweils notieren, was zu sehen ist:")
    for text, byte5, sek in LED:
        try:
            dev.write([0x00, 0x02, 0, 0, 0, 0, 0, byte5, 0, 0])
            out(f"  jetzt: {text}  ({sek} s)")
        except Exception as e:
            out(f"  LED-Befehl fehlgeschlagen ({e}) — RaKScribe setzt die LEDs dann nicht, Tasten gehen trotzdem.")
            return
        time.sleep(sek)


def main():
    global _log
    ap = argparse.ArgumentParser(description="SpeechMike-Hardware-Prüfung (nur hidapi)")
    ap.add_argument("--sekunden", type=int, default=60)
    ap.add_argument("--ohne-led", action="store_true")
    ap.add_argument("--ohne-abfrage", action="store_true", help="Modus/Modell nicht abfragen (nur mitlesen)")
    a = ap.parse_args()
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), time.strftime("speechmike_probe_%Y%m%d_%H%M%S.log"))
    try:
        _log = open(pfad, "w", encoding="utf-8")
    except OSError:
        _log = None
    out(f"SpeechMike-Prüfung {time.strftime('%d.%m.%Y %H:%M:%S')} · {platform.platform()} · Python {platform.python_version()}")
    try:
        import hid
    except ImportError:
        out("hidapi fehlt: bitte  pip install hidapi==0.15.0  und erneut starten.")
        return 4
    try:
        out(f"hidapi {hid.version_str()}")
    except Exception:
        pass
    alle = [d for d in hid.enumerate() if d.get("vendor_id") in VENDOREN]
    out(f"\n== Gefundene Philips/Nuance-HID-Schnittstellen: {len(alle)}")
    for d in alle:
        out(f"  {d['vendor_id']:04x}:{d['product_id']:04x} {PRODUKTE.get(d['product_id'], '?'):34s} Usage-Page 0x{d.get('usage_page', 0):04x} "
            f"Usage {d.get('usage', 0)}  Schnittstelle {d.get('interface_number')}  „{d.get('product_string') or ''}“  "
            f"Seriennr.: {'ja' if d.get('serial_number') else 'nein'}  Pfad {d['path']!r}")
    haupt = next((d for d in alle if d.get("vendor_id") == 0x0911 and d.get("usage_page") == USAGE_PAGE), None)
    if not haupt:
        out("\nKein SpeechMike mit Hersteller-Schnittstelle (Usage-Page 0xFFA0) gefunden — angesteckt? Anderer USB-Port?")
        return 2
    out(f"\n== Öffne {haupt['vendor_id']:04x}:{haupt['product_id']:04x} Usage-Page 0xFFA0 geteilt …")
    dev = hid.device()
    try:
        dev.open_path(haupt["path"])
    except Exception as e:
        out(f"  FEHLGESCHLAGEN: {e} — hält ein anderes Programm das Gerät exklusiv? (SpeechControl/SpeechMagic schließen und"
            " erneut probieren, Ergebnis bitte melden)")
        return 3
    out("  geöffnet (geteilt) ✓")
    nebenstellen = []
    for d in alle:
        if d is haupt or d.get("vendor_id") != haupt["vendor_id"]:
            continue
        n = hid.device()
        try:
            n.open_path(d["path"])
            nebenstellen.append((f"{d['product_id']:04x}/0x{d.get('usage_page', 0):04x}", n))
            out(f"  weitere Schnittstelle 0x{d.get('usage_page', 0):04x}/{d.get('usage', 0)} wird roh mitgelesen")
        except Exception as e:
            out(f"  weitere Schnittstelle 0x{d.get('usage_page', 0):04x}/{d.get('usage', 0)} nicht lesbar ({e}) — normal bei Tastatur/Maus")
    if not a.ohne_abfrage:
        out("\n== Abfrage (nur lesen, wie das Google/Philips-SDK):")
        abfragen(dev)
    try:
        mitlesen(dev, a.sekunden, nebenstellen)
        if not a.ohne_led:
            leds(dev)
    except KeyboardInterrupt:
        out("\nabgebrochen")
    finally:
        try:
            dev.write([0x00, 0x02, 0, 0, 0, 0, 0, 0, 0, 0])
        except Exception:
            pass
        dev.close()
        for _, n in nebenstellen:
            try:
                n.close()
            except Exception:
                pass
    out(f"\nFertig. Protokoll: {pfad if _log else '(nicht geschrieben)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
