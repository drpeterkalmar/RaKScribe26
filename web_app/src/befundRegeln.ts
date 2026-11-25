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
// kaiscribe-schulter-ergebnis-n1 (Punkt 65): unnummeriert nur die Einleitung „Vergleich zur Voruntersuchung vom …:“
export const UNNUM_RE = /^(?:im\s+)?vergleich\s+zu[rm]?\s+vor[^\n]*:$|^HKA = Hüft-Knie-Sprunggelenk-Winkel|^Weitere Winkelmessungen sind den KI-Auswertungsbildern|^(?:LCE|AI|CCD) = (?:lateraler Center-Edge|Acetabulumindex|Caput-Collum)|^Anmerkung:/i;  // kaiscribe-georg-2011-n1 (Punkt 9)

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
  const r = mammasonoBeidseits(befundUeberschriftSichern(csaBereinigen(nummerieren ? ergebnisTextSichern(report) : report)));
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

// kaiscribe-rho-regel-becken-n1 (Kanban #533, Georg 23.11.2026 „Die Regel muss sitzen!“): EINE Rho-Regel wie ris-mods
// ibl/rho_regel.py – Score ≥ 7 UND Region LWS UND keine DEXA in den 2 Jahren davor; sonst kein Rho-Teil.
// Sync: befund_regeln.py rho_regel/rho_regel_anwenden (Fixtures „rho“ → „regel“). Die Web-App kennt kein CAS → dexa "frei"
// (das Diktat „Rho“ ist die Auskunft des Arztes).
const RHO_LWS = /lendenwirbel|lumbal|(?<![a-zäöüß])lws(?![a-zäöüß])/i;
export function rhoRegel(score: string | number | null | undefined, lws: boolean, dexa: string): [boolean, string] {
  const s = String(score ?? '').trim().replace(/≥/g, '').replace(/ /g, '');
  if (!/^\d{1,2}$/.test(s) || Number(s) < 1 || Number(s) > 10) return [false, 'kein Rho-Score 1–10'];
  if (!lws) return [false, 'Rho-Region nicht LWS'];
  if (Number(s) < RHO_AB) return [false, `Rho-Score ${Number(s)} < ${RHO_AB}`];
  if (dexa !== 'frei') return [false, dexa === 'gesperrt' ? 'Knochendichte in den letzten 2 Jahren' : 'DEXA der letzten 2 Jahre unbekannt'];
  return [true, 'Rho-Regel erfüllt'];
}

export function rhoRegelAnwenden(report: string, dexa = 'frei'): [string, string] {
  if (!report || !report.includes(`## ${RHO_TITEL}`)) return [report, ''];
  const zeilen = report.split('\n');
  const a = zeilen.findIndex(z => z.trim() === `## ${RHO_TITEL}`);
  const kopf = (z: string) => { const s = z.trim(); return s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:+$/, '')); };
  let e = a + 1;
  while (e < zeilen.length && !kopf(zeilen[e])) e++;
  const block = zeilen.slice(a, e).join('\n');
  const m = block.match(/Der Score von (≥\s*7|\d{1,2})(?![\p{L}\p{N}_])/u);
  const score = m ? m[1] : '≥7';
  const andere = [...zeilen.slice(0, a), ...zeilen.slice(e)];
  const lws = andere.filter(kopf).some(z => RHO_LWS.test(z.trim().slice(3)));
  const [ja, grund] = rhoRegel(score, lws, dexa);
  if (ja) return [report, ''];
  return [andere.join('\n').trim().replace(/\n{4,}/g, '\n\n\n'), grund];
}

// kaiscribe-rho-osteopen-n1 (Georg 22.11.2026, „Überall ersetzen“): Rho-Schlussbefund (Score ≥ 7) im Befund →
// Mineralisations-Normalsatz in der Beschreibung aller Untersuchungen durch „Osteopenischer Knochenaspekt.“; weitere
// Normalsätze dazu im selben Teil fallen weg; Diktat nennt die Knochendichte selbst → nichts; Ergebnis unverändert.
// Sync: befund_regeln.py osteopen_ersetzen (Fixtures „rho“ → „osteopen“).
export const OSTEOPEN_SATZ = 'Osteopenischer Knochenaspekt.';
const OSTEO_WORT = /mineral|kalksalz|knochenstruktur|spongiosa/i;
const OSTEO_NORMAL = /^(?:regelrecht|unauffällig|normal|regulär|altersentsprechend|altersgerecht|homogen)(?:e|er|em|en|es)?$/;
const OSTEO_ERLAUBT = new Set((
  'im übrigen ansonsten sonst die der das des den mitdargestellten mitabgebildeten abgebildeten dargestellten erfassten ' +
  'miterfassten übrigen skelettabschnitte skelettanteile knochen knöchernen ist sind stellt stellen sich dar zeigt zeigen ' +
  'bezüglich hinsichtlich mineralgehalt mineralisation knochenmineralisation knochenmineralgehalt kalksalzgehalt ' +
  'knochenstruktur knochenstrukturen spongiosastruktur und sowie bei scharfer scharf abgrenzbarkeit abgrenzbar ' +
  'spongiosabälkchen soweit erfasst mitabgebildet beckens femurs').split(' '));
const OSTEO_VORSATZ = /^(im übrigen|ansonsten|sonst)\s+/i;
const OSTEO_DIKTIERT = /mineral|osteopen|osteopor|kalksalz|entkalk|kalkarm|knochenarm|knochendicht|knochenatroph|demineral/i;
const OSTEO_IM_BEFUND = /osteopen|osteopor|demineral|kalksalzminder|kalkarm|vermindert[\p{L}]*\s+(?:knochen)?mineral/iu;

const osteoNormal = (satz: string): boolean => {
  const w = satz.toLowerCase().match(/[a-zäöüß]+/g) || [];
  return w.length > 0 && OSTEO_WORT.test(satz) && w.some(x => OSTEO_NORMAL.test(x))
    && w.every(x => OSTEO_ERLAUBT.has(x) || OSTEO_NORMAL.test(x));
};

const osteoSatz = (satz: string, erster: boolean): string | null => {
  const kern = satz.trim();
  if (osteoNormal(kern)) {
    if (!erster) return '';
    const m = kern.match(OSTEO_VORSATZ);
    return m ? m[0] + OSTEOPEN_SATZ[0].toLowerCase() + OSTEOPEN_SATZ.slice(1) : OSTEOPEN_SATZ;
  }
  const p = kern.indexOf(', ');
  if (p >= 0) {
    const kopf = kern.slice(0, p), rest = kern.slice(p + 2).trim();
    if (rest && osteoNormal(kopf)) return (erster ? OSTEOPEN_SATZ + ' ' : '') + rest[0].toUpperCase() + rest.slice(1);
  }
  return null;
};

const rhoAb7ImBefund = (report: string): boolean => {
  if (!report.includes(`## ${RHO_TITEL}`) || !report.includes(RHO_ERGEBNIS)) return false;
  const m = report.match(/Der Score von (≥\s*7|\d{1,2})(?![\p{L}\p{N}_])/u);
  return !m || !/^\d+$/.test(m[1]) || Number(m[1]) >= RHO_AB;
};

export function osteopenErsetzen(report: string, diktat = ''): [string, string[]] {
  if (!report || !rhoAb7ImBefund(report)) return [report, []];
  if (OSTEO_DIKTIERT.test(rhoErkennen(diktat || '')[0] || '')) return [report, []];
  const zeilen = report.split('\n');
  const teile: [number, string][] = [];
  let titel = '', imBefund = true, rho = false;
  zeilen.forEach((z, i) => {
    const st = z.trim();
    if (st.startsWith('## ')) {
      const kopf = st.slice(3).trim().replace(/:$/, '').toLowerCase();
      if (kopf === 'befund') imBefund = true;
      else if (kopf === 'ergebnis') imBefund = false;
      else { titel = st.slice(3).trim(); imBefund = true; rho = st === `## ${RHO_TITEL}`; }
      return;
    }
    if (imBefund && !rho && st) teile.push([i, titel]);
  });
  if (teile.some(([i]) => OSTEO_IM_BEFUND.test(zeilen[i]))) return [report, []];
  const geaendert: string[] = [], ersetzt = new Set<string>(), weg = new Set<number>();
  for (const [i, t] of teile) {
    const stuecke = zeilen[i].split(/(?<=[.!?])(\s+)(?=[A-ZÄÖÜ])/);
    const neu: string[] = [];
    let anders = false;
    for (let k = 0; k < stuecke.length; k += 2) {
      const r = osteoSatz(stuecke[k], !ersetzt.has(t));
      if (r === null) neu.push(stuecke[k]);
      else { anders = true; ersetzt.add(t); if (r) neu.push(r); }
      if (k + 1 < stuecke.length) neu.push(stuecke[k + 1]);
    }
    if (anders) {
      zeilen[i] = neu.join('').replace(/\s{2,}/g, ' ').trim();
      if (!zeilen[i]) weg.add(i);
      if (!geaendert.includes(t)) geaendert.push(t);
    }
  }
  if (!geaendert.length) return [report, []];
  const out: string[] = [];
  zeilen.forEach((z, k) => {
    if (weg.has(k)) return;
    if (!z.trim() && out.length && !out[out.length - 1].trim() && weg.has(k - 1)) return;
    out.push(z);
  });
  return [out.join('\n'), geaendert];
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
export type WiderspruchBefund = { id: string; name: string; phrase: string; gruppen: string[]; global: boolean; seite?: string };
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
        const b: WiderspruchBefund = { id: k.id, name: k.name, phrase: widPhrase(roh, i) || roh, gruppen: [...alle].sort(),
          global: !!k.global || alle.size === 0 };
        const sd = widSeite(t);
        if (sd) b.seite = sd;
        out.push(b);
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
// 3.20.2 (Abnahme 21.11.2026): Normalsatz, der ausdrücklich die ANDERE Seite nennt, widerspricht einem Befund mit Seite nicht
const WID_RECHTS = /(?<![a-zäöüß])rechts(?:seitig[a-zäöüß]*)?(?![a-zäöüß])|(?<![a-zäöüß])rechte[nrsm]?(?![a-zäöüß])/iu;
const WID_LINKS = /(?<![a-zäöüß])links(?:seitig[a-zäöüß]*)?(?![a-zäöüß])|(?<![a-zäöüß])linke[nrsm]?(?![a-zäöüß])/iu;
const WID_BEIDE = /(?<![a-zäöüß])(?:beidseit[a-zäöüß]*|bds|beide[nrsm]?)(?![a-zäöüß])/iu;
export function widSeite(t: string): string {
  const r = WID_RECHTS.test(t || ''), l = WID_LINKS.test(t || '');
  if (r === l || WID_BEIDE.test(t || '')) return '';
  return r ? 'rechts' : 'links';
}
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
    const ss = widSeite(s);
    const ids: string[] = [];
    for (const x of befunde) {
      const k = kat.get(x.id);
      if (!k) continue;
      const treffer = (k.merkmale || []).some(mn => {
        const rx = c.merk[mn];
        return !!rx && rx[0].test(s) && !(rx[1] && rx[1].test(s));
      });
      if (treffer && widBetrifft(sg, x) && !(x.seite && ss && ss !== x.seite)) ids.push(x.id);
    }
    if (ids.length) out.push([a, b, ids]);
  }
  return out;
}

const WID_VERB = /^(?:ist|sind|zeigt|zeigen|weist|weisen|stellt|stellen|steht|stehen|liegt|liegen|erscheint|erscheinen|endet|enden|besteht|bestehen|findet|finden|ragt|ragen)$/u;
const WID_KLEIN = new RegExp('^(?:normale?[rsnm]?|normal|regelrechte?[rsnm]?|regelrecht|glatte?[rsnm]?|scharfe?[rsnm]?|' +
  'anatomisch[a-zäöüß]*|ordnungsgemäße?[rsnm]?|keine?[rsnm]?|kein|unauffällige?[rsnm]?|altersentsprechende?[rsnm]?|' +
  'symmetrische?[rsnm]?|achsengerechte?[rsnm]?|allseits|harmonische?[rsnm]?|regulär[a-zäöüß]*|intakte?[rsnm]?|' +
  'gute?[rsnm]?|erhaltene?[rsnm]?|beide[rn]?|die|der|das|den|dem|des|eine?[rsnm]?|sie|es|rechts|links)$', 'iu');
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
  // #401 (Georg 16.11.2026: „Der AC-Gelenk …“ von Hand ergänzt): Satz mit Artikel, alte Formen bleiben erkannt
  'Das AC-Gelenk ist altersentsprechend, keine Luxation.': ['AC-Gelenk altersentsprechend, keine Luxation.',
    'Der AC-Gelenk altersentsprechend, keine Luxation.'],
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
// „(Arthrose Grad 3 nach Kellgren & Lawrence)“ — Ergebnisformat (Regel-Register kl-ergebnis). Sync: befund_regeln.py kl_klammer
export const klKlammer = (grad: string): string => `(Arthrose Grad ${grad} nach Kellgren & Lawrence)`;
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
  // kaiscribe-schulter-ergebnis-n1 (Punkt 70, RH 94): mehrere Grad-Adjektive → Grad zum Adjektiv DIESER Diagnose
  const adjOk = !d.length && !e.length;
  const zeilen = report.split('\n').map(z => {
    if (z.includes('(IB Lab') || !z.toLowerCase().includes('kellgren')) return z;
    const gZ = adjOk ? klGradZeile(z.replace(KL_KI, '')) : null;
    if (gZ && ok.includes(gZ)) {
      return z.replace(KL_KI, (m0: string, g1?: string, g2?: string) => {
        const ist = KL_WERT[(g1 || g2 || '').toLowerCase()] ?? 'X';
        if (ist === gZ) return m0;
        aend.push(`K&L-Grad ${ist} → ${gZ} (Adjektiv derselben Diagnose)`);
        return m0.replace(new RegExp(KL_G_KI + String.raw`(?=\s+nach)`, 'i'), gZ);
      });
    }
    return z.replace(KL_KI, ersetzen);
  });
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
  // kaiscribe-schulter-ergebnis-n1 (Punkt 60/69): diktierte Coxarthrose → „Keine Coxarthrosezeichen.“ raus (Sync: befund_regeln.py)
  ['coxarthrose', 'co[xk]arthros', null, ['^(?:(?:im übrigen|ansonsten),?\\s+)?keine co[xk]arthrosezeichen']],
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

// 37c (Georg 20.11.2026; Abnahme 3.20.2 am 21.11.): Stellungssatz hinter nicht-stellungsbezogener Pathologie → nach vorn (Sync: befund_regeln.py)
export const STELLUNG_UEBRIGEN = /^Im [Üü]brigen,?\s+(normale[rn]?\s+(?:Form\s+und\s+)?Stellung\b[\s\S]*)$/u;
function stellungVor(text: string, spans: [number, number][]): [string, string] {
  for (let k = 1; k < spans.length; k++) {
    const [x, y] = spans[k];
    const m = STELLUNG_UEBRIGEN.exec(text.slice(x, y));
    if (!m) continue;
    if (spans.slice(0, k).some(([p, q]) => bejaht(text.slice(p, q).toLowerCase(), STELLUNG_PATHO))) return [text, ''];
    const satz = m[1].charAt(0).toUpperCase() + m[1].slice(1);
    const ohne = satzWeg(text, x, y);
    const a = spans[0][0];
    return [ohne.slice(0, a) + satz + ' ' + ohne.slice(a), `Stellung zuerst: ${satz.slice(0, 50)}`];
  }
  return [text, ''];
}

export function befundAnfang(text: string, templates?: VorlagenMap): [string, string] {
  const spans = saetzeMitLage(text || '');
  if (!spans.length) return [text, ''];
  const [a, b] = spans[0];
  const s = text.slice(a, b);
  const m = UEBRIGEN_ANFANG.exec(s);
  if (!m) return stellungVor(text, spans);
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

const SEITE_ADJ = /((?:^|[.!?]\s+|\n)(?:Rechts|Links|Beidseits)\s+)(Degenerative[nrs]?|Geringe[nrs]?|Geringgradige[nrs]?|Mäßige[nrs]?|Mäßiggradige[nrs]?|Deutliche[nrs]?|Ausgeprägte[nrs]?|Beginnende[nrs]?|Fortgeschrittene[nrs]?|Zarte[nrs]?|Kleine[nrs]?|Diskrete[nrs]?)(?=\s+[A-ZÄÖÜ])/gu;
const SKOL_DIKTIERT = /(?<![a-zäöüß])skoliose(?![a-zäöüß])/u;
const SEITAUSBIEGUNG = /(?<![A-Za-zÄÖÜäöüß])Seitausbiegung(?![a-zäöüß])/u;
const GWS_AP_TITEL = /ganzaufnahme der wirbelsäule a\.?-?p/iu;
const GWS_ERSTE = /^(?:Normale Stellung|Alignementlinien|Rechtskonvexe skoliotische|Linkskonvexe skoliotische|Flachbogige|Skoliose)/u;
const KNIE_BDS_TITEL = /knie[a-zäöüß]*.*(?:beidseit|bds)/iu;
const ANMERKUNG_ZEILE = /^(?:Anmerkung:|Weitere Winkelmessungen|HKA = |LCE = )/u;
const seitenRang = (z: string): number => { const sd = widSeite(z); return sd === 'rechts' ? 0 : sd === 'links' ? 2 : 1; };

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
    if (SKOL_DIKTIERT.test(dk) && !tl.includes('skoliose') && SEITAUSBIEGUNG.test(text)) {   // Diktat wörtlich (Sync: befund_regeln.py)
      text = text.replace(new RegExp(SEITAUSBIEGUNG.source, 'gu'), 'Skoliose');
      aend.push('diktierte Skoliose statt „Seitausbiegung“');
    }
    const lead = text.length - text.trimStart().length;
    const [neu, x] = befundAnfang(text.slice(lead), templates);
    if (x) { text = text.slice(0, lead) + neu; aend.push(x); }
    if (GWS_AP_TITEL.test(titel)) {
      const l2 = text.length - text.trimStart().length;
      if (GWS_ERSTE.test(text.slice(l2))) { text = text.slice(0, l2) + 'Wirbelsäule: ' + text.slice(l2); aend.push('GWS a.p.: Beschriftung „Wirbelsäule:“'); }
    }
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
  // 33 (Georg 20.11.2026, Abnahme 21.11.): Knie beidseits – im Ergebnis rechts zuerst (Sync: befund_regeln.py)
  for (const [a, e] of abschnitt(zeilen, 'ergebnis')) {
    if (!KNIE_BDS_TITEL.test(titelVor(zeilen, a - 1))) continue;
    const idx: number[] = [];
    for (let i = a; i < e; i++) if (zeilen[i].trim() && !ANMERKUNG_ZEILE.test(zeilen[i].trim())) idx.push(i);
    const alt = idx.map(i => zeilen[i]);
    const neu = alt.map((z, k) => [z, k] as [string, number]).sort((x, y) => seitenRang(x[0]) - seitenRang(y[0]) || x[1] - y[1]).map(x => x[0]);
    if (neu.some((z, k) => z !== alt[k])) {
      idx.forEach((i, k) => { zeilen[i] = neu[k]; });
      aend.push('Knie beidseits: Ergebnis rechts zuerst');
      erg = true;
    }
  }
  let out = zeilen.join('\n');
  const klein = out.replace(SEITE_ADJ, (_m, a: string, b: string) => a + b.toLowerCase());
  if (klein !== out) { aend.push('Adjektiv nach Seitenwort klein'); out = klein; }
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
  const [out2, x2] = georg2311(out, diktat, templates);   // kaiscribe-schulter-ergebnis-n1 (Georg 22./23.11.2026, Punkte 48–70)
  const [out3, x3] = ursula2011(out2, templates);          // kaiscribe-ursula-2011-text-n1 (Ursula 20.11.2026, Punkte 3/4/7/10)
  return [out3, [...aend, ...x2, ...x3]];
}

// ══ kaiscribe-schulter-ergebnis-n1 (Georg Riegler 22./23.11.2026, Punkte 48–70) – Sync: befund_regeln.py georg_2311,
// Fixtures „georg_2311“. Beschreibung der Regeln siehe dort. Ohne Treffer bleibt der Text Zeichen für Zeichen gleich.
export const KORTIKALIS_UEBRIGEN = 'Im Übrigen glatte und scharfe Begrenzung der normal breiten Kortikalis ohne pathologische Konturunterbrechung.';
export const ENTHESIO_SATZ = 'kortikale Unregelmäßigkeiten und vermehrte Sklerosierung';
export const NERV_UNAUFFAELLIG = 'Unauffälliger Befund am N. {name}{seite}.';
export const DUNN_TITEL = ' sowie Dunn-Aufnahme';
export const DUNN_TITEL_BDS = ' sowie Dunn-Aufnahmen beidseits';
export const ZUSATZPROJEKTIONEN: Record<string, { aktiv: boolean; diktat: string; region: string }> = {
  dunn: { aktiv: true, diktat: '(?<![a-zäöüß])dunn(?![a-zäöüß])', region: 'hüft|becken' } };
const SCHNITT_TITEL = /sonogra|ultraschall|(?<![a-zäöüß])(?:mr|mrt|ct)(?![a-zäöüß])|magnetres|computertomo/iu;
const SONO_TITEL = /sonogra|ultraschall/iu;
const SCHULTER_TITEL = /schulter/iu;
const BECKEN_TITEL = /becken|hüft/iu;
const ANS_KONTUR = /^(?:ansonsten|im übrigen),?\s+(?:sind\s+)?die gelenkfl[äa]chen\s+(?:sind\s+)?regelrecht konturiert/u;
const ENTH_RX = /enthesiopath/u;
const AC_RX = /(?<![a-zäöüß])ac-|(?<![a-zäöüß])acg(?![a-zäöüß])|acromioclavicular|akromioklavikular/u;
const GELENK_RX = /glenohumeral|omarthros|gelenks?spalt|osteophyt|humeruskopf/u;
const ADJW = '(gering[a-zäöüß]*|leicht[a-zäöüß]*|mäßig[a-zäöüß]*|mittelgradig[a-zäöüß]*|hochgradig[a-zäöüß]*|ausgeprägt[a-zäöüß]*|deutlich[a-zäöüß]*|beginnend[a-zäöüß]*)';
const ENTH_SATZ = new RegExp('^(?:(?:im übrigen|ansonsten),?\\s+)?(?:(?:geringe|mäßige|zarte|diskrete)\\s+)?(?:zeichen\\s+(?:einer|der)\\s+)?(?:' + ADJW +
  '\\s+)?enthesiopathi[a-zäöüß]*\\s+(.+?)\\s*\\.?$', 'iu');
const ENTH_ADJ: [RegExp, string][] = [[/^(?:gering|leicht)/iu, 'Geringe'], [/^(?:mäßig|mittelgradig)/iu, 'Mäßige'],
  [/^(?:hochgradig|ausgeprägt)/iu, 'Hochgradige'], [/^beginnend/iu, 'Beginnende'], [/^deutlich/iu, 'Deutliche']];
const ENTH_DIKTAT = new RegExp(ADJW + '\\s+(?:[a-zäöüß0-9_]+\\s+)?enthesiopath', 'iu');
const BURSA_PATHO = /bursitis|bursaverdick|bursa[a-zäöüß -]{0,40}(?:verdick|flüssigkeit|erguss|distendiert|distension)|(?:flüssigkeit|erguss)[a-zäöüß ]{0,30}bursa|step-?sign[a-zäöüß ]{0,15}positiv|positive[sn]? step-?sign/u;
const BURSA_NORMAL = /bursa[^.]*(?:ohne|kein[a-zäöüß0-9_]*)\s[^.]*(?:wandverdick|flüssigkeit|erguss|bursitis|verdick)|(?:kein[a-zäöüß0-9_]*|ohne)\s[^.]*(?:bursitis|flüssigkeit[^.]*bursa)/u;
const STEP_NORMAL = /^(?:(?:im übrigen|ansonsten),?\s+)?kein nachweis eines step-?sign/u;
const STEP_PATHO = /step-?sign[a-zäöüß ]{0,15}positiv|positive[sn]? step-?sign|impingement/u;
const FRAKTUR_RX = /fraktur|ausriss|fissur|infraktion|(?<![a-zäöüß])fragment/u;
const NICHT_DISLOZIERT = /(?<![a-zäöüß])nicht[- ](?:disloziert|dislociert|verschoben|verlagert)[a-zäöüß]*/gu;
const KL_ADJ_SEITE = new RegExp('(?<![a-zäöüß])(' + KL_ADJ.map(([, r]) => r).join('|') + ')\\s+(?:rechts|links|beidseits)(?![a-zäöüß])', 'giu');
// Abend-Abnahme 24.11.2026 (Fall H): „Coxarthrose links hochgradig, rechts gering“ – Seite VOR dem Adjektiv zählt ebenso
const KL_SEITE_ADJ = new RegExp('(?<![a-zäöüß])(?:rechts|links|beidseits),?\\s+(' + KL_ADJ.map(([, r]) => r).join('|') + ')(?![a-zäöüß])', 'giu');
const PATHO_EXTRA = /status post|zustand nach|(?<![a-zäöüß])(?:st\.|z\.)\s?[pn]\.|enthesi|unregelmäßig|prothes|(?<![a-zäöüß])tep(?![a-zäöüß])|ausriss|fragment|verdick|bursitis|degenerat|stenose|hypertroph|zyste|erosion|lockerung|sklerosier|osteophyt|randanbau|randzack|dysplas|steiles pfannendach|überdachung|coxa (?:valga|vara)|beckenschief|beinlängen|fibroostos|tendinos|ruptur|ganglion|lipom|tumor|raumforder|hämatom|serom|abszess/u;
const NERV_TITEL = /(?:sonogra|ultraschall)[^\n]*(?:(?<![a-zäöüß])n\.|nerv)/iu;
const NERV_NAME = /(?:(?<![a-zäöüß])n\.|nervus|nerv)\s*(medianus|ulnaris|radialis|ischiadicus|peroneus|fibularis|tibialis|femoralis|suralis|pudendus|saphenus|obturatorius|axillaris|musculocutaneus|suprascapularis|iliohypogastricus|ilioinguinalis|cutaneus femoris lateralis|femoralis cutaneus lateralis)/iu;
const NERV_PATHO = /verdick|auftreib|aufgetrieben|schwell|kompression|engpass|neurom|ödem|vergrößer|erhöht|hypoechogen|hyperäm|läsion|neuritis|irritation|luxation|instabil|einengung|kaliberschwank|neuropath|kompressions/u;
const BS_GROSS = /Beckenschiefstand von (\d+) mm(?:,\s*(rechts|links) tiefer(?:stehend)?)?/gu;
const HIPPO_SATZ = /^(?:Geringer Beckenschiefstand|Beckenschiefstand von|Kein Beckenschiefstand|Beinlängendifferenz von|Keine Beinlängendifferenz)/u;
const VERLAUF = /unverändert[a-zäöüß0-9_]*[^.]{0,60}(?:vor(?:untersuchung|befund|aufnahme)|vergleich)|vergleich zu[rm]? vor(?:untersuchung|aufnahme|befund)|befund(?:änderung|konstanz|progredienz)|zur voruntersuchung|größenkonstant/iu;
const UEB = '(?:(?:Im [Üü]brigen|Ansonsten),?\\s+)?';
const HUEFTKOPF_BDS = new RegExp('^' + UEB + '(?:[Oo]rdnungsgemäße|[Nn]ormale|[Rr]egelrechte) Stellung der normal geformten Hüftköpfe\\.$', 'u');
const HUEFTKOPF_EIN = new RegExp('^' + UEB + '(?:[Oo]rdnungsgemäße|[Nn]ormale|[Rr]egelrechte) Stellung des normal geformten (rechten|linken) Hüftkopfes\\.$', 'u');
const HUEFT_SPALT = new RegExp('^' + UEB + '(?:(Rechts|Links) )?[Nn]ormal konfigurierte, glatte Gelenkflächen mit allseits normal weitem Gelenkspalt\\.$', 'u');
const HUEFT_EIN_FORM = new RegExp('^' + UEB + 'Anatomisch normale Form des Hüftgelenkes mit regelrechter Stellung des Hüftkopfes in der Pfanne\\.$', 'u');
const HUEFT_BETROFFEN = /prothes|(?<![a-zäöüß])tep(?![a-zäöüß])|endoprothes|coxarthros|koxarthros|dysplas|steiles pfannendach|grenzwertige überdachung|lce-winkel beträgt|ai-winkel beträgt|acetabulumindex beträgt|(?<![a-zäöüß])(?:lce|ai)(?:-winkel)?\s+(?:von\s+)?(?:rechts\s+|links\s+)?\d/gu;
const KL_AUSNAHME = /(?<![a-zäöüß])(?:ac|acg|si|isg)(?![a-zäöüß])|acromioclavicular|akromioklavikular|iliosakral|sakroiliakal|symphys|facetten|spondyl|unkovertebral|uncovertebral|wirbel|rhizarthros|daumensattel/iu;
const KL_DOPPEL = /^((?:[A-ZÄÖÜ][a-zäöüß]+\s+)?)([A-ZÄÖÜa-zäöüß-]*[Aa]rthrose)\s+(rechts|links)\s+und\s+([a-zäöüß]+)\s+(?:(?:[A-ZÄÖÜa-zäöüß-]*[Aa]rthrose)\s+)?(rechts|links)\s*\.?$/u;
const NB2 = '(?<![A-Za-zÄÖÜäöüß])', NA2 = '(?![A-Za-zÄÖÜäöüß])';
const WORT_ERSETZEN: [RegExp, (m: string, ...g: string[]) => string][] = [
  [new RegExp(NB2 + '([Kk])einerlei Zeichen einer (?:peri)?(?:prothetischen|peripherischen|periprothetischen) Fraktur', 'gu'), (_m, k) => k + 'eine Zeichen einer periprothetischen Fraktur'],
  [new RegExp(NB2 + '(?:peripherischen|prothetischen)(?= Fraktur)', 'gu'), () => 'periprothetischen'],
  [new RegExp(NB2 + '([Kk])ein(?:e)? sicheres? periprothetische[n]? Fraktur', 'gu'), (_m, k) => k + 'eine sichere periprothetische Fraktur'],
  [new RegExp(NB2 + 'des Material post' + NA2 + '|' + NB2 + 'des Material(?=[.,;])', 'gu'), () => 'des Materials'],
];
const cap = (s: string): string => s ? s[0].toUpperCase() + s.slice(1).toLowerCase() : s;
const ohneNum = (z: string): string => z.replace(NUM_RE, '').trim();

const pathoSatz = (s: string): boolean => {
  const t = (s || '').toLowerCase().replace(/^(?:im übrigen|ansonsten),?\s+/u, '');
  return hasPathology(t) || bejaht(t, PATHO_EXTRA);
};
type Zeilen = (string[] | null)[];
const zerlegen = (text: string): Zeilen =>
  text.split('\n').map(z => (!z.trim() ? null : saetzeMitLage(z).map(([a, b]) => z.slice(a, b).trim())));
const flach = (L: Zeilen): [number, number][] => {
  const out: [number, number][] = [];
  L.forEach((z, i) => { if (z) z.forEach((_s, k) => out.push([i, k])); });
  return out;
};
const zusammen = (L: Zeilen): string => {
  const out: string[] = [];
  let leer = false;
  for (const z of L) {
    if (z === null) { if (!leer || !out.length) out.push(''); leer = true; }
    else if (z.length) { out.push(z.join(' ')); leer = false; }
  }
  return out.join('\n');
};
const saetzeVon = (L: Zeilen): string[] => flach(L).map(([i, k]) => L[i]![k]);
const umstellen = (L: Zeilen, raus: number[], nach: number, neue: string[]): Zeilen => {
  const pos = flach(L);
  const ziel = nach >= 0 && nach < pos.length ? pos[nach] : null;
  const weg = new Set(raus.map(r => pos[r].join(',')));
  const M: ([string, string | null][] | null)[] = L.map((z, i) => (z === null ? null : z.map((s, k) => [s, `${i},${k}`] as [string, string | null]).filter(x => !weg.has(x[1]!))));
  if (ziel === null) {
    const i0 = M.findIndex(z => z !== null);
    if (i0 < 0) return L;
    M[i0] = [...neue.map(s => [s, null] as [string, string | null]), ...M[i0]!];
  } else {
    const z = M[ziel[0]]!;
    const j = z.findIndex(x => x[1] === ziel.join(','));
    M[ziel[0]] = [...z.slice(0, j + 1), ...neue.map(s => [s, null] as [string, string | null]), ...z.slice(j + 1)];
  }
  return M.map(z => (z === null ? null : z.map(x => x[0])));
};

const schulterOrdnen = (L: Zeilen): Zeilen => {
  const s = saetzeVon(L);
  const kat = s.map(x => {
    const t = x.toLowerCase();
    if (ANS_KONTUR.test(t)) return 'ans';
    if (t.includes(ENTHESIO_SATZ.toLowerCase()) || bejaht(t, ENTH_RX)) return 'ent';
    if (AC_RX.test(t)) return 'ac';
    if (GELENK_RX.test(t) || new RegExp(KL_TAB_RE.source, 'iu').test(x)) return 'g';
    return '';
  });
  if (!kat.includes('ans') && !kat.includes('ent')) return L;
  const g = kat.map((k, i) => (k === 'g' ? i : -1)).filter(i => i >= 0);
  const letztG = g.length ? g[g.length - 1] : -1;
  const acs = kat.map((k, i) => (k === 'ac' && i < letztG ? i : -1)).filter(i => i >= 0);
  const raus = [...kat.map((k, i) => (k === 'ans' || k === 'ent' ? i : -1)).filter(i => i >= 0), ...acs];
  const anker = kat.map((k, i) => ((k === 'g' || k === 'ac') && !raus.includes(i) ? i : -1)).filter(i => i >= 0);
  if (!anker.length) return L;
  const neu = [...acs.map(i => s[i]), ...s.filter((_x, i) => kat[i] === 'ans'), ...s.filter((_x, i) => kat[i] === 'ent')];
  const reihe = s.map((_x, i) => i).filter(i => !raus.includes(i));
  const p = reihe.indexOf(anker[anker.length - 1]) + 1;
  const probe = [...reihe.slice(0, p).map(i => s[i]), ...neu, ...reihe.slice(p).map(i => s[i])];
  if (probe.length === s.length && probe.every((x, i) => x === s[i])) return L;
  return umstellen(L, raus, anker[anker.length - 1], neu);
};

const enthesio = (satz: string, dk: string): string | null => {
  const m = ENTH_SATZ.exec(satz);
  if (!m || !m[2]) return null;
  let ort = m[2].trim().replace(/\.$/u, '');
  const ol = ort.toLowerCase();
  if (/^(?:am|an der|an den|an|im bereich)\s/u.test(ol)) { /* bleibt */ }
  else if (ol.startsWith('des ')) ort = 'am ' + ort.slice(4);
  else if (ol.startsWith('der ')) ort = 'an der ' + ort.slice(4);
  else if (ol.startsWith('vom ')) ort = 'am ' + ort.slice(4);
  else if (ol.startsWith('von der ')) ort = 'an der ' + ort.slice(8);
  else ort = 'am ' + ort;
  let adj = m[1] || '';
  if (!adj) { const md = ENTH_DIKTAT.exec(dk || ''); adj = md ? md[1] : ''; }
  const wort = adj ? (ENTH_ADJ.find(([rx]) => rx.test(adj))?.[1] ?? '') : '';
  return wort ? `${wort} ${ENTHESIO_SATZ} ${ort}.` : `${ENTHESIO_SATZ[0].toUpperCase()}${ENTHESIO_SATZ.slice(1)} ${ort}.`;
};

const bursa = (L: Zeilen, dk: string): [Zeilen, string[]] => {
  const s = saetzeVon(L);
  const nI = s.findIndex(x => x.toLowerCase().includes('bursa') && BURSA_NORMAL.test(x.toLowerCase()) && !STEP_NORMAL.test(x.toLowerCase()));
  const stI = s.findIndex(x => STEP_NORMAL.test(x.toLowerCase()));
  const rest = s.filter((_x, i) => i !== nI && i !== stI).map(x => x.toLowerCase()).join(' ');
  const aend: string[] = [];
  const raus: number[] = [];
  let neu: string[] = [], nach = -1;
  if (stI >= 0 && (bejaht(dk, STEP_PATHO) || bejaht(rest, STEP_PATHO))) { raus.push(stI); aend.push(`Step-sign-Normalsatz gestrichen: ${s[stI].slice(0, 50)}`); }
  if (nI >= 0 && (bejaht(dk, BURSA_PATHO) || bejaht(rest, BURSA_PATHO))) {
    const p = s.findIndex((x, i) => i !== nI && i !== stI && bejaht(x.toLowerCase(), BURSA_PATHO));
    raus.push(nI);
    aend.push(`Bursa-Normalsatz gestrichen: ${s[nI].slice(0, 50)}`);
    if (p >= 0) {
      raus.push(p);
      neu = [s[p]];
      const vor = [...Array(nI).keys()].filter(i => !raus.includes(i));
      nach = vor.length ? vor[vor.length - 1] : -1;
    }
  }
  if (!raus.length) return [L, []];
  return [umstellen(L, [...new Set(raus)].sort((a, b) => a - b), nach, neu), aend];
};

const fraktur = (L: Zeilen): [Zeilen, string[]] => {
  const s = saetzeVon(L);
  const f = s.map((x, i) => (bejaht(x.toLowerCase().replace(NICHT_DISLOZIERT, ''), FRAKTUR_RX) && !UEBRIGEN_ANFANG.test(x) ? i : -1)).filter(i => i >= 0);
  const k = s.findIndex((x, i) => x.toLowerCase().includes('kortikalis') && /glatt|scharf|regelrecht/u.test(x.toLowerCase()) && !f.includes(i));
  if (!f.length || k < 0) return [L, []];
  const nachK = f.filter(i => i > k);
  if (!nachK.length) {
    if (k === f[f.length - 1] + 1 && s[k] === KORTIKALIS_UEBRIGEN) return [L, []];
    return [umstellen(L, [k], f[f.length - 1], [KORTIKALIS_UEBRIGEN]), ['Kortikalis-Satz direkt hinter die Fraktur']];
  }
  const vor = [...Array(k).keys()].filter(i => !nachK.includes(i));
  return [umstellen(L, [...nachK, k], vor.length ? vor[vor.length - 1] : -1, [...nachK.map(i => s[i]), KORTIKALIS_UEBRIGEN]),
    ['Fraktur an die Stelle der Kortikalis-Beschreibung']];
};

const uebrigenNurNachPatho = (L: Zeilen, templates?: VorlagenMap): [Zeilen, string[]] => {
  const s = saetzeVon(L);
  const aend: string[] = [];
  const pos = flach(L);
  for (let j = 1; j < s.length; j++) {
    const m = UEBRIGEN_ANFANG.exec(s[j]);
    if (!m || s.slice(0, j).some(pathoSatz)) continue;
    const rest = s[j].slice(m[0].length);
    let neu: string | null;
    if (WID_VERB.test(rest.split(' ', 1)[0].toLowerCase())) { neu = vorlageZurueck(rest, templates); if (neu === null) continue; }
    else neu = rest.slice(0, 1).toUpperCase() + rest.slice(1);
    aend.push(`ohne „${m[1]}“ (keine Pathologie davor): ${neu.slice(0, 50)}`);
    L[pos[j][0]]![pos[j][1]] = neu;
    s[j] = neu;
  }
  return [L, aend];
};

const seitenAus = (t0: string, titelSeite = ''): Set<string> => {
  const t = (t0 || '').toLowerCase();
  if (/beidseit|(?<![a-zäöüß])bds(?![a-zäöüß])|beider/u.test(t)) return new Set(['rechts', 'links']);
  const out = new Set<string>();
  if (WID_RECHTS.test(t)) out.add('rechts');
  if (WID_LINKS.test(t)) out.add('links');
  if (!out.size && (titelSeite === 'rechts' || titelSeite === 'links')) out.add(titelSeite);
  return out;
};

const huefteSeiten = (L: Zeilen, titel: string): [Zeilen, string[]] => {
  const ts = widSeite(titel);
  const betr = new Set<string>();
  for (const x of saetzeVon(L)) {
    if (HUEFTKOPF_BDS.test(x) || HUEFTKOPF_EIN.test(x) || HUEFT_SPALT.test(x) || HUEFT_EIN_FORM.test(x)) continue;
    const t = x.toLowerCase();
    for (const m of t.matchAll(HUEFT_BETROFFEN)) {
      const vor = t.slice(Math.max(0, m.index! - 60), m.index!).split(/[.;:,\n]/u).pop()!;
      if (NEG_NAH.test(vor)) continue;
      for (const sd of seitenAus(t, ts)) betr.add(sd);
    }
  }
  if (!betr.size) return [L, []];
  const aend: string[] = [];
  const einzeln = !titel.toLowerCase().includes('becken');
  const beide = betr.has('rechts') && betr.has('links');
  const andere = beide ? '' : ['rechts', 'links'].find(x => !betr.has(x))!;
  const adj: Record<string, string> = { rechts: 'rechten', links: 'linken' };
  const pos = flach(L);
  for (let idx = pos.length - 1; idx >= 0; idx--) {
    const [i, k] = pos[idx];
    const x = L[i]![k];
    let neu = x;
    if (HUEFTKOPF_BDS.test(x)) neu = beide ? '' : `Ordnungsgemäße Stellung des normal geformten ${adj[andere]} Hüftkopfes.`;
    else if (HUEFTKOPF_EIN.test(x)) { const sd = HUEFTKOPF_EIN.exec(x)![1] === 'rechten' ? 'rechts' : 'links'; if (betr.has(sd)) neu = ''; }
    else if (HUEFT_SPALT.test(x)) {
      const sm = HUEFT_SPALT.exec(x)![1];
      if (sm) { if (betr.has(sm.toLowerCase())) neu = ''; }
      else if (einzeln) { if (betr.has(ts) || !ts) neu = ''; }
      else if (beide) neu = '';
      else neu = `${cap(andere)} normal konfigurierte, glatte Gelenkflächen mit allseits normal weitem Gelenkspalt.`;
    } else if (HUEFT_EIN_FORM.test(x) && einzeln && (betr.has(ts) || !ts)) neu = '';
    if (neu !== x) {
      aend.push(`Hüfte ${[...betr].sort().join('/')}: ${x.slice(0, 45)} → ${neu.slice(0, 45) || 'gestrichen'}`);
      if (neu) L[i]![k] = neu; else L[i]!.splice(k, 1);
    }
  }
  return [L, aend];
};

const klGradZeile = (z: string): string | null => {
  const m = new RegExp(KL_ADJ_RE.source, 'iu').exec(z || '');
  if (!m) return null;
  return KL_ADJ.find(([, r]) => new RegExp('^(?:' + r + ')$', 'iu').test(m[1]))?.[0] ?? null;
};

const befundOps = (text: string, titel: string, dk: string, templates?: VorlagenMap): [string, string[]] => {
  let L = zerlegen(text);
  if (!flach(L).length) return [text, []];
  const aend: string[] = [];
  const schnitt = SCHNITT_TITEL.test(titel);
  if (!schnitt) {
    for (const [i, k] of flach(L)) {
      const x = L[i]![k];
      if (bejaht(x.toLowerCase(), ENTH_RX) && !/^(?:kein|ohne)/u.test(x.toLowerCase())) {
        const neu = enthesio(x, dk);
        if (neu && neu !== x) { L[i]![k] = neu; aend.push(`Enthesiopathie beschreibend: ${neu.slice(0, 50)}`); }
      }
    }
    if (SCHULTER_TITEL.test(titel)) {
      const L2 = schulterOrdnen(L);
      if (L2 !== L) { L = L2; aend.push('Schulter: Gelenk → AC → „Ansonsten …“ → Enthesiopathie'); }
    }
    if (!WS_TITEL.test(titel) && !THORAX_TITEL.test(titel)) { const [L2, x] = fraktur(L); L = L2; aend.push(...x); }
  }
  if (SONO_TITEL.test(titel)) { const [L2, x] = bursa(L, dk); L = L2; aend.push(...x); }
  if (BECKEN_TITEL.test(titel) && !schnitt) { const [L2, x] = huefteSeiten(L, titel); L = L2; aend.push(...x); }
  { const [L2, x] = uebrigenNurNachPatho(L, templates); L = L2; aend.push(...x); }
  if (!aend.length) return [text, []];
  const lead = text.slice(0, text.length - text.replace(/^\n+/u, '').length);
  const trail = text.slice(text.replace(/\n+$/u, '').length);
  return [lead + zusammen(L).replace(/^\n+|\n+$/gu, '') + trail, aend];
};

type Teil = [number, string, [number, number] | null, [number, number] | null];
const teileVon = (zeilen: string[]): Teil[] => {
  const out: Teil[] = [];
  let akt: Teil | null = null;
  zeilen.forEach((z, i) => {
    const s = z.trim();
    if (!s.startsWith('## ')) return;
    const k = s.slice(3).trim().toLowerCase().replace(/:$/u, '');
    if (k === 'befund' || k === 'ergebnis') {
      if (akt === null) { akt = [-1, '', null, null]; out.push(akt); }
      let j = i + 1;
      while (j < zeilen.length && !zeilen[j].trimStart().startsWith('## ')) j++;
      akt[k === 'befund' ? 2 : 3] = [i + 1, j];
    } else { akt = [i, s.slice(3).trim(), null, null]; out.push(akt); }
  });
  return out;
};
const ergZeilen = (zeilen: string[], e: [number, number]): number[] => {
  const out: number[] = [];
  for (let i = e[0]; i < e[1]; i++) if (zeilen[i].trim()) out.push(i);
  return out;
};

const klErgebnis = (punkte: string[], dk: string): [string[], string[]] => {
  if (!dk || !arthroseDiktiert(dk)) return [punkte, []];
  const aend: string[] = [], out: string[] = [];
  const diktiert = klGrade(dk), adj = new Set(klAdjektivGrade(dk));
  for (const m of dk.matchAll(KL_ADJ_SEITE)) for (const [g, r] of KL_ADJ) if (new RegExp('^(?:' + r + ')$', 'iu').test(m[1])) adj.add(g);
  for (const m of dk.matchAll(KL_SEITE_ADJ)) for (const [g, r] of KL_ADJ) if (new RegExp('^(?:' + r + ')$', 'iu').test(m[1])) adj.add(g);
  for (const p of punkte) {
    const t = ohneNum(p);
    const md = KL_DOPPEL.exec(t);
    if (md && klGradZeile(t)) {
      const [, adj1, diag, s1, adj2, s2] = md;
      if (s1 !== s2) {
        const a = `${adj1}${diag} ${s1}.`, b2 = `${adj2[0].toUpperCase()}${adj2.slice(1)} ${diag} ${s2}.`;
        out.push(a, b2);
        aend.push(`Arthrose je Seite: ${a} / ${b2}`);
        continue;
      }
    }
    out.push(p);
  }
  const fertig: string[] = [];
  for (let p of out) {
    const t = ohneNum(p);
    if (KL_AUSNAHME.test(t) || !ARTHROSE_KI.test(t) || VERNEINT.test(t.split('rthros')[0]) || new RegExp(KL_KI.source, 'i').test(t) || /kellgren/i.test(t)) { fertig.push(p); continue; }
    const g = diktiert.length === 1 ? diktiert[0] : (!diktiert.length ? klGradZeile(t) : null);
    if (g && (diktiert.length || adj.has(g))) {
      let kern = p.trimEnd();
      if (kern.endsWith('.')) kern = kern.slice(0, -1);
      p = `${kern} ${klKlammer(g)}.`;
      aend.push(`K&L-Klammer ergänzt (Grad ${g})`);
    }
    fertig.push(p);
  }
  return [fertig, aend];
};

// eigener Arthrose-Deskriptor der KI → Standardsatz statt (Sync: befund_regeln.py _KL_EIGEN)
const KL_KOMP = /(?<![a-zäöüß])(medial|lateral|femoropatellar|femorotibial|retropatellar|patellofemoral)/u;
const KL_EIGEN = /osteophyt|gelenks?spalt[a-zäöüß]*verschmäler|verschmälerung des [a-zäöüß]+ gelenks?spalt|subchondral/u;
const klBefund = (text: string, punkte: string[], titel: string): [string, string[]] => {
  const je: [string, number][] = [];
  for (const p of punkte) {
    const t = ohneNum(p);
    const m = new RegExp(KL_KI.source, 'i').exec(t);
    if (!m || KL_AUSNAHME.test(t)) continue;
    const g = Number(KL_WERT[(m[1] || m[2] || '').toLowerCase()] ?? '0') || 0;
    if (g && KL_TABELLE[g]) je.push([widSeite(t), g]);
  }
  if (!je.length) return [text, []];
  let L = zerlegen(text);
  const uniq = [...new Map(je.map(x => [x.join('|'), x] as [string, [string, number]])).values()];
  const fehlt = uniq.filter(([, g]) => !saetzeVon(L).some(x => x.toLowerCase().includes(KL_TABELLE[g].slice(0, -1).toLowerCase())));
  if (!fehlt.length) return [text, []];
  const mehr = new Set(je.map(x => x[0])).size > 1;
  const ts = widSeite(titel);
  const aend: string[] = [];
  for (const [sd, g] of fehlt) {
    const satz = KL_TABELLE[g];
    const s = saetzeVon(L);
    const passt = (x: string): boolean => !sd || ['', sd].includes(widSeite(x));
    const diag = s.map((x, i) => ((bejaht(x.toLowerCase(), ARTHROSE_KI) || bejaht(x.toLowerCase(), KL_EIGEN)) && !new RegExp(KL_TAB_RE.source, 'iu').test(x) && !KL_AUSNAHME.test(x) && passt(x)
      && (!mehr || widSeite(x) === sd || !widSeite(x)) ? i : -1)).filter(i => i >= 0);
    const vor: string[] = sd && (mehr || ts !== sd) ? [sd] : [];
    const mk = diag.length ? KL_KOMP.exec(s[diag[0]].toLowerCase()) : null;   // Kompartiment bleibt (kl-knie-betont)
    if (mk) vor.push(mk[1]);
    const vj = vor.join(' ');
    const neu = vor.length ? `${vj[0].toUpperCase()}${vj.slice(1)} ${satz[0].toLowerCase()}${satz.slice(1)}` : satz;
    if (diag.length) L = umstellen(L, diag.slice(0, 1), diag[0] - 1, [neu]);
    else {
      let deg = s.findIndex(x => x.toLowerCase().includes('degenerativ') && !!sd && widSeite(x) === sd);
      if (deg < 0) deg = s.findIndex(x => /gelenkfl|gelenks?spalt/u.test(x.toLowerCase()));   // hinter den Gelenk-Satz
      L = umstellen(L, [], deg >= 0 ? deg : (s.length ? 0 : -1), [neu]);
    }
    aend.push(`K&L-Standardsatz im Befund: ${neu.slice(0, 50)}`);
  }
  const lead = text.slice(0, text.length - text.replace(/^\n+/u, '').length);
  const trail = text.slice(text.replace(/\n+$/u, '').length);
  return [lead + zusammen(L).replace(/^\n+|\n+$/gu, '') + trail, aend];
};

export function georg2311(report: string, diktat = '', templates?: VorlagenMap): [string, string[]] {
  if (!report || !report.includes('## ')) return [report, []];
  let out = report;
  const aend: string[] = [];
  for (const [rx, f] of WORT_ERSETZEN) {
    const neu = out.replace(rx, f as (m: string, ...g: string[]) => string);
    if (neu !== out) { aend.push('Wortlaut periprothetisch/Material'); out = neu; }
  }
  const dk = (diktat || '').toLowerCase();
  let zeilen = out.split('\n');
  let ergNeu = false;
  let teile = teileVon(zeilen);
  const beckenDa = teile.some(([, t]) => BECKEN_TITEL.test(t) && !SCHNITT_TITEL.test(t));
  for (const [, titel, b] of [...teile].reverse()) {
    if (!b) continue;
    const text = zeilen.slice(b[0], b[1]).join('\n');
    const [neu, x] = befundOps(text, titel, dk, templates);
    if (x.length) { zeilen.splice(b[0], b[1] - b[0], ...neu.split('\n')); aend.push(...x); }
  }
  teile = teileVon(zeilen);
  if (beckenDa) {
    const wandern: string[] = [];
    for (const [, titel, b, e] of teile) {
      if (!WS_TITEL.test(titel)) continue;
      for (const rng of [b, e]) {
        if (!rng) continue;
        for (let i = rng[0]; i < rng[1]; i++) {
          const t = ohneNum(zeilen[i]);
          if (HIPPO_SATZ.test(t)) { wandern.push(satzform(t)); zeilen[i] = '\u0000'; }
        }
      }
    }
    if (wandern.length) {
      zeilen = zeilen.filter(z => z !== '\u0000');
      teile = teileVon(zeilen);
      const ziel = teile.find(t => BECKEN_TITEL.test(t[1]) && !SCHNITT_TITEL.test(t[1]) && t[2]);
      if (ziel) {
        const [b0, b1] = ziel[2]!;
        const schon = zeilen.slice(b0, b1).join('\n');
        const rein = [...new Set(wandern)].filter(w => !schon.includes(w));
        let k = -1;
        for (let i = b0; i < b1; i++) if (zeilen[i].trim()) { k = i; break; }
        if (rein.length && k >= 0) zeilen[k] = rein.join(' ') + ' ' + zeilen[k].trimStart();
        aend.push(`HIPPO-Sätze aus dem Wirbelsäulen-Teil in die Beckenübersicht (${wandern.length})`);
      }
      ergNeu = true;
      teile = teileVon(zeilen);
    }
  }
  for (const [, titel, b, e] of [...teile].reverse()) {
    if (!e) continue;
    const idx = ergZeilen(zeilen, e);
    const bef = b ? zeilen.slice(b[0], b[1]).join('\n') : '';
    let punkte = idx.map(i => zeilen[i]);
    const alt = [...punkte];
    const schnitt = SCHNITT_TITEL.test(titel);
    if (BECKEN_TITEL.test(titel) && !schnitt) {
      const m = [...bef.matchAll(BS_GROSS)].find(x => Number(x[1]) >= 10);
      if (m && !punkte.some(p => p.toLowerCase().includes('beckenschiefstand'))) {
        const satz = `Beckenschiefstand von ${m[1]} mm` + (m[2] ? `, ${m[2]} tiefer.` : '.');
        punkte = punkte.filter(p => !(WID_NORMAL_ERG.test(p) && !hasPathology(p)));
        punkte.unshift(satz);
        aend.push(`HIPPO ≥ 10 mm ins Ergebnis: ${satz}`);
      }
    }
    if (!schnitt && !WS_TITEL.test(titel)) { const [p2, x] = klErgebnis(punkte, dk); punkte = p2; aend.push(...x); }
    if (SCHULTER_TITEL.test(titel) && !schnitt) {
      const rang = (p: string): number | null => {
        const t = p.toLowerCase();
        return /omarthros|glenohumeral/u.test(t) ? 0 : AC_RX.test(t) ? 1 : t.includes('enthesiopath') ? 2 : null;
      };
      const slots = punkte.map((p, k) => (rang(p) !== null ? k : -1)).filter(k => k >= 0);
      const sortiert = slots.map(k => punkte[k]).map((p, k) => [p, k] as [string, number])
        .sort((x, y) => rang(x[0])! - rang(y[0])! || x[1] - y[1]).map(x => x[0]);
      slots.forEach((k, j) => { punkte[k] = sortiert[j]; });
    }
    if (NERV_TITEL.test(titel)) {
      const mn = NERV_NAME.exec(titel) || NERV_NAME.exec(bef);
      if (mn) {
        const name = mn[1].toLowerCase();
        const saetze = [...diktatSaetze(diktat || '').map(([a, c]) => (diktat || '').slice(a, c)), ...saetzeMitLage(bef).map(([a, c]) => bef.slice(a, c))];
        const nervPatho = saetze.some(x => bejaht(x.toLowerCase(), NERV_PATHO) && (x.toLowerCase().includes(name) || x.toLowerCase().includes('nerv')));
        if (!nervPatho && !punkte.some(p => p.toLowerCase().includes(name) && p.toLowerCase().includes('unauffällig'))) {
          const ds = diktierteSeite(dk);
          const sd = widSeite(titel) || (ds === 'rechts' || ds === 'links' ? ds : '');
          const satz = NERV_UNAUFFAELLIG.replace('{name}', name).replace('{seite}', sd ? ' ' + sd : '');
          punkte = punkte.filter(p => !['unauffälliger befund', 'regelrechte darstellung'].includes(ohneNum(p).replace(/\.$/u, '').toLowerCase()));
          punkte.unshift(satz);
          aend.push(`Nerv unauffällig: ${satz}`);
        }
      }
    }
    const v = punkte.map((p, k) => (VERLAUF.test(ohneNum(p)) && !UNNUM_RE.test(ohneNum(p)) ? k : -1)).filter(k => k >= 0);
    if (v.length && v[0] !== 0) {
      const [p] = punkte.splice(v[0], 1);
      punkte.unshift(p);
      aend.push(`Verlauf als 1. Punkt: ${ohneNum(p).slice(0, 50)}`);
    }
    if (punkte.length !== alt.length || punkte.some((p, k) => p !== alt[k])) {
      ergNeu = true;
      if (idx.length) zeilen.splice(idx[0], idx[idx.length - 1] + 1 - idx[0], ...punkte);
      else zeilen.splice(e[0], 0, ...punkte);
    }
  }
  teile = teileVon(zeilen);
  for (const [, titel, b, e] of [...teile].reverse()) {
    if (!dk || !b || !e || SCHNITT_TITEL.test(titel) || WS_TITEL.test(titel)) continue;
    const [neu, x] = klBefund(zeilen.slice(b[0], b[1]).join('\n'), ergZeilen(zeilen, e).map(i => zeilen[i]), titel);
    if (x.length) { zeilen.splice(b[0], b[1] - b[0], ...neu.split('\n')); aend.push(...x); }
  }
  const dunn = ZUSATZPROJEKTIONEN.dunn;
  if (dunn.aktiv && new RegExp(dunn.diktat, 'u').test(dk)) {
    for (const [ti, titel] of teileVon(zeilen)) {
      if (ti >= 0 && new RegExp(dunn.region, 'iu').test(titel) && !titel.toLowerCase().includes('dunn')) {
        const bds = /dunn[^.]{0,40}(?:beidseit|bds)|(?:beidseit|bds)[^.]{0,40}dunn/u.test(dk);
        zeilen[ti] = zeilen[ti].trimEnd() + (bds ? DUNN_TITEL_BDS : DUNN_TITEL);
        aend.push('Titel mit Dunn-Aufnahme');
      }
    }
  }
  out = zeilen.join('\n');
  if (ergNeu) out = ergebnisNummerieren(out);
  return [out, aend];
}

const abschnitteVon = (b: string): { befund: string[]; ergebnis: string[] } => {
  const t = { befund: [] as string[], ergebnis: [] as string[] };
  let akt: 'befund' | 'ergebnis' | null = null;
  for (const z of b.split('\n')) {
    const s = z.trim();
    const k = s.startsWith('## ') ? s.slice(3).trim().toLowerCase().replace(/:$/u, '') : null;
    if (k === 'befund' || k === 'ergebnis') { akt = k; continue; }
    if (akt && s) t[akt].push(s);
  }
  return t;
};
const bloeckeVereinen = (a: string, b: string): string => {
  const ta = abschnitteVon(a), tb = abschnitteVon(b);
  const altText = ta.befund.join(' ');
  const dazu: string[] = [];
  for (const z of tb.befund) for (const [x0, x1] of saetzeMitLage(z)) {
    const x = z.slice(x0, x1).trim();
    if (x && !altText.includes(x) && !vorlageNormalisieren(altText).includes(vorlageNormalisieren(x))) dazu.push(x);
  }
  let ergAlt = ta.ergebnis.map(ohneNum);
  const ergDazu = tb.ergebnis.map(ohneNum).filter(z => !ergAlt.includes(z) && !(WID_NORMAL_ERG.test(z) && ergAlt.some(e => !WID_NORMAL_ERG.test(e))));
  if (ergDazu.some(e => !WID_NORMAL_ERG.test(e))) ergAlt = ergAlt.filter(e => !(WID_NORMAL_ERG.test(e) && !hasPathology(e)));
  const kopf = a.trim().split('\n', 1)[0];
  const bef = ta.befund.length <= 1 ? [...ta.befund, ...dazu].join(' ') : [...ta.befund, ...(dazu.length ? [dazu.join(' ')] : [])].join('\n');
  return `${kopf}\n\n## Befund\n${bef}\n\n## Ergebnis\n` + [...ergAlt, ...ergDazu].join('\n');
};

export function teileZusammenlegen(report: string, diktat = ''): [string, string[]] {
  if (!report || (report.match(/## /gu) || []).length < 4) return [report, []];
  const bloecke = report.trim().split(/\n{2,}(?=## (?!Befund\b|Ergebnis\b))/u).filter(b => b.trim());
  if (bloecke.length < 2) return [report, []];
  const kopf = (b: string): string => {
    const z = b.trim().split('\n', 1)[0].trim();
    return z.startsWith('## ') && !['befund', 'ergebnis'].includes(z.slice(3).trim().toLowerCase().replace(/:$/u, '')) ? z.slice(3).trim().toLowerCase() : '';
  };
  const aend: string[] = [], out: string[] = [];
  const gesehen = new Map<string, number>();
  const titelAlle = bloecke.map(kopf);
  for (const b of bloecke) {
    const k = kopf(b);
    if (k && k.includes('unterarm') && diktat && !diktat.toLowerCase().includes('unterarm') && titelAlle.some(t => t !== k && /handgelenk|ellbogen/u.test(t))) {
      aend.push('Teil „Unterarm“ ohne diktierten Unterarm entfernt');
      continue;
    }
    if (k && gesehen.has(k)) {
      const z = gesehen.get(k)!;
      out[z] = bloeckeVereinen(out[z], b);
      aend.push(`doppelter Teil zusammengelegt: ${k.slice(0, 40)}`);
      continue;
    }
    if (k) gesehen.set(k, out.length);
    out.push(b);
  }
  if (!aend.length) return [report, []];
  return [ergebnisNummerieren(out.map(x => x.trim()).join('\n\n\n')), aend];
}

export function pruefzeilen2311(report: string, templates?: VorlagenMap): string[] {   // Sync: pruefzeilen_2311 (ohne Diktat)
  const out: string[] = [];
  const zeilen = (report || '').split('\n');
  const vorlagen = templates ? vorlagenSaetze(templates)[0] : new Map<string, Set<string>>();
  for (const [, titel, b, e] of teileVon(zeilen)) {
    const name = titel || 'Befund';
    if (e && !ergZeilen(zeilen, e).length) { out.push(`${name}: Ergebnis leer – bitte prüfen`); continue; }
    if (!b || !e) continue;
    const punkte = ergZeilen(zeilen, e).map(i => ohneNum(zeilen[i]));
    const zaehl = punkte.filter(p => !UNNUM_RE.test(p));
    const nurNormal = punkte.length > 0 && zaehl.every(p => WID_NORMAL_ERG.test(p) && !hasPathology(p));
    const bef = zeilen.slice(b[0], b[1]).join(' ');
    BS_GROSS.lastIndex = 0;
    const patho = saetzeMitLage(bef).map(([x, y]) => bef.slice(x, y)).filter(s => pathoSatz(s) && !HIPPO_SATZ.test(s)
      && !new RegExp(BS_GROSS.source, 'u').test(s) && !UEBRIGEN_ANFANG.test(s) && !s.includes(OSTEOPEN_SATZ)
      && !vorlagen.has(vorlageNormalisieren(s)) && !/^(?:normale?|regelrechte?|unauffällige?)(?![a-zäöüß])/iu.test(s));
    if (nurNormal && patho.length) out.push(`${name}: Befund nicht geformt – „Regelrechte Darstellung“ trotz Pathologie, bitte prüfen`);
  }
  return out;
}

// 49a/52: Überschriften im Nur-Text-Weg als „## …“ (Sync: befund_regeln.py nur_text_ueberschriften)
const NT_KOPF = /^\s*(?:\*\*)?\s*(Befund|Ergebnis|Beurteilung)\s*:?\s*(?:\*\*)?\s*$/iu;
const NT_KOPF_TEXT = /^\s*(?:\*\*)?\s*(Ergebnis|Beurteilung)\s*:\s*(?:\*\*)?\s*(\S.*)$/iu;
const NT_TITEL = /^\s*(?:\*\*)?\s*([A-ZÄÖÜ][^.:;!?\n]{2,80}?)\s*:\s*(?:\*\*)?\s*$/u;
const NT_UNTERSUCHUNG = /röntgen|sonogra|ultraschall|(?<![a-zäöüß])(?:mr|mrt|ct)(?![a-zäöüß])|aufnahme|übersicht|ebenen|ganzbein|mammogra|weichteil|gelenk|wirbelsäule|thorax|abdomen|schulter|hüft|knie|becken|hand|fuß|fuss|ellbogen|sprung|unterarm|unterschenkel|oberarm|oberschenkel|nerv|(?<![a-zäöüß])(?:hws|bws|lws|gws|n\.)(?![a-zäöüß])/iu;
export function nurTextUeberschriften(text: string): string {
  if (!text || text.includes('## ')) return text;
  let geaendert = false;
  const aus: string[] = [];
  for (const z of text.split('\n')) {
    const m = NT_KOPF.exec(z), mt = NT_KOPF_TEXT.exec(z), mu = NT_TITEL.exec(z);
    if (m) aus.push('## ' + m[1][0].toUpperCase() + m[1].slice(1).toLowerCase());
    else if (mt) aus.push('## ' + mt[1][0].toUpperCase() + mt[1].slice(1).toLowerCase(), mt[2]);
    else if (mu && mu[1].split(/\s+/u).filter(Boolean).length <= 8 && NT_UNTERSUCHUNG.test(mu[1])) aus.push('## ' + mu[1].trim());
    else { aus.push(z); continue; }
    geaendert = true;
  }
  return geaendert ? aus.join('\n') : text;
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

// ══ kaiscribe-ursula-2011-text-n1 (Ursula Hofmeister, Durchsicht der KaiScribe-Briefe vom 20.11.2026) – Sync:
// befund_regeln.py ursula_2011 / ergebnis_text_sichern / befund_schluss, Fixtures „ursula_2011“. Beschreibung siehe dort.
const PROZENTIG = /(?<![\d,])(\d+(?:,\d+)?)[ \t]?-?[ \t]?(?:[Pp]rozent|%)[ \t]?-?[ \t]?ig(e[nrsm]?)?(?![a-zäöüß])/gu;
const WS_SEITE = /[ \t]*(?<![A-Za-z0-9_ÄÖÜäöüß-])(?:beidseits|beidseitig|bds\.|bds|rechts|links|re\.|li\.)(?![A-Za-z0-9_ÄÖÜäöüß-])/giu;
const WS_PAARIG = /hüft|becken|knie|schulter|sprung|fu(?:ß|ss)|hand|finger|zehe|ellbogen|iliosakral|rippe|clavicula|klavikula|(?<![a-zäöüß])(?:isg|sig)(?![a-zäöüß])/iu;
const IM_UEBRIGEN = /^Im [Üü]brigen,?\s+/u;
const LABEL_UEBRIGEN = /^([A-ZÄÖÜ][^:.]{0,48}):\s+im [Üü]brigen\s+/u;
const TROCHANTER = /(?<![A-Za-zÄÖÜäöüß])((?:[Pp]er|[Ii]nter|[Ss]ub|[Pp]eri)?)([Tt])rochanter(e[nrsm]?)?(?![A-Za-zäöüß])/gu;
const VERKLAKUNG = /(?<![A-Za-zÄÖÜäöüß])([Vv])erklak(ung(?:en)?|t(?:e[nrsm]?)?)(?![a-zäöüß])/gu;
const TH_WIRBEL = /(?<![A-Za-zÄÖÜäöüß])T[Hh][ \t]?(1[0-2]|[1-9])(?!\d)/gu;

const uebrigenFolge = (L: Zeilen, templates?: VorlagenMap): [Zeilen, string[]] => {
  const s = saetzeVon(L), pos = flach(L), aend: string[] = [];
  let davor = false;
  s.forEach((x, j) => {
    const m = IM_UEBRIGEN.exec(x), ml = LABEL_UEBRIGEN.exec(x);
    if (m || ml) {
      if (davor) {
        let neu: string | null;
        if (m) {
          const rest = x.slice(m[0].length);
          neu = WID_VERB.test(rest.split(' ', 1)[0].toLowerCase()) ? vorlageZurueck(rest, templates)
            : (vorlageZurueck(rest, templates) ?? rest.slice(0, 1).toUpperCase() + rest.slice(1));
        } else {
          const kurz = ml![1] + ': ' + x.slice(ml![0].length);
          neu = vorlageZurueck(kurz, templates) ?? kurz;
        }
        if (neu) {
          aend.push(`„Im Übrigen“ nicht doppelt: ${neu.slice(0, 50)}`);
          L[pos[j][0]]![pos[j][1]] = neu;
          s[j] = neu;
        }
      }
      davor = true;
    } else if (pathoSatz(x)) davor = false;
  });
  return [L, aend];
};

export function ursula2011(report: string, templates?: VorlagenMap): [string, string[]] {
  if (!report) return [report, []];
  const aend: string[] = [];
  const zeilen = report.split('\n');
  zeilen.forEach((z, i) => {
    const s = z.trim();
    if (s.startsWith('## ') && !['befund', 'ergebnis'].includes(s.slice(3).trim().toLowerCase().replace(/:+$/u, ''))
      && WS_TITEL.test(s) && !WS_PAARIG.test(s) && new RegExp(WS_SEITE.source, 'iu').test(s.slice(3))) {
      const neu = '## ' + s.slice(3).replace(WS_SEITE, ' ').split(/\s+/u).filter(Boolean).join(' ');
      if (neu !== s) { zeilen[i] = neu; aend.push(`Wirbelsäule ohne Seite: ${neu.slice(3)}`); }
    }
  });
  for (const [a, e] of abschnitt(zeilen, 'befund').reverse()) {
    const text = zeilen.slice(a, e).join('\n');
    const L0 = zerlegen(text);
    if (!flach(L0).length) continue;
    const [L, x] = uebrigenFolge(L0, templates);
    if (x.length) {
      aend.push(...x);
      const lead = text.slice(0, text.length - text.replace(/^\n+/u, '').length);
      const trail = text.slice(text.replace(/\n+$/u, '').length);
      zeilen.splice(a, e - a, ...(lead + zusammen(L).replace(/^\n+|\n+$/gu, '') + trail).split('\n'));
    }
  }
  let out = zeilen.join('\n');
  const regeln: [string, RegExp, (m: string, ...g: string[]) => string][] = [
    ['Prozent', PROZENTIG, (_m, z, e) => z + '%ig' + (e || '')],
    ['trochantär', TROCHANTER, (m, vor, t, endung) => (!vor && t === 'T' && !endung) ? m : vor + t + 'rochantär' + (endung || '')],
    ['Verkalkung', VERKLAKUNG, (_m, v, rest) => v + 'erkalk' + rest],
    ['Th + Zahl', TH_WIRBEL, (_m, n) => 'Th' + n],
  ];
  for (const [name, rx, ers] of regeln) {
    const neu = out.replace(rx, ers as (m: string, ...g: string[]) => string);
    if (neu !== out) { aend.push(`Schreibweise ${name}`); out = neu; }
  }
  return [out, aend];
}

export function ergebnisTextSichern(report: string): string {
  if (!report || !report.includes('## ')) return report;
  const out: string[] = [];
  let imErg = false;
  const zeilen = report.split('\n');
  const naechsterKopf = (i: number): string | null => {
    for (const z2 of zeilen.slice(i + 1)) if (z2.trim().startsWith('## ')) return z2.trim().slice(3).trim().toLowerCase().replace(/:+$/u, '');
    return null;
  };
  for (const [i, z] of zeilen.entries()) {
    const s = z.trim();
    if (!s.startsWith('## ')) { out.push(z); continue; }
    const k = s.slice(3).trim();
    const m = /^ergebnis\s*:\s*(\S.*)$/iu.exec(k);
    if (m) { out.push('## Ergebnis', m[1]); imErg = true; continue; }
    const kl = k.toLowerCase().replace(/:+$/u, '');
    if (kl === 'ergebnis') imErg = true;
    else if (kl === 'befund') imErg = false;
    else if (imErg && (/[.!?]$/u.test(k) || /^\d+[.)]\s/u.test(k)) && !['befund', 'ergebnis'].includes(naechsterKopf(i) ?? '')) { out.push(k); continue; }
    else imErg = false;
    out.push(z);
  }
  return out.join('\n');
}

const LOSE_REGION = new RegExp('^(?:' + MOD + '(?:(?:der|die|das|des)\\s+)?(?:' + REGION_ALT + '|' +
  REGIONEN_OHNE_SEITE.map(([, p]) => p).join('|') + ')(?:\\s+in\\s+(?:2|zwei)\\s+ebenen)?(?:\\s+' + SEITE + ')?)\\s*[.:]?$', 'iu');

// kaiscribe-dexa-doppelt-rh60-n1 (Ursula 23.11.2026, RH 60): nie ein unbefüllter Platzhalter [...] im Befund – sichtbare
// Lücke „…“ + rote Prüfzeile, der Satz bleibt. Sync: befund_regeln.py platzhalter_entfernen / PLATZHALTER_ZEILE.
export const PLATZHALTER = /\[[^[\]\n]{1,40}\]/g;
export const PLATZHALTER_ZEILE = '{name}: Platzhalter {ph} nicht befüllt (im Befund „…“) – bitte ergänzen, bitte prüfen';

export function platzhalterEntfernen(report: string): [string, string[]] {
  if (!report || !(report.match(PLATZHALTER) || []).length) return [report, []];
  const out: string[] = [], zeilen: string[] = [];
  let titel = 'Befund';
  for (const z of report.split('\n')) {
    const k = z.trim();
    if (k.startsWith('## ') && !['befund', 'ergebnis'].includes(k.slice(3).trim().replace(/:$/, '').toLowerCase())) titel = k.slice(3).trim();
    for (const ph of [...new Set(z.match(PLATZHALTER) || [])]) {
      const h = PLATZHALTER_ZEILE.replace('{name}', titel).replace('{ph}', ph);
      if (!zeilen.includes(h)) zeilen.push(h);
    }
    out.push(z.replace(PLATZHALTER, '…'));
  }
  return [out.join('\n'), zeilen];
}

export function befundSchluss(report: string): [string, string[]] {
  if (!report || !report.includes('## ')) return [report, []];
  let zeilen = report.split('\n');
  const aend: string[] = [];
  for (let i = 0; i < zeilen.length; i++) {
    if (zeilen[i].trim().toLowerCase().replace(/:+$/u, '') === '## ergebnis') {
      let j = i + 1;
      while (j < zeilen.length && !zeilen[j].trim()) j++;
      if (j > i + 1 && j < zeilen.length && !zeilen[j].trimStart().startsWith('## ')) {
        zeilen.splice(i + 1, j - i - 1);
        aend.push('Leerzeile nach „Ergebnis“ weg');
      }
    }
  }
  const kopf = (z: string): boolean => z.trim().startsWith('## ') && !['befund', 'ergebnis'].includes(z.trim().slice(3).trim().toLowerCase().replace(/:+$/u, ''));
  const titel = zeilen.map((z, i) => (kopf(z) ? i : -1)).filter(i => i >= 0);
  const teile: [number, number][] = titel.map((t, k) => [t, k + 1 < titel.length ? titel[k + 1] : zeilen.length]);
  const inhalt = (a: number, b: number): number[] => {
    const o: number[] = [];
    for (let j = a; j < b; j++) if (zeilen[j].trim() && !zeilen[j].trim().startsWith('## ')) o.push(j);
    return o;
  };
  const weg = new Set<number>();
  for (const [a, b] of teile) {
    const c = inhalt(a + 1, b);
    if (c.length && LOSE_REGION.test(zeilen[c[c.length - 1]].trim())) {
      aend.push(`loses Wort weg: ${zeilen[c[c.length - 1]].trim().slice(0, 30)}`);
      weg.add(c[c.length - 1]);
    }
  }
  const voll = teile.filter(([a, b]) => inhalt(a + 1, b).some(j => !weg.has(j)));
  if (voll.length) {
    for (const t of teile) {
      if (!voll.includes(t)) {
        aend.push(`Überschrift ohne Inhalt weg: ${zeilen[t[0]].trim().slice(3, 43)}`);
        for (let j = t[0]; j < t[1]; j++) weg.add(j);
      }
    }
  }
  if (!weg.size) return [zeilen.join('\n'), aend];
  zeilen = zeilen.filter((_z, j) => !weg.has(j));
  while (zeilen.length && !zeilen[zeilen.length - 1].trim()) zeilen.pop();
  return [zeilen.join('\n'), aend];
}
