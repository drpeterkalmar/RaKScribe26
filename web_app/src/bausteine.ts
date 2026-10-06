// Ordinations-Textbausteine (v3.3.0, Peter 06.10.2026): „Baustein Mammo 1“, „Baustein Ösophagus 2“ …
// 1:1-Port von source_code/bausteine.py (EXE). Daten: ordi_bausteine.json (eine Datei für beide Apps).
// Gemeinsame Fälle: ordi_bausteine_tests.json (Repo-Root), Gate tests/offline/test_ordi_bausteine.py (Parität EXE = Web).
import daten from '../../ordi_bausteine.json' with { type: 'json' };

export type Baustein = { gruppe: string; art: 'befund' | 'struktur' | 'satz'; titel: string; befund: string;
  ergebnis: string; text?: string; sprich: string[] };
export type Bausteine = Record<string, Baustein>;
export const ORDI_BAUSTEINE: Bausteine = (daten as unknown as { bausteine: Bausteine }).bausteine;

const ZAHL: Record<string, string> = { '1': 'eins|ein|eine', '2': 'zwei|zwo', '3': 'drei', '4': 'vier', '5': 'fünf|fuenf' };
const UML: [string, string][] = [['ae', '(?:ä|ae)'], ['oe', '(?:ö|oe)'], ['ue', '(?:ü|ue)'], ['ss', '(?:ß|ss)']];
const W = 'a-zäöüß0-9';
const FUELL = new Set(`unauffaellig unauffällig normal normalbefund regelrecht ok o b ob punkt komma ende danke bitte und
rechts links beidseits bds re li seite rechtsseitig linksseitig beidseitig`.split(/\s+/));

const tokenRe = (t: string): string => {
  if (/^\d+$/.test(t)) return '(?:' + t + (ZAHL[t] ? '|' + ZAHL[t] : '') + ')';
  let s = t;
  for (const [a, b] of UML) s = s.split(a).join(b);
  return s;
};
const aliasRe = (alias: string): string => alias.split(' ').map(tokenRe).join('[\\s\\-_.+/]*');

const CACHE = new WeakMap<Bausteine, [string, RegExp][]>();
const muster = (b: Bausteine): [string, RegExp][] => {
  let m = CACHE.get(b);
  if (!m) {
    const paare: [number, number, string, string][] = [];
    for (const [key, x] of Object.entries(b)) for (const a of x.sprich || []) paare.push([a.replace(/ /g, '').length, a.split(' ').length, key, a]);
    // wie Python: längster Alias zuerst (ohne Leerzeichen), dann weniger Wörter, dann Key (Codepoint-Ordnung)
    paare.sort((p, q) => (q[0] - p[0]) || (p[1] - q[1]) || (p[2] < q[2] ? -1 : p[2] > q[2] ? 1 : 0));
    m = paare.map(([, , key, a]) => [key, new RegExp('(^|[^' + W + '])baustein[\\s:,.\\-]*(' + aliasRe(a) + ')(?![' + W + '])', 'gi')]);
    CACHE.set(b, m);
  }
  return m;
};

export const finden = (text: string, b: Bausteine): [number, number, string][] => {
  const treffer: [number, number, string][] = [];
  for (const [key, rx] of muster(b)) {
    rx.lastIndex = 0;
    for (const m of (text || '').matchAll(rx)) {
      const s = (m.index ?? 0) + m[1].length, e = (m.index ?? 0) + m[0].length;
      if (!treffer.some(([ts, te]) => s < te && ts < e)) treffer.push([s, e, key]);
    }
  }
  return treffer.sort((p, q) => p[0] - q[0]);
};

export const saetzeEinsetzen = (text: string, b: Bausteine): string => {
  for (const [s, e, key] of finden(text, b).reverse()) {
    if (b[key].art === 'satz') text = text.slice(0, s) + (b[key].text || '') + text.slice(e);
  }
  return text;
};

const strip = (s: string): string => s.replace(/^[ ,.;:\-\n]+|[ ,.;:\-\n]+$/g, '');
export const befundBaustein = (seg: string, b: Bausteine): [string | null, string] => {
  for (const [s, e, key] of finden(seg, b)) {
    if (b[key].art !== 'satz') return [key, strip(seg.slice(0, s) + ' ' + seg.slice(e))];
  }
  return [null, seg];
};

export const nurBaustein = (rest: string): boolean =>
  ((rest || '').toLowerCase().match(new RegExp('[' + W + ']+', 'g')) || []).every(w => FUELL.has(w));

const seiteVon = (text: string): string | null => {
  const t = (text || '').toLowerCase();
  if (/(?<![a-zäöü])(beidseits|beidseitig|bds)(?![a-zäöü])/.test(t)) return 'beidseits';
  const r = /(?<![a-zäöü])(rechts|rechtsseitig)(?![a-zäöü])/.test(t);
  const l = /(?<![a-zäöü])(links|linksseitig)(?![a-zäöü])/.test(t);
  if (r && !l) return 'rechts';
  if (l && !r) return 'links';
  return null;
};
const seiteTauschen = (txt: string, nach: string): string =>
  txt.replace(new RegExp('(?<![a-zäöü])' + (nach === 'rechts' ? 'links' : 'rechts') + '(?![a-zäöü])', 'g'), nach);

export const vorlage = (key: string, b: Bausteine, diktat = '') => {
  const x = b[key];
  let titel = x.titel || '', befund = x.befund || '', ergebnis = x.ergebnis || '';
  const seite = seiteVon(diktat), eigen = seiteVon(titel);
  if ((seite === 'rechts' || seite === 'links') && (eigen === 'rechts' || eigen === 'links') && seite !== eigen) {
    [titel, befund, ergebnis] = [titel, befund, ergebnis].map(s => seiteTauschen(s, seite));
  } else if (seite && !eigen && !/(?<![a-zäöü])(beidseits|bds\.?)(?![a-zäöü])/i.test(titel)) {
    const m = /\s+in\s+(?:\d|zwei|einer|drei)\b/i.exec(titel);
    titel = m ? titel.slice(0, m.index) + ' ' + seite + titel.slice(m.index) : titel + ' ' + seite;
  }
  return { titel, body: titel + '\n' + befund, display_name: titel, ergebnis: ergebnis || 'Unauffälliger Befund.', befund };
};

export const bericht = (key: string, b: Bausteine, diktat = ''): string => {
  const v = vorlage(key, b, diktat);
  return `## ${v.titel}\n\n## Befund\n${v.befund}\n\n## Ergebnis\n${v.ergebnis}`;
};

export const kiHinweis = (key: string): string =>
  `<ordi_baustein>Die Vorlage ist ein Textbaustein der Ordination (${key}). Übernimm ihren Wortlaut ` +
  'unverändert und ändere oder ergänze NUR, was im Diktat steht. Nicht diktierte Sätze des Bausteins ' +
  'bleiben wörtlich stehen.</ordi_baustein>';
