// SpeechMike-Tasten direkt lesen (v3.8.0, Peter 11.10.2026) — WebHID, ohne Konfiguration in Philips SpeechControl.
// Protokoll nach dem Google/Philips-SDK „dictation_support“ (GoogleChromeLabs, Apache-2.0, src/speechmike_hid_device.ts),
// als eigenes schlankes Modul: gleiche Dekodierung wie die EXE (source_code/speechmike.py, gemeinsame Fälle
// tests/offline/speechmike_faelle.txt), keine Geräte-Abfragen beim Verbinden (deren Antworten landen auch bei
// SpeechControl), unbekannte Berichte werden ignoriert statt Fehler zu werfen.
// Belegung (Peter 11.10., Nachtrag 3): Record = Aufnahme/Pause/Weiter, INS = Befund rechts erstellen (nichts kopieren),
// EOL = sichtbaren Befund weiterschicken + leeren, Stop = Pause, F1 = Neu, F2 = Nur Text; übrige Tasten nur ins Protokoll.
import type { UiEreignis } from './lauf.ts';

export const VENDOR_ID = 0x0911;
export const PRODUKT_IDS = [0x0c1c, 0x0c1d, 0x0c1e, 0x0fa0];
export const USAGE_PAGE = 0xffa0;
const BERICHT_TASTEN = 0x80;

export const TASTEN: ReadonlyArray<readonly [string, number]> = [
  ['F1', 1 << 1], ['F2', 1 << 2], ['F3', 1 << 3], ['F4', 1 << 4], ['COMMAND', 1 << 5],
  ['RECORD', 1 << 8], ['STOP', 1 << 9], ['PLAY', 1 << 10], ['FF', 1 << 11], ['REW', 1 << 12],
  ['EOL', 1 << 13], ['INS', 1 << 14], ['INSTR', 1 << 15],
];
export const SCHIEBER = ['RECORD', 'STOP', 'PLAY', 'REW', 'FF'];
const SCHIEBER_MASKE = TASTEN.filter(([n]) => SCHIEBER.includes(n)).reduce((s, [, b]) => s | b, 0);

export const BELEGUNG: Readonly<Record<string, UiEreignis | 'nur_text'>> = {
  RECORD: 'record', INS: 'ins', EOL: 'eol', STOP: 'stop', F1: 'reset', F2: 'nur_text',
};
export const ENTPRELL_S = 0.25;
// Tasten, deren Bit bei jedem Druck umschaltet (Sync: speechmike.py UMSCHALTER) — laut SDK keine
export const UMSCHALTER: ReadonlySet<string> = new Set<string>();

export const hexBytes = (d: ArrayLike<number>): string => Array.from(d, b => b.toString(16).padStart(2, '0')).join(' ');

export type TastenEreignis = [taste: string, gedrueckt: boolean];

/** Tastenberichte → Ereignisse, je Taste über die Bit-Flanke (Druckknöpfe und Schieberstellungen). */
export class Dekodierer {
  maske: number | null = null;
  private letzterDruck = new Map<string, number>();
  private gemeldet = new Set<string>();
  private entprellS: number;
  private umschalter: ReadonlySet<string>;

  constructor(entprellS = ENTPRELL_S, umschalter: ReadonlySet<string> = UMSCHALTER) {
    this.entprellS = entprellS;
    this.umschalter = umschalter;
  }

  zuruecksetzen(): void {
    this.maske = null;
    this.letzterDruck.clear();
    this.gemeldet.clear();
  }

  bericht(daten: ArrayLike<number>, zeit: number): TastenEreignis[] {
    if (daten.length < 9 || daten[0] !== BERICHT_TASTEN) return [];
    const neu = daten[7] | (daten[8] << 8);
    let alt = this.maske;
    if (alt === null) {
      alt = 0;
      const gesetzt = TASTEN.filter(([, b]) => neu & b).map(([n]) => n);
      if (gesetzt.some(n => SCHIEBER.includes(n)) && gesetzt.some(n => !SCHIEBER.includes(n))) {
        alt = neu & SCHIEBER_MASKE;  // erster Bericht: Schieberstellung + echte Taste → Stellung ist Ausgangslage
      }
    }
    this.maske = neu;
    const out: TastenEreignis[] = [];
    for (const [name, bit] of TASTEN) {
      const an = (neu & bit) !== 0, vorher = (alt & bit) !== 0;
      if (an === vorher) continue;
      if (an || this.umschalter.has(name)) {
        const t0 = this.letzterDruck.get(name);
        if (t0 !== undefined && zeit - t0 < this.entprellS) continue;  // prellt
        this.letzterDruck.set(name, zeit);
        if (!this.umschalter.has(name)) this.gemeldet.add(name);
        out.push([name, true]);
      } else if (this.gemeldet.has(name)) {
        this.gemeldet.delete(name);
        out.push([name, false]);
      }
    }
    return out;
  }
}

// ── LEDs (Befehl 0x02; Byte 5: Record grün Bit 0–1, rot Bit 2–3 · Modus 0 aus, 1 langsam, 2 schnell, 3 an) ──
const AUS = 0, LANGSAM = 1, SCHNELL = 2, AN = 3;
const ledDaten = (gruen = AUS, rot = AUS): number[] => [0x02, 0, 0, 0, 0, 0, gruen | (rot << 2), 0, 0];
export type LedName = 'aus' | 'aufnahme' | 'pause' | 'verarbeitung' | 'befund_bereit';
export const LED: Readonly<Record<LedName, number[]>> = {
  aus: ledDaten(),
  aufnahme: ledDaten(AUS, AN),
  pause: ledDaten(AUS, LANGSAM),
  verarbeitung: ledDaten(SCHNELL, SCHNELL),
  befund_bereit: ledDaten(AN, AUS),
};

export function ledFuer(zustand: string, befundWartet = false): LedName {
  if (zustand === 'RECORDING') return 'aufnahme';
  if (zustand === 'PAUSED') return 'pause';
  if (zustand === 'PROCESSING') return 'verarbeitung';
  return zustand === 'READY' && befundWartet ? 'befund_bereit' : 'aus';
}

// ── EOL nur mit fertigem Befund (Sync: speechmike.py sendefaehig) ──
const PLATZHALTER = ['... Befund wird geladen ...', '... Text wird korrigiert ...'];
export const sendefaehig = (befund: string): boolean => {
  const t = (befund || '').trim();
  return !!t && !PLATZHALTER.includes(t) && !t.includes('konnte nicht erstellt werden');
};

// ── WebHID ──────────────────────────────────────────────────────────────────────────────────────────────────
// Eigene Mindest-Typen (WebHID steht nicht in der DOM-Lib von TypeScript)
export type HidGeraet = EventTarget & {
  opened: boolean; vendorId: number; productId: number; productName?: string;
  collections?: { usagePage?: number; usage?: number }[];
  open(): Promise<void>; close(): Promise<void>; sendReport(reportId: number, data: BufferSource): Promise<void>;
};
export type HidApi = EventTarget & {
  getDevices(): Promise<HidGeraet[]>;
  requestDevice(o: { filters: object[] }): Promise<HidGeraet[]>;
};
type HidBerichtEreignis = Event & { device: HidGeraet; reportId: number; data: DataView };
type HidVerbindungsEreignis = Event & { device: HidGeraet };

export const HID_FILTER = PRODUKT_IDS.map(productId => ({ vendorId: VENDOR_ID, productId, usagePage: USAGE_PAGE, usage: 1 }));

/** navigator.hid oder null (Safari/iPhone/Firefox: kein WebHID → Menüpunkt ausblenden). */
export function webHid(): HidApi | null {
  if (typeof navigator === 'undefined') return null;
  const hid = (navigator as unknown as { hid?: HidApi }).hid;
  return hid && typeof hid.getDevices === 'function' ? hid : null;
}

export const passend = (d: HidGeraet): boolean =>
  d.vendorId === VENDOR_ID && PRODUKT_IDS.includes(d.productId)
  && (d.collections ?? []).some(c => c.usagePage === USAGE_PAGE);

export type SpeechMikeRueckrufe = {
  taste: (taste: string, gedrueckt: boolean, roh: string) => void;
  status: (verbunden: string | null) => void;
  log?: (zeile: string) => void;
};

/** Verbindung zur Web-App: beim Laden über getDevices() (frühere Freigabe), sonst per „SpeechMike verbinden“
 *  (requestDevice braucht einen Klick). An-/Abstecken über die connect/disconnect-Ereignisse von navigator.hid. */
export class SpeechMikeVerbindung {
  private hid: HidApi;
  private cb: SpeechMikeRueckrufe;
  private geraet: HidGeraet | null = null;
  private dek = new Dekodierer();
  private ledSoll: LedName = 'aus';
  private ledGesendet: LedName | null = null;
  private onBericht = (e: Event) => this.bericht(e as HidBerichtEreignis);
  private onConnect = (e: Event) => { const d = (e as HidVerbindungsEreignis).device; if (!this.geraet && passend(d)) void this.oeffnen(d); };
  private onDisconnect = (e: Event) => { if ((e as HidVerbindungsEreignis).device === this.geraet) this.getrennt(); };

  constructor(hid: HidApi, cb: SpeechMikeRueckrufe) {
    this.hid = hid;
    this.cb = cb;
  }

  private log(zeile: string): void {
    (this.cb.log ?? console.log)(zeile);
  }

  async start(): Promise<void> {
    this.hid.addEventListener('connect', this.onConnect);
    this.hid.addEventListener('disconnect', this.onDisconnect);
    try {
      const d = (await this.hid.getDevices()).find(passend);
      if (d) await this.oeffnen(d);
    } catch (e) {
      this.log(`[SPEECHMIKE] getDevices fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  /** Menü „SpeechMike verbinden“ — nur aus einem Klick heraus aufrufen (Nutzer-Geste). */
  async verbinden(): Promise<boolean> {
    try {
      const d = (await this.hid.requestDevice({ filters: HID_FILTER })).find(passend);
      if (!d) return false;
      if (d !== this.geraet) await this.oeffnen(d);
      return true;
    } catch (e) {
      this.log(`[SPEECHMIKE] Verbinden fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`);
      return false;
    }
  }

  get verbunden(): boolean {
    return this.geraet !== null;
  }

  led(name: LedName): void {
    this.ledSoll = name;
    void this.ledSenden();
  }

  stop(): void {
    this.hid.removeEventListener('connect', this.onConnect);
    this.hid.removeEventListener('disconnect', this.onDisconnect);
    const g = this.geraet;
    if (g) {
      g.removeEventListener('inputreport', this.onBericht);
      g.sendReport(0, new Uint8Array(LED.aus)).catch(() => {}).finally(() => { g.close().catch(() => {}); });
    }
    this.geraet = null;
  }

  /** Tests/Selbsttest: Bericht wie vom Gerät verarbeiten. */
  einspeisen(daten: ArrayLike<number>, zeit = performance.now() / 1000): void {
    for (const [taste, gedrueckt] of this.dek.bericht(daten, zeit)) {
      const roh = hexBytes(daten);
      this.log(`[SPEECHMIKE] Taste ${taste} ${gedrueckt ? 'gedrückt' : 'losgelassen'} (raw ${roh})`);
      this.cb.taste(taste, gedrueckt, roh);
    }
  }

  private async oeffnen(d: HidGeraet): Promise<void> {
    try {
      if (!d.opened) await d.open();
    } catch (e) {
      this.log(`[SPEECHMIKE] Öffnen fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`);
      return;
    }
    if (this.geraet && this.geraet !== d) this.geraet.removeEventListener('inputreport', this.onBericht);
    this.geraet = d;
    this.dek.zuruecksetzen();
    this.ledGesendet = null;
    d.addEventListener('inputreport', this.onBericht);
    const name = `${d.productName || 'SpeechMike'} (${d.vendorId.toString(16).padStart(4, '0')}:${d.productId.toString(16).padStart(4, '0')})`;
    this.log(`[SPEECHMIKE] Verbunden: ${name}`);
    this.cb.status(name);
    void this.ledSenden();
  }

  private getrennt(): void {
    this.geraet?.removeEventListener('inputreport', this.onBericht);
    this.geraet = null;
    this.ledGesendet = null;
    this.log('[SPEECHMIKE] Getrennt.');
    this.cb.status(null);
  }

  private bericht(e: HidBerichtEreignis): void {
    if (e.reportId !== 0) return;
    this.einspeisen(new Uint8Array(e.data.buffer, e.data.byteOffset, e.data.byteLength));
  }

  private async ledSenden(): Promise<void> {
    const g = this.geraet, soll = this.ledSoll;
    if (!g || soll === this.ledGesendet) return;
    this.ledGesendet = soll;
    try {
      await g.sendReport(0, new Uint8Array(LED[soll]));
    } catch (e) {
      this.log(`[SPEECHMIKE] LED nicht gesetzt: ${e instanceof Error ? e.message : String(e)}`);  // nie fatal
    }
  }
}
