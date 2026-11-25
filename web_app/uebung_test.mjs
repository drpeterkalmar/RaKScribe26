// uebung_test.mjs — Web: KaiScribe-Übungsmodus (src/uebung.ts, kaiscribe-uebung-n1 25.11.2026), ohne Netz.
// HARTE SPERRE: im Übungsmodus fängt die App jeden Ausgang ab (Zwischenablage = Weg ins CAS, fremde fetch/XHR-Ziele,
// sendBeacon, WebSocket, window.open) – 0 echte Aufrufe. Erlaubt bleiben nur STT/Befund-KI/Drive-Schlüssel + Übungsdienst.
// Dazu: Quelltext-Prüfung, dass App.tsx im Übungsmodus nie kopiert/sendet, und der Dienst-Client.
//   cd web_app && node --experimental-strip-types --no-warnings uebung_test.mjs
import { readFileSync } from 'node:fs';
import { uebungBasis, sperreEinrichten, UebungDienst, ERLAUBTE_HOSTS, UEBUNG_BALKEN } from './src/uebung.ts';

let fail = 0, n = 0;
const check = (ok, label, got) => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      got ${JSON.stringify(got)?.slice(0, 400)}`); };

// ── Übungsmodus erkennen ──
check(uebungBasis('https://drpeterkalmar.github.io/RaKScribe26/') === null, 'ohne ?uebung kein Übungsmodus');
check(uebungBasis('https://dexa.example.ts.net:8473/?uebung') === 'https://dexa.example.ts.net:8473', '?uebung → eigene Herkunft');
check(uebungBasis('https://drpeterkalmar.github.io/RaKScribe26/?uebung=https://dexa.example.ts.net:8473/x') === 'https://dexa.example.ts.net:8473', '?uebung=https://… → Dienst');
check(uebungBasis('https://x.github.io/?uebung=http://boese.example') === null, 'http-Dienst (nicht lokal) abgelehnt');
check(uebungBasis('http://localhost:5173/?uebung=http://127.0.0.1:8473') === 'http://127.0.0.1:8473', 'lokaler Test-Dienst erlaubt');

// ── Sperre an einem Attrappen-Fenster ──
const echt = [];
const DIENST = 'https://dexa.example.ts.net:8473';
const w = {
  location: { origin: 'https://drpeterkalmar.github.io' },
  fetch: async (u) => { echt.push(['fetch', String(u)]); return { ok: true, status: 200, json: async () => ({}) }; },
  XMLHttpRequest: class { open(m, u) { echt.push(['xhr', u]); } },
  WebSocket: class { constructor(u) { echt.push(['ws', u]); } },
  open: (u) => { echt.push(['open', u]); return {}; },
  navigator: {
    sendBeacon: (u) => { echt.push(['beacon', u]); return true; },
    clipboard: { writeText: async () => { echt.push(['clip', 'writeText']); }, write: async () => { echt.push(['clip', 'write']); } },
  },
};
const versuche = sperreEinrichten(w, DIENST);
check(sperreEinrichten(w, DIENST) === versuche, 'doppelt einrichten: dieselbe Sperre');

const AUSGAENGE = [
  'http://localhost:8765/whisper',                       // lokaler Whisper
  'http://127.0.0.1:8766/bruecke',                       // Brücke
  'https://plaza.ordi.local/wado?x',                     // Plaza
  'https://elga.gv.at/api',                              // ELGA
  'https://marc.example/upload', 'https://teleimage.example/x',
  'https://hooks.example/speechmagic',
  'https://api.telegram.org/bot/sendMessage',
  'https://evil.googleapis.com.example.com/x',           // ähnlicher Hostname
  'http://eu-speech.googleapis.com/v1/speech:recognize', // erlaubter Host, aber ohne https
  'https://drpeterkalmar.github.io/api/irgendwas',       // eigene Herkunft, aber API-Pfad
];
for (const ziel of AUSGAENGE) {
  let fehler = null;
  try { await w.fetch(ziel, { method: 'POST' }); } catch (e) { fehler = e; }
  check(fehler && String(fehler.message).includes(UEBUNG_BALKEN), `fetch gesperrt: ${ziel}`, fehler?.message);
}
let xf = null; try { new w.XMLHttpRequest().open('POST', 'http://127.0.0.1:8766/cas'); } catch (e) { xf = e; }
check(!!xf, 'XHR zu fremdem Ziel gesperrt');
let wf = null; try { new w.WebSocket('wss://x.example/socket'); } catch (e) { wf = e; }
check(!!wf, 'WebSocket gesperrt');
check(w.navigator.sendBeacon('https://x.example/log', 'daten') === false, 'sendBeacon gesperrt');
check(w.open('https://x.example/') === null, 'window.open fremd gesperrt');
let cf = 0;
await w.navigator.clipboard.writeText('Befund').catch(() => cf++);
await w.navigator.clipboard.write([]).catch(() => cf++);
check(cf === 2, 'Zwischenablage (Weg ins CAS) gesperrt: writeText + write');
check(echt.length === 0, 'SPERRE: 0 echte Aufrufe an gesperrte Ziele', echt);
check(versuche.length === AUSGAENGE.length + 6, 'jeder Versuch gezählt', versuche.length);

// erlaubte Ziele gehen durch
const ERLAUBT = ['https://oauth2.googleapis.com/token', 'https://eu-speech.googleapis.com/v1/speech:recognize',
  'https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize',
  'https://aiplatform.eu.rep.googleapis.com/v1/x', 'https://api.anthropic.com/v1/messages',
  'https://www.googleapis.com/drive/v3/files?q=x', DIENST + '/api/faelle?tag=20261123',
  'https://drpeterkalmar.github.io/RaKScribe26/assets/index.js'];
for (const z of ERLAUBT) await w.fetch(z, {});
check(echt.length === ERLAUBT.length && echt.every(([a], i) => a === 'fetch' && echt[i][1] === ERLAUBT[i]), 'erlaubte Ziele (STT, KI, Drive, Übungsdienst, Bundle) gehen durch', echt);
check(ERLAUBTE_HOSTS.length === 5, 'genau 5 erlaubte fremde Hosts', ERLAUBTE_HOSTS);

// ── Quelltext: alle Netz-Ziele der App sind abgedeckt, App.tsx sendet in der Übung nie ──
const src = (f) => readFileSync(new URL('./src/' + f, import.meta.url), 'utf8');
const app = src('App.tsx');
const hosts = new Set();
for (const f of ['stt.ts', 'gemini.ts', 'llmAnbieter.ts', 'net.ts', 'pipeline.ts', 'App.tsx']) {
  for (const m of src(f).matchAll(/https?:\/\/([a-z0-9.-]+)(?::\d+)?\//gi)) hosts.add(m[1]);
}
const unbekannt = [...hosts].filter(h => !ERLAUBTE_HOSTS.includes(h) && !['github.com', 'localhost'].includes(h));
check(unbekannt.length === 0, 'alle Netz-Ziele im Quelltext sind erlaubt oder gesperrt (github.com = EXE-Link, localhost = Whisper gesperrt)', unbekannt);
check(/if \(!text \|\| UEBUNG_BASIS\) return false;/.test(app), 'App: copyTextToClipboard im Übungsmodus sofort false (nie kopieren)');
check(/if \(UEBUNG_BASIS\) \{ await uebungAbgeben\(\); return; \}/.test(app), 'App: EOL im Übungsmodus = Abgabe in die Übungsablage');
check(/if \(UEBUNG_BASIS\) \{ setStatusText\('Übung: bitte diktieren/.test(app), 'App: Audio-Upload im Übungsmodus aus');
check(app.includes('uebung-balken') && app.includes('{UEBUNG_BALKEN}'), 'App: roter Dauerbalken');
const main = src('main.tsx');
check(main.indexOf('sperreEinrichten(') > 0 && main.indexOf('sperreEinrichten(') < main.indexOf('createRoot('), 'main.tsx: Sperre VOR dem ersten Render');

// ── Dienst-Client ──
const rufe = [];
const fake = async (u, init = {}) => {
  rufe.push({ u, init });
  const pfad = new URL(u).pathname;
  const ant = {
    '/api/anmelden': [200, { token: 't1', kuerzel: 'kp', variante: 'anonym', stt_rest_s: 3600 }],
    '/api/tage': [200, { tage: ['20261123'], stt_rest_s: 3600 }],
    '/api/loesung': [403, { fehler: 'erst abgeben' }],
    '/api/stt': [200, { stt_rest_s: 3540, faktor: 2 }],
  }[pfad] || [404, {}];
  return { ok: ant[0] < 300, status: ant[0], json: async () => ant[1], blob: async () => new Blob(['PK']) };
};
const d = new UebungDienst(DIENST + '/', fake);
await d.anmelden('kp', 'geheim');
check(d.token === 't1' && d.kuerzel === 'kp' && d.variante === 'anonym', 'Client: Anmeldung');
await d.tage();
check(rufe.at(-1).init.headers.Authorization === 'Bearer t1' && rufe.at(-1).u === DIENST + '/api/tage', 'Client: Token im Kopf, Basis ohne //');
let lf = null; try { await d.loesung('20261123', 'RH12'); } catch (e) { lf = e.message; }
check(lf === 'Erst abgeben, dann Lösung', 'Client: Lösung vor Abgabe → Hinweis', lf);
await d.stt(30);
check(d.sttRestS === 3540 && JSON.parse(rufe.at(-1).init.body).sekunden === 30, 'Client: STT buchen');
check(!JSON.stringify(rufe).includes('geheim') || rufe[0].u.endsWith('/api/anmelden'), 'Client: Kennwort nur an /api/anmelden');

console.log(`\n${n - fail}/${n} PASS`);
process.exit(fail ? 1 : 0);
