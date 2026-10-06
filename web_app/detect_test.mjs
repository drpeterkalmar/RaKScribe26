// detect_test.mjs — Web-detectTemplate (App.tsx, per Function-Extract) gegen eine Fall-Liste (JSON [[diktat, key], ...]).
// Aufruf aus ../test_normalbefunde.py (TEIL 2b): node detect_test.mjs <faelle.json>  → Ausgabe JSON {diktat: key}
import fs from 'node:fs';
import { vorrangVorlage } from './src/befundRegeln.ts';
const vorrangData = JSON.parse(fs.readFileSync(new URL('../vorlagen_vorrang.json', import.meta.url), 'utf8'));
const src = fs.readFileSync(new URL('./src/App.tsx', import.meta.url), 'utf8');
const templates = JSON.parse(fs.readFileSync(new URL('./src/templates.json', import.meta.url), 'utf8'));
const s = src.indexOf('const detectTemplate = (text: string): string => {');
let i = src.indexOf('{', s), d = 0, e = i;
for (; e < src.length; e++) { if (src[e] === '{') d++; if (src[e] === '}') { d--; if (!d) break; } }
const body = src.slice(i, e + 1).replace(/: \[string, string\[\]\]\[\]/g, '').replace(/: \[string\[\], string\]\[\]/g, '');
const detF = new Function('templates', 'text', 'vorrangVorlage', 'vorrangData', body.replace(/ as VorrangDaten/g, ''));
const det = (tpl, t) => detF(tpl, t, vorrangVorlage, vorrangData);
const faelle = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const [t] of faelle) out[t] = det(templates, t);
process.stdout.write(JSON.stringify(out));
