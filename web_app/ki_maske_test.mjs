// ki_maske_test.mjs — Web-Maske (src/kiMaske.ts) = source_code/ki_maske.py, Fall für Fall (kaiscribe-haiku-ab-n1).
//   node --experimental-strip-types ki_maske_test.mjs <faelle.json>   → JSON [{maskiert, zuwert, rest}] auf stdout
//   (tests/offline/test_ki_maske_web.py ruft das auf und vergleicht mit Python)
import { readFileSync } from 'node:fs';
import { Maske, MaskeUnsicher } from './src/kiMaske.ts';
import { maskieren, korrekturPlausibel } from './src/llmAnbieter.ts';

if (process.argv[2] === '--anbieter') {   // Prompt-Aufteilung + Pflicht-Platzhalter + Plausibilität wie llm_anbieter.py
  const out = JSON.parse(readFileSync(process.argv[3], 'utf8')).map(([prompt, roh, antwort]) => {
    try { const { fest, rest, pflicht } = maskieren(prompt); return { fest, rest, pflicht, plausibel: korrekturPlausibel(roh, antwort) }; }
    catch (e) { return { fehler: e.message }; }
  });
  process.stdout.write(JSON.stringify(out), () => process.exit(0));   // erst nach dem Schreiben beenden (große Ausgabe)
} else {

const faelle = JSON.parse(readFileSync(process.argv[2], 'utf8'));

const out = faelle.map(([text, namen]) => {
  const m = new Maske(namen || []);
  try {
    const maskiert = m.maskieren(text);
    let rest = '';
    try { m.restpruefung([maskiert]); } catch (e) { rest = e instanceof MaskeUnsicher ? e.message : 'FEHLER ' + e; }
    return { maskiert, zuwert: Object.fromEntries(m.zuWert), rest, zurueck: m.zuruecksetzen(maskiert) };
  } catch (e) {
    return { fehler: e instanceof MaskeUnsicher ? e.message : 'FEHLER ' + e };
  }
});
process.stdout.write(JSON.stringify(out));
}
