// befundRegeln.ts — deterministische Befund-Regeln der Web-App (v3.2).
// Gleiche Semantik wie source_code/befund_regeln.py (EXE). Beide Engines laufen in
// tests/offline/befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
// IMMER an beiden Stellen + Fixture.
//
//   splitRegionen(text)        Diktat mit ≥2 Regionen → ein Segment je Region (je eigener Befund)
//   ergebnisNummerieren(rep)   Ergebnis-Zeilen ohne Nummer → "1. 2. 3."; ein einzelner Ergebnispunkt unnummeriert (v3.18.3)
//   hasPathology(text)         Pathologie-Stichwort ohne Negation (Normalsatz-Check der Nummerierung);
//                              die Bypass-Entscheidung trifft normalbypass.ts isPureNormalFinding (v3.2)
//   ergebnisMitSeite(e, raw)   Bypass-Ergebnis = Normal-Ergebnis des Templates + diktierte Seite
//   titelMitSeite(t, raw)      Bypass-Überschrift bekommt die diktierte Seite
//   promptVersion / stripPromptMarker   Versionsmarker der gemeinsamen Prompt-Datei radiology_prompt.txt

// v3.16.6: Kurzsatz-Muster (Empfehlungen/Einschränkungen) aus der gemeinsamen Regel-Datei
import vorrangJson from '../../vorlagen_vorrang.json' with { type: 'json' };

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

// kaiscribe-mehrfach-seitenlos-n1 (Georg 19.11.2026, CAS lws+bü in EINEM Diktat → nur ein LWS-Befund): Regionen ohne Seite
// trennen jetzt auch – nur am Satzanfang (nicht nach Komma) und als eigenes Wort („Fibroostosen am Becken“ trennt nicht).
// Familien mit Kombi-Vorlage trennen untereinander nicht (HWS/BWS/LWS, Becken + Hüfte, Kreuzbein + Steißbein).
// Sync: befund_regeln.py REGIONEN_OHNE_SEITE
export const REGIONEN_OHNE_SEITE: [string, string][] = [
  ["becken", "becken(?:übersicht)?|bü|hüften\\s+(?:beidseits|bds\\.?)|beide\\s+hüften"],
  ["lws", "lws|lendenwirbelsäule"],
  ["bws", "bws|brustwirbelsäule"],
  ["hws", "hws|halswirbelsäule"],
  ["gws", "gws|ganzwirbelsäule|gesamte\\s+wirbelsäule|wirbelsäule\\s+gesamt"],
  ["thorax", "thorax|lunge"],
  ["schaedel", "schädel"],
  ["nnh", "nnh|nasennebenhöhlen"],
  ["abdomen", "abdomen"],
  ["kreuzbein", "kreuzbein|sakrum|sacrum|os\\s+sacrum"],
  ["steissbein", "steißbein|steissbein"],
];
const FAMILIE: Record<string, string> = { lws: 'ws', bws: 'ws', hws: 'ws', gws: 'ws', becken: 'becken', huefte: 'becken',
  kreuzbein: 'sakrum', steissbein: 'sakrum' };
const GRENZE_SATZ = `(?:^|[.!?:;\\n]|${NB}punkt${NA}|${NB}neue\\s+zeile${NA}|${NB}neuzeile${NA}|${NB}absatz${NA})`;
const OHNE_SEITE_SRC = GRENZE_SATZ + '\\s*(' + MOD + '(?:(?:der|die|das|des)\\s+)?(?<r>' +
  REGIONEN_OHNE_SEITE.map(([g, p]) => `(?<o_${g}>${p})`).join('|') + `))${NA}`;
const familie = (key: string): string => {
  const [g] = key.split('|');
  return FAMILIE[g] ?? key;
};

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
  let saetze: [number, number][] | null = null;
  const marker: { pos: number; key: string }[] = [];
  for (const m of t.matchAll(new RegExp(MARKER_SRC, 'giu'))) {
    const g = m.groups || {};
    const region = g.r1 || g.r2;
    const seite = g.s1 || g.s2;
    marker.push({ pos: (m.index ?? 0) + m[0].length - m[1].length, key: gruppe(region) + '|' + seiteNorm(seite) });
  }
  for (const m of t.matchAll(new RegExp(OHNE_SEITE_SRC, 'giu'))) {  // kaiscribe-mehrfach-seitenlos-n1
    const g = REGIONEN_OHNE_SEITE.find(([r]) => m.groups?.['o_' + r])![0];
    marker.push({ pos: (m.index ?? 0) + m[0].length - m[1].length, key: g + '|' });
  }
  marker.sort((a, b) => a.pos - b.pos || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  for (const { pos, key } of marker) {
    if (saetze === null) saetze = diktatSaetze(t);
    if (kurzMarker(t, pos, saetze)) continue;  // v3.16.6: „Fuß rechts in 2 Ebenen empfohlen“ → keine eigene Region
    if (starts.length && starts[starts.length - 1].key === key) continue;
    if (starts.some(s => s.key === key)) continue;
    // HWS + LWS, Becken + Hüfte rechts: Kombi-Vorlage → derselbe Befund
    if (starts.some(s => familie(s.key) === familie(key) && (s.key.endsWith('|') || key.endsWith('|')))) continue;
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
// v3.19.x (Georg 17.11.2026, IB Lab LAMA): Schlussanmerkung „HKA = Hüft-Knie-Sprunggelenk-Winkel, …“ ohne Nummer. Sync: befund_regeln.py
// v3.19.8 (Georg 17.11.2026, IB Lab FROG): ebenso „Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS …“.
// v3.19.13 (Georg 18.11.2026, IB Lab HIPPO): auch „LCE = …“ / „AI = …“ / „CCD = …“. Sync: befund_regeln.py _UNNUM_RE
const UNNUM_RE = /^(?:im\s+)?vergleich\s+zu[rm]?\s+vor|^HKA = Hüft-Knie-Sprunggelenk-Winkel|^Weitere Winkelmessungen sind den KI-Auswertungsbildern|^(?:LCE|AI|CCD) = (?:lateraler Center-Edge|Acetabulumindex|Caput-Collum)|^Anmerkung:/i;  // kaiscribe-georg-2011-n1 (Punkt 9)

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
  if (zaehlbar.length === 1) { // v3.18.3 (Peter 12.11.2026): EIN Ergebnispunkt wird nie nummeriert
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

// kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkte 19/40c/31): Rho IMMER als eigener Einzelbefund ganz am Schluss mit
// eigener Überschrift, eigenem Text und Ergebnis; diktierter Score < 7 → kein Text. Sync: befund_regeln.py
export const RHO_TITEL = 'Opportunistisches Knochendichtescreening (KI)';
export const RHO_AB = 7;
export function rhoEinfuegen(report: string, score: string): string {
  if (!report || report.includes(RHO_ERGEBNIS)) return report;
  if (score && /^\d+$/.test(score) && Number(score) < RHO_AB) return report;
  const befund = RHO_BEFUND.replace('{score}', score ? `Der Score von ${score} (Skala 1–10) zeigt` : 'Der Score von ≥7 (Skala 1–10) zeigt');  // Georg 13.10.: ohne diktierten Score immer ≥7
  return befundeZusammenfuegen([report, `## ${RHO_TITEL}\n\n## Befund\n${befund}\n\n## Ergebnis\n${RHO_ERGEBNIS}`]);
}

export function rhoAnsEnde(report: string): string {
  if (!report || !report.includes(`## ${RHO_TITEL}`)) return report;
  const zeilen = report.split('\n');
  const a = zeilen.findIndex(z => z.trim() === `## ${RHO_TITEL}`);
  let e = a + 1;
  const kopf = (z: string) => { const s = z.trim(); return s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:$/, '')); };
  while (e < zeilen.length && !kopf(zeilen[e])) e++;
  if (e >= zeilen.length) return report;
  const block = zeilen.slice(a, e).join('\n').trim();
  const rest = [...zeilen.slice(0, a), ...zeilen.slice(e)].join('\n').trim().replace(/\n{4,}/g, '\n\n\n');
  return befundeZusammenfuegen([rest, block]);
}

export const befundeZusammenfuegen = (reports: string[]): string =>
  reports.map(r => (r || '').trim()).filter(Boolean).join('\n\n\n');

// ── v3.2.3 (Peter 06.10.: alle Vorlagen erreichbar + korrekt priorisiert) ──────────────────────────────────
// Vorrang-Regeln + Namens-Treffer aus ../../vorlagen_vorrang.json. Sync: source_code/befund_regeln.py vorrang_vorlage.
export type VorrangRegel = { key: string; alle?: string[]; keins?: string[]; bereich?: string };
export type VorrangDaten = { regeln: VorrangRegel[]; fuellwoerter?: string[]; kopf_woerter?: number; name_ausnahmen?: Record<string, string>;
  widersprueche?: WiderspruchDaten; kurzsaetze?: KurzsatzDaten };   // v3.15.5, v3.16.6

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
  gruppen?: string[]; global?: boolean; ergebnis?: string; befund?: string; streichen?: string };
export type WiderspruchDaten = { kategorien?: WiderspruchKategorie[]; merkmale?: Record<string, { muster: string; ausser?: string }>;
  strukturen?: Record<string, string>; strukturen_vorrang?: Record<string, string[]>; einschraenkung?: string; verneinung_vor?: string;
  verneinung_nach?: string; skelett?: string };
export type WiderspruchBefund = { id: string; name: string; phrase: string; gruppen: string[]; global: boolean };
type WidKat = WiderspruchKategorie & { _re: RegExp; _aus: RegExp | null; _bef: RegExp | null; _str: RegExp | null };
type WidC = { kat: WidKat[]; merk: Record<string, [RegExp, RegExp | null]>; strukt: [string, RegExp][]; vorrang: Record<string, string[]>;
  einschraenkung: RegExp | null; verneinung_vor: RegExp | null; verneinung_nach: RegExp | null; skelett: RegExp | null };

const WID_CACHE = new WeakMap<object, WidC>();
const widC = (d: WiderspruchDaten = {}): WidC => {
  let c = WID_CACHE.get(d);
  if (!c) {
    const rx = (s?: string) => (s ? new RegExp(s, 'u') : null);
    c = {
      kat: (d.kategorien || []).map(k => ({ ...k, _re: new RegExp(k.muster, 'gu'), _aus: rx(k.ausser),
        _bef: k.befund ? new RegExp(k.befund, 'gu') : null, _str: rx(k.streichen) })),
      merk: Object.fromEntries(Object.entries(d.merkmale || {}).map(([n, m]) => [n, [new RegExp(m.muster, 'u'), rx(m.ausser)]])),
      strukt: Object.entries(d.strukturen || {}).map(([n, m]) => [n, new RegExp(m, 'u')]), vorrang: d.strukturen_vorrang || {},
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
// Befund-Lage: genauere Struktur verdrängt die gröbere (strukturen_vorrang: AC-Gelenk statt Schulter). Sync: _wid_vorrang.
const widVorrang = (g: Set<string>, c: WidC): Set<string> => {
  for (const [n, weg] of Object.entries(c.vorrang)) if (g.has(n)) for (const x of weg) g.delete(x);
  return g;
};

// v3.18.11 (Echttest 14.11.2026): Chirp-Marken „{Punkt}“, „{Komma}“ … → Satzzeichen, bevor Diktat-Teilsätze wörtlich ins
// Ergebnis kommen (Arthrose-Wächter, Kurzsätze). Ohne „{“/„}“ unverändert. Sync: stt_satzzeichen, Fixtures „stt_satzzeichen“.
const STT_ZEICHEN: Record<string, string> = {
  punkt: '.', komma: ',', doppelpunkt: ':', semikolon: ';', fragezeichen: '?', ausrufezeichen: '!',
  'klammer auf': '(', 'klammer zu': ')', bindestrich: '-', 'schrägstrich': '/',
};
const STT_MARKE = /[ \t]*\{[ \t]*([^{}\n]*?)[ \t]*\}([ \t]*)/g;
export function sttSatzzeichen(text: string): string {
  if (!text || (!text.includes('{') && !text.includes('}'))) return text;
  const t = text.replace(STT_MARKE, (_m, wort: string, nach: string) => {
    const w = ws(wort.replace(/-/g, ' '));
    const z = STT_ZEICHEN[w.toLowerCase()];
    if (z === undefined) return (w ? ' ' + w : '') + nach;
    if (z === '(' || z === '/') return z === '(' ? ' (' : '/';
    return (z === '-' ? ' -' : z) + nach;
  }).replace(/[{}]/g, '');
  return t.replace(/([.,;:!?])\1+/g, '$1');
}

export function widerspruchBefunde(diktat: string, d?: WiderspruchDaten): WiderspruchBefund[] {
  const c = widC(d);
  const out: WiderspruchBefund[] = [];
  for (const teil of (sttSatzzeichen(diktat) || '').split(WID_TRENNER)) {
    const roh = ws(teil).replace(WID_VORSPANN, '');
    const t = roh.toLowerCase();
    if (!t) continue;
    for (const k of c.kat) {
      if (k._aus && k._aus.test(t)) continue;
      for (const m of t.matchAll(k._re)) {
        const i = m.index ?? 0;
        if (c.verneinung_vor && c.verneinung_vor.test(t.slice(0, i))) continue;
        if (c.verneinung_nach && c.verneinung_nach.test(t.slice(i + m[0].length))) continue;
        const alle = new Set([...widVorrang(widGruppen(t, c), c), ...(k.gruppen || [])]);
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
  'm', 'mm', 'li', 're', 'bds', 'vs', 'st', 'p', 'i', 'dr', 'o', 's', 'co', 'e', 'g', 'ap', 'pa', 'bspw', 'usw',
  'dig', 'proc']);  // kaiscribe-georg-2011-n1: „Dig. V“
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
  t = t.replace(/^(?:wie bei|vereinbar mit)\s/iu, 'Bild wie bei ');   // Regel 3q: „Bild wie bei …“
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
    const weg = new Set(treffer.filter(([x0, x1, ids]) => ids.some(i => {
      const r = kat.get(i)?._str;
      return !!r && r.test(text.slice(x0, x1).toLowerCase());
    })).map(([x0, x1]) => `${x0}:${x1}`));
    const stuecke: [number, number, string][] = [...treffer.map(([x0, x1]): [number, number, string] => [x0, x1, 'e']),
      ...vor.map(([x0, x1]): [number, number, string] => [x0, x1, 'v'])].sort((x, y) => x[0] - y[0] || x[1] - y[1]);
    const neu: string[] = [];
    let pos = 0, erste: number | null = null;
    for (const [s0, s1Roh, art] of stuecke) {
      let s1 = s1Roh;
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
        if (weg.has(`${s0}:${s1}`)) {          // verneint den Befund ausdrücklich („keine Luxation“) → streichen
          aenderungen.push(`gestrichen: ${text.slice(s0, s1).trim().slice(0, 60)}`);
          if (text.slice(s1, s1 + 1) === ' ') s1 += 1;
          else if (neu[neu.length - 1].endsWith(' ')) neu[neu.length - 1] = neu[neu.length - 1].slice(0, -1);
        } else {
          neu.push(satzEinschraenken(text.slice(s0, s1)));
          aenderungen.push(`eingeschränkt: ${text.slice(s0, s1).trim().slice(0, 60)}`);
        }
      }
      pos = s1;
    }
    neu.push(text.slice(pos));
    text = neu.join('');
    if (weg.size) text = text.replace(/[ \t]+(?=\n|$)/gu, '');   // nach dem Streichen keine Leerzeichen am Zeilenende
    // kaiscribe-georg-2011-n1 (Georg 20.11.2026, RH 78): Schreibvarianten (c/k/z, femoropatellar↔patellofemoral) zählen als
    // beschrieben, ein schon dastehender Satz wird nie ein zweites Mal angehängt (Sync: befund_regeln.py)
    const fehlend = befunde.filter(b => kat.has(b.id) && !schreibvarianten(text).some(v => widBeschreibt(v, kat.get(b.id)!, c))
      && !phraseVorhanden(b.phrase, text));
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

// ── v3.18.13 Abschnittsprüfung (Peter 14.11.2026: „er hat einen pathologischen befund und einen normalbefund gemeinsam
// geschrieben“, Kanban #314). Je Region: (1) Befunde, die der Abschnitt selbst nennt (Befundteil + Ergebnis) ↔ Normalsätze
// desselben Befundteils (einschränken/streichen, nichts ergänzen); (2) Normalsatz einer fremden Vorlage mit einer Struktur,
// die sonst weder im Titel, Abschnitt noch Diktat vorkommt → weg. Sync: befund_regeln.py abschnitte_bereinigen,
// Fixtures „abschnitte“.
type VorlagenMap = Record<string, { body?: string; display_name?: string } | undefined>;
// Frühere Wortlaute von Vorlagensätzen zählen wie der heutige Satz (kaiscribe-humeruskopf-artikel-n1, Georg 16.11.2026).
// Sync: befund_regeln.py VORLAGEN_ALTFORMEN.
export const VORLAGEN_ALTFORMEN: Record<string, string[]> = {
  'Der Humeruskopf steht in regelrechter Artikulation.': ['Humeruskopf in regelrechter Artikulation.'],
};
const VORLAGEN_SAETZE = new WeakMap<object, [Map<string, Set<string>>, Map<string, Set<string>>]>();
const vorlagenSaetze = (templates: VorlagenMap, d?: WiderspruchDaten): [Map<string, Set<string>>, Map<string, Set<string>>] => {
  let v = VORLAGEN_SAETZE.get(templates);
  if (!v) {
    const w = new Map<string, Set<string>>(), gruppen = new Map<string, Set<string>>();
    const c = widC(d);
    for (const [key, t] of Object.entries(templates)) {
      const body = t?.body || '';
      for (const [a, b] of saetzeMitLage(body)) {
        const n = vorlageNormalisieren(body.slice(a, b));
        if (n) { if (!w.has(n)) w.set(n, new Set()); w.get(n)!.add(key); }
      }
      gruppen.set(key, widGruppen((t?.display_name || key).toLowerCase(), c));
    }
    for (const [neu, alte] of Object.entries(VORLAGEN_ALTFORMEN)) {
      const keys = w.get(vorlageNormalisieren(neu));
      if (!keys) continue;
      for (const alt of alte) {
        const n = vorlageNormalisieren(alt);
        if (!w.has(n)) w.set(n, new Set());
        for (const k of keys) w.get(n)!.add(k);
      }
    }
    v = [w, gruppen];
    VORLAGEN_SAETZE.set(templates, v);
  }
  return v;
};
const ohneGenerisch = (g: Set<string>): Set<string> => new Set([...g].filter(x => !WID_GENERISCH.has(x)));
const schnitt = (a: Set<string>, b: Set<string>): boolean => [...a].some(x => b.has(x));

const regionenBloecke = (zeilen: string[]): [number, number | null, number | null, number | null, number | null][] => {
  const out: { t: number; b: number | null; e: number | null }[] = [];
  zeilen.forEach((z, i) => {
    if (!z.trimStart().startsWith('## ')) return;
    const s = z.trim().toLowerCase().replace(/:+$/u, '');
    if (s === '## befund') { if (out.length) out[out.length - 1].b = i + 1; }
    else if (s === '## ergebnis') { if (out.length) out[out.length - 1].e = i + 1; }
    else out.push({ t: i, b: null, e: null });
  });
  return out.map((x, n) => {
    const ende = n + 1 < out.length ? out[n + 1].t : zeilen.length;
    const be = x.b === null ? null : (x.e !== null && x.e > x.b ? x.e - 1 : ende);
    return [x.t, x.b, be, x.e, x.e === null ? null : ende];
  });
};

export function abschnitteBereinigen(report: string, diktat = '', templates?: VorlagenMap, d?: WiderspruchDaten): [string, string[]] {
  if (!report || !report.includes('## Befund')) return [report, []];
  const c = widC(d);
  const kat = new Map(c.kat.map(k => [k.id, k]));
  const zeilen = report.split('\n');
  const aenderungen: string[] = [];
  const dGruppen = ohneGenerisch(widGruppen(sttSatzzeichen(diktat || '').toLowerCase(), c));
  const [w, vGruppen] = templates ? vorlagenSaetze(templates, d) : [new Map<string, Set<string>>(), new Map<string, Set<string>>()];
  for (const [tI, ba, be, ea, ee] of regionenBloecke(zeilen).reverse()) {
    if (ba === null || be === null) continue;
    let text = zeilen.slice(ba, be).join('\n');
    if (!istSkelettText(text, d)) continue;
    const ergebnis = ea !== null && ee !== null ? zeilen.slice(ea, ee).join('\n') : '';
    const stellen: [number, number, string][] = [];
    // Befunde nur aus Sätzen, die nicht wörtlich aus einer Vorlage stammen (Sync: befund_regeln.py)
    const eigen = !w.size ? text : saetzeMitLage(text).filter(([a, b]) => !w.has(vorlageNormalisieren(text.slice(a, b))))
      .map(([a, b]) => text.slice(a, b)).join(' ');
    const befunde = widerspruchBefunde(klDeskriptorNeutral(eigen) + '\n' + ergebnis, d);
    for (const [x0, x1, ids] of widerspruchSaetze(text, befunde, d)) {
      const weg = ids.some(i => { const r = kat.get(i)?._str; return !!r && r.test(text.slice(x0, x1).toLowerCase()); });
      stellen.push([x0, x1, weg ? 's' : 'e']);
    }
    const tGruppen = ohneGenerisch(widGruppen(zeilen[tI].trim().slice(3).toLowerCase(), c));
    if (w.size && tGruppen.size) {
      const saetze = saetzeMitLage(text);
      const belegt = new Set([...tGruppen, ...dGruppen, ...ohneGenerisch(widGruppen(ergebnis.toLowerCase(), c))]);
      for (const [a, b] of saetze) {
        const keys = w.get(vorlageNormalisieren(text.slice(a, b)));
        if (!keys || [...keys].some(k => schnitt(vGruppen.get(k) || new Set(), tGruppen))) continue;
        const sg = ohneGenerisch(widGruppen(text.slice(a, b).toLowerCase(), c));
        const rest = new Set<string>();
        for (const [a2, b2] of saetze) if (a2 !== a || b2 !== b) for (const x of ohneGenerisch(widGruppen(text.slice(a2, b2).toLowerCase(), c))) rest.add(x);
        if (sg.size && !schnitt(sg, new Set([...belegt, ...rest])) && !stellen.some(([x0, x1]) => x0 <= a && a < x1)) stellen.push([a, b, 'f']);
      }
    }
    if (!stellen.length) continue;
    const neu: string[] = [];
    let pos = 0;
    for (const [s0, s1Roh, art] of [...stellen].sort((x, y) => x[0] - y[0] || x[1] - y[1] || (x[2] < y[2] ? -1 : x[2] > y[2] ? 1 : 0))) {
      let s1 = s1Roh;
      if (s0 < pos) continue;
      neu.push(text.slice(pos, s0));
      if (art === 'e') {
        neu.push(satzEinschraenken(text.slice(s0, s1)));
        aenderungen.push(`eingeschränkt: ${text.slice(s0, s1).trim().slice(0, 60)}`);
      } else {
        aenderungen.push((art === 's' ? 'gestrichen: ' : 'fremder Vorlagensatz weg: ') + text.slice(s0, s1).trim().slice(0, 60));
        if (text.slice(s1, s1 + 1) === ' ') s1 += 1;
        else if (neu[neu.length - 1].endsWith(' ')) neu[neu.length - 1] = neu[neu.length - 1].slice(0, -1);
      }
      pos = s1;
    }
    neu.push(text.slice(pos));
    text = neu.join('');
    if (stellen.some(([, , art]) => art !== 'e')) text = text.replace(/[ \t]+(?=\n|$)/gu, '');
    zeilen.splice(ba, be - ba, ...text.split('\n'));
  }
  return [zeilen.join('\n'), aenderungen];
}

// ── v3.16.6 Kurzsätze (Peter 18.10.2026: „Diktierte Kurzsätze dürfen im Befund nie wegfallen.“) ─────────────────────
// Empfehlungs- und Einschränkungssätze, Muster in vorlagen_vorrang.json „kurzsaetze“ (EINE Quelle für EXE + Web).
// (1) ohneEmpfehlungen: Text für die Vorlagenwahl ohne diese Sätze — „Gehaltene Aufnahmen … empfohlen“ löst nicht die
//     Stress-Vorlage aus (sonst befundet die KI nie gemachte Aufnahmen), „Die Hüfte ist nicht miterfasst“ nicht Becken+Hüfte.
// (2) kurzsaetzeSichern: fehlt nach der KI ein diktierter Empfehlungs-/Einschränkungssatz, kommt er wörtlich zurück.
// Sync: source_code/befund_regeln.py (diktat_saetze, ohne_empfehlungen, kurzsaetze_sichern), Fälle befund_regeln_fixtures.json
// „kurzsaetze“ — gleiche Ausgabe Zeichen für Zeichen.
export type KurzsatzDaten = { empfehlung?: string; einschraenkung?: string; verneinung?: string; anteil?: number; stamm?: number;
  stoppwoerter?: string[]; synonyme?: Record<string, string[]> };
export const KURZSAETZE: KurzsatzDaten = (vorrangJson as { kurzsaetze?: KurzsatzDaten }).kurzsaetze || {};
type KurzC = { empf: RegExp | null; ein: RegExp | null; vern: RegExp | null; stopp: Set<string>; syn: Record<string, string[]>;
  anteil: number; stamm: number };
const KURZ_CACHE = new WeakMap<object, KurzC>();
const kurzC = (d: KurzsatzDaten = KURZSAETZE): KurzC => {
  let c = KURZ_CACHE.get(d);
  if (!c) {
    const rx = (p?: string) => (p ? new RegExp(p, 'u') : null);
    c = { empf: rx(d.empfehlung), ein: rx(d.einschraenkung), vern: rx(d.verneinung), stopp: new Set(d.stoppwoerter || []),
      syn: d.synonyme || {}, anteil: d.anteil ?? 0.5, stamm: d.stamm ?? 5 };
    KURZ_CACHE.set(d, c);
  }
  return c;
};
// Satzgrenzen zusätzlich zu saetzeMitLage: „;“, gesprochenes „Punkt“ …, „12 mm.“ (mm/cm stehen dort als Abkürzung)
const KURZ_GRENZE = /;|(?<![a-zäöüßA-ZÄÖÜ])(?:[pP]unkt|PUNKT|[nN]eue [zZ]eile|[nN]euzeile|[aA]bsatz)(?![a-zäöüßA-ZÄÖÜ])|(?<=[0-9] mm)\.(?=\s)|(?<=[0-9]mm)\.(?=\s)|(?<=[0-9] cm)\.(?=\s)|(?<=[0-9]cm)\.(?=\s)/gu;

// Sätze eines Diktats: wie saetzeMitLage, dazu „;“ und gesprochenes „Punkt“/„neue Zeile“/„Absatz“
export function diktatSaetze(text: string): [number, number][] {
  const t = text || '';
  const out: [number, number][] = [];
  for (const [a, b] of saetzeMitLage(t)) {
    let pos = a;
    for (const m of t.slice(a, b).matchAll(KURZ_GRENZE)) {
      const s = a + (m.index ?? 0);
      if (t.slice(pos, s).trim()) out.push([pos, s]);
      pos = s + m[0].length;
    }
    if (t.slice(pos, b).trim()) out.push([pos, b]);
  }
  return out.map(([a, b]) => {
    const st = t.slice(a, b);
    return [a + (st.length - st.trimStart().length), a + st.trimEnd().length] as [number, number];
  });
}

const teilsaetze = (t: string, a: number, b: number): [number, number][] => {
  const out: [number, number][] = [];
  let pos = a;
  for (let i = a; i < b; i++) if (t[i] === ',') { out.push([pos, i]); pos = i + 1; }
  out.push([pos, b]);
  return out.filter(([x, y]) => t.slice(x, y).trim());
};

const kurzTreffer = (t: string, c: KurzC): [number, number, string][] => {
  const out: [number, number, string][] = [];
  diktatSaetze(t).forEach(([a, b], i) => {
    const s = t.slice(a, b).toLowerCase();
    if (c.empf && c.empf.test(s)) {
      const teile = teilsaetze(t, a, b);
      if (i === 0) {  // Satz 1 nennt die Untersuchung: nur Teilsätze nach dem ersten Komma
        for (const [x, y] of teile.slice(1)) if (c.empf.test(t.slice(x, y).toLowerCase())) out.push([x, y, 'e']);
      } else out.push([a, b, 'e']);
      return;
    }
    if (c.ein && c.ein.test(s)) {
      teilsaetze(t, a, b).forEach(([x, y], j) => {
        if ((i || j) && c.ein!.test(t.slice(x, y).toLowerCase())) out.push([x, y, 'n']);
      });
    }
  });
  return out;
};

// Steht die Regionsnennung an pos in einem Empfehlungs- oder Einschränkungs-Teilsatz (ab pos bis zum Komma)?
const kurzMarker = (t: string, pos: number, saetze: [number, number][], d: KurzsatzDaten = KURZSAETZE): boolean => {
  const c = kurzC(d);
  for (const [a, b] of saetze) {
    if (a <= pos && pos < b) {
      for (const [x, y] of teilsaetze(t, a, b)) {
        if (x <= pos && pos < y) {
          const s = t.slice(pos, y).toLowerCase();
          return !!((c.empf && c.empf.test(s)) || (c.ein && c.ein.test(s)));
        }
      }
    }
  }
  return false;
};

// Text für die Vorlagenwahl ohne Empfehlungssätze und Einschränkungs-Teilsätze; ohne solche Sätze unverändert
export function ohneEmpfehlungen(text: string, d: KurzsatzDaten = KURZSAETZE): string {
  const t = text || '';
  const treffer = kurzTreffer(t, kurzC(d));
  if (!treffer.length) return text;
  const neu: string[] = [];
  let pos = 0;
  for (const [a, b] of [...treffer].sort((x, y) => x[0] - y[0] || x[1] - y[1])) {
    neu.push(t.slice(pos, a));
    pos = Math.max(pos, b);
  }
  neu.push(t.slice(pos));
  const rest = neu.join('');
  return rest.trim() ? rest : text;
}

const kurzWoerter = (t: string): string[] => vorlageNormalisieren(t).split(' ').filter(Boolean);
const kurzInhalt = (t: string, c: KurzC): string[][] =>
  kurzWoerter(t).filter(w => (w.length >= 3 || w in c.syn) && !c.stopp.has(w) && !/^\d+$/.test(w))
    .map(w => [w.slice(0, c.stamm), ...(c.syn[w] || [])]);

const kurzVorhanden = (einheit: string, art: string, rsaetze: string[], c: KurzC): boolean => {
  const inhalt = kurzInhalt(einheit, c);
  const rx = art === 'e' ? c.empf : c.ein;
  if (!inhalt.length) return rsaetze.some(s => !!rx && rx.test(s.toLowerCase()));
  const noetig = Math.max(1, Math.ceil(inhalt.length * c.anteil));
  for (const s of rsaetze) {
    const ws = kurzWoerter(s);
    const hits = inhalt.filter(alt => ws.some(w => alt.some(a => w.startsWith(a)))).length;
    const low = s.toLowerCase();
    if (art === 'e') {
      if (hits >= noetig || (hits && rx && rx.test(low))) return true;
    } else if (hits >= noetig && c.vern && c.vern.test(low)) return true;
  }
  return false;
};

const KURZ_WEICHTEIL = /weichteil|weichgewebe|subkutan|subcutan|hautmantel/iu;
const befundEinfuegen = (zeilen: string[], a: number, e: number, satz: string): void => {
  const inhalt: number[] = [];
  for (let i = a; i < e; i++) if (zeilen[i].trim() && !zeilen[i].trimStart().startsWith('#')) inhalt.push(i);
  if (!inhalt.length) { zeilen.splice(e, 0, satz); return; }
  const i = inhalt[inhalt.length - 1];
  const z = zeilen[i];
  const lage = saetzeMitLage(z);
  if (lage.length && KURZ_WEICHTEIL.test(z.slice(lage[lage.length - 1][0], lage[lage.length - 1][1]))) {
    const s0 = lage[lage.length - 1][0];
    if (z.slice(0, s0).trim()) zeilen[i] = z.slice(0, s0) + satz + ' ' + z.slice(s0);
    else if (inhalt.length > 1) { const j = inhalt[inhalt.length - 2]; zeilen[j] = zeilen[j].trimEnd() + ' ' + satz; }
    else zeilen.splice(i, 0, satz);
    return;
  }
  zeilen[i] = z.trimEnd() + ' ' + satz;
};
const ergebnisZeile = (zeilen: string[]): number => zeilen.findIndex(z => z.trim().toLowerCase().replace(/:+$/u, '') === '## ergebnis');

// Nach der KI (EXE + Web gleich): fehlt ein diktierter Empfehlungssatz → wörtlich als letzter Ergebnis-Punkt; fehlt eine
// diktierte Einschränkung („die BWS ist nicht abgebildet“) → wörtlich als Befundsatz vor dem Weichteil-Satz.
export function kurzsaetzeSichern(report: string, diktat: string, d: KurzsatzDaten = KURZSAETZE): [string, string[]] {
  if (!report || !report.includes('## Ergebnis')) return [report, []];
  const c = kurzC(d);
  const dk = sttSatzzeichen(diktat || '');   // v3.18.11: Chirp-Marken nie wörtlich ins Ergebnis
  const treffer = kurzTreffer(dk, c);
  if (!treffer.length) return [report, []];
  const zeilen = report.split('\n');
  const rtext = zeilen.filter(z => !z.trimStart().startsWith('#')).join('\n');
  const rsaetze = saetzeMitLage(rtext).map(([a, b]) => rtext.slice(a, b));
  const satzLage = diktatSaetze(dk);
  const neuErg: string[] = [], neuBef: string[] = [];
  for (const [a, b, art] of treffer) {
    let einheit = dk.slice(a, b);
    if (kurzVorhanden(einheit, art, rsaetze, c)) continue;
    if (art === 'n' && !kurzInhalt(einheit, c).length) {  // „eingeschränkt beurteilbar“ allein → ganzer Satz
      const s = satzLage.find(([x, y]) => x <= a && a < y);
      if (s) einheit = dk.slice(s[0], s[1]);
    }
    const satz = satzform(stripZ(ws(einheit), ' ,;:'));
    if (satz && !neuErg.includes(satz) && !neuBef.includes(satz)) (art === 'e' ? neuErg : neuBef).push(satz);
  }
  if (!neuErg.length && !neuBef.length) return [report, []];
  if (neuBef.length) {
    const bef = abschnitt(zeilen, 'befund');
    let a = 0, e = ergebnisZeile(zeilen);
    if (bef.length) [a, e] = bef[0];
    for (const s of neuBef) {
      befundEinfuegen(zeilen, a, e, s);
      e = ergebnisZeile(zeilen);
    }
  }
  let out: string;
  if (neuErg.length) {
    const erg = abschnitt(zeilen, 'ergebnis');
    const [a, e] = erg[erg.length - 1];
    let stelle = e;
    while (stelle > a && !zeilen[stelle - 1].trim()) stelle--;
    zeilen.splice(stelle, 0, ...neuErg);
    out = ergebnisNummerieren(zeilen.join('\n'));
  } else out = zeilen.join('\n');
  return [out, [...neuBef.map(s => 'Befund ergänzt: ' + s), ...neuErg.map(s => 'Ergebnis ergänzt: ' + s)]];
}

// ── v3.18.4 Kellgren-&-Lawrence-Wächter (Peter 12.11.2026, RH 38: „KaiScribe konfabuliert noch zu viel“) ──────────
// Ein K&L-Grad steht nur, wenn er diktiert ist oder aus einem IB-Lab-Baustein kommt (nur EXE) — nie aus dem Wortlaut.
// Nach der KI: Grad-Angaben ohne Deckung → bei genau einem erlaubten Grad eingesetzt, sonst entfernt (Diagnose bleibt).
// Sync: source_code/befund_regeln.py (kl_grade, kl_bereinigen), Fixtures befund_regeln_fixtures.json „kl“.
// K&L-Deskriptor-Tabelle (freigegeben Georg/Peter, = befund_regeln.KL_TABELLE, Gen-Prompt Abschnitt ARTHROSE)
export const KL_TABELLE: Record<number, string> = {
  0: 'Unauffälliger Gelenksspalt, keine Osteophyten.',
  1: 'Geringe Osteophytenbildung, fragliche Gelenksspaltverschmälerung.',
  2: 'Geringe Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer Randzuschärfung.',
  3: 'Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung.',
  4: 'Aufgehobener Gelenksspalt mit ausgeprägter subchondraler Sklerosierung, Zystenbildung und ausgeprägten Osteophyten.',
};
// Für die Befund-Erkennung der Widerspruchs-Wächter ist ein Tabellensatz die Arthrose selbst (Georg 18.11.2026, Nr. 34)
const KL_TAB_RE = new RegExp(Object.entries(KL_TABELLE).filter(([g]) => g !== '0').map(([, s]) => s.slice(0, -1))
  .sort((a, b) => b.length - a.length).map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'gi');

export function klDeskriptorNeutral(text: string): string {
  return (text || '').replace(KL_TAB_RE, 'Gelenkspaltverschmälerung');
}

const KL_G = String.raw`(?:[0-4]|IV|III|II|I|null|eins|zwei|drei|vier)`;
const KL_G_KI = String.raw`(?:[0-4]|IV|III|II|I|null|eins|zwei|drei|vier|X)`;  // KI-Ausgabe: auch der Platzhalter „Grad X“
const KL_WERT: Record<string, string> = { '0': '0', null: '0', '1': '1', i: '1', eins: '1', '2': '2', ii: '2', zwei: '2',
  '3': '3', iii: '3', drei: '3', '4': '4', iv: '4', vier: '4' };
const KL_NAME = String.raw`kellgren(?:[\s-]*(?:&|und)?[\s-]*lawrence)?`;
const KL_SEITE = String.raw`(?:\s*(?:links|rechts|beidseits))?`;
const KL_TEXT = new RegExp(
  String.raw`(?<![\wäöüß])grad\s+(` + KL_G + String.raw`)\s+nach\s+` + KL_NAME +
  String.raw`|(?<![\wäöüß])` + KL_NAME + String.raw`(?:[\s-]*(?:grad|grade|score|stadium))?` + KL_SEITE + String.raw`\s*:?\s*(` + KL_G +
  String.raw`)(?![\wäöüß])` +
  String.raw`|(?<![\wäöüß])(?:kl|k\s*&\s*l)(?:[\s-]*(?:grad|grade))?` + KL_SEITE + String.raw`\s*:?\s*(` + KL_G + String.raw`)(?![\wäöüß])`,
  'gi');
const KL_KI = new RegExp(
  String.raw`\s*\(\s*(?:Arthrose\s+)?Grad\s+(` + KL_G_KI + String.raw`)\s+nach\s+Kellgren(?:\s*(?:&|und)\s*Lawrence)?\s*\)` +
  String.raw`|,?\s*(?:Arthrose\s+)?Grad\s+(` + KL_G_KI + String.raw`)\s+nach\s+Kellgren(?:\s*(?:&|und)\s*Lawrence)?`, 'gi');
// v3.18.5 (Nachtrag RH 99): Arthrose-Wort im Diktat, auch als Verhörer; Grad-Adjektiv direkt vor einer diktierten Arthrose
const ARTHROSE_DIKTAT = /th?ros|rthrot|rtrot/i;
const KL_ADJ: [string, string][] = [['1', String.raw`beginnend\w*|initial\w*|minimal\w*`], ['2', String.raw`gering\w*|leicht\w*`],
  ['3', String.raw`m[äa]ß\w*|mittelgradig\w*`], ['4', String.raw`hochgradig\w*|ausgeprägt\w*|schwer\w*`]];
const KL_ADJ_RE = new RegExp(String.raw`(?<![\wäöüß])(` + KL_ADJ.map(([, r]) => r).join('|') + String.raw`)\s+(?:[\wäöüß-]+\s+){0,2}?` +
  String.raw`[\wäöüß-]*(?:th?ros|rthrot|rtrot)`, 'gi');

export function arthroseDiktiert(diktat: string): boolean {
  return ARTHROSE_DIKTAT.test(diktat || '');
}

const FEMOROPATELLAR = /patell|femoropat/i;

export function klAdjektivGrade(diktat: string, femoropatellar = false): string[] {
  const out = new Set<string>();
  for (const m of (diktat || '').matchAll(KL_ADJ_RE)) {
    if (femoropatellar && !FEMOROPATELLAR.test(m[0])) continue;
    for (const [g, r] of KL_ADJ) if (new RegExp('^(?:' + r + ')$', 'i').test(m[1])) out.add(g);
  }
  return [...out].sort();
}

export function klGrade(text: string): string[] {
  const out = new Set<string>();
  for (const m of (text || '').matchAll(KL_TEXT)) {
    const g = m.slice(1).find(x => x) as string;
    out.add(KL_WERT[g.toLowerCase()]);
  }
  return [...out].sort();
}

export function klBereinigen(report: string, diktat: string, erlaubt: string[] = []): [string, string[]] {
  if (!report || !/kellgren/i.test(report)) return [report, []];
  const d = klGrade(diktat);
  const e = [...new Set(erlaubt)].sort();
  // kaiscribe-kl-tabelle-zurueck-n1 (Georg 18.11.2026, Nr. 50): IB-Lab-Grad (KOALA, femorotibial) vor Adjektiv, daneben
  // der Adjektiv-Grad einer diktierten Femoropatellar-Arthrose
  const ok = d.length ? d : e.length ? [...new Set([...e, ...klAdjektivGrade(diktat, true)])].sort() : klAdjektivGrade(diktat);
  const aend: string[] = [];
  const ersetzen = (m0: string, g1?: string, g2?: string): string => {
    const g = KL_WERT[(g1 || g2 || '').toLowerCase()] ?? 'X';
    if (ok.includes(g)) return m0;
    if (ok.length === 1) {
      aend.push(`K&L-Grad ${g} → ${ok[0]}`);
      return m0.replace(new RegExp(KL_G_KI + String.raw`(?=\s+nach)`, 'i'), ok[0]);
    }
    if (ok.length && g !== 'X') {
      aend.push(`K&L-Grad ${g} nicht diktiert (diktiert/IB Lab: ${ok.join(', ')}) – stehen gelassen`);
      return m0;
    }
    aend.push(`K&L-Grad ${g} ohne Diktat/IB Lab entfernt`);
    return '';
  };
  const zeilen = report.split('\n').map(z =>
    z.includes('(IB Lab') || !z.toLowerCase().includes('kellgren') ? z : z.replace(KL_KI, ersetzen));
  return [zeilen.join('\n'), aend];
}

// ── v3.18.5 Arthrose-Wächter (Peter 12.11.2026, Nachtrag RH 99: Becken + HIPPO-Messwerte, keine Arthrose diktiert →
// „Coxarthrose (Kellgren & Lawrence Grad 3) beidseits“). Ohne Arthrose-Wort im Diktat fallen Ergebnis-Punkte weg, die eine
// Arthrose positiv nennen; verneinte Nennungen und IB-Lab-Zeilen bleiben. Sync: befund_regeln.py arthrose_bereinigen.
const ARTHROSE_KI = /arthros|arthrot/i;
const VERNEINT = /(?<![\wäöüß])(?:kein\w*|ohne|nicht|frei von)(?![\wäöüß])/i;

export function arthroseBereinigen(report: string, diktat: string, d?: WiderspruchDaten): [string, string[]] {
  if (!report || !report.includes('## Ergebnis') || arthroseDiktiert(diktat) || !ARTHROSE_KI.test(report)) return [report, []];
  const zeilen = report.split('\n');
  const aend: string[] = [];
  const raus = new Set<number>();
  const erg = new Set<number>();
  let imErg = false;
  zeilen.forEach((z, i) => {
    if (z.trim().startsWith('## ')) { imErg = z.trim().startsWith('## Ergebnis'); return; }
    if (imErg) erg.add(i);
    const ohneKl = z.replace(KL_KI, '');   // erlaubte K&L-Klammer (IB Lab) ist keine Arthrose-Diagnose
    if (!imErg || z.includes('(IB Lab') || !ARTHROSE_KI.test(ohneKl)) return;
    const vor = ohneKl.slice(0, ohneKl.search(ARTHROSE_KI));
    if (VERNEINT.test(vor)) return;
    raus.add(i);
    aend.push('Arthrose ohne Diktat entfernt: ' + z.replace(/^\s*\d+\.\s*/, '').trim());
  });
  if (!raus.size) return [report, []];
  // kaiscribe-konfab-regress-n1 (13.11.2026, RH 99 „Beginnende degenerative Veränderungen … mit kleinen Randanbauten“ →
  // KI „Beginnende Coxarthrose rechts“ → Ergebnis leer): an die Stelle des entfernten Punkts tritt der DIKTIERTE
  // degenerative Befund (Katalog „arthrose“ der Widerspruchs-Regeln), wenn das Ergebnis ihn nicht schon nennt
  const rest = [...erg].filter(i => !raus.has(i)).sort((a, b) => a - b).map(i => zeilen[i]).join(' ').toLowerCase();
  const statt = [...new Set(widerspruchBefunde(diktat, d).filter(b => b.id === 'arthrose').map(b => satzAusPhrase(b.phrase)))]
    .filter(s => s && !rest.includes(s.slice(0, -1).toLowerCase()));
  const erste = Math.min(...raus);
  const neu: string[] = [];
  zeilen.forEach((z, i) => {
    if (i === erste) neu.push(...statt);
    if (!raus.has(i)) neu.push(z);
  });
  aend.push(...statt.map(s => `diktierter Befund statt Arthrose: ${s}`));
  return [ergebnisNummerieren(neu.join('\n')), aend];
}

// ── kaiscribe-georg-2011-n1 (Georg Riegler 20.11.2026, Diktiertag) ─────────────────────────────────────────────────────
// Grundregeln nach allen anderen Wächtern: Befund beginnt nie mit „Im Übrigen/Ansonsten“ (7/14b/21a/32), Pleuraerguss →
// Sinus-Satz raus + „Ansonsten das Zwerchfell beidseits glatt begrenzt.“ (10), Widerspruchsregel 14a/18/37b/40a, diktierte
// Abstufung „skoliotische Asymmetrie“ (20), KI-Hinweise nie im Ergebnis (21b), „SI-Gelenksarthrose“ (38), Wirbelsäule ohne
// K&L-Grad (42). Sync: source_code/befund_regeln.py grundregeln, Fixtures „georg_2011“.
export const UEBRIGEN_ANFANG = /^(Im [Üü]brigen|Ansonsten)\b,?\s+/u;
const STELLUNG_PATHO = /fraktur|luxation|fehlstellung|disloz|dislokation|hochstand|skolio|listhes|dissoziation|achsabweich|achsfehl|seitausbieg|kontinuitätsunterbrech|fragment|valgus|varus|fehlhaltung|streckhaltung|beckenschiefstand|abkippung|versatz/u;
const NEG_NAH = /(?<![a-zäöüß])(?:kein[a-zäöüß]*|ohne|nicht|ausschluss|frei von)(?![a-zäöüß])/u;
const WS_TITEL = /wirbelsäule|halswirbel|brustwirbel|lendenwirbel|(?<![a-zäöüß])(?:hws|bws|lws|gws)(?![a-zäöüß])/iu;
const THORAX_TITEL = /thorax|lunge/iu;
export const GEORG_STREICHEN: [string, string, RegExp | null, string[]][] = [
  ['humeruskopfhochstand', 'hochstand des humeruskopf|humeruskopf[a-zäöüß]*hochstand|humeruskopf[a-zäöüß ]{0,25}hochstand|schulterhochstand|kopfhochstand', null,
    ['humeruskopf[^.]*regelrechte[rn]? artikulation']],
  ['infiltrat', 'infiltrat', null, ['(?<![a-zäöüß])kein(?:e[nmrs]?)?(?![a-zäöüß])[^.]*infiltrat']],
  ['beckenschiefstand', 'beckenschiefstand|beckenkippung|beckenhochstand|becken[a-zäöüß ]{0,15}schief', null,
    ['symmetrische form des beckenskelett', 'becken(?:schaufeln|kämme)[^.]*gleich ?hoch']],
  ['skoliose', 'skolio|seitausbieg|cobb', WS_TITEL,
    ['^(?:(?:im übrigen|ansonsten),?\\s+)?normaler achsenverlauf', '^(?:(?:im übrigen|ansonsten),?\\s+)?(?:annähernd\\s+)?achsengerechte stellung']],
];
const GEORG_RX = GEORG_STREICHEN.map(([i, w, t, ss]) => [i, new RegExp(w, 'u'), t, ss.map(x => new RegExp(x, 'u'))] as const);
const KEINE_SKOLIOSE = /keine skoliose|kein[a-zäöüß]* (?:hinweis auf|nachweis einer?) skoliose/u;
const PLEURA = /pleuraerg(?:u|ü)(?:ss|ß)|pleuraeffusion|erg(?:u|ü)ss[a-zäöüß ]{0,20}pleura/u;
const ERGUSS_SATZ = /erg(?:u|ü)(?:ss|ß)|stumpf|randwinkel|winkelerguss/u;
const SINUS_FREI = /(?<![a-zäöüß])sinus(?![a-zäöüß])[^.]*(?<![a-zäöüß])frei(?![a-zäöüß])/u;
const ZWERCHFELL_NORMAL = /^(?:(?:im übrigen|ansonsten),?\s+)?(?:das\s+|beide\s+)?zwerchfell[a-zäöüß]*[^.]*(?:normaler lage|scharf|glatt)/u;
export const ZWERCHFELL_ANSONSTEN = 'Ansonsten das Zwerchfell beidseits glatt begrenzt.';
const KI_PUNKT = /^\s*(?:\d+\s*[.)]\s*)?(?:KI\s*[:(-]|\(KI\)|RBfracture\b)/iu;
const SI_ARTHROSE = /(?<![\p{L}\p{N}_-])(?:ISG|SIG|SI|Iliosakral|Iliosacral|Sakroiliakal|Sacroiliacal)(?:[- ]?[Gg]elenk(?:s|e)?)?[- ]?[Aa]rthrose(n?)(?![\p{L}\p{N}_])/gu;
const KL_KLAMMER_WS = /\s*\((?:Arthrose\s+)?Grad\s+(?:\d|[IVX]+)\s+nach\s+Kellgren[^)]*\)/gu;
const SKOL_ABSTUFUNG = /skoliotische[a-zäöüß]*\s+(asymmetrie|fehlhaltung|haltung|seitabweichung)/u;
const SKOLIOSE_WORT = /(?<![\p{L}\p{N}_])Skoliose(?![\p{L}\p{N}_])/gu;

const bejaht = (text: string, rx: RegExp): boolean => {
  for (const m of (text || '').matchAll(new RegExp(rx.source, 'gu'))) {
    const vor = text.slice(Math.max(0, m.index! - 60), m.index!).split(/[.;:,\n]/u).pop()!;
    if (!NEG_NAH.test(vor)) return true;
  }
  return false;
};

const satzWeg = (text: string, a: number, b: number): string => {
  let vor = text.slice(0, a), nach = text.slice(b);
  if (nach.startsWith(' ')) nach = nach.slice(1);
  else if (vor.endsWith(' ')) vor = vor.slice(0, -1);
  if ((!vor || vor.endsWith('\n')) && nach.startsWith('\n')) nach = nach.slice(1);
  return vor + nach;
};

const titelVor = (zeilen: string[], i: number): string => {
  for (let j = i - 1; j >= 0; j--) {
    const s = zeilen[j].trim();
    if (s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:$/, ''))) return s.slice(3).trim();
  }
  return '';
};

const worte = (s: string): string => (s || '').toLowerCase().split(/[^a-zäöüß0-9-]+/u).filter(Boolean).sort().join('\u0001');
const VORLAGEN_WORTE = new WeakMap<object, Map<string, string>>();
const vorlageZurueck = (rest: string, templates?: VorlagenMap): string | null => {
  if (!templates) return null;
  let c = VORLAGEN_WORTE.get(templates);
  if (!c) {
    c = new Map();
    for (const v of Object.values(templates)) {
      const body = (v && v.body) || '';
      for (const [a, b] of saetzeMitLage(body)) if (!c.has(worte(body.slice(a, b)))) c.set(worte(body.slice(a, b)), body.slice(a, b).trim());
    }
    VORLAGEN_WORTE.set(templates, c);
  }
  return c.get(worte(rest)) ?? null;
};

export function befundAnfang(text: string, templates?: VorlagenMap): [string, string] {
  const spans = saetzeMitLage(text || '');
  if (!spans.length) return [text, ''];
  const [a, b] = spans[0];
  const s = text.slice(a, b);
  const m = UEBRIGEN_ANFANG.exec(s);
  if (!m) return [text, ''];
  const ansonsten = m[1].toLowerCase().startsWith('ansonsten');
  for (const [x, y] of spans.slice(1)) {
    const t = text.slice(x, y);
    if (UEBRIGEN_ANFANG.test(t)) continue;
    if (ansonsten ? hasPathology(t) : bejaht(t.toLowerCase(), STELLUNG_PATHO)) {
      const ohne = satzWeg(text, a, b);
      const y2 = y - (text.length - ohne.length);
      return [ohne.slice(0, y2) + ' ' + s + ohne.slice(y2), `hinter die Pathologie: ${s.slice(0, 50)}`];
    }
  }
  const rest = s.slice(m[0].length);
  let neu: string | null;
  if (WID_VERB.test(rest.split(' ', 1)[0].toLowerCase())) {
    neu = vorlageZurueck(rest, templates);
    if (neu === null) return [text, ''];
  } else neu = rest.slice(0, 1).toUpperCase() + rest.slice(1);
  return [text.slice(0, a) + neu + text.slice(b), `ohne „${m[1]}“: ${neu.slice(0, 50)}`];
}

const saetzeStreichen = (text: string, rxs: readonly RegExp[]): [string, string[]] => {
  const aend: string[] = [];
  for (const [a, b] of saetzeMitLage(text).reverse()) {
    const s = text.slice(a, b);
    if (rxs.some(rx => rx.test(s.toLowerCase()))) {
      text = satzWeg(text, a, b);
      aend.push(`gestrichen: ${s.trim().slice(0, 60)}`);
    }
  }
  return [text, aend];
};

const pleura = (text: string, diktat: string): [string, string[]] => {
  const quelle = diktat.toLowerCase();
  const m = new RegExp(PLEURA.source, 'u').exec(quelle);
  const seite = m ? diktierteSeite(quelle.slice(Math.max(0, m.index - 60), m.index + m[0].length + 60)) : diktierteSeite(text);
  const aend: string[] = [];
  for (const [a, b] of saetzeMitLage(text).reverse()) {
    const s = text.slice(a, b).toLowerCase();
    if (!SINUS_FREI.test(s) || bejaht(s, ERGUSS_SATZ)) continue;
    const andere = ({ rechts: 'links', links: 'rechts' } as Record<string, string>)[seite];
    if (seite !== 'beidseits' && (s.includes('übrig') || (andere && s.includes(andere) && !s.includes(seite || '-')))) continue;
    aend.push(`gestrichen: ${text.slice(a, b).slice(0, 60)}`);
    text = satzWeg(text, a, b);
  }
  const spans = saetzeMitLage(text);
  let erguss = spans.find(([x, y]) => bejaht(text.slice(x, y).toLowerCase(), ERGUSS_SATZ) && !ZWERCHFELL_NORMAL.test(text.slice(x, y).toLowerCase()));
  if (!erguss || text.includes(ZWERCHFELL_ANSONSTEN)) return [text, aend];
  for (const [a, b] of [...spans].reverse()) {
    if (ZWERCHFELL_NORMAL.test(text.slice(a, b).toLowerCase()) && !(a === erguss[0] && b === erguss[1])) {
      aend.push(`gestrichen: ${text.slice(a, b).slice(0, 60)}`);
      if (a < erguss[0]) {
        const d = text.length;
        text = satzWeg(text, a, b);
        erguss = [erguss[0] - (d - text.length), erguss[1] - (d - text.length)];
      } else text = satzWeg(text, a, b);
    }
  }
  const y = erguss[1];
  aend.push('ergänzt: ' + ZWERCHFELL_ANSONSTEN);
  return [text.slice(0, y) + ' ' + ZWERCHFELL_ANSONSTEN + text.slice(y), aend];
};

const DAUMEN = /(?<![a-zäöüß])daumen(?![a-zäöüß])/u;
const ANDERER_FINGER = /zeigefinger|mittelfinger|ringfinger|kleinfinger|(?<![a-zäöüß])dig(?:itus|\.)?\s*(?:ii|iii|iv|v|[2-5])(?![a-z0-9])/u;
const DAUMEN_SATZ_RE = /Normale Form der Phalangen((?: beidseits)?) und im Rahmen der Varianz auch des Endgliedes bei achsengerechter Stellung\./gu;
export const DAUMEN_SATZ = 'Normale Form der Phalangen{bds}, achsengerechte Stellung.';
const kopfzeile = (s: string): boolean => s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:$/, ''));

// 28b/29: diktierter Daumen statt CAS-„Finger“ in Überschrift und Ergebnis; Daumen-Normalsatz ohne Varianz-Endglied
const daumen = (zeilen: string[], dk: string, aend: string[]): void => {
  const nurDaumen = bejaht(dk, DAUMEN) && !ANDERER_FINGER.test(dk);
  let titel = '';
  zeilen.forEach((z, i) => {
    const s = z.trim();
    if (kopfzeile(s)) {
      if (nurDaumen && /^## Finger(?![a-zäöüß])/u.test(s)) {
        zeilen[i] = z.replace('## Finger', '## Daumen');
        aend.push(`Überschrift Daumen statt Finger: ${zeilen[i].trim().slice(0, 50)}`);
      }
      titel = zeilen[i];
      return;
    }
    if (s.startsWith('## ') || !titel.toLowerCase().includes('daumen')) return;
    let neu = z.replace(DAUMEN_SATZ_RE, (_m, bds: string) => DAUMEN_SATZ.replace('{bds}', bds));
    if (nurDaumen) {
      neu = neu.replace(/(?<![\p{L}\p{N}_])des Fingers(?![\p{L}\p{N}_])/gu, 'des Daumens')
        .replace(/(?<![\p{L}\p{N}_])Finger(?=\s+(?:rechts|links|beidseits)(?![\p{L}\p{N}_]))/gu, 'Daumen');
    }
    if (neu !== z) { aend.push(`Daumen: ${neu.trim().slice(0, 50)}`); zeilen[i] = neu; }
  });
};

// 26 (RH 49, Georg): Titel der Kombi Becken + Hüfte mit einer Seite (Sync: befund_regeln.py)
const KOMBI_TITEL_RE = /^## Beckenübersicht und Hüfte (rechts|links)(?: in 2 Ebenen)?[ \t]*$/u;
export const KOMBI_TITEL = '## Becken sowie Hüftgelenk in 2 Ebenen {seite}';

export function grundregeln(report: string, diktat = '', templates?: VorlagenMap): [string, string[]] {
  if (!report || !report.includes('## ')) return [report, []];
  const zeilen = report.split('\n');
  const aend: string[] = [];
  zeilen.forEach((z, i) => {
    const m = KOMBI_TITEL_RE.exec(z.trim());
    if (m) { zeilen[i] = KOMBI_TITEL.replace('{seite}', m[1]); aend.push(`Titel ${zeilen[i].slice(3)}`); }
  });
  const dk = (diktat || '').toLowerCase();
  daumen(zeilen, dk, aend);
  for (const [a, e] of abschnitt(zeilen, 'befund').reverse()) {
    const titel = titelVor(zeilen, a - 1);
    let text = zeilen.slice(a, e).join('\n');
    let tl = text.toLowerCase();
    for (const [i, wenn, nurTitel, saetze] of GEORG_RX) {
      if (nurTitel !== null && !nurTitel.test(titel)) continue;
      if (!(bejaht(dk, wenn) || bejaht(tl, wenn))) continue;
      if (i === 'skoliose' && (KEINE_SKOLIOSE.test(dk) || KEINE_SKOLIOSE.test(tl))) continue;
      const [t2, x] = saetzeStreichen(text, saetze);
      text = t2;
      aend.push(...x.map(z => `${i}: ${z}`));
      tl = text.toLowerCase();
    }
    if (THORAX_TITEL.test(titel) && (bejaht(dk, PLEURA) || bejaht(tl, PLEURA))) {
      const [t2, x] = pleura(text, diktat || '');
      text = t2;
      aend.push(...x.map(z => `pleuraerguss: ${z}`));
    }
    const lead = text.length - text.trimStart().length;
    const [neu, x] = befundAnfang(text.slice(lead), templates);
    if (x) { text = text.slice(0, lead) + neu; aend.push(x); }
    zeilen.splice(a, e - a, ...text.split('\n'));
  }
  const skol = /skoliose|flachprofil/u.test(dk) ? null : SKOL_ABSTUFUNG.exec(dk);
  let erg = false;
  for (const [a, e] of abschnitt(zeilen, 'ergebnis').reverse()) {
    for (let i = e - 1; i >= a; i--) {
      const z = zeilen[i];
      if (KI_PUNKT.test(z)) {
        aend.push(`KI-Hinweis nicht im Ergebnis: ${z.trim().slice(0, 60)}`);
        zeilen.splice(i, 1);
        erg = true;
      } else if (skol && new RegExp(SKOLIOSE_WORT.source, 'u').test(z)) {
        zeilen[i] = z.replace(SKOLIOSE_WORT, 'skoliotische ' + skol[1].charAt(0).toUpperCase() + skol[1].slice(1).toLowerCase());
        aend.push(`diktierte Abstufung: ${zeilen[i].trim().slice(0, 60)}`);
        erg = true;
      }
    }
  }
  let out = zeilen.join('\n');
  const si = out.replace(SI_ARTHROSE, (_m, n: string) => 'SI-Gelenksarthrose' + n);
  if (si !== out) { aend.push('Schreibweise SI-Gelenksarthrose'); out = si; }
  if (out.includes('Kellgren')) {
    const zz = out.split('\n');
    let titel = '';
    zz.forEach((z, i) => {
      const s = z.trim();
      if (s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:$/, ''))) titel = s.slice(3);
      else if (WS_TITEL.test(titel) && new RegExp(KL_KLAMMER_WS.source, 'u').test(z)) {
        zz[i] = z.replace(KL_KLAMMER_WS, '');
        aend.push('Wirbelsäule ohne K&L-Grad');
        erg = true;
      }
    });
    out = zz.join('\n');
  }
  if (erg) out = ergebnisNummerieren(out);
  return [out, aend];
}

// 13 (RH 78): Schreibvarianten für die Nachprüfung „Befund fehlt im Text“ (Sync: befund_regeln.py)
const VERTAUSCHT: [string, string][] = [['femoropatellar', 'patellofemoral'], ['femorotibial', 'tibiofemoral'], ['retropatellar', 'femoropatellar']];
export function schreibvarianten(text: string): string[] {
  const t = (text || '').toLowerCase();
  const out = [t, t.replace(/[kz]/gu, 'c'), t.replace(/c(?!h)/gu, 'k')];
  for (const [x, y] of VERTAUSCHT) {
    const basis = out.slice(0, 3);
    out.push(...basis.filter(v => v.includes(x)).map(v => v.split(x).join(y)), ...basis.filter(v => v.includes(y)).map(v => v.split(y).join(x)));
  }
  return [...new Set(out)];
}
const inhaltsworte = (t: string): Set<string> =>
  new Set((t || '').toLowerCase().replace(/[kz]/gu, 'c').split(/[^a-zäöüß0-9]+/u).filter(w => w.length >= 4));
export function phraseVorhanden(phrase: string, text: string): boolean {
  const w = inhaltsworte(phrase);
  if (!w.size) return false;
  const restC = schreibvarianten(text).join(' ').replace(/[kz]/gu, 'c');
  const da = (x: string): boolean => {
    if (restC.includes(x)) return true;
    return VERTAUSCHT.some(([p, q]) => [[p, q], [q, p]].some(([u, v]) => x.includes(u) && restC.includes(x.split(u).join(v))));
  };
  return [...w].every(da);
}
