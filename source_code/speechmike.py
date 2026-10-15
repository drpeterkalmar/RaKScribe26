"""SpeechMike-Tasten direkt lesen (v3.8.0, Peter 11.10.2026) — ohne Konfiguration in Philips SpeechControl.

Protokoll nach dem Google/Philips-SDK „dictation_support“ (GoogleChromeLabs, Apache-2.0, src/speechmike_hid_device.ts):
herstellereigene HID-Schnittstelle (Usage-Page 0xFFA0) der Philips-SpeechMikes (Hersteller 0x0911). Ein Tastenbericht
hat Byte 0 = 0x80, die Tasten stehen als 16-Bit-Maske in Byte 7/8 (little endian). LEDs: Befehl 0x02 + 8 Datenbytes.

Ohne Windows und ohne hidapi importierbar: Dekodierung, LED-Bytes und Belegung sind reine Funktionen (Gegenstück
web_app/src/speechmike.ts, gemeinsame Fälle tests/offline/speechmike_faelle.txt). SpeechMikeLeser liest im
Hintergrund-Thread mit hidapi (pip „hidapi“, Modul hid). hidapi öffnet unter Windows GETEILT (FILE_SHARE_READ|WRITE):
Philips SpeechControl/SpeechMagic bekommen dieselben Tastenberichte weiterhin.

Belegung (Peter 11.10., Nachtrag 3 — endgültig): Record = Aufnahme/Pause/Weiter, INS = Befund rechts erstellen (nichts
einfügen), EOL = sichtbaren Befund weiterschicken + alles leeren, Stop = Pause, F1 = Neu, F2 = Nur Text. Alle anderen
Tasten nur ins Protokoll — außer bei offener Mammo-Maske (v3.15: Spulen = Feld, F3/Play = übernehmen, F4/Command = Maske
aus/an; Belegung in masken.json, RaKScribe.py _maske_taste).
"""
import collections
import threading
import time

VENDOR_ID = 0x0911
# SDK DEVICE_FILTERS (SPEECHMIKE_HID): verkabelte SpeechMikes (LFH35xx/36xx, SMP37xx/38xx), Premium Air (SMP40xx),
# SpeechOne/Ambient, alle Modelle im Browser-Modus. Peters Gerät: 0911:0c1c.
PRODUKT_IDS = (0x0C1C, 0x0C1D, 0x0C1E, 0x0FA0)
USAGE_PAGE = 0xFFA0
BERICHT_TASTEN = 0x80

# (Name, Bit der 16-Bit-Maske) — SDK BUTTON_MAPPINGS_SPEECHMIKE. Bit 0/7 = Barcode-Scanner (nicht belegt), Bit 6 frei.
TASTEN = (
    ("F1", 1 << 1), ("F2", 1 << 2), ("F3", 1 << 3), ("F4", 1 << 4), ("COMMAND", 1 << 5),
    ("RECORD", 1 << 8), ("STOP", 1 << 9), ("PLAY", 1 << 10), ("FF", 1 << 11), ("REW", 1 << 12),
    ("EOL", 1 << 13), ("INS", 1 << 14), ("INSTR", 1 << 15),
)
# Schiebeschalter-Modelle (z. B. LFH3510/3610): die Schieberstellung steht als Dauer-Bit in JEDEM Bericht
SCHIEBER = ("RECORD", "STOP", "PLAY", "REW", "FF")
_SCHIEBER_MASKE = sum(b for n, b in TASTEN if n in SCHIEBER)

# Taste → Ereignis der Oberfläche (jobstate.UI_EREIGNISSE); fehlt die Taste, wird sie nur protokolliert
BELEGUNG = {"RECORD": "record", "INS": "ins", "EOL": "eol", "STOP": "stop", "F1": "reset", "F2": "nur_text"}

# v3.15.4 (Peter 15.10.: „ich hab im büro nur ein ambient … hat aber weniger buttons“): Tasten des SpeechMike Ambient
# PSM5000 laut Philips-Handbuch (Event-Modus): Record, Vorspulen, Rückspulen, Play, Command, INS/OVR, EOL — keine F1–F4,
# kein INSTR. Es meldet sich wie ein Premium Air als 0911:0C1D „SpeechMike III“; erkennbar an der Seriennummer „PSM5…“
# (Ordi-Probelauf 15.10.: PSM5000…). Das SDK nutzt für das Ambient dieselben Tasten-Bits (Druckknöpfe, kein Schieber).
AMBIENT_TASTEN = frozenset({"RECORD", "FF", "REW", "PLAY", "COMMAND", "INS", "EOL"})


def modell(info):
    """Gerätemodell aus der USB-Kennung (hid.enumerate-Eintrag), ohne Befehl ans Gerät — nur für Hilfezeile/Diagnose.
    → {"name": …, "tasten": Menge der Tasten oder None (= alle, z. B. Premium)}."""
    serie = str((info or {}).get("serial_number") or "").strip().upper()
    produkt = str((info or {}).get("product_string") or "")
    if serie.startswith("PSM5") or "ambient" in produkt.lower():
        return {"name": "SpeechMike Ambient (PSM5000)", "tasten": AMBIENT_TASTEN}
    return {"name": "", "tasten": None}


def tasten_maske(roh):
    """16-Bit-Tastenmaske aus der Rohzeile eines Tastenberichts („80 00 … 00 04“) — 0, wenn nicht lesbar."""
    try:
        b = [int(x, 16) for x in str(roh or "").split()]
    except ValueError:
        return 0
    return (b[7] | (b[8] << 8)) if len(b) >= 9 and b[0] == BERICHT_TASTEN else 0


def schieber_stellung(roh):
    """Steht im Bericht eine Schieberstellung (REC/STOP/PLAY/REW/FF)? Beim Loslassen einer Druckknopf-Taste nein — beim
    Weiterschieben eines Schiebers ja (die neue Stellung kommt im selben Bericht)."""
    return bool(tasten_maske(roh) & _SCHIEBER_MASKE)

ENTPRELL_S = 0.25    # zweiter Druck derselben Taste innerhalb 0,25 s = Prellen, zählt nicht
# Tasten, deren Bit bei jedem Druck umschaltet statt beim Loslassen zurückzugehen (falls die Hardware-Prüfung am rog17
# das für INS/OVR zeigt: hier eintragen — dann zählt jede Flanke als Druck). Laut SDK sind alle Tasten Druckknöpfe.
UMSCHALTER = frozenset()


def hex_bytes(daten):
    return " ".join(f"{b:02x}" for b in daten)


class Dekodierer:
    """Tastenberichte → [(Taste, gedrückt)]. Jede Taste einzeln über ihre Bit-Flanke — das trägt Druckknöpfe UND
    Schieberstellungen (Dauer-Bit). Gleicher Bericht zweimal = kein Ereignis. Andere Berichte (Funkstatus 0x94,
    Bewegung 0x9e, Antworten auf Befehle von SpeechControl) werden ignoriert."""

    def __init__(self, entprell_s=ENTPRELL_S, umschalter=UMSCHALTER):
        self.entprell_s = entprell_s
        self.umschalter = umschalter
        self.zuruecksetzen()

    def zuruecksetzen(self):
        self.maske = None            # None = seit dem Verbinden noch kein Tastenbericht
        self._letzter_druck = {}
        self._gemeldet = set()       # gedrückt gemeldete Tasten (nur deren Loslassen wird gemeldet)

    def bericht(self, daten, zeit=None):
        daten = list(daten)
        if len(daten) < 9 or daten[0] != BERICHT_TASTEN:
            return []
        zeit = time.monotonic() if zeit is None else zeit
        neu = daten[7] | (daten[8] << 8)
        alt = self.maske
        if alt is None:
            alt = 0
            gesetzt = [n for n, b in TASTEN if neu & b]
            if any(n in SCHIEBER for n in gesetzt) and any(n not in SCHIEBER for n in gesetzt):
                # erster Bericht nach dem Verbinden: Schieberstellung + echte Taste → Stellung ist die Ausgangslage
                alt = neu & _SCHIEBER_MASKE
        self.maske = neu
        out = []
        for name, bit in TASTEN:
            an, vorher = bool(neu & bit), bool(alt & bit)
            if an == vorher:
                continue
            if an or name in self.umschalter:
                t0 = self._letzter_druck.get(name)
                if t0 is not None and zeit - t0 < self.entprell_s:
                    continue  # prellt
                self._letzter_druck[name] = zeit
                if name not in self.umschalter:
                    self._gemeldet.add(name)
                out.append((name, True))
            elif name in self._gemeldet:
                self._gemeldet.discard(name)
                out.append((name, False))
        return out


# ── LEDs ────────────────────────────────────────────────────────────────────────────────────────────────────────
# Befehl 0x02, Datenbyte 5: Record-LED grün (Bit 0–1) / rot (2–3), Instruction grün (4–5) / rot (6–7);
# Byte 6: INS/OVR grün (4–5) / rot (6–7); Byte 7: F4 (0–1), F3 (2–3), F2 (4–5), F1 (6–7). Modus 0 aus, 1 langsam
# blinkend, 2 schnell blinkend, 3 an (SDK sendLedState).
AUS, LANGSAM, SCHNELL, AN = 0, 1, 2, 3


def led_daten(record_gruen=AUS, record_rot=AUS):
    return [0x02, 0, 0, 0, 0, 0, record_gruen | (record_rot << 2), 0, 0]


LED = {
    "aus": led_daten(),
    "aufnahme": led_daten(record_rot=AN),                                  # Aufnahme: rot
    "pause": led_daten(record_rot=LANGSAM),                                # Pause: rot blinkend
    "verarbeitung": led_daten(record_gruen=SCHNELL, record_rot=SCHNELL),   # Befund wird erstellt: gelb blinkend (rot+grün)
    "befund_bereit": led_daten(record_gruen=AN),                           # Befund wartet auf EOL: grün
}


def led_fuer(zustand, befund_wartet=False):
    """LED-Name zum Zustand der Zustandsmaschine (jobstate)."""
    return {"RECORDING": "aufnahme", "PAUSED": "pause", "PROCESSING": "verarbeitung"}.get(
        zustand, "befund_bereit" if (zustand == "READY" and befund_wartet) else "aus")


# ── EOL nur mit fertigem Befund ─────────────────────────────────────────────────────────────────────────────────
PLATZHALTER = ("... Befund wird geladen ...", "... Text wird korrigiert ...")
FEHLTEXT_MERKMAL = "konnte nicht erstellt werden"


def sendefaehig(befund):
    """True, wenn rechts ein fertiger Befund steht, den EOL weiterschicken darf (nicht leer, kein Platzhalter,
    keine gescheiterte Region)."""
    t = (befund or "").strip()
    return bool(t) and t not in PLATZHALTER and FEHLTEXT_MERKMAL not in t


# ── Hintergrund-Thread (Windows: hidapi) ──────────────────────────────────────────────────────────────────────────
def passend(info):
    return (info.get("vendor_id") == VENDOR_ID and info.get("product_id") in PRODUKT_IDS
            and info.get("usage_page") == USAGE_PAGE)


class SpeechMikeLeser:
    """Sucht alle 2 s ein SpeechMike, öffnet es geteilt, meldet Tasten (on_taste(name, gedrückt, roh_hex) — läuft im
    Lese-Thread, der Aufrufer reicht per after(0, …) in die Oberfläche weiter) und setzt die LEDs. Ab-/Anstecken wird
    erkannt; ohne Gerät oder ohne hidapi passiert nichts (Protokollzeile). LED-Fehler sind nie fatal."""

    def __init__(self, on_taste, log=print, on_verbindung=None, hid_modul=None, scan_s=2.0):
        self.on_taste = on_taste
        self.log = log
        self.on_verbindung = on_verbindung or (lambda beschreibung: None)
        self._hid = hid_modul
        self.scan_s = scan_s
        self.verbunden = None              # Beschreibung des offenen Geräts oder None
        self.modell = None                 # v3.15.4: modell(info) des offenen Geräts (Ambient: Tasten ohne F1–F4)
        self.dekodierer = Dekodierer()
        self.verlauf = collections.deque(maxlen=40)   # Diagnose: letzte Tasten
        self.led_soll = "aus"
        self._led_gesendet = None
        self._led_fehler_gemeldet = False
        self._stop = threading.Event()
        self._thread = None

    # Steuerung
    def starten(self):
        self._thread = threading.Thread(target=self._lauf, daemon=True, name="speechmike")
        self._thread.start()

    def beenden(self, warten=0.6):
        self.led_soll = "aus"
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=warten)

    def led(self, name):
        """LED-Zustand vormerken; der Lese-Thread schreibt ihn (kein gleichzeitiger Zugriff auf das Gerät)."""
        if name in LED:
            self.led_soll = name

    def einspeisen(self, daten, zeit=None):
        """Selbsttest/Tests: einen Bericht so verarbeiten, als käme er vom Gerät (gleicher Weg wie im Lese-Thread)."""
        self._melden(self.dekodierer.bericht(daten, zeit), daten)

    # intern
    def _melden(self, ereignisse, daten):
        for name, gedrueckt in ereignisse:
            zeile = f"[SPEECHMIKE] Taste {name} {'gedrückt' if gedrueckt else 'losgelassen'} (raw {hex_bytes(daten)})"
            self.log(zeile)
            self.verlauf.append(time.strftime("%H:%M:%S ") + zeile[13:])
            try:
                self.on_taste(name, gedrueckt, hex_bytes(daten))
            except Exception as e:  # die Oberfläche darf den Lese-Thread nie beenden
                self.log(f"[SPEECHMIKE] Fehler bei Taste {name}: {e}")

    def _lauf(self):
        try:
            hid = self._hid if self._hid is not None else __import__("hid")
        except Exception as e:
            self.log(f"[SPEECHMIKE] hidapi nicht verfügbar ({e}) — SpeechMike-Tasten aus, F10/F9 gehen weiter.")
            return
        kein_geraet_gemeldet = False
        while not self._stop.is_set():
            try:
                info = next((d for d in hid.enumerate(VENDOR_ID, 0) if passend(d)), None)
            except Exception as e:
                self.log(f"[SPEECHMIKE] Gerätesuche fehlgeschlagen: {e}")
                info = None
            if info is None:
                if not kein_geraet_gemeldet:
                    self.log("[SPEECHMIKE] Kein SpeechMike gefunden — suche weiter (Anstecken genügt).")
                    kein_geraet_gemeldet = True
                self._stop.wait(self.scan_s)
                continue
            kein_geraet_gemeldet = False
            dev = hid.device()
            try:
                dev.open_path(info["path"])
            except Exception as e:
                self.log(f"[SPEECHMIKE] Öffnen fehlgeschlagen ({e}) — hält ein anderes Programm das Gerät exklusiv? "
                         "Neuer Versuch in 5 s.")
                self._stop.wait(5)
                continue
            beschreibung = (f"{info.get('product_string') or 'SpeechMike'} "
                            f"({info['vendor_id']:04x}:{info['product_id']:04x})").strip()
            self.modell = modell(info)
            self.verbunden = beschreibung
            self.dekodierer.zuruecksetzen()
            self._led_gesendet = None
            self.log(f"[SPEECHMIKE] Verbunden: {beschreibung}, Usage-Page 0x{USAGE_PAGE:04X}, geteilt geöffnet."
                     + (f" Modell: {self.modell['name']} – Tasten ohne F1–F4." if self.modell["tasten"] else ""))
            self.on_verbindung(beschreibung)
            try:
                self._lesen(dev)
            except Exception as e:
                self.log(f"[SPEECHMIKE] Verbindung getrennt ({e}).")
            finally:
                try:
                    dev.close()
                except Exception:
                    pass
                self.verbunden = self.modell = None
                self.on_verbindung(None)

    def _led_schreiben(self, dev):
        soll = self.led_soll
        if soll == self._led_gesendet:
            return
        try:
            dev.write([0x00] + LED[soll])  # Report-ID 0 + Befehl
        except Exception as e:
            if not self._led_fehler_gemeldet:
                self.log(f"[SPEECHMIKE] LED nicht gesetzt ({e}) — Tasten gehen trotzdem.")
                self._led_fehler_gemeldet = True
        self._led_gesendet = soll

    def _lesen(self, dev):
        while True:
            self._led_schreiben(dev)
            if self._stop.is_set():
                return
            daten = dev.read(64, 100)
            if daten:
                self._melden(self.dekodierer.bericht(daten), daten)
