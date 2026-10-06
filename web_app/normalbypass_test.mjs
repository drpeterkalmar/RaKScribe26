// normalbypass_test.mjs — prüft src/normalbypass.ts gegen ../normal_bypass_tests.json (Pendant zur Python-Engine).
//   node --experimental-strip-types normalbypass_test.mjs
import { readFileSync } from 'node:fs';
import { isPureNormalFinding } from './src/normalbypass.ts';

const T = JSON.parse(readFileSync(new URL('../templates.json', import.meta.url), 'utf8'));  // Umbau Schritt 20: nur noch eine Vorlagen-Datei
const DN = Object.values(T).map(v => v.display_name);
const cases = JSON.parse(readFileSync(new URL('../normal_bypass_tests.json', import.meta.url), 'utf8')).cases;
let fail = 0;
for (const c of cases) {
  const got = isPureNormalFinding(c.in, DN);
  const ok = got === c.bypass;
  if (!ok) fail++;
  console.log(ok ? 'PASS' : 'FAIL', '|', JSON.stringify(c.in).slice(0, 70), '→', got);
}
console.log(`${cases.length - fail}/${cases.length} PASS (TS)`);
process.exit(fail ? 1 : 0);
