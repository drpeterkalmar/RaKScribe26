// normalbypass.ts — v3.2: Wann darf der Normalbefund-Bypass (ohne LLM) laufen?
// Pendant: source_code/normalbypass.py (gleiche Semantik, gleiche Fixtures: normal_bypass_tests.json).
//
// Peter 05.10.: Der alte Bypass schrieb das Diktat 1:1 ins Ergebnis und griff auch bei Diktaten wie
// "Thorax: Kardiomegalie, sonst unauffällig". Jetzt steht im Bypass-Ergebnis der Normal-Ergebnis-Satz
// des Templates — deshalb greift der Bypass NUR, wenn das Diktat ausschließlich aus
// Untersuchungsbezeichnung + Normal-Worten besteht. Jedes unbekannte Wort → LLM-Strukturierung.

const NORMAL_MARKERS = /unauff(?:ae|ä)?llig|\bnormal|regelrecht|\bob\b|ohne (?:pathologischen )?befund|kein pathologischer befund|normalbefund/;
const RESTWORTE = new Set(["sonst", "ansonsten", "übrigen", "übrigens", "abgesehen", "außer", "ausser", "bis", "aber", "jedoch",
  "bei", "mit", "wie", "vereinbar", "verdacht", "v.a", "va", "dd", "z.n", "zn", "zustand", "nach"]);
const FUELL = new Set([
  "und", "in", "der", "die", "das", "des", "dem", "den", "ist", "sind", "im", "am", "zum", "zur", "vom", "von",
  "beider", "beide", "beidseits", "beidseitig", "bds", "links", "rechts", "li", "re", "linkes", "rechtes",
  "linken", "rechten", "linke", "rechte", "seitlich", "seitl", "pa", "p", "a", "ap", "lateral", "axial",
  "ebenen", "ebene", "zwei", "2", "1", "3", "eine", "ein", "röntgen", "rö", "roentgen", "aufnahme", "aufnahmen",
  "befund", "ohne", "kein", "keine", "pathologisch", "pathologischen", "pathologischer", "sono", "sonographie",
  "sonografie", "ultraschall", "untersuchung", "stehend", "liegend", "stand", "liegen", "vollkommen", "völlig",
  "komplett", "insgesamt", "altersentsprechend", "altersentsprechender", "darstellung", "dargestellt",
  "unauffällig", "unauffällige", "unauffälliger", "unauffälliges", "unauffaellig", "unauffällig.", "normal",
  "normale", "normaler", "normales", "regelrecht", "regelrechte", "regelrechter", "regelrechtes", "ob",
  "normalbefund", "also", "hier", "heute", "punkt", "es", "sich", "zeigt", "zeigen", "sowie",
]);
const SYNONYME = [
  "lunge", "lungen", "herz", "brustkorb", "thorax", "torax", "hws", "bws", "lws", "hw", "osg", "usg", "isg",
  "knie", "hüfte", "hüft", "hüften", "schulter", "schultern", "ellbogen", "ellenbogen", "sprunggelenk",
  "handgelenk", "hand", "fuß", "fuss", "finger", "daumen", "zehe", "zehen", "becken", "schädel", "kopf",
  "nnh", "nebenhöhlen", "wirbelsäule", "halswirbelsäule", "brustwirbelsäule", "lendenwirbelsäule",
  "gelenk", "gelenke", "gelenks", "skelett", "mamma", "mammae", "brust", "brüste", "abdomen", "bauch",
  "schilddrüse", "sd", "nerv", "nervus", "n", "m", "muskel", "muskulatur", "weichteile", "weichteil",
  "unterschenkel", "oberschenkel", "unterarm", "oberarm", "venen", "beinvenen", "halsgefäße", "carotis",
  "carotiden", "duplex", "rippen", "sternum", "kreuzbein", "steißbein", "calcaneus", "ferse", "kahnbein",
  "skaphoid", "scaphoid", "orbita", "orbitae", "jochbein", "jochbogen", "nasenbein", "kiefer", "opg",
];
const WORTTEILE = ["röntgen", "roentgen", "aufnahme", "aufnahmen", "sonographie", "sonografie", "sono", "schall",
  "ultraschall", "gelenk", "gelenks", "gelenke", "bild", "untersuchung"];
const FUGEN = ["", "s", "n", "en", "e"];

function regionWords(displayNames: string[]): Set<string> {
  const w = new Set(SYNONYME);
  for (const dn of displayNames) {
    for (const t of (dn || "").toLowerCase().match(/[a-zäöüß]+/g) || []) {
      if (t.length >= 2 && !RESTWORTE.has(t)) w.add(t);
    }
  }
  return w;
}

function tokens(text: string): string[] {
  let t = text.toLowerCase();
  t = t.replace(/o\.\s*b\.?/g, " ob ");
  t = t.replace(/p\.\s*a\.?/g, " pa ");
  t = t.replace(/a\.\s*-?\s*p\.?/g, " ap ");
  t = t.replace(/[^\p{L}\p{N}_]+/gu, " ");
  const out: string[] = [];
  for (const tok of t.split(/\s+/).filter(Boolean)) out.push(...tok.split("_").filter(Boolean));
  return out;
}

function compoundOk(tok: string, allowed: Set<string>): boolean {
  const parts = new Set([...allowed, ...WORTTEILE]);
  for (let i = 2; i < tok.length - 1; i++) {
    const a = tok.slice(0, i), b = tok.slice(i);
    if (!parts.has(b)) continue;
    for (const f of FUGEN) {
      if (f && a.endsWith(f) && parts.has(a.slice(0, -f.length))) return true;
      if (!f && parts.has(a)) return true;
    }
  }
  return false;
}

/** true = Diktat ist ein reiner Normalbefund (nur Untersuchung + Normal-Worte) → Bypass erlaubt. */
export function isPureNormalFinding(text: string, displayNames: string[] = []): boolean {
  if (!text || !text.trim()) return false;
  const low = text.toLowerCase();
  if (!NORMAL_MARKERS.test(low.replace("o. b", "ob").replace("o.b", "ob"))) return false;
  const toks = tokens(text);
  if (!toks.length || toks.length > 16) return false;
  const region = regionWords(displayNames);
  for (const tok of toks) {
    if (RESTWORTE.has(tok)) return false;
    if (FUELL.has(tok) || region.has(tok) || /^\d+$/.test(tok)) continue;
    if (compoundOk(tok, region)) continue;
    return false;
  }
  return true;
}
