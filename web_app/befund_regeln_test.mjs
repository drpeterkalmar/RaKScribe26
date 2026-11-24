// befund_regeln_test.mjs — Web-Engine (src/befundRegeln.ts) gegen ../befund_regeln_fixtures.json.
// Pendant zu ../befund_regeln_test.py (das ruft dieses Skript auf).
//   cd web_app && node --experimental-strip-types befund_regeln_test.mjs
import { readFileSync } from 'node:fs';
import { csaBereinigen, splitRegionen, ergebnisNummerieren, befundUeberschriftSichern, ergebnisMitSeite, titelMitSeite, mammasonoBeidseits, promptVersion, stripPromptMarker, rhoErkennen, rhoEinfuegen, widersprucheBereinigen, abschnitteBereinigen, satzEinschraenken, widerspruchBefunde, widerspruchPrompt, ohneEmpfehlungen, kurzsaetzeSichern, klGrade, klBereinigen, klAdjektivGrade, arthroseBereinigen, sttSatzzeichen, grundregeln, rhoAnsEnde, rhoRegel, rhoRegelAnwenden, osteopenErsetzen, teileZusammenlegen, nurTextUeberschriften, nachbearbeiten, befundSchluss } from './src/befundRegeln.ts';

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
for (const c of F.georg_2011.faelle) {   // kaiscribe-georg-2011-n1 (Georg 20.11.2026): Grundregeln
  const g = grundregeln(c.in, c.diktat, TPL)[0]; check(g === c.out, 'georg_2011: ' + c.name, g);
  check(grundregeln(g, c.diktat, TPL)[0] === g, 'georg_2011 zweimal gleich: ' + c.name.slice(0, 50), 'nicht idempotent');
}
for (const c of F.georg_2311.faelle) {   // kaiscribe-schulter-ergebnis-n1 (Georg 22./23.11.2026, Punkte 48–70)
  const g = grundregeln(c.in, c.diktat, TPL)[0]; check(g === c.out, 'georg_2311: ' + c.name, g);
  check(grundregeln(g, c.diktat, TPL)[0] === g, 'georg_2311 zweimal gleich: ' + c.name.slice(0, 50), 'nicht idempotent');
}
for (const c of F.ursula_2011.faelle) {   // kaiscribe-ursula-2011-text-n1 (Ursula 20.11.2026, Punkte 3/4/7/10)
  const g = grundregeln(c.in, c.diktat, TPL)[0]; check(g === c.out, 'ursula_2011: ' + c.name, g);
  check(grundregeln(g, c.diktat, TPL)[0] === g, 'ursula_2011 zweimal gleich: ' + c.name.slice(0, 50), 'nicht idempotent');
}
for (const c of F.ursula_2011.nachbearbeiten) { const g = nachbearbeiten(c.in); check(g === c.out, 'ursula_2011 nachbearbeiten: ' + c.name, g); }
for (const c of F.ursula_2011.schluss) {
  const g = befundSchluss(c.in)[0]; check(g === c.out, 'ursula_2011 Schluss: ' + c.name, g);
  check(befundSchluss(g)[0] === g, 'ursula_2011 Schluss zweimal gleich: ' + c.name.slice(0, 50), 'nicht idempotent');
}
for (const c of F.georg_2311.teile) { const g = teileZusammenlegen(c.in, c.diktat)[0]; check(g === c.out, 'georg_2311 Teile: ' + c.name, g); }
for (const c of F.georg_2311.nur_text) { const g = nurTextUeberschriften(c.in); check(g === c.out, 'georg_2311 Nur Text: ' + c.name, g); }
for (const c of F.rho.osteopen) { const g = osteopenErsetzen(c.report, c.diktat)[0]; check(g === c.out, 'rho osteopen: ' + c.name.slice(0, 50), g); check(osteopenErsetzen(g, c.diktat)[0] === g, 'rho osteopen zweimal gleich: ' + c.name.slice(0, 40), 'nicht idempotent'); }
for (const c of F.rho.regel) { const g = rhoRegelAnwenden(c.report, c.dexa); check(JSON.stringify(g) === JSON.stringify([c.out, c.grund]), 'rho regel: ' + c.name.slice(0, 50), g); }   // kaiscribe-rho-regel-becken-n1
for (const c of F.rho.regel_score) { const g = rhoRegel(c.score, c.lws, c.dexa); check(JSON.stringify(g) === JSON.stringify(c.out), `rho regel score: ${c.score}/${c.lws}/${c.dexa}`, g); }
for (const c of F.rho.ans_ende) { const g = rhoAnsEnde(c.in); check(g === c.out, 'rho ans Ende: ' + c.in.slice(0, 30), g); }
for (const c of F.abschnitte.faelle) { const g = abschnitteBereinigen(c.in, c.diktat, TPL, WD)[0]; check(g === c.out, 'abschnitte: ' + c.name, g); }   // v3.18.13
// v3.16.6: Kurzsätze (Daten aus vorlagen_vorrang.json, Standard = gebündelte Datei)
for (const c of F.kurzsaetze.ohne) { const g = ohneEmpfehlungen(c.in); check(g === c.out, 'ohne Empfehlung: ' + c.in.slice(0, 45), g); }
for (const c of F.kurzsaetze.sichern) { const g = kurzsaetzeSichern(c.in, c.diktat)[0]; check(g === c.out, 'kurzsatz: ' + c.name, g); }
// v3.18.4: K&L-Wächter (RH 38: Grad nur aus Diktat oder IB Lab)
for (const c of F.kl.grade) { const g = klGrade(c.in); check(JSON.stringify(g) === JSON.stringify(c.out), 'kl-grade: ' + c.in.slice(0, 45), g); }
for (const c of F.kl.bereinigen) { const g = klBereinigen(c.in, c.diktat, c.erlaubt)[0]; check(g === c.out, 'kl: ' + c.name, g); }
// v3.18.5 (Nachtrag RH 99): Grad zum Adjektiv nur bei diktierter Arthrose; keine Arthrose ohne Diktat
for (const c of F.kl.adjektiv) { const g = klAdjektivGrade(c.in); check(JSON.stringify(g) === JSON.stringify(c.out), 'kl-adjektiv: ' + c.in.slice(0, 45), g); }
for (const c of F.arthrose.bereinigen) { const g = arthroseBereinigen(c.in, c.diktat, WD)[0]; check(g === c.out, 'arthrose: ' + c.name, g); }
// v3.18.11 (Echttest 14.11.): Chirp-Marken {Punkt}/{Komma} … → Satzzeichen
for (const c of F.stt_satzzeichen.faelle) { const g = sttSatzzeichen(c.in); check(g === c.out, 'stt-marken: ' + c.in.slice(0, 45), g); }
for (const c of F.prompt_version) { const g = [promptVersion(c.in), stripPromptMarker(c.in)]; check(g[0] === c.version && g[1] === c.stripped, 'version: ' + c.in.slice(0, 40), g); }
console.log(`${n - fail}/${n} PASS (TS)`);
process.exit(fail ? 1 : 0);
