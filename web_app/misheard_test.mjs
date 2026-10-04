// misheard_test.mjs — prüft misheard_words.json gegen misheard_tests.json mit der Web-Engine
// (src/misheard.ts). Pendant zu ../misheard_test.py — beide müssen grün sein.
//
//   cd web_app && node --experimental-strip-types misheard_test.mjs
import { readFileSync } from 'node:fs';
import { compileMisheard, applyMisheard, misheardPromptBlock } from './src/misheard.ts';

const file = JSON.parse(readFileSync(new URL('../misheard_words.json', import.meta.url), 'utf8'));
const cases = JSON.parse(readFileSync(new URL('../misheard_tests.json', import.meta.url), 'utf8')).cases;
if (process.argv.includes('--block')) { process.stdout.write(misheardPromptBlock(file)); process.exit(0); }
const compiled = compileMisheard(file);
let fail = 0;
for (const c of cases) {
  const got = applyMisheard(c.in, compiled);
  const ok = got === c.out;
  if (!ok) fail++;
  console.log(ok ? 'PASS' : 'FAIL', '|', c.in.slice(0, 60), '→', ok ? got.slice(0, 70) : `${JSON.stringify(got)}  (erwartet ${JSON.stringify(c.out)})`);
}
const blk = misheardPromptBlock(file);
console.log(`\n${cases.length - fail}/${cases.length} PASS · ${compiled.length} auto-Regexe · Prompt-Block ${blk.length} Zeichen`);
process.exit(fail ? 1 : 0);
