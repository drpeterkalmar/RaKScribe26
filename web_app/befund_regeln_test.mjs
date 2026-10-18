// befund_regeln_test.mjs — Web-Engine (src/befundRegeln.ts) gegen ../befund_regeln_fixtures.json.
// Pendant zu ../befund_regeln_test.py (das ruft dieses Skript auf).
//   cd web_app && node --experimental-strip-types befund_regeln_test.mjs
import { readFileSync } from 'node:fs';
import { csaBereinigen, splitRegionen, ergebnisNummerieren, befundUeberschriftSichern, ergebnisMitSeite, titelMitSeite, mammasonoBeidseits, promptVersion, stripPromptMarker, rhoErkennen, rhoEinfuegen, widersprucheBereinigen, satzEinschraenken, widerspruchBefunde, widerspruchPrompt, ohneEmpfehlungen, kurzsaetzeSichern } from './src/befundRegeln.ts';

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
for (const c of F.rho.erkennen) { const g = rhoErkennen(c.in); check(JSON.stringify(g) === JSON.stringify(c.out), 'rho erkennen: ' + c.in.slice(0, 45), g); }
for (const c of F.rho.einfuegen) { const g = rhoEinfuegen(c.report, c.score); check(g === c.out, 'rho einfügen: ' + c.report.slice(0, 30), g); }
// v3.15.5: umschriebene Skelettbefunde vs. Normalsätze (Daten aus vorlagen_vorrang.json wie in pipeline.ts)
const WD = JSON.parse(readFileSync(new URL('../vorlagen_vorrang.json', import.meta.url), 'utf8')).widersprueche;
const TPL = JSON.parse(readFileSync(new URL('../templates.json', import.meta.url), 'utf8'));
for (const c of F.widerspruch.bereinigen) { const g = widersprucheBereinigen(c.in, c.diktat, WD)[0]; check(g === c.out, 'widerspruch: ' + c.name, g); }
for (const c of F.widerspruch.einschraenken) { const g = satzEinschraenken(c.in); check(g === c.out, 'einschränken: ' + c.in.slice(0, 40), g); }
for (const c of F.widerspruch.befunde) { const g = widerspruchBefunde(c.in, WD).map(b => [b.id, b.phrase, b.global]); check(JSON.stringify(g) === JSON.stringify(c.out), 'befunde: ' + c.in, g); }
for (const c of F.widerspruch.prompt) { const g = widerspruchPrompt(widerspruchBefunde(c.diktat, WD), TPL[c.vorlage].body, WD); check(g === c.out, 'wid-prompt: ' + c.diktat, g); }
// v3.16.6: Kurzsätze (Daten aus vorlagen_vorrang.json, Standard = gebündelte Datei)
for (const c of F.kurzsaetze.ohne) { const g = ohneEmpfehlungen(c.in); check(g === c.out, 'ohne Empfehlung: ' + c.in.slice(0, 45), g); }
for (const c of F.kurzsaetze.sichern) { const g = kurzsaetzeSichern(c.in, c.diktat)[0]; check(g === c.out, 'kurzsatz: ' + c.name, g); }
for (const c of F.prompt_version) { const g = [promptVersion(c.in), stripPromptMarker(c.in)]; check(g[0] === c.version && g[1] === c.stripped, 'version: ' + c.in.slice(0, 40), g); }
console.log(`${n - fail}/${n} PASS (TS)`);
process.exit(fail ? 1 : 0);
