// sync_test.mjs — Web-Seite der gemeinsamen Fixtures (../sync_fixtures.json, Umbau Schritte 13/20):
// stitchOverlaps (src/stt.ts) = stitch_overlaps (source_code/stt.py).
//   cd web_app && node --experimental-strip-types sync_test.mjs            → Prüfung
//   cd web_app && node --experimental-strip-types sync_test.mjs --chirp    → CHIRP_PHRASES als JSON (für test_stt.py)
import { readFileSync } from 'node:fs';
import { stitchOverlaps, CHIRP_PHRASES } from './src/stt.ts';

if (process.argv.includes('--chirp')) { process.stdout.write(JSON.stringify(CHIRP_PHRASES)); process.exit(0); }
const F = JSON.parse(readFileSync(new URL('../sync_fixtures.json', import.meta.url), 'utf8'));
let fail = 0, n = 0;
const check = (ok, label, got) => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      got ${JSON.stringify(got)}`); };
for (const [a, b, soll] of F.stitch) { const g = stitchOverlaps(a, b); check(g === soll, `stitch: ${a.slice(0, 30)} | ${b.slice(0, 30)}`, g); }
console.log(`${n - fail}/${n} PASS (sync TS)`);
process.exit(fail ? 1 : 0);
