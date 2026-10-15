// v3.15.5: Matrix-Fälle aus tests/offline/widerspruch_matrix_test.py (stdin: [{report, diktat}]) durch die Web-Engine
// (befundRegeln.ts) → stdout: [report] — der Python-Test vergleicht Zeichen für Zeichen mit der EXE-Engine.
import { readFileSync } from 'node:fs';
import { widersprucheBereinigen } from './src/befundRegeln.ts';
const daten = JSON.parse(readFileSync(new URL('../vorlagen_vorrang.json', import.meta.url), 'utf-8')).widersprueche;
const faelle = JSON.parse(readFileSync(0, 'utf-8'));
process.stdout.write(JSON.stringify(faelle.map(f => widersprucheBereinigen(f.report, f.diktat, daten)[0])));
