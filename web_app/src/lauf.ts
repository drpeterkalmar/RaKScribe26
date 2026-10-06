// Lauf-Verwaltung der Web-App (Umbau Schritt 8, Gutachten P2-7): jede Aufnahme bzw. jeder Audio-Upload ist ein
// Lauf mit eigener Nummer und eigenem AbortController. „Neu“/F9 bricht den laufenden Lauf ab; ein abgebrochener
// oder überholter Lauf schreibt weder Transkript noch Befund und kopiert nichts in die Zwischenablage.
import { istAbbruch } from './net.ts';

export class LaufVerwaltung {
  aktuelleId = 0;
  private laufend: Lauf | null = null;

  /** Neuer Lauf; ein noch laufender wird abgebrochen. */
  neu(): Lauf {
    this.laufend?.controller.abort();
    const lauf = new Lauf(++this.aktuelleId, this);
    this.laufend = lauf;
    return lauf;
  }

  /** Laufenden Lauf abbrechen (Neu/F9). */
  abbrechen(): void {
    this.laufend?.controller.abort();
    this.laufend = null;
    this.aktuelleId++;
  }
}

export class Lauf {
  readonly id: number;
  readonly controller = new AbortController();
  private verwaltung: LaufVerwaltung;

  constructor(id: number, verwaltung: LaufVerwaltung) {
    this.id = id;
    this.verwaltung = verwaltung;
  }

  get signal(): AbortSignal {
    return this.controller.signal;
  }

  aktuell(): boolean {
    return this.verwaltung.aktuelleId === this.id && !this.controller.signal.aborted;
  }

  /** fn nur ausführen, solange dieser Lauf aktuell ist. */
  nurAktuell<A extends unknown[]>(fn: (...a: A) => unknown): (...a: A) => void {
    return (...a: A) => {
      if (this.aktuell()) fn(...a);
    };
  }
}

export type BefundUi = {
  transkript: (text: string) => void;
  befund: (report: string) => void;
  status: (text: string) => void;
  fertig: () => void;                       // Status „Bereit“
  fehler: (meldung: string) => void;
  kopieren: (report: string) => unknown;
};

export type BefundSchritte = {
  transkribieren: (signal: AbortSignal) => Promise<string>;
  korrigieren: (text: string, signal: AbortSignal) => Promise<string>;   // Call 0
  befundErstellen: (text: string, signal: AbortSignal) => Promise<string>;  // Regionen → Bypass | Call 1 + 2
};

export type BefundOptionen = {
  transkriptVorPruefung?: boolean;  // Aufnahme: Rohtranskript sofort zeigen (wie bisher)
  statusVorBefund?: string;         // Upload: „KI-Strukturierung läuft …“
  fehlerPrefix: string;
};

/** Transkript → Korrektur → Befund → Kopieren, gemeinsam für Aufnahme und Upload. Jede Oberflächen-Änderung
 *  nur, solange der Lauf aktuell ist; ein Abbruch endet still. */
export async function befundLauf(lauf: Lauf, schritte: BefundSchritte, uiRoh: BefundUi, opt: BefundOptionen): Promise<void> {
  const ui: BefundUi = {
    transkript: lauf.nurAktuell(uiRoh.transkript),
    befund: lauf.nurAktuell(uiRoh.befund),
    status: lauf.nurAktuell(uiRoh.status),
    fertig: lauf.nurAktuell(uiRoh.fertig),
    fehler: lauf.nurAktuell(uiRoh.fehler),
    kopieren: lauf.nurAktuell(uiRoh.kopieren),
  };
  try {
    let text = (await schritte.transkribieren(lauf.signal)).trim();
    if (!lauf.aktuell()) return;
    if (opt.transkriptVorPruefung) ui.transkript(text);
    if (!text) throw new Error('Es wurde kein gesprochener Text erkannt.');

    ui.status('Korrigiere medizinische Fachbegriffe (Gemini Flash)...');
    text = await schritte.korrigieren(text, lauf.signal);
    if (!lauf.aktuell()) return;
    ui.transkript(text);

    if (opt.statusVorBefund) ui.status(opt.statusVorBefund);
    const report = await schritte.befundErstellen(text, lauf.signal);
    if (!lauf.aktuell()) return;
    ui.befund(report);
    ui.fertig();
    if (lauf.aktuell()) await uiRoh.kopieren(report);
  } catch (err: unknown) {
    if (istAbbruch(err) || !lauf.aktuell()) return;
    console.error(err);
    ui.fehler(opt.fehlerPrefix + (err instanceof Error ? err.message : String(err)));
  }
}
