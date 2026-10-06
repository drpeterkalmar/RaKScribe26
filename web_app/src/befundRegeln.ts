// befundRegeln.ts — deterministische Befund-Regeln der Web-App (v3.2).
// Gleiche Semantik wie source_code/befund_regeln.py (EXE). Beide Engines laufen in
// befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
// IMMER an beiden Stellen + Fixture.
//
//   splitRegionen(text)        Diktat mit ≥2 Regionen → ein Segment je Region (je eigener Befund)
//   ergebnisNummerieren(rep)   Ergebnis-Zeilen ohne Nummer → "1. 2. 3."; einzelner Normalbefund-Satz unnummeriert
//   hasPathology(text)         Pathologie-Stichwort ohne Negation (Normalsatz-Check der Nummerierung);
//                              die Bypass-Entscheidung trifft normalbypass.ts isPureNormalFinding (v3.2)
//   ergebnisMitSeite(e, raw)   Bypass-Ergebnis = Normal-Ergebnis des Templates + diktierte Seite
//   titelMitSeite(t, raw)      Bypass-Überschrift bekommt die diktierte Seite
//   promptVersion / stripPromptMarker   Versionsmarker der gemeinsamen Prompt-Datei radiology_prompt.txt

const W = '[\\p{L}\\p{N}_]';
const NB = `(?<!${W})`; // kein Wortzeichen davor
const NA = `(?!${W})`;  // kein Wortzeichen danach

// ── Prompt-Versionierung ──────────────────────────────────────────────────────
const MARKER_RE = /<!--\s*RAKSCRIBE_PROMPT_VERSION:\s*([\w.-]+)\s*-->[ \t]*\r?\n?/;
export const promptVersion = (text: string): string => (MARKER_RE.exec(text || '') || [])[1] || '';
export const stripPromptMarker = (text: string): string => (text || '').replace(MARKER_RE, '');

// ── Pathologie-Stichworte ─────────────────────────────────────────────────────
const PATHO = [
  "arthrose", "fraktur", "osteo", "spondyl", "tendin", "calcarea", "bursitis",
  "tenosynovitis", "teppich", "ruptur", "luxation", "skoliose", "kyphose",
  "impression", "edgren", "scheuermann", "bi-rads", "morb", "thrombose",
  "mondor", "tumor", "metastas", "entzünd", "ödem", "erguss",
  "verschmäler", "skleros", "osteophyt", "beckenschief", "beinlängen",
  "listhesis", "chondr", "fissur", "kontusion", "depression", "n. ulnaris",
  "anconeus", "epitrochlear", "guyon", "flachbogig", "cobb", "schmorl",
  "patholog", "verdacht", "suspekt", "läsion", "herd", "verkalkung",
  "kalk", "fremdkörper", "emphysem", "infiltrat", "stauung",
  "thromb", "vene", "axillär", "axillar",
];
const NEG = [
  "kein ", "keine ", "keinem ", "keinen ", "keiner ", "kein nachweis",
  "nicht nachweisbar", "nicht vorhanden", "ausschluss", "frei von",
  "ohne nachweis", "ohne patholog", "ohne fraktur", "ohne arthrose",
  "kein hinweis", "keine zeichen", "nicht nachweis",
];

export function hasPathology(text: string): boolean {
  const tl = (text || '').toLowerCase();
  return PATHO.some(kw => {
    const idx = tl.indexOf(kw);
    if (idx === -1) return false;
    const before = tl.substring(Math.max(0, idx - 30), idx);
    return !NEG.some(n => before.includes(n));
  });
}

// ── Seite in der Bypass-Überschrift ───────────────────────────────────────────
const SEITE_IN_TITEL = new RegExp(`${NB}(rechts|links|beidseits|bds\\.?)${NA}`, 'iu');

export function diktierteSeite(raw: string): string {
  const tl = (raw || '').toLowerCase();
  if (new RegExp(`${NB}(beidseits|bds\\.?|beide[nr]?)${NA}`, 'u').test(tl)) return 'beidseits';
  const r = new RegExp(`${NB}rechts${NA}`, 'u').test(tl);
  const l = new RegExp(`${NB}links${NA}`, 'u').test(tl);
  if (r && l) return 'beidseits';
  return r ? 'rechts' : (l ? 'links' : '');
}

export function ergebnisMitSeite(ergebnis: string, raw: string): string {
  const e = (ergebnis || '').trim() || 'Unauffälliger Befund.';
  const seite = diktierteSeite(raw);
  if (!seite || SEITE_IN_TITEL.test(e) || !e.startsWith('Regelrechte Darstellung')
      || new RegExp(`${NB}beide[rnms]?${NA}`, 'iu').test(e)) return e;
  const i = e.indexOf('.');
  return i === -1 ? `${e} ${seite}.` : e.slice(0, i) + ' ' + seite + e.slice(i);
}

export function titelMitSeite(titel: string, raw: string): string {
  const seite = diktierteSeite(raw);
  if (!seite || !titel || SEITE_IN_TITEL.test(titel)) return titel;
  const m = /\s+in\s+(?:\d|zwei|einer|drei)\b/i.exec(titel);
  if (m) return titel.slice(0, m.index) + ' ' + seite + titel.slice(m.index);
  return titel + ' ' + seite;
}

// ── Regionen-Trenner ─────────────────────────────────────────────────────────
export const REGIONEN: [string, string][] = [
  ["schulter", "schulter(?:gelenk)?"],
  ["oberarm", "oberarm|humerus"],
  ["ellbogen", "el(?:l|le)n?bogen(?:gelenk)?"],
  ["unterarm", "unterarm|vorderarm"],
  ["hand", "hand(?:gelenk|wurzel)?|finger|daumen"],
  ["huefte", "hüfte|hüftgelenk"],
  ["oberschenkel", "oberschenkel|femur"],
  ["knie", "knie(?:gelenk)?"],
  ["unterschenkel", "unterschenkel"],
  ["sprunggelenk", "(?:oberes\\s+)?sprunggelenk|osg"],
  ["fuss", "(?:vor|rück|mittel)?fu(?:ß|ss)|großzehe|zehe|calcaneus|kalkaneus|ferse"],
  ["clavicula", "clavicula|klavikula|schlüsselbein"],
];
const REGION_ALT = REGIONEN.map(([, p]) => p).join('|');
const MOD = '(?:(?:röntgen|sonographie|sonografie|ultraschall)\\s+(?:der\\s+|des\\s+|vom\\s+)?)?';
const SEITE = '(?:rechts|links|beidseits|bds\\.?)(?:seitig)?';
const GRENZE = `(?:^|[.!?:;,\\n]|${NB}punkt${NA}|${NB}neue\\s+zeile${NA}|${NB}neuzeile${NA}|${NB}absatz${NA})`;
const MARKER_SRC = GRENZE + '\\s*(' + MOD +
  `(?:(?:(?:der|die|das)\\s+)?(?<s1>rechte[nsmr]?|linke[nsmr]?)\\s+(?<r1>${REGION_ALT})` +
  `|(?<r2>${REGION_ALT})(?:\\s+in\\s+(?:2|zwei)\\s+ebenen)?\\s+(?<s2>${SEITE})))${NA}`;

const gruppe = (wort: string): string => {
  const w = wort.toLowerCase();
  for (const [g, p] of REGIONEN) if (new RegExp(`^(?:${p})$`, 'iu').test(w)) return g;
  return w;
};
const seiteNorm = (s: string): string => {
  const l = s.toLowerCase();
  return l.startsWith('recht') ? 'rechts' : l.startsWith('link') ? 'links' : 'beidseits';
};
const SEG_REST = new RegExp(`(?:\\s*(?:${NB}neue\\s+zeile|${NB}neuzeile|${NB}absatz|[,;]))+\\s*$`, 'iu');

export function splitRegionen(text: string): string[] {
  const t = text || '';
  const starts: { pos: number; key: string }[] = [];
  for (const m of t.matchAll(new RegExp(MARKER_SRC, 'giu'))) {
    const g = m.groups || {};
    const region = g.r1 || g.r2;
    const seite = g.s1 || g.s2;
    const key = gruppe(region) + '|' + seiteNorm(seite);
    const pos = (m.index ?? 0) + m[0].length - m[1].length;
    if (starts.length && starts[starts.length - 1].key === key) continue;
    if (starts.some(s => s.key === key)) continue;
    starts.push({ pos, key });
  }
  if (starts.length < 2) return [t];
  const segs: string[] = [];
  starts.forEach((s, i) => {
    const a = i === 0 ? 0 : s.pos;
    const b = i + 1 < starts.length ? starts[i + 1].pos : t.length;
    const seg = t.slice(a, b).replace(SEG_REST, '').trim();
    if (seg) segs.push(seg);
  });
  return segs.length >= 2 ? segs : [t];
}

// ── Ergebnis-Nummerierung ────────────────────────────────────────────────────
const NUM_RE = /^\s*(?:\*\*)?\s*\d+\s*[.)]\s*(?:\*\*)?\s*/;
const BULLET_RE = /^\s*[-*•–]\s+/;
const UNNUM_RE = /^(?:im\s+)?vergleich\s+zu[rm]?\s+vor/i;
const NORMALSATZ_RE = /(regelrecht|unauffällig|normal|altersentsprechend|ohne pathologisch|kein pathologisch)/i;
const istNormalsatz = (s: string): boolean => NORMALSATZ_RE.test(s) && !hasPathology(s);

function nummeriereBlock(lines: string[]): string[] {
  const items: number[] = [];
  lines.forEach((ln, i) => {
    if (!ln.trim()) return;
    if ((ln[0] === ' ' || ln[0] === '\t') && items.length) return; // eingerückte Fortsetzung bleibt
    items.push(i);
  });
  if (!items.length) return lines;
  const texte = new Map<number, string>();
  for (const i of items) texte.set(i, lines[i].replace(NUM_RE, '').replace(BULLET_RE, '').trim());
  const zaehlbar = items.filter(i => !UNNUM_RE.test(texte.get(i)!));
  const out = [...lines];
  if (zaehlbar.length === 1 && istNormalsatz(texte.get(zaehlbar[0])!)) {
    out[zaehlbar[0]] = texte.get(zaehlbar[0])!;
    return out;
  }
  let n = 0;
  for (const i of items) {
    if (zaehlbar.includes(i)) out[i] = `${++n}. ${texte.get(i)}`;
    else out[i] = texte.get(i)!;
  }
  return out;
}

export function ergebnisNummerieren(report: string): string {
  if (!report || !report.includes('## Ergebnis')) return report;
  const lines = report.split('\n');
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    out.push(lines[i]);
    if (lines[i].trim().startsWith('## Ergebnis')) {
      let j = i + 1;
      while (j < lines.length && !lines[j].trimStart().startsWith('#')) j++;
      out.push(...nummeriereBlock(lines.slice(i + 1, j)));
      i = j;
      continue;
    }
    i++;
  }
  return out.join('\n');
}

export function befundUeberschriftSichern(report: string): string {
  if (!report || !report.includes('## Ergebnis')) return report;
  const out: string[] = [];
  let titelIdx: number | null = null;
  let hatBefund = false;
  for (const ln of report.split('\n')) {
    const st = ln.trim();
    if (st.startsWith('## ')) {
      const kopf = st.slice(3).trim().replace(/:$/, '').toLowerCase();
      if (kopf === 'befund') hatBefund = true;
      else if (kopf === 'ergebnis') {
        if (titelIdx !== null && !hatBefund) out.splice(titelIdx + 1, 0, '', '## Befund');
        titelIdx = null; hatBefund = false;
      } else { titelIdx = out.length; hatBefund = false; }
    }
    out.push(ln);
  }
  return out.join('\n');
}

// v3.2.2 (Skill-Regel 3ac, Georg 05.10.): nicht diktierte Querschnittsflächen raus, CSA nie im Ergebnis.
// Sync: source_code/befund_regeln.py csa_bereinigen (gleiche Regexe, gleiche Fixtures).
export function csaBereinigen(report: string): string {
  if (!report || (!report.includes('CSA') && !report.includes('Querschnittsfläche'))) return report;
  let r = report.replace(/\s*\((?:[^()]*?)\[CSA_[^\]]*\][^()]*\)/g, '');
  r = r.replace(/\s+mit\s+(?:regelrechter|normaler)\s+Querschnittsfläche\s+von\s+\[CSA_[^\]]*\]\s*mm²\s*(?:\([^()]*\))?/g, '');
  // Satz-Einheit: alles außer Punkt/Zeilenende, aber Abkürzungen wie "N. medianus", "Lig." gehören zum Satz
  const u = String.raw`(?:[^.\n]|\b(?:N|n|Nn|M|Mm|Lig|Ligg|ca|bzw)\.|\.\d)`;
  const satz = String.raw`[^.\n\s]` + u + String.raw`*?\[CSA_[^\]]*\]` + u + String.raw`*\.`;
  r = r.replace(new RegExp(String.raw`^[ \t]*` + satz + String.raw`[ \t]*`, 'gm'), '');
  r = r.replace(new RegExp(String.raw`[ \t]*` + satz, 'g'), '');
  const idx = r.indexOf('## Ergebnis');
  if (idx >= 0) {
    const kopf = r.slice(0, idx), erg = r.slice(idx + '## Ergebnis'.length);
    r = kopf + '## Ergebnis' + erg.replace(/,?\s*(?:mit\s+(?:einer\s+)?)?(?:Querschnittsfläche|CSA)[^.,;\n]*?\d+(?:[.,]\d+)?\s*mm²(?:\s*\([^()]*\))?/g, '');
  }
  return r;
}

export const nachbearbeiten = (report: string): string => ergebnisNummerieren(befundUeberschriftSichern(csaBereinigen(report)));

export const befundeZusammenfuegen = (reports: string[]): string =>
  reports.map(r => (r || '').trim()).filter(Boolean).join('\n\n\n');

// ── v3.2.3 (Peter 06.10.: alle Vorlagen erreichbar + korrekt priorisiert) ──────────────────────────────────
// Vorrang-Regeln + Namens-Treffer aus ../../vorlagen_vorrang.json. Sync: source_code/befund_regeln.py vorrang_vorlage.
export type VorrangRegel = { key: string; alle?: string[]; keins?: string[]; bereich?: string };
export type VorrangDaten = { regeln: VorrangRegel[]; fuellwoerter?: string[]; kopf_woerter?: number; name_ausnahmen?: Record<string, string> };

export const vorlageNormalisieren = (text: string): string => {
  let t = (text || '').toLowerCase().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss');
  t = t.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  t = t.replace(/ph/g, 'f');
  t = t.replace(/[^a-z0-9]+/g, ' ');
  return t.trim();
};

const escRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export const vorrangVorlage = (text: string, templates: Record<string, { display_name: string }>, d: VorrangDaten): string | null => {
  let woerter = vorlageNormalisieren(text).split(' ').filter(Boolean);
  const fuell = new Set(d.fuellwoerter || []);
  while (woerter.length && fuell.has(woerter[0])) woerter = woerter.slice(1);
  const voll = woerter.join(' ');
  const kopf = woerter.slice(0, d.kopf_woerter ?? 5).join(' ');
  for (const r of d.regeln || []) {
    if (!(r.key in templates)) continue;
    const ziel = r.bereich === 'text' ? voll : kopf;
    if ((r.alle || []).every(p => new RegExp(p).test(ziel)) && !(r.keins || []).some(p => new RegExp(p).test(voll))) return r.key;
  }
  let best: string | null = null, bestLen = 0;
  const ausnahmen = d.name_ausnahmen || {};
  for (const [key, v] of Object.entries(templates)) {
    const dn = v.display_name || '';
    if (key === 'allgemein' || dn.toLowerCase().includes('(allgemein)')) continue;
    const n = vorlageNormalisieren(dn);
    if (n.split(' ').length < 2 || n.length <= bestLen) continue;
    const m = new RegExp('(?:^| )' + escRe(n) + '(?: |$)').exec(voll);
    if (!m || voll.slice(0, m.index).split(' ').filter(Boolean).length > 2) continue;
    if (key in ausnahmen && new RegExp(ausnahmen[key]).test(voll)) continue;
    best = key; bestLen = n.length;
  }
  return best;
};
