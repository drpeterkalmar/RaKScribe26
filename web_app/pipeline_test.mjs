// pipeline_test.mjs — Web-Pipeline ohne Browser (Umbau Schritt 8, Gutachten P2-7/P2-10): Lauf-Abbruch,
// Fehlerweitergabe der Spracherkennung, kein Whisper-Aufruf auf GitHub Pages. fetch wird nachgebaut.
//   cd web_app && node --experimental-strip-types pipeline_test.mjs
import { generateKeyPairSync } from 'node:crypto';
import { LaufVerwaltung, befundLauf } from './src/lauf.ts';
import { transcribeAudio, base64AusBytes, whisperErlaubt } from './src/stt.ts';
import { fetchWithRetry } from './src/net.ts';

let fail = 0, n = 0;
const check = (ok, label, detail = '') => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      ${detail}`); };
const pause = (ms) => new Promise(r => setTimeout(r, ms));
const offen = () => { let res, rej; const p = new Promise((a, b) => { res = a; rej = b; }); return { p, res, rej }; };
console.warn = () => {}; console.error = () => {}; console.log = ((orig) => (...a) => { if (/^(PASS|FAIL|\d)/.test(String(a[0]))) orig(...a); })(console.log);

// ── 1. befundLauf: normaler Lauf, Abbruch, Überholen, Fehler ────────────────────────────────────────────
function ui() {
  const log = [];
  return { log, ui: {
    transkript: t => log.push(['transkript', t]), befund: t => log.push(['befund', t]), status: t => log.push(['status', t]),
    fertig: () => log.push(['fertig']), fehler: m => log.push(['fehler', m]), kopieren: t => log.push(['kopieren', t]),
  } };
}
const OPT = { transkriptVorPruefung: true, fehlerPrefix: 'Fehler: ' };
{
  const v = new LaufVerwaltung(); const lauf = v.neu(); const { log, ui: u } = ui();
  await befundLauf(lauf, {
    transkribieren: async () => ' knie rechts unauffällig ',
    korrigieren: async t => t.replace('knie', 'Knie'),
    befundErstellen: async t => `## Befund zu ${t}`,
  }, u, OPT);
  const arten = log.map(x => x[0]).join(',');
  check(arten === 'transkript,status,transkript,befund,fertig,kopieren', 'normaler Lauf: Transkript → Korrektur → Befund → Kopieren', arten);
  check(log.at(-1)[1] === '## Befund zu Knie rechts unauffällig', 'kopiert wird der fertige Befund');
}
{
  // Abbruch (Neu/F9) während Call 0 — danach darf nichts mehr geschrieben oder kopiert werden
  const v = new LaufVerwaltung(); const lauf = v.neu(); const { log, ui: u } = ui();
  const k = offen(); let befundAufgerufen = false;
  const fertig = befundLauf(lauf, {
    transkribieren: async () => 'Schulter rechts Omarthrose',
    korrigieren: async () => k.p,
    befundErstellen: async () => { befundAufgerufen = true; return '## X'; },
  }, u, OPT);
  await pause(5);
  const vorher = log.length;
  v.abbrechen();
  check(lauf.signal.aborted, 'Abbruch setzt das AbortSignal des Laufs');
  k.res('Schulter rechts Omarthrose (korrigiert)');
  await fertig;
  check(log.length === vorher && !befundAufgerufen, 'abgebrochener Lauf schreibt nichts mehr (kein Befund, kein Kopieren)', JSON.stringify(log.slice(vorher)));
}
{
  // Ein neuer Lauf (z. B. Upload) überholt den alten: der alte schreibt nichts mehr
  const v = new LaufVerwaltung(); const alt = v.neu(); const { log, ui: u } = ui();
  const t = offen();
  const p = befundLauf(alt, { transkribieren: async () => t.p, korrigieren: async x => x, befundErstellen: async () => '## alt' }, u, OPT);
  const neu = v.neu();
  t.res('alter Text'); await p;
  check(!alt.aktuell() && neu.aktuell() && log.length === 0, 'überholter Lauf schreibt nichts', JSON.stringify(log));
}
{
  // Abbruch als AbortError aus dem Netz → still, keine Fehlermeldung
  const v = new LaufVerwaltung(); const lauf = v.neu(); const { log, ui: u } = ui();
  const p = befundLauf(lauf, {
    transkribieren: (signal) => new Promise((_, rej) => signal.addEventListener('abort', () => { const e = new Error('Abgebrochen'); e.name = 'AbortError'; rej(e); })),
    korrigieren: async x => x, befundErstellen: async x => x,
  }, u, OPT);
  v.abbrechen(); await p;
  check(log.length === 0, 'AbortError → keine Fehlermeldung', JSON.stringify(log));
}
{
  const v = new LaufVerwaltung(); const lauf = v.neu(); const { log, ui: u } = ui();
  await befundLauf(lauf, { transkribieren: async () => '', korrigieren: async x => x, befundErstellen: async x => x }, u, OPT);
  check(log.some(x => x[0] === 'fehler' && x[1] === 'Fehler: Es wurde kein gesprochener Text erkannt.'), 'leeres Diktat → Fehlermeldung mit Präfix', JSON.stringify(log));
}

// ── 2. Spracherkennung: Google-403 kommt an, kein localhost-Aufruf auf GitHub Pages ──────────────────────
const { privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048, privateKeyEncoding: { type: 'pkcs8', format: 'pem' }, publicKeyEncoding: { type: 'spki', format: 'pem' } });
const sttKey = { client_email: 'test@example.iam.gserviceaccount.com', private_key: privateKey };
let aufrufe = [];
const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
globalThis.fetch = async (url) => {
  aufrufe.push(String(url));
  if (url.includes('oauth2.googleapis.com')) return json(200, { access_token: 'tok', expires_in: 3600 });
  if (url.includes('speech.googleapis.com')) return json(403, { error: { code: 403, message: 'Permission denied: Cloud Speech-to-Text API has not been used in project rakscribe' } });
  if (url.includes('localhost:8765')) return json(200, { text: 'Whisper-Text', elapsed_seconds: 1 });
  throw new Error('unerwartete URL ' + url);
};
let speicher = {};
globalThis.localStorage = { getItem: k => (k in speicher ? speicher[k] : null), setItem: (k, v) => { speicher[k] = String(v); } };
const wav = new Blob([new Uint8Array(44 + 32000)], { type: 'audio/wav' });

globalThis.location = { hostname: 'drpeterkalmar.github.io' };
check(!whisperErlaubt(), 'GitHub Pages: Whisper-Fallback aus');
let fehler = null;
try { await transcribeAudio(wav, true, { sttKey }); } catch (e) { fehler = e; }
check(fehler && /Permission denied: Cloud Speech-to-Text API/.test(fehler.message), 'Google-403 → Meldung kommt beim Nutzer an', fehler && fehler.message);
check(!aufrufe.some(u => u.includes('localhost')), 'kein localhost-Aufruf auf Nicht-localhost', aufrufe.join(' '));
check(aufrufe.some(u => u.includes('eu-speech.googleapis.com')), 'chirp_3 wurde versucht');

aufrufe = [];
fehler = null;
try { await transcribeAudio(wav, false, { sttKey }); } catch (e) { fehler = e; }
check(fehler && /Permission denied/.test(fehler.message) && !aufrufe.some(u => u.includes('localhost')), 'Chunk-Pfad (latest_long): ebenso kein Whisper, Google-Meldung', aufrufe.join(' '));

globalThis.location = { hostname: 'localhost' };
aufrufe = [];
const lokal = await transcribeAudio(wav, true, { sttKey });
check(lokal === 'Whisper-Text' && aufrufe.some(u => u.includes('localhost:8765')), 'localhost: Whisper-Fallback wie bisher');

globalThis.location = { hostname: 'drpeterkalmar.github.io' };
speicher.whisper_fallback = '1';
check(whisperErlaubt(), "localStorage.whisper_fallback = '1' schaltet Whisper frei");
speicher = {};

const ac = new AbortController(); ac.abort();
aufrufe = [];
fehler = null;
globalThis.location = { hostname: 'localhost' };
try { await transcribeAudio(wav, true, { sttKey, signal: ac.signal }); } catch (e) { fehler = e; }
check(fehler && fehler.name === 'AbortError' && !aufrufe.some(u => u.includes('localhost:8765')), 'Abbruch → AbortError, auch lokal kein Whisper', aufrufe.join(' '));

// ── 3. fetchWithRetry: Abbruch während der Retry-Pause → sofort AbortError, kein weiterer Versuch ────────
{
  let versuche = 0;
  globalThis.fetch = async () => { versuche++; return json(503, {}); };
  const c = new AbortController();
  const t0 = Date.now();
  setTimeout(() => c.abort(), 30);
  let e = null;
  try { await fetchWithRetry('https://example.invalid/x', { signal: c.signal }, 5000, 3); } catch (err) { e = err; }
  check(e && e.name === 'AbortError' && versuche === 1 && Date.now() - t0 < 1000, 'Abbruch in der Retry-Pause → AbortError ohne weiteren Versuch', `${e && e.name} ${versuche}`);
  versuche = 0;
  globalThis.fetch = async () => { versuche++; return versuche < 2 ? json(503, {}) : json(200, { ok: 1 }); };
  const r = await fetchWithRetry('https://example.invalid/y', {}, 5000, 3);
  check(r.status === 200 && versuche === 2, 'ohne Abbruch: 503 → Retry → 200 (wie bisher)');
}

// ── 4. Base64 ohne FileReader = Node-Base64 ─────────────────────────────────────────────────────────────
{
  const bytes = new Uint8Array(150001);
  for (let i = 0; i < bytes.length; i++) bytes[i] = (i * 2654435761) >>> 24;
  check(base64AusBytes(bytes) === Buffer.from(bytes).toString('base64'), 'base64AusBytes = Buffer.toString(base64) (150001 Bytes)');
  check(base64AusBytes(new Uint8Array(0)) === '', 'leere Daten → leerer String');
}

console.log(`${n - fail}/${n} PASS (pipeline)`);
process.exit(fail ? 1 : 0);
