// befund_regeln_test.mjs — Web-Engine (src/befundRegeln.ts) gegen ../befund_regeln_fixtures.json.
// Pendant zu ../befund_regeln_test.py (das ruft dieses Skript auf).
//   cd web_app && node --experimental-strip-types befund_regeln_test.mjs
import { readFileSync } from 'node:fs';
import { csaBereinigen, splitRegionen, ergebnisNummerieren, befundUeberschriftSichern, ergebnisMitSeite, titelMitSeite, mammasonoBeidseits, promptVersion, stripPromptMarker } from './src/befundRegeln.ts';

const F = JSON.parse(readFileSync(new URL('../befund_regeln_fixtures.json', import.meta.url), 'utf8'));
let fail = 0, n = 0;
const check = (ok, label, got) => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      got ${JSON.stringify(got)}`); };
for (const c of F.split) { const g = splitRegionen(c.in); check(JSON.stringify(g) === JSON.stringify(c.out), 'split: ' + c.name, g); }
for (const c of F.nummerieren) { const g = ergebnisNummerieren(c.in); check(g === c.out, 'num: ' + c.name, g); }
for (const c of F.csa) { const g = csaBereinigen(c.in); check(g === c.out, 'csa: ' + c.name, g); }
for (const c of F.befund_sichern) { const g = befundUeberschriftSichern(c.in); check(g === c.out, 'sichern: ' + c.name, g); }
for (const c of F.ergebnis_seite) { const g = ergebnisMitSeite(c.ergebnis, c.raw); check(g === c.out, 'ergebnis: ' + c.raw, g); }
for (const c of F.titel_seite) { const g = titelMitSeite(c.titel, c.raw); check(g === c.out, 'titel: ' + c.titel, g); }
for (const c of F.mammasono_beidseits) { const g = mammasonoBeidseits(c.in); check(g === c.out, 'mammasono: ' + JSON.stringify(c.in.slice(0, 40)), g); }
for (const c of F.prompt_version) { const g = [promptVersion(c.in), stripPromptMarker(c.in)]; check(g[0] === c.version && g[1] === c.stripped, 'version: ' + c.in.slice(0, 40), g); }
console.log(`${n - fail}/${n} PASS (TS)`);
process.exit(fail ? 1 : 0);
