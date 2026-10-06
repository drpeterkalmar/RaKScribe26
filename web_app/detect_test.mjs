// detect_test.mjs — Web-Erkennung (src/detect.ts, Umbau Schritt 17: direkt importiert statt aus App.tsx herausgeschnitten).
//   node detect_test.mjs <faelle.json>          → JSON {diktat: key}    (test_normalbefunde.py TEIL 2/2c, vorlagen_erreichbar_test.py)
//   node detect_test.mjs --titel <faelle.json>  → JSON [titel, …] für [[raw, display_name], …]  (TEIL 4b, titel_fixtures.py)
import fs from 'node:fs';
import { detectTemplate, deriveUntersuchungsTitel } from './src/detect.ts';

const lies = (rel) => JSON.parse(fs.readFileSync(new URL(rel, import.meta.url), 'utf8'));
if (process.argv[2] === '--titel') {
  const faelle = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  process.stdout.write(JSON.stringify(faelle.map(([raw, dn]) => deriveUntersuchungsTitel(raw, dn))));
} else {
  const templates = lies('../templates.json');
  const vorrang = lies('../vorlagen_vorrang.json');
  const faelle = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const out = {};
  for (const [t] of faelle) out[t] = detectTemplate(t, templates, vorrang);
  process.stdout.write(JSON.stringify(out));
}
