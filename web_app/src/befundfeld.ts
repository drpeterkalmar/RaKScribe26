// Rechtes Befundfeld nie still überschreiben (kaiscribe-befundfeld-sicher-n1, Peter 20.11.2026, 3.19.16).
// Steht rechts schon Text, ist ein Diktat eine ERGÄNZUNG (mit Cursor/Markierung an der Stelle, sonst ans Ende des
// Befundteils des passenden Abschnitts, vor „## Ergebnis“); Titel und Text bleiben. Restructure: Peters Änderungen
// seit dem letzten KaiScribe-Stand haben Vorrang. Sync: source_code/befundfeld.py — gemeinsame Fälle
// tests/offline/snapshots/befundfeld_faelle.txt (pipeline_test.mjs ≡ tests/offline/test_befundfeld.py).
import vorrangJson from '../../vorlagen_vorrang.json' with { type: 'json' };
import { REGIONEN, REGIONEN_OHNE_SEITE, diktierteSeite, hasPathology, saetzeMitLage, vorlageNormalisieren, widerspruchBefunde,
  widerspruchSaetze, type WiderspruchDaten, ergebnisNummerieren, UNNUM_RE } from './befundRegeln.ts';

const WID_STANDARD = (vorrangJson as { widersprueche?: WiderspruchDaten }).widersprueche;
const UEBERSCHRIFT = /^\s*##\s+(.*?)\s*$/;
const ERGEBNIS_ZEILE = /^\s*(?:\*\*)?\s*ergebnis(?![\p{L}\d_])/iu;
const SATZENDE = '.!?:;)';
const STOPP = new Set(['und', 'oder', 'der', 'die', 'das', 'des', 'dem', 'den', 'ein', 'eine', 'einer', 'eines', 'einem', 'einen',
  'mit', 'ohne', 'bei', 'von', 'vom', 'zum', 'zur', 'ist', 'sind', 'wird', 'werden', 'sich', 'auch', 'nicht',
  'kein', 'keine', 'keiner', 'keinen', 'noch', 'als', 'auf', 'aus', 'fuer', 'nach', 'ueber', 'unter', 'sowie',
  'im', 'in', 'am', 'an', 'zu', 'es', 'eher', 'etwas', 'bzw', 'ca', 're', 'li', 'zusaetzlich', 'ausserdem']);

export type Modus = 'neu' | 'ergaenzung' | 'cursor' | 'geruest' | 'maske';
export const STATUS: Record<string, string> = { neu: 'Neuer Befund', ergaenzung: 'Ergänzung', geruest: 'Neuer Befund (IB-Lab-Gerüst)' };

/** Was macht das nächste Diktat mit dem rechten Feld? (Mammo-Maske und IB-Lab-Gerüst gibt es nur in der EXE)
 *  abgeschlossen = Befund rechts ging schon automatisch hinaus (F10/Knopf: kopiert) — zählt wie nach EOL. */
export const modus = (rechts: string, geruest = false, cursor = false, maske = false, abgeschlossen = false): Modus =>
  maske ? 'maske' : geruest ? 'geruest' : (!(rechts || '').trim() || (abgeschlossen && !cursor)) ? 'neu' : cursor ? 'cursor' : 'ergaenzung';

// kaiscribe-ergaenzung-ohne-ins-n1 (Peter 26.11.2026): Cursor/Markierung rechts → Record → sprechen → Pause ⇒ der
// Abschnitt steht sofort wörtlich an der Stelle (ohne INS); EOL während einer Ergänzung nie „Erst INS“.
// Sync: befundfeld.py eol_aktion, gemeinsame Fälle tests/offline/snapshots/ergaenzung_eol_faelle.txt
export type EolAktion = 'senden' | 'abschliessen' | 'einfuegen' | 'warten' | 'sperre';
export const ergaenzungLaeuft = (einbau: string | null, ziel = false): boolean =>
  ziel || einbau === 'cursor' || einbau === 'ergaenzung';
export const pauseFuegtEin = (ziel: boolean, maske = false): boolean => ziel && !maske;
export function eolAktion(zustand: string, einbau: string | null, ziel = false, offen = 0): EolAktion {
  if (zustand === 'READY' || zustand === 'ERROR') return 'senden';
  if (!['RECORDING', 'PAUSED', 'PROCESSING'].includes(zustand) || !ergaenzungLaeuft(einbau, ziel)) return 'sperre';
  if (zustand === 'PROCESSING' || offen) return 'warten';
  if (zustand === 'PAUSED' && ziel) return 'abschliessen';
  return 'einfuegen';
}

type Art = 'befund' | 'ergebnis' | 'titel' | null;
const art = (zeile: string): Art => {
  const m = UEBERSCHRIFT.exec(zeile);
  if (!m) return null;
  const n = m[1].trim().replace(/:+$/, '').trim().toLowerCase();
  return n === 'befund' || n === 'ergebnis' ? n : 'titel';
};

export type Block = { titel: string | null; titel_zeile: number | null; start: number; ende: number;
  befund: [number, number] | null; ergebnis: [number, number] | null };

/** Befundtext → Abschnitte je Untersuchung (Zeilennummern, ende exklusiv) — wie befundfeld.py bloecke. */
export function bloecke(report: string): Block[] {
  const zeilen = (report || '').split('\n');
  const out: Block[] = [];
  let akt: Block | null = null;
  let sektion: 'befund' | 'ergebnis' | null = null;
  const schliessen = (i: number) => {
    if (akt) { akt.ende = i; if (sektion) akt[sektion] = [akt[sektion]![0], i]; }
    sektion = null;
  };
  const oeffnen = (i: number, titel: string | null = null, tz: number | null = null) => {
    akt = { titel, titel_zeile: tz, start: i, ende: zeilen.length, befund: null, ergebnis: null };
    out.push(akt);
  };
  zeilen.forEach((z, i) => {
    const a = art(z);
    if (a === 'titel') {
      schliessen(i);
      oeffnen(i, UEBERSCHRIFT.exec(z)![1].trim(), i);
    } else if (a) {
      const b = akt as Block | null;
      if (!b || b[a]) { schliessen(i); oeffnen(i); }
      else if (sektion) b[sektion] = [b[sektion]![0], i];
      (akt as unknown as Block)[a] = [i + 1, zeilen.length];
      sektion = a;
    } else if (!akt && z.trim()) {
      oeffnen(i);
    }
  });
  schliessen(zeilen.length);
  return out;
}

const regionen = (text: string): Set<string> => {
  const t = (text || '').toLowerCase();
  return new Set([...REGIONEN, ...REGIONEN_OHNE_SEITE].filter(([, pat]) => new RegExp(`(?<![\\p{L}\\d_])(?:${pat})`, 'u').test(t)).map(([k]) => k));
};
const zeilenOffset = (zeilen: string[], i: number): number => zeilen.slice(0, i).reduce((s, z) => s + z.length + 1, 0);
const letzteInhaltszeile = (zeilen: string[], a: number, e: number): number | null => {
  for (let i = Math.min(e, zeilen.length) - 1; i >= a; i--) if (zeilen[i].trim()) return i;
  return null;
};

/** Stelle für eine Ergänzung OHNE Cursor → [offset, art] (wie befundfeld.py ergaenzung_stelle). */
export function ergaenzungStelle(report: string, neu: string): [number, 'zeile' | 'anhaengen' | 'davor'] {
  const text = report || '';
  const zeilen = text.split('\n');
  const bl = bloecke(text).filter(b => b.befund || b.ergebnis);
  if (!bl.length) {
    const ez = zeilen.findIndex((z, i) => i > 0 && ERGEBNIS_ZEILE.test(z));
    if (ez > 0) {
      const j = letzteInhaltszeile(zeilen, 0, ez);
      if (j !== null) return [zeilenOffset(zeilen, j) + zeilen[j].length, 'zeile'];
    }
    return [text.trimEnd().length, 'anhaengen'];
  }
  let wahl = bl[bl.length - 1];
  const reg = regionen(neu);
  if (bl.length > 1 && reg.size) {
    let kand = bl.filter(b => [...regionen(b.titel || '')].some(k => reg.has(k)));
    const seite = diktierteSeite(neu);
    if (kand.length > 1 && seite) {
      const mitSeite = kand.filter(b => [seite, ''].includes(diktierteSeite(b.titel || '')));
      if (mitSeite.length) kand = mitSeite;
    }
    if (kand.length) wahl = kand[0];
  }
  if (wahl.befund) {
    const [a, e] = wahl.befund;
    let j = letzteInhaltszeile(zeilen, a, e);
    if (j === null) j = a - 1;
    return [zeilenOffset(zeilen, j) + zeilen[j].length, 'zeile'];
  }
  const a = wahl.ergebnis![0] - 1;
  const j = letzteInhaltszeile(zeilen, wahl.start, a);
  if (j === null) return [zeilenOffset(zeilen, a), 'davor'];
  return [zeilenOffset(zeilen, j) + zeilen[j].length, 'zeile'];
}

const satz = (neu: string, gross: boolean): string => {
  let s = (neu || '').split(/\s+/).filter(Boolean).join(' ');
  if (gross && /^\p{Ll}/u.test(s)) s = s[0].toUpperCase() + s.slice(1);
  if (s && !SATZENDE.includes(s[s.length - 1])) s += '.';
  return s;
};

/** Ergänzung ohne Cursor einbauen; Titel und übriger Text bleiben Zeichen für Zeichen. → [Text, Cursor] */
// kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkt 62): „zweitens …“ / „Punkt 2 …“ / „an zweiter Stelle …“ →
// neuer Ergebnispunkt 2, die folgenden rücken nach. Sync: befundfeld.py ergebnis_ordinal/ergebnis_einfuegen.
const ORDNUNG = ['erst', 'zweit', 'dritt', 'viert', 'fünft', 'sechst', 'siebt', 'acht', 'neunt', 'zehnt'];
const ZAHLWORT = ['eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn'];
const ORDINAL_RE = new RegExp('^\\s*(?:(?:(?:als\\s+)?neue[rn]?\\s+)?punkt\\s+(\\d{1,2}|' + ZAHLWORT.join('|') + ')(?![\\p{L}\\d_])' +
  '|an\\s+(' + ORDNUNG.join('|') + ')er\\s+stelle|(' + ORDNUNG.join('|') + ')ens(?![\\p{L}\\d_]))\\s*[:,.\\-]?\\s*', 'iu');
export function ergebnisOrdinal(neu: string): [number | null, string] {
  const m = ORDINAL_RE.exec(neu || '');
  if (!m || !(neu || '').slice(m[0].length).trim()) return [null, neu];
  let n: number;
  if (m[1]) { const g = m[1].toLowerCase(); n = /^\d+$/u.test(g) ? Number(g) : ZAHLWORT.indexOf(g) + 1; }
  else n = ORDNUNG.indexOf((m[2] || m[3]).toLowerCase()) + 1;
  return [n >= 1 ? n : null, neu.slice(m[0].length)];
}
export function ergebnisEinfuegen(report: string, neu: string, gross = true, cursor: number | null = null): [string, number] | null {
  const [n, rest] = ergebnisOrdinal(neu);
  if (n === null) return null;
  const text = report || '';
  const zeilen = text.split('\n');
  const bl = bloecke(text).filter(b => b.ergebnis);
  if (!bl.length) return null;
  let wahl: Block | undefined = bl[bl.length - 1];
  if (cursor !== null) {
    const zeile = (text.slice(0, cursor).match(/\n/gu) || []).length;
    wahl = bl.find(b => b.ergebnis![0] - 1 <= zeile && zeile < b.ergebnis![1]);
    if (!wahl) return null;
  } else {
    const reg = regionen(rest);
    const kand = bl.filter(b => reg.size && [...regionen(b.titel || '')].some(x => reg.has(x)));
    if (kand.length) wahl = kand[0];
  }
  const [a, e] = wahl.ergebnis!;
  const punkte: number[] = [];
  for (let i = a; i < e; i++) if (zeilen[i].trim() && ![' ', '\t'].includes(zeilen[i].slice(0, 1)) && !UNNUM_RE.test(zeilen[i].replace(NUM, '').trim())) punkte.push(i);
  const s = satz(rest, gross);
  if (!s) return null;
  const ziel = n - 1 < punkte.length ? punkte[n - 1] : (punkte.length ? punkte[punkte.length - 1] + 1 : (letzteInhaltszeile(zeilen, a, e) ?? (a - 1)) + 1);
  zeilen.splice(ziel, 0, s);
  const neuText = ergebnisNummerieren(zeilen.join('\n'));
  const nz = neuText.split('\n');
  return [neuText, zeilenOffset(nz, ziel) + nz[ziel].length];
}

export function ergaenzen(report: string, neu: string, gross = true): [string, number] {
  const text = report || '';
  const s = satz(neu, gross);
  if (!s) return [text, text.length];
  if (!text.trim()) return [s, s.length];
  const eo = ergebnisEinfuegen(text, neu, gross);   // Punkt 62: „zweitens …“ → Ergebnispunkt 2
  if (eo !== null) return eo;
  const [pos, a] = ergaenzungStelle(text, s);
  if (a === 'zeile') return [text.slice(0, pos) + '\n' + s + text.slice(pos), pos + 1 + s.length];
  if (a === 'davor') return [text.slice(0, pos) + s + '\n\n' + text.slice(pos), pos + s.length];
  return [text.slice(0, pos) + ' ' + s + text.slice(pos), pos + 1 + s.length];
}

// ── Restructure ────────────────────────────────────────────────────────────────────────────────────────────────
const NUM = /^\s*(?:\*\*)?\s*\d+\s*[.)]\s*(?:\*\*)?\s*/;

/** Inhaltssätze (ohne Überschriften, Ergebnis-Nummern weg) → [satz, abschnitt]. */
export function saetze(report: string, mitErgebnis = true): [string, string][] {
  const out: [string, string][] = [];
  let sektion: string | null = null;
  for (let z of (report || '').split('\n')) {
    const a = art(z);
    if (a) { sektion = a !== 'titel' ? a : null; continue; }
    if (sektion === 'ergebnis' && !mitErgebnis) continue;
    if (sektion === 'ergebnis') z = z.replace(NUM, '');
    for (const [x, y] of saetzeMitLage(z)) {
      const s = z.slice(x, y).trim();
      if (vorlageNormalisieren(s)) out.push([s, sektion || 'text']);
    }
  }
  return out;
}

/** Peters Ergänzungen/Änderungen = Sätze im Feld, die im letzten KaiScribe-Stand nicht standen. */
export function vorrang(stand: string, aktuell: string): string[] {
  const alt = new Set(saetze(stand).map(([s]) => vorlageNormalisieren(s)));
  const out: string[] = [];
  const gesehen = new Set<string>();
  for (const [s] of saetze(aktuell)) {
    const n = vorlageNormalisieren(s);
    if (!alt.has(n) && !gesehen.has(n)) { gesehen.add(n); out.push(s); }
  }
  return out;
}

export const blockText = (report: string, b: Block): string =>
  (report || '').split('\n').slice(b.start, b.ende).join('\n').replace(/^\n+|\n+$/g, '');

/** Abschnitt → Eingangstext der Befundkette; widersprechende Normalsätze vorher heraus. → [segment, gestrichen] */
export function umbauSegment(text: string, vor: string[], wid: WiderspruchDaten | undefined = WID_STANDARD): [string, string[]] {
  const vorN = new Set(vor.map(vorlageNormalisieren));
  const befunde = vor.length ? widerspruchBefunde(vor.join(' . '), wid) : [];
  let titel = '';
  const teile: string[] = [], ergebnis: string[] = [], gestrichen: string[] = [];
  let sektion: string | null = null;
  for (let z of (text || '').split('\n')) {
    const a = art(z);
    if (a) {
      if (a === 'titel' && !titel) titel = UEBERSCHRIFT.exec(z)![1].trim();
      if (a !== 'titel') sektion = a;
      continue;
    }
    if (!z.trim()) continue;
    if (sektion === 'ergebnis') { ergebnis.push(z.replace(NUM, '').trim()); continue; }
    if (befunde.length) {
      const weg = widerspruchSaetze(z, befunde, wid).filter(([x, y]) => !vorN.has(vorlageNormalisieren(z.slice(x, y))));
      for (const [x, y] of [...weg].reverse()) {
        gestrichen.unshift(z.slice(x, y).trim());
        z = (z.slice(0, x).trimEnd() + ' ' + z.slice(y).trimStart()).trim();
      }
      if (!z.trim()) continue;
    }
    teile.push(z.trim());
  }
  const seg = [...(titel ? [titel + ':'] : []), ...teile, ...(ergebnis.length ? ['Ergebnis: ' + ergebnis.join(' ')] : [])].join('\n');
  return [seg, gestrichen];
}

/** <umbau>-Hinweis für den Gen-Prompt (an der Stelle {examples}) — Wortlaut = befundfeld.py umbau_block. */
export function umbauBlock(vor: string[], gestrichen: string[] = [], ohneStand = false): string {
  if (!vor.length && !ohneStand) return '';
  const z = ['<umbau>',
    'Das Diktat ist KEIN neues Diktat, sondern der aktuelle Text aus dem Befundfeld (Untersuchung, Befund, ' +
    'bisheriges Ergebnis), den der Arzt ergänzt bzw. geändert hat. Erstelle daraus den Befund nach allen ' +
    'Regeln dieses Prompts vollständig neu strukturiert.'];
  if (vor.length) {
    z.push('Vom Arzt ergänzt oder geändert (VORRANG – gilt vor Vorlage und bisherigem Text):');
    z.push(...vor.map(s => `- „${s}“`));
  } else z.push('Der ganze Text stammt vom Arzt (alles hat Vorrang).');
  z.push('Regeln für den Umbau:',
    '1. Jede Vorrang-Angabe steht im Befund an der fachlich passenden Stelle (Wortlaut möglichst beibehalten); ' +
    'ist sie ein Befund, steht sie auch im Ergebnis.',
    '2. Normal- und Vorlagensätze, die einer Vorrang-Angabe widersprechen, bleiben so nicht stehen (Regeln wie ' +
    'bei <widersprueche>).',
    '3. Alle übrigen Angaben des bisherigen Textes (Befunde, Messwerte, Seiten, Grade, Empfehlungen, IB-Lab-Texte) ' +
    'bleiben inhaltlich vollständig erhalten. Nichts erfinden, nichts weglassen.',
    '4. Das Ergebnis wird an die Vorrang-Angaben angepasst; Nummerierung wie immer.',
    '5. Die Überschrift (Untersuchung) bleibt wie im bisherigen Text.');
  if (gestrichen.length) z.push('Schon entfernt, weil sie einer Vorrang-Angabe widersprechen: ' + gestrichen.map(s => `„${s}“`).join(' '));
  z.push('</umbau>');
  return z.join('\n');
}

/** Überschriften des neuen Befunds der Reihe nach durch die bisherigen ersetzen (nur bei gleicher Anzahl). */
export function titelUebernehmen(neu: string, altTitel: (string | null)[]): string {
  const alt = altTitel.filter((t): t is string => !!t);
  const zeilen = (neu || '').split('\n');
  const pos = bloecke(neu).map(b => b.titel_zeile).filter((x): x is number => x !== null);
  if (!alt.length || pos.length !== alt.length) return neu;
  pos.forEach((i, k) => { zeilen[i] = '## ' + alt[k]; });
  return zeilen.join('\n');
}

const woerter = (text: string): string[] =>
  vorlageNormalisieren(text).split(' ').filter(w => w && (w.length >= 4 || /^\d+$/.test(w)) && !STOPP.has(w));

/** Steht der Inhalt von satz im report? Alle Zahlen und mindestens anteil der Inhaltswörter. */
export function inhaltDa(s: string, report: string, anteil = 0.7): boolean {
  const w = woerter(s);
  if (!w.length) return true;
  const r = new Set(vorlageNormalisieren(report).split(' ').filter(Boolean));
  const da = (x: string) => /^\d+$/.test(x) ? r.has(x) : [...r].some(y => y.startsWith(x.slice(0, Math.max(4, x.length - 2))));
  if (!w.filter(x => /^\d+$/.test(x)).every(da)) return false;
  return w.filter(da).length >= anteil * w.length;
}

export const fehlende = (liste: string[], report: string): string[] => liste.filter(s => !inhaltDa(s, report));

const VERNEINUNG = /(?<![a-zäöüß])(?:kein|keine|keinen|keiner|keines|ohne|nicht)(?![a-zäöüß])/i;
/** Verneint satz etwas, das Peter jetzt als Befund ergänzt hat? Dann ist sein Wegfall gewollt (keine Prüfzeile). */
export function verneintVorrang(s: string, vor: string[]): boolean {
  if (!VERNEINUNG.test(s || '')) return false;
  const vw = new Set(vor.flatMap(woerter).filter(w => !/^\d+$/.test(w)));
  const pre = (x: string) => x.slice(0, Math.max(4, x.length - 2));
  return woerter(s).filter(w => !/^\d+$/.test(w) && w !== 'hinweis' && w !== 'nachweis')
    .some(w => [...vw].some(v => v.includes(pre(w)) || w.includes(pre(v))));   // auch Komposita („Wulstfraktur“)
}

export const pruefzeile = (s: string, ergebnis = false): string =>
  `„${s.length <= 60 ? s : s.slice(0, 59) + '…'}“ ${ergebnis ? 'nicht im Ergebnis' : 'nicht sicher im neuen Befund'} – bitte prüfen`;

/** Vorher als widersprechend entfernte Sätze dürfen nicht wörtlich zurückkommen (nur Befundteil/Text). */
export function streichen(report: string, weg: string[]): string {
  const wegN = new Set(weg.map(vorlageNormalisieren));
  if (!wegN.size) return report;
  const out: string[] = [];
  let sektion: string | null = null;
  for (let z of (report || '').split('\n')) {
    const a = art(z);
    if (a) sektion = a;
    else if (sektion !== 'ergebnis') {
      const vorher = z;
      for (const [x, y] of [...saetzeMitLage(z)].reverse()) {
        if (wegN.has(vorlageNormalisieren(z.slice(x, y)))) {
          const links = z.slice(0, x).trimEnd(), rechts = z.slice(y).trimStart();
          z = links + (links && rechts ? ' ' : '') + rechts;
        }
      }
      if (vorher.trim() && !z.trim()) continue;
    }
    out.push(z);
  }
  return out.join('\n');
}

/** Alle Zeilen unter „## Ergebnis“. */
export function ergebnisText(report: string): string {
  const out: string[] = [];
  let sektion: string | null = null;
  for (const z of (report || '').split('\n')) {
    const a = art(z);
    if (a) sektion = a;
    else if (sektion === 'ergebnis') out.push(z);
  }
  return out.join('\n');
}

/** Vorrang-Angaben mit Pathologie, die im Ergebnis nicht vorkommen. */
export function ergebnisFehlt(vor: string[], report: string): string[] {
  const erg = ergebnisText(report);
  if (!erg.trim()) return [];
  return vor.filter(s => hasPathology(s) && !inhaltDa(s, erg, 0.5));
}
