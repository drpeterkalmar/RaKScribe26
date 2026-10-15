// befundRegeln.ts — deterministische Befund-Regeln der Web-App (v3.2).
// Gleiche Semantik wie source_code/befund_regeln.py (EXE). Beide Engines laufen in
// tests/offline/befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
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

// v3.7.4 (Georg 09.10.): Ergebnis-Punkt beginnt groß und endet mit Punkt. Sync: befund_regeln.py satzform
const SATZENDE = /[.!?:;]$/;
const satzanfangGross = (s: string): string => (s && /\p{Ll}/u.test(s[0]) ? s[0].toUpperCase() + s.slice(1) : s);
export const satzform = (s: string): string => {
  let t = s.trimEnd();
  if (!t) return s;
  t = satzanfangGross(t);
  if (!SATZENDE.test(t) && !(t.endsWith('**') && SATZENDE.test(t.slice(0, -2).trimEnd()))) t += '.';
  return t;
};

function nummeriereBlock(lines: string[]): string[] {
  const items: number[] = [];
  lines.forEach((ln, i) => {
    if (!ln.trim()) return;
    if ((ln[0] === ' ' || ln[0] === '\t') && items.length) return; // eingerückte Fortsetzung bleibt
    items.push(i);
  });
  if (!items.length) return lines;
  const texte = new Map<number, string>();
  for (const i of items) texte.set(i, satzanfangGross(lines[i].replace(NUM_RE, '').replace(BULLET_RE, '').trim()));
  const zaehlbar = items.filter(i => !UNNUM_RE.test(texte.get(i)!));
  const out = [...lines];
  if (zaehlbar.length === 1 && istNormalsatz(texte.get(zaehlbar[0])!)) {
    out[zaehlbar[0]] = texte.get(zaehlbar[0])!;
  } else {
    let n = 0;
    for (const i of items) {
      if (zaehlbar.includes(i)) out[i] = `${++n}. ${texte.get(i)}`;
      else out[i] = texte.get(i)!;
    }
  }
  // v3.7.4: Punkt ans Ende jedes Ergebnis-Punkts (bei eingerückter Fortsetzung an deren letzte Zeile)
  items.forEach((i, k) => {
    const ende = k + 1 < items.length ? items[k + 1] : lines.length;
    let letzte = i;
    for (let j = i; j < ende; j++) if (out[j].trim()) letzte = j;
    const einzug = out[letzte].slice(0, out[letzte].length - out[letzte].trimStart().length);
    out[letzte] = einzug + satzform(out[letzte].trimStart());
  });
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

// v3.7.2 (Peter 07.10.: „Mammasono ist eigentlich immer beidseits“) — Sync: befund_regeln.py mammasono_beidseits
const MAMMASONO_TITEL = /^##[ \t]+Mamma[- ]?sono(?:graph|graf)ie\b[^\n]*$/gim;
export const mammasonoBeidseits = (report: string): string => (report || '').replace(MAMMASONO_TITEL, '## Mammasonographie beidseits');

// v3.7.2 (Peter 07.10.): wörtliche Ordi-Bausteine bleiben unnummeriert (nummerieren = false). Sync: befund_regeln.py
export const nachbearbeiten = (report: string, nummerieren = true): string => {
  const r = mammasonoBeidseits(befundUeberschriftSichern(csaBereinigen(report)));
  return nummerieren ? ergebnisNummerieren(r) : r;
};

// ── v3.9.0 (Georg 13.10.): Rho-Textbaustein (opportunistisches Knochendichtescreening, KI-Software Rho) ──────
// Sync: source_code/befund_regeln.py rho_erkennen/rho_einfuegen (gleiche Regexe, gleiche Fixtures „rho“).
export const RHO_BEFUND = 'Opportunistisches Knochendichtescreening mittels CE-zertifizierter, klinisch validierter KI-Software ' +
  '(Rho): {score} eine erhöhte Wahrscheinlichkeit für eine verminderte Knochendichte. Der Score korreliert ' +
  'in Studien eng mit dem DEXA-T-Score, ersetzt diesen jedoch nicht. Da keine Knochendichtemessung aus den ' +
  'letzten 2 Jahren vorliegt, wird eine weiterführende Abklärung mittels DEXA empfohlen.';
export const RHO_ERGEBNIS = 'Opportunistisches Knochendichtescreening auffällig. Abklärung mittels DEXA empfohlen.';
const RHO_NUM = String.raw`(?:[\s:,-]*(?:score|skor|stufe|wert)?[\s:,-]*(?:von\s+)?(\d{1,2})(?!\s*(?:mm|cm|%|grad|°)))?`;
const RHO_SRC = String.raw`(?<![\p{L}\p{N}_-])(?:` +
  String.raw`(?:rho|ro|roh|row)(?:[\s-]*(?:score|skor|stufe))?` + RHO_NUM +
  String.raw`|zus[äa]tzlich(?:e[nrsm]?)?\s+(?:dexa|dxa|dexa-?messung|knochendichtemessung)(?:[\s-]*empfehlung)?(?:\s+empfohlen)?` + RHO_NUM +
  String.raw`|opportunistische[sn]?\s+knochen(?:dichte)?[\s-]*screening(?:[\s-]*(?:auff[äa]llig|positiv))?` + RHO_NUM +
  String.raw`)(?![\p{L}\p{N}_-])(?:\s*(?:punkt|\.))?`;

export function rhoErkennen(seg: string): [string, string, boolean] {
  if (!seg) return [seg, '', false];
  let score = '', gefunden = false;
  for (const m of seg.matchAll(new RegExp(RHO_SRC, 'giu'))) {
    gefunden = true;
    const z = m.slice(1).find(g => g) || '';
    if (z && !score) score = z;
  }
  if (!gefunden) return [seg, '', false];
  let rest = seg.replace(new RegExp(RHO_SRC, 'giu'), ' ');
  rest = rest.replace(/[ \t]{2,}/g, ' ').replace(/\s+([.,;:])/g, '$1');
  rest = rest.replace(/(?:^|(?<=[.,;:]))\s*[.,;:](?=\s|$)/g, '').replace(/^[ ,;:]+|[ ,;:]+$/g, '');
  return [rest || seg, score, true];
}

export function rhoEinfuegen(report: string, score: string): string {
  if (!report || report.includes(RHO_ERGEBNIS)) return report;
  const befund = RHO_BEFUND.replace('{score}', score ? `Der Score von ${score} (Skala 1–10) zeigt` : 'Der Score von ≥7 (Skala 1–10) zeigt');  // Georg 13.10.: ohne diktierten Score immer ≥7
  if (!report.includes('## Ergebnis')) return report.trimEnd() + '\n\n' + befund + '\n\n## Ergebnis\n' + RHO_ERGEBNIS;
  const i = report.lastIndexOf('## Ergebnis');
  const kopf = report.slice(0, i).trimEnd();
  let erg = report.slice(i + '## Ergebnis'.length);
  const zeilen = erg.split('\n').filter(z => z.trim());
  const nummeriert = zeilen.some(z => NUM_RE.test(z));
  erg = erg.trimEnd() + '\n' + RHO_ERGEBNIS;
  const neu = kopf + '\n\n' + befund + '\n\n## Ergebnis' + erg;
  return (nummeriert || zeilen.length <= 1) ? ergebnisNummerieren(neu) : neu;
}

export const befundeZusammenfuegen = (reports: string[]): string =>
  reports.map(r => (r || '').trim()).filter(Boolean).join('\n\n\n');

// ── v3.2.3 (Peter 06.10.: alle Vorlagen erreichbar + korrekt priorisiert) ──────────────────────────────────
// Vorrang-Regeln + Namens-Treffer aus ../../vorlagen_vorrang.json. Sync: source_code/befund_regeln.py vorrang_vorlage.
export type VorrangRegel = { key: string; alle?: string[]; keins?: string[]; bereich?: string };
export type VorrangDaten = { regeln: VorrangRegel[]; fuellwoerter?: string[]; kopf_woerter?: number; name_ausnahmen?: Record<string, string>;
  widersprueche?: WiderspruchDaten };   // v3.15.5

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

// ── v3.15.5 Widerspruchs-Prüfung Pathologie ↔ Normalsatz (Peter 15.10.2026: „Fibroostosen, Exostosen, Spondylosen usw.
// können in praktisch jeder Knochenregion auftreten.“). Katalog + Normalsatz-Merkmale: vorlagen_vorrang.json
// „widersprueche“. Sync: source_code/befund_regeln.py (widerspruch_befunde, widerspruch_saetze, satz_einschraenken,
// widersprueche_bereinigen, widerspruch_prompt) — gleiche Ausgabe Zeichen für Zeichen (tests/offline/widerspruch_matrix_test.py).
export type WiderspruchKategorie = { id: string; name: string; muster: string; ausser?: string; merkmale?: string[];
  gruppen?: string[]; global?: boolean; ergebnis?: string; befund?: string };
export type WiderspruchDaten = { kategorien?: WiderspruchKategorie[]; merkmale?: Record<string, { muster: string; ausser?: string }>;
  strukturen?: Record<string, string>; einschraenkung?: string; verneinung_vor?: string; verneinung_nach?: string; skelett?: string };
export type WiderspruchBefund = { id: string; name: string; phrase: string; gruppen: string[]; global: boolean };
type WidKat = WiderspruchKategorie & { _re: RegExp; _aus: RegExp | null; _bef: RegExp | null };
type WidC = { kat: WidKat[]; merk: Record<string, [RegExp, RegExp | null]>; strukt: [string, RegExp][];
  einschraenkung: RegExp | null; verneinung_vor: RegExp | null; verneinung_nach: RegExp | null; skelett: RegExp | null };

const WID_CACHE = new WeakMap<object, WidC>();
const widC = (d: WiderspruchDaten = {}): WidC => {
  let c = WID_CACHE.get(d);
  if (!c) {
    const rx = (s?: string) => (s ? new RegExp(s, 'u') : null);
    c = {
      kat: (d.kategorien || []).map(k => ({ ...k, _re: new RegExp(k.muster, 'gu'), _aus: rx(k.ausser),
        _bef: k.befund ? new RegExp(k.befund, 'gu') : null })),
      merk: Object.fromEntries(Object.entries(d.merkmale || {}).map(([n, m]) => [n, [new RegExp(m.muster, 'u'), rx(m.ausser)]])),
      strukt: Object.entries(d.strukturen || {}).map(([n, m]) => [n, new RegExp(m, 'u')]),
      einschraenkung: rx(d.einschraenkung), verneinung_vor: rx(d.verneinung_vor), verneinung_nach: rx(d.verneinung_nach),
      skelett: rx(d.skelett),
    };
    WID_CACHE.set(d, c);
  }
  return c;
};

const WID_TRENNER = /[.;,:!?\n]+|(?<![a-zäöüß])(?:punkt|neue zeile|neuzeile|absatz)(?![a-zäöüß])|\s[–-]\s/iu;
const WID_VORSPANN = /^(?:und|sowie|mit|zusätzlich|außerdem|ausserdem|auch|dazu|bei)\s+/iu;
const WID_REGION_SEITE = new RegExp(
  '(?<![a-zäöüß])(?:rechts|links|beidseits|beidseitig|bds|re|li|röntgen|sono[a-zäöüß]*|ultraschall|ct|mrt?|' +
  '(?:knie|hüft|hand|sprung|ellbogen|ellenbogen|schulter|iliosakral|kiefer)(?:gelenk[a-zäöüß]*)?|knie|hüfte|ferse|' +
  'calcaneus|kalkaneus|becken[a-zäöüß]*|[hbl]ws|wirbelsäule|schulter|ellbogen|hand|finger|daumen|fuß|fuss|vorfuß|' +
  'mittelfuß|zehe[a-zäöüß]*|osg|usg|unterschenkel|oberschenkel|oberarm|unterarm|schädel|thorax|clavicula|patella|' +
  'in (?:2|zwei) ebenen|befund)(?![a-zäöüß])', 'giu');
const stripZ = (t: string, z: string): string => {
  let a = 0, e = t.length;
  while (a < e && z.includes(t[a])) a++;
  while (e > a && z.includes(t[e - 1])) e--;
  return t.slice(a, e);
};
const ws = (t: string): string => t.split(/\s+/).filter(Boolean).join(' ');

const widPhrase = (roh: string, start: number): string => {
  const vor = roh.slice(0, start);
  let ende = 0;
  for (const m of vor.matchAll(WID_REGION_SEITE)) ende = (m.index ?? 0) + m[0].length;
  return stripZ(roh.slice(ende), ' ,;:');
};
const widGruppen = (text: string, c: WidC): Set<string> => new Set(c.strukt.filter(([, rx]) => rx.test(text)).map(([n]) => n));

export function widerspruchBefunde(diktat: string, d?: WiderspruchDaten): WiderspruchBefund[] {
  const c = widC(d);
  const out: WiderspruchBefund[] = [];
  for (const teil of (diktat || '').split(WID_TRENNER)) {
    const roh = ws(teil).replace(WID_VORSPANN, '');
    const t = roh.toLowerCase();
    if (!t) continue;
    for (const k of c.kat) {
      if (k._aus && k._aus.test(t)) continue;
      for (const m of t.matchAll(k._re)) {
        const i = m.index ?? 0;
        if (c.verneinung_vor && c.verneinung_vor.test(t.slice(0, i))) continue;
        if (c.verneinung_nach && c.verneinung_nach.test(t.slice(i + m[0].length))) continue;
        const alle = new Set([...widGruppen(t, c), ...(k.gruppen || [])]);
        out.push({ id: k.id, name: k.name, phrase: widPhrase(roh, i) || roh, gruppen: [...alle].sort(),
          global: !!k.global || alle.size === 0 });
        break;
      }
    }
  }
  return out;
}

const WID_TEILSATZ = '.,;:\n';
function widNennt(text: string, k: WidKat, c: WidC, rx?: RegExp): boolean {
  for (const m of text.matchAll(rx || k._re)) {
    const i = m.index ?? 0;
    let a = 0;
    for (let j = i - 1; j >= 0; j--) if (WID_TEILSATZ.includes(text[j])) { a = j + 1; break; }
    let e = text.length;
    for (let j = i + m[0].length; j < text.length; j++) if (WID_TEILSATZ.includes(text[j])) { e = j; break; }
    if (k._aus && k._aus.test(text.slice(a, e))) continue;
    if (c.verneinung_vor && c.verneinung_vor.test(text.slice(a, i))) continue;
    if (c.verneinung_nach && c.verneinung_nach.test(text.slice(i + m[0].length, e))) continue;
    return true;
  }
  return false;
}

// Befund genannt ODER mit seinen Deskriptoren beschrieben (Diagnosen gehören laut Prompt ins Ergebnis)
const widBeschreibt = (text: string, k: WidKat, c: WidC): boolean => widNennt(text, k, c) || (!!k._bef && widNennt(text, k, c, k._bef));

export const istSkelettText = (text: string, d?: WiderspruchDaten): boolean => {
  const rx = widC(d).skelett;
  return !!rx && rx.test((text || '').toLowerCase());
};

const WID_ABK = new Set(['bzw', 'ca', 'z', 'b', 'u', 'a', 'v', 'd', 'h', 'evtl', 'ggf', 'inkl', 'max', 'min', 'lig', 'n', 'nn',
  'm', 'mm', 'li', 're', 'bds', 'vs', 'st', 'p', 'i', 'dr', 'o', 's', 'co', 'e', 'g', 'ap', 'pa', 'bspw', 'usw']);
export function saetzeMitLage(text: string): [number, number][] {
  const t = text || '';
  const out: [number, number][] = [];
  let start = 0;
  for (let i = 0; i < t.length; i++) {
    const ch = t[i];
    if (ch === '\n') {
      if (t.slice(start, i).trim()) out.push([start, i]);
      start = i + 1;
    } else if ('.!?'.includes(ch) && (i + 1 === t.length || ' \n'.includes(t[i + 1]))) {
      const teile = t.slice(start, i).split(/[\s(/]/);
      const wort = stripZ(teile[teile.length - 1].toLowerCase(), '-.');
      if (ch !== '.' || !(WID_ABK.has(wort) || /^[a-zäöü](?:\.-?[a-zäöü])*$/u.test(wort || '-'))) {
        out.push([start, i + 1]);
        start = i + 1;
      }
    }
  }
  if (t.slice(start).trim()) out.push([start, t.length]);
  return out.filter(([a, b]) => t.slice(a, b).trim()).map(([a, b]) => [a + (t.slice(a, b).length - t.slice(a, b).trimStart().length), b]);
}

const WID_GENERISCH = new Set(['gelenk', 'weichteile']);
function widBetrifft(sg: Set<string>, b: WiderspruchBefund): boolean {
  const fg = new Set(b.gruppen);
  if (b.global || sg.size === 0) return true;
  const sgSpez = [...sg].filter(x => !WID_GENERISCH.has(x));
  const fgSpez = [...fg].filter(x => !WID_GENERISCH.has(x));
  const schnitt = (a: string[] | Set<string>, s: Set<string>) => [...a].some(x => s.has(x));
  if (sgSpez.length) return schnitt(sgSpez, new Set(fgSpez)) || (fgSpez.length === 0 && schnitt(sg, fg));
  return schnitt(sg, fg);
}

export function widerspruchSaetze(text: string, befunde: WiderspruchBefund[], d?: WiderspruchDaten): [number, number, string[]][] {
  if (!befunde.length) return [];
  const c = widC(d);
  const kat = new Map(c.kat.map(k => [k.id, k]));
  const out: [number, number, string[]][] = [];
  for (const [a, b] of saetzeMitLage(text || '')) {
    const s = text.slice(a, b).toLowerCase();
    if (c.einschraenkung && c.einschraenkung.test(s)) continue;
    if (befunde.some(x => kat.has(x.id) && widBeschreibt(s, kat.get(x.id)!, c))) continue;
    const sg = widGruppen(s, c);
    const ids: string[] = [];
    for (const x of befunde) {
      const k = kat.get(x.id);
      if (!k) continue;
      const treffer = (k.merkmale || []).some(mn => {
        const rx = c.merk[mn];
        return !!rx && rx[0].test(s) && !(rx[1] && rx[1].test(s));
      });
      if (treffer && widBetrifft(sg, x)) ids.push(x.id);
    }
    if (ids.length) out.push([a, b, ids]);
  }
  return out;
}

const WID_VERB = /^(?:ist|sind|zeigt|zeigen|weist|weisen|stellt|stellen|steht|stehen|liegt|liegen|erscheint|erscheinen|endet|enden|besteht|bestehen|findet|finden|ragt|ragen)$/u;
const WID_KLEIN = new RegExp('^(?:normale?[rsnm]?|normal|regelrechte?[rsnm]?|regelrecht|glatte?[rsnm]?|scharfe?[rsnm]?|' +
  'anatomisch[a-zäöüß]*|ordnungsgemäße?[rsnm]?|keine?[rsnm]?|kein|unauffällige?[rsnm]?|altersentsprechende?[rsnm]?|' +
  'symmetrische?[rsnm]?|achsengerechte?[rsnm]?|allseits|harmonische?[rsnm]?|regulär[a-zäöüß]*|intakte?[rsnm]?|' +
  'gute?[rsnm]?|erhaltene?[rsnm]?|beide[rn]?|die|der|das|den|dem|des|eine?[rsnm]?|sie|es)$', 'iu');
const kleinAnfang = (t: string): string => {
  const w = t.split(' ', 1)[0];
  return WID_KLEIN.test(w.replace(/[,:]+$/u, '')) ? w.charAt(0).toLowerCase() + t.slice(1) : t;
};

export function satzEinschraenken(satz: string): string {
  const t = (satz || '').trim();
  const m = /^([A-ZÄÖÜ][^:.]{0,48}):\s+(\S[\s\S]*)$/u.exec(t);
  if (m && !m[1].split(/\s+/).some(w => WID_VERB.test(w.toLowerCase()))) return `${m[1]}: im Übrigen ${kleinAnfang(m[2])}`;
  const w = t.split(' ');
  for (let i = 1; i < Math.min(13, w.length); i++) {
    if (WID_VERB.test(w[i].toLowerCase())) {
      const subjekt = w.slice(0, i).join(' ');
      return 'Im Übrigen ' + w[i] + ' ' + kleinAnfang(subjekt) + (i + 1 >= w.length ? '' : ' ' + w.slice(i + 1).join(' '));
    }
  }
  return 'Im Übrigen ' + kleinAnfang(t);
}

export function widerspruchPrompt(befunde: WiderspruchBefund[], vorlage: string, d?: WiderspruchDaten): string {
  if (!befunde.length || !istSkelettText(vorlage, d)) return '';
  const saetze = widerspruchSaetze(vorlage, befunde, d);
  if (!saetze.length) return '';
  const diktiert = befunde.map(b => `„${b.phrase}“ (${b.name})`).join('; ');
  const liste = saetze.map(([a, e]) => `„${(vorlage || '').slice(a, e).trim()}“`).join(' ');
  return '<widersprueche>\n' +
    `Diktiert: ${diktiert}.\n` +
    `Diese Sätze der Vorlage widersprechen dem diktierten Befund und dürfen so NICHT stehen bleiben: ${liste}\n` +
    'Regeln: Schränke jeden dieser Sätze nur im betroffenen Teil ein („Im Übrigen …“ bzw. „…, abgesehen von …“) ' +
    'oder lass den betroffenen Teil weg; den übrigen Normaltext der Vorlage übernimmst du wörtlich. Der Befund ' +
    'steht als eigener Satz an der Stelle des betroffenen Normalsatzes. Im Ergebnis steht er als nummerierter ' +
    'Punkt (mit Seite) — nie „Regelrechte Darstellung …“ oder „unauffällig“ für die ganze Untersuchung.\n' +
    '</widersprueche>';
}

const WID_NORMAL_ERG = /regelrechte darstellung|unauffällige[rsn]? (?:befund|darstellung)|ohne pathologischen befund|normalbefund|altersentsprechend unauffällig|regelrechter befund/iu;
const abschnitt = (zeilen: string[], name: string): [number, number][] => {
  const out: [number, number][] = [];
  zeilen.forEach((z, i) => {
    if (z.trim().toLowerCase().replace(/:+$/u, '') === '## ' + name) {
      let j = i + 1;
      while (j < zeilen.length && !zeilen[j].trimStart().startsWith('## ')) j++;
      out.push([i + 1, j]);
    }
  });
  return out;
};
// Sätze, die den diktierten Befund nennen/beschreiben und in derselben Zeile NACH dem ersten eingeschränkten Normalsatz
// stehen — die stellt widersprucheBereinigen vor ihn („Plantarer Fersensporn. Im Übrigen normale Form des Calcaneus …“)
function befundsaetzeDanach(text: string, treffer: [number, number, string[]][], befunde: WiderspruchBefund[],
  kat: Map<string, WidKat>, c: WidC): [number, number][] {
  if (!treffer.length) return [];
  const erste = treffer[0][0];
  const nl = text.indexOf('\n', erste);
  const ende = nl < 0 ? text.length : nl;
  const eingeschraenkt = new Set(treffer.map(([x0, x1]) => `${x0}:${x1}`));
  return saetzeMitLage(text).filter(([a, b]) => erste < a && b <= ende && !eingeschraenkt.has(`${a}:${b}`)
    && befunde.some(x => kat.has(x.id) && widBeschreibt(text.slice(a, b).toLowerCase(), kat.get(x.id)!, c)));
}

const satzAusPhrase = (phrase: string, seite = ''): string => {
  let t = stripZ(ws(phrase || ''), ' ,;:.');
  if (seite && !/(?<![a-zäöüß])(?:rechts|links|beidseits|beidseitig|bds)(?![a-zäöüß])/iu.test(t)) t = `${t} ${seite}`;
  return t ? t.charAt(0).toUpperCase() + t.slice(1) + '.' : '';
};

export function widersprucheBereinigen(report: string, diktat: string, d?: WiderspruchDaten): [string, string[]] {
  const befunde = widerspruchBefunde(diktat, d);
  if (!befunde.length || !report || !report.includes('## Befund')) return [report, []];
  const c = widC(d);
  const kat = new Map(c.kat.map(k => [k.id, k]));
  let zeilen = report.split('\n');
  const aenderungen: string[] = [];
  const seite = diktierteSeite(diktat);
  for (const [a, e] of abschnitt(zeilen, 'befund')) {
    let text = zeilen.slice(a, e).join('\n');
    if (!istSkelettText(text, d)) continue;
    const treffer = widerspruchSaetze(text, befunde, d);
    const vor = befundsaetzeDanach(text, treffer, befunde, kat, c);
    const stuecke: [number, number, string][] = [...treffer.map(([x0, x1]): [number, number, string] => [x0, x1, 'e']),
      ...vor.map(([x0, x1]): [number, number, string] => [x0, x1, 'v'])].sort((x, y) => x[0] - y[0] || x[1] - y[1]);
    const neu: string[] = [];
    let pos = 0, erste: number | null = null;
    for (const [s0, s1, art] of stuecke) {
      const stueck = text.slice(pos, s0);
      if (art === 'v') {                       // Befundsatz: wandert vor den ersten eingeschränkten Satz
        neu.push(stueck.endsWith(' ') ? stueck.slice(0, -1) : stueck);
        aenderungen.push(`vorgezogen: ${text.slice(s0, s1).trim().slice(0, 60)}`);
      } else {
        neu.push(stueck);
        if (erste === null) {
          neu.push(vor.map(([x0, x1]) => text.slice(x0, x1) + ' ').join(''));
          erste = neu.reduce((n, x) => n + x.length, 0);
        }
        neu.push(satzEinschraenken(text.slice(s0, s1)));
        aenderungen.push(`eingeschränkt: ${text.slice(s0, s1).trim().slice(0, 60)}`);
      }
      pos = s1;
    }
    neu.push(text.slice(pos));
    text = neu.join('');
    const fehlend = befunde.filter(b => kat.has(b.id) && !widBeschreibt(text.toLowerCase(), kat.get(b.id)!, c));
    if (fehlend.length) {
      const satz = fehlend.map(b => satzAusPhrase(b.phrase)).join(' ');
      if (erste !== null) text = text.slice(0, erste) + satz + ' ' + text.slice(erste);
      else {
        const anfang = text.length - text.trimStart().length;
        const absatz = text.indexOf('\n\n', anfang);
        const stelle = absatz > 0 ? absatz : text.trimEnd().length;
        text = text.slice(0, stelle).trimEnd() + ' ' + satz + text.slice(stelle);
      }
      aenderungen.push(`Befund ergänzt: ${satz.slice(0, 60)}`);
    }
    zeilen = [...zeilen.slice(0, a), ...text.split('\n'), ...zeilen.slice(e)];
    break;
  }
  for (const [a, e0] of abschnitt(zeilen, 'ergebnis')) {
    let e = e0;
    const inhalt: number[] = [];
    for (let i = a; i < e; i++) if (zeilen[i].trim()) inhalt.push(i);
    const nennt = inhalt.filter(i => befunde.some(b => {
      const k = kat.get(b.id);
      if (!k) return false;
      const z = zeilen[i].toLowerCase();
      return widNennt(z, k, c) || (new RegExp(k.ergebnis || '$^', 'u').test(z) && !WID_NORMAL_ERG.test(zeilen[i]));
    }));
    const normal = inhalt.filter(i => WID_NORMAL_ERG.test(zeilen[i]) && !nennt.includes(i));
    if (normal.length) {
      for (const i of [...normal].reverse()) {
        aenderungen.push(`Ergebnis ohne Normalsatz: ${zeilen[i].trim().slice(0, 60)}`);
        zeilen.splice(i, 1);
      }
      e -= normal.length;
    }
    if (!nennt.length) {
      const punkte = befunde.map(b => satzAusPhrase(b.phrase, seite));
      let stelle = e;
      while (stelle > a && !zeilen[stelle - 1].trim()) stelle--;
      zeilen.splice(stelle, 0, ...punkte);
      aenderungen.push('Ergebnis ergänzt: ' + punkte.map(p => p.slice(0, 40)).join('; '));
    }
    zeilen = ergebnisNummerieren(zeilen.join('\n')).split('\n');
    break;
  }
  return [zeilen.join('\n'), aenderungen];
}
