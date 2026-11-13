// KaiFormat-Maske für die Web-App (kaiscribe-haiku-ab-n1, 13.11.2026) — Port von source_code/ki_maske.py
// (= ~/dev/ris-mods/bruecke/ki_maske.py, Peters Entscheid 03.11.2026: Claude direkt bei Anthropic nur maskiert).
// Gleiche Muster, gleiche Reihenfolge, gleiche Platzhalter ⟦P1⟧ ⟦D1⟧ ⟦N1⟧ ⟦A1⟧ ⟦E1⟧ — tests/offline/test_ki_maske_web.py
// vergleicht beide Seiten Fall für Fall. JS-Unterschiede: \w und \b sind in JS nur ASCII → W/B unten (Unicode wie Python);
// (?i:…) gibt es nicht überall → ci() schreibt die Buchstaben als [xX].

export const KLAMMER_AUF = '⟦';
export const KLAMMER_ZU = '⟧';
export const PLATZHALTER = /⟦[PDNAE]\d+⟧/g;

export class MaskeUnsicher extends Error {}

const W = '[\\p{L}\\p{N}_]';
const B = `(?:(?<=${W})(?!${W})|(?<!${W})(?=${W}))`;
const nfc = (t: string | null | undefined): string => (t || '').normalize('NFC');
const esc = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');   // „-“ nicht: mit u-Flag ungültig
const ci = (s: string): string => s.replace(/\p{L}/gu, c => (c.toLowerCase() === c.toUpperCase() ? c : `[${c.toLowerCase()}${c.toUpperCase()}]`));
const rx = (src: string, flags = ''): RegExp => new RegExp(src.replace(/\\b/g, B), 'gu' + flags);

const MONATE = 'J(?:ä|ae)nner|Januar|Feber|Februar|M(?:ä|ae)rz|April|Mai|Juni|Juli|August|September|Oktober|November|' +
  'Dezember|J(?:ä|ae)n\\.|Jan\\.|Feb\\.|M(?:ä|ae)r\\.|Apr\\.|Jun\\.|Jul\\.|Aug\\.|Sept?\\.|Okt\\.|Nov\\.|Dez\\.';
const JAHR = '(?:19|20)\\d{2}';

const EMAIL = rx(`[\\p{L}\\p{N}_.+-]+@[\\p{L}\\p{N}_-]+(?:\\.[\\p{L}\\p{N}_-]+)+|\\b(?:https?://|www\\.)\\S+`, 'i');

const DATUM = [
  rx('\\b\\d{4}-\\d{1,2}-\\d{1,2}\\b'),
  rx(`(?<![\\d,.])(?:0?[1-9]|[12]\\d|3[01])\\s?\\.\\s?(?:0?[1-9]|1[0-2])\\s?\\.\\s?(?:${JAHR}|\\d{2})(?!\\d|,\\d)`),
  rx('(?<![\\d,.])(?:0?[1-9]|[12]\\d|3[01])\\.(?:0?[1-9]|1[0-2])\\.(?!\\d|,\\d)'),
  rx(`(?<![\\d,./])(?:0?[1-9]|[12]\\d|3[01])/(?:0?[1-9]|1[0-2])/(?:${JAHR}|\\d{2})(?![\\d/])`),
  rx(`(?<![\\d,./])(?:0?[1-9]|1[0-2])\\s?/\\s?${JAHR}(?!\\d)`),
  rx(`(?:(?<![\\d,.])(?:0?[1-9]|[12]\\d|3[01])\\.?\\s*)?\\b(?:${MONATE})(?:(?<=\\.)|\\b)(?:\\s*(?:${JAHR}|\\d{2})(?!\\d))?`, 'i'),
  rx('(?<![\\d,.])(?:19[3-9]\\d|20[0-4]\\d)(?!\\d|,\\d)'),
];

const NUMMER = [
  rx('\\b(?:SV-?Nr|SVNR|VSNR|SV-Nummer|Sozialversicherungs(?:nummer|nr)|Versicherungs(?:nummer|nr)|Vers\\.-?Nr|' +
     'Pat(?:ienten)?\\.?-?(?:Nr|Nummer|ID)|PID|Diktat(?:nummer|-?Nr)?|Untersuchungs(?:nummer|-?Nr)|RH|' +
     'Acc(?:ession)?(?:-?(?:Nr|No|Nummer))?|AccNo|Auftrags(?:nummer|-?Nr)|Befund(?:nummer|-?Nr)|Zl|Akt(?:enzahl)?|' +
     'Fall(?:nummer|-?Nr)|Aufnahmezahl|Nr|No)\\.?\\s*[:.#]?\\s*(\\d[\\d\\s/.-]{0,24}\\d|\\d)', 'i'),
  rx('\\b(?:Tel(?:efon)?|Fax|Handy|Mobil|Mob|Ruf(?:nummer)?)\\.?\\s*[:.]?\\s*(\\+?[\\d(][\\d\\s()/-]{4,}\\d)', 'i'),
  rx('(?<![\\d,.])(\\d{4}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2})(?!\\d|,\\d)'),
  rx('(\\+\\d{1,3}[\\s/-]?(?:\\(0\\))?[\\d\\s/-]{5,}\\d|\\b0\\d{2,4}[\\s/-]\\d{2,}(?:[\\s/-]\\d{2,})*)'),
  rx('(?<![\\d,])(\\d{5,})(?!\\d|,\\d)'),
];

const STRASSE = '(?:' + ['stra(?:ß|ss)e', 'str\\.', 'gasse', 'g\\.', 'weg', 'platz', 'pl\\.', 'allee', 'ring', 'zeile', 'kai',
  'l(?:ä|ae)nde', 'promenade', 'gürtel', 'guertel', 'steig', 'hof', 'siedlung', 'markt', 'berg', 'feld', 'au'].map(ci).join('|') + ')';
const ADRESSE = [
  rx(`\\b(?:[A-ZÄÖÜ][\\p{L}\\p{N}_\\-äöüß.]*?${STRASSE}|Gürtel|Guertel|Ring|Weg|Platz|Kai|Lände|Allee|Gasse|` +
     'Stra(?:ß|ss)e|Zeile|Promenade|Markt)\\s+\\d+[a-zA-Z]?(?:\\s?[/-]\\s?\\d+[a-zA-Z]?)*'),
  rx('\\b(?:A-)?[1-9]\\d{3}\\s+[A-ZÄÖÜ][a-zäöüß]+(?:\\s+(?:an|am|im|bei|ob)\\s+der\\s+[A-ZÄÖÜ][a-zäöüß]+)?\\b'),
];

const TITEL_WORT = '(?:Dr|Prim|Primar(?:ius|ia)?|OA|OÄ|OAe|Oberarzt|Oberärztin|Prof|Univ\\.?-?Prof|Doz|Priv\\.?-?Doz|Mag|DDr|' +
  'Dipl\\.?-?Ing|FA|FÄ|Fachärztin|Facharzt|Frau|Fr|Herrn?|Hr|Kolleg(?:e|en|in)|Zuweiser(?:in)?|Hausarzt|' +
  'Hausärztin|fecit|i\\.\\s?V|med|univ|MSc|PhD|MBA|MAS|Med\\.?-?Rat|OMR|Familie)';
const NAME_TOKEN = "[A-ZÄÖÜ][a-zäöüßéèáàç'’]+(?:-[A-ZÄÖÜ][a-zäöüßéèáàç'’]+)?";
const NACH_TITEL = rx(`\\b${TITEL_WORT}\\.?(?:\\s+${TITEL_WORT}\\.?)*\\s+((?:von\\s+|van\\s+|de\\s+)?${NAME_TOKEN}(?:\\s+${NAME_TOKEN}){0,2})`);
const KEIN_NAME = new Set(['doktor', 'kollegin', 'kollege', 'kollegen', 'patientin', 'patient', 'befund', 'bitte', 'danke', 'dank',
  'med', 'univ', 'prof', 'dr', 'zuweisung', 'zuweiser', 'der', 'die', 'das', 'und', 'mit', 'zur', 'zum',
  'im', 'am', 'vom', 'von', 'nach', 'laut', 'lt', 'befunde', 'befunder', 'befunderin', 'rücksprache',
  'ruecksprache', 'kontrolle', 'verlauf', 'vorbefund', 'vorbefunde', 'untersuchung', 'ordination', 'praxis',
  'spital', 'klinik', 'abteilung', 'station', 'ambulanz', 'röntgen', 'roentgen', 'sonographie', 'mammographie']);
const ZUSATZ = ['von', 'van', 'de', 'zu'];

type Art = 'P' | 'D' | 'N' | 'A' | 'E';

export class Maske {
  namen: string[];
  wertZu = new Map<string, string>();
  zuWert = new Map<string, string>();
  zaehler: Record<Art, number> = { P: 0, D: 0, N: 0, A: 0, E: 0 };

  constructor(namen: string[] = []) {
    this.namen = namenVarianten(namen);
  }

  private ph(art: Art, wert: string): string {
    const schluessel = art + '|' + wert.trim().replace(/\s+/g, ' ').toLowerCase();
    let ph = this.wertZu.get(schluessel);
    if (ph === undefined) {
      this.zaehler[art] += 1;
      ph = `${KLAMMER_AUF}${art}${this.zaehler[art]}${KLAMMER_ZU}`;
      this.wertZu.set(schluessel, ph);
      this.zuWert.set(ph, wert);
    }
    return ph;
  }

  private ersetze(text: string, muster: RegExp, art: Art, gruppe = 0): string {
    return text.replace(muster, (...args) => {
      const m = args[0] as string;
      if (gruppe === 0) return this.ph(art, m);
      const roh = args[gruppe] as string | undefined;
      if (roh === undefined) return m;
      const s = m.length - roh.length;   // die Nummern-Gruppe steht bei allen Mustern am Ende des Treffers
      return m.slice(0, s) + this.ph(art, roh) + m.slice(s + roh.length);
    });
  }

  maskieren(text: string): string {
    let t = nfc(text);
    if (t.includes(KLAMMER_AUF) || t.includes(KLAMMER_ZU)) throw new MaskeUnsicher('Platzhalterzeichen schon im Text');
    for (const v of this.namen) {
      t = t.replace(new RegExp(`(?<![\\p{L}\\p{N}_${KLAMMER_AUF}])${esc(v)}(?![\\p{L}\\p{N}_])`, 'giu'), m => this.ph('P', m));
    }
    t = this.ersetze(t, EMAIL, 'E');
    for (const m of NUMMER.slice(0, 4)) t = this.ersetze(t, m, 'N', 1);
    for (const m of DATUM) t = this.ersetze(t, m, 'D');
    for (const m of ADRESSE) t = this.ersetze(t, m, 'A');
    t = this.ersetze(t, NUMMER[4], 'N', 1);
    t = t.replace(NACH_TITEL, (m0: string, name: string) => this.nameNachTitel(m0, name));
    return t;
  }

  private nameNachTitel(m0: string, name: string): string {
    const keep: string[] = [];
    for (const w of name.split(/\s+/)) {
      if (ZUSATZ.includes(w)) { keep.push(w); continue; }
      if (KEIN_NAME.has(w.toLowerCase().replace(/^\.+|\.+$/g, ''))) break;
      keep.push(w);
    }
    while (keep.length && ZUSATZ.includes(keep[keep.length - 1])) keep.pop();
    if (!keep.length) return m0;
    const n = keep.join(' ');
    const s = m0.length - name.length;   // Name = Gruppe 1 am Ende des Treffers
    return m0.slice(0, s) + this.ph('P', n) + m0.slice(s + n.length);
  }

  restpruefung(texte: string[]): true {
    const alles = texte.map(t => nfc(t).replace(PLATZHALTER, ' ')).join('\n');
    for (const v of this.namen) {
      if (new RegExp(`(?<![\\p{L}\\p{N}_])${esc(v)}(?![\\p{L}\\p{N}_])`, 'iu').test(alles)) throw new MaskeUnsicher('bekannter Name im Text');
    }
    if (/\d{5,}/.test(alles)) throw new MaskeUnsicher('lange Ziffernfolge');
    if (/(?<![\d,])\d{1,2}\.\d{1,2}\.(?:\d{2,4})?(?!\d|,\d)/.test(alles)) throw new MaskeUnsicher('Datumsmuster');
    if (/(?<![\d,])(?:19[3-9]\d|20[0-4]\d)(?!\d|,\d)/.test(alles)) throw new MaskeUnsicher('Jahreszahl');
    if (alles.includes('@')) throw new MaskeUnsicher('E-Mail');
    if (/\d{3,}\s\d{3,}/.test(alles)) throw new MaskeUnsicher('Ziffernblock');
    return true;
  }

  zuruecksetzen(text: string): string {
    return (text || '').replace(PLATZHALTER, m => this.zuWert.get(m) ?? m);
  }
}

const namenVarianten = (namen: string[]): string[] => {
  const out = new Set<string>();
  for (const roh of namen) {
    const n = nfc(String(roh || '')).trim();
    if (!n) continue;
    const teile = [n, ...n.split(/[\s,;/]+/)];
    for (const t of [...teile]) if (t.includes('-')) teile.push(...t.split('-'));
    for (const t0 of teile) {
      const t = t0.replace(/^[ .,'"]+|[ .,'"]+$/g, '');
      if (t.length < 3 || KEIN_NAME.has(t.toLowerCase()) || ['dr', 'med', 'univ', 'prof', 'mag', 'frau', 'herr'].includes(t.toLowerCase())) continue;
      out.add(t);
      out.add(t.replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss').replace(/Ä/g, 'Ae').replace(/Ö/g, 'Oe').replace(/Ü/g, 'Ue'));
    }
  }
  return [...out].sort((a, b) => b.length - a.length);
};
