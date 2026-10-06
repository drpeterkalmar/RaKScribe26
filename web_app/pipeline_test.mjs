// pipeline_test.mjs — Web-Pipeline ohne Browser (Umbau Schritt 8, Gutachten P2-7/P2-10): Lauf-Abbruch,
// Fehlerweitergabe der Spracherkennung, kein Whisper-Aufruf auf GitHub Pages. fetch wird nachgebaut.
//   cd web_app && node --experimental-strip-types pipeline_test.mjs
import { generateKeyPairSync } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { LaufVerwaltung, befundLauf } from './src/lauf.ts';
import { transcribeAudio, base64AusBytes, whisperErlaubt } from './src/stt.ts';
import { fetchWithRetry } from './src/net.ts';
import { wavFromInt16 } from './src/audio.ts';
import { befundAusDiktat } from './src/pipeline.ts';
import { correctTranscriptionWithGemini, validationPrompt, correctionPrompt, SYS_MSG, VERTEX_ENDPOINT } from './src/gemini.ts';
import { nachbearbeiten } from './src/befundRegeln.ts';

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
const PHR = JSON.parse(readFileSync(new URL('../phrases.json', import.meta.url), 'utf8'));
const phrasen = { medical: PHR.medical_web, chirp: PHR.chirp };  // wie App.tsx (Umbau Schritt 20)
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
try { await transcribeAudio(wav, true, { sttKey, phrasen }); } catch (e) { fehler = e; }
check(fehler && /Permission denied: Cloud Speech-to-Text API/.test(fehler.message), 'Google-403 → Meldung kommt beim Nutzer an', fehler && fehler.message);
check(!aufrufe.some(u => u.includes('localhost')), 'kein localhost-Aufruf auf Nicht-localhost', aufrufe.join(' '));
check(aufrufe.some(u => u.includes('eu-speech.googleapis.com')), 'chirp_3 wurde versucht');

aufrufe = [];
fehler = null;
try { await transcribeAudio(wav, false, { sttKey, phrasen }); } catch (e) { fehler = e; }
check(fehler && /Permission denied/.test(fehler.message) && !aufrufe.some(u => u.includes('localhost')), 'Chunk-Pfad (latest_long): ebenso kein Whisper, Google-Meldung', aufrufe.join(' '));

globalThis.location = { hostname: 'localhost' };
aufrufe = [];
const lokal = await transcribeAudio(wav, true, { sttKey, phrasen });
check(lokal === 'Whisper-Text' && aufrufe.some(u => u.includes('localhost:8765')), 'localhost: Whisper-Fallback wie bisher');

globalThis.location = { hostname: 'drpeterkalmar.github.io' };
speicher.whisper_fallback = '1';
check(whisperErlaubt(), "localStorage.whisper_fallback = '1' schaltet Whisper frei");
speicher = {};

const ac = new AbortController(); ac.abort();
aufrufe = [];
fehler = null;
globalThis.location = { hostname: 'localhost' };
try { await transcribeAudio(wav, true, { sttKey, phrasen, signal: ac.signal }); } catch (e) { fehler = e; }
check(fehler && fehler.name === 'AbortError' && !aufrufe.some(u => u.includes('localhost:8765')), 'Abbruch → AbortError, auch lokal kein Whisper', aufrufe.join(' '));

// ── 2a. Phrasenlisten aus phrases.json landen in den Requests (Umbau Schritt 20) ──────────────────────────────
{
  const gesendet = [];
  globalThis.fetch = async (url, opt) => {
    if (url.includes('oauth2')) return json(200, { access_token: 'tok', expires_in: 3600 });
    gesendet.push({ url, body: JSON.parse(opt.body) });
    return json(200, { results: [{ alternatives: [{ transcript: 'ok' }] }] });
  };
  await transcribeAudio(wav, true, { sttKey, phrasen });
  await transcribeAudio(wav, false, { sttKey, phrasen });
  const chirp = gesendet[0].body.config.adaptation.phraseSets[0].inlinePhraseSet.phrases;
  const chunk = gesendet[1].body.config.speechContexts[0];
  check(chirp.map(p => p.value).join('|') === PHR.chirp.join('|') && chirp.every(p => p.boost === 10) && PHR.chirp.length === 68,
        'chirp_3: PhraseSet = phrases.json chirp (68, Boost 10)');
  check(chunk.phrases.join('|') === PHR.medical_web.join('|') && chunk.boost === 15 && new Set(chunk.phrases).size === chunk.phrases.length,
        '6-s-Chunk: speechContexts = phrases.json medical_web (ohne Doppelte, Boost 15)');
}

// ── 2b. Langes Diktat (> 59 s): Segmente 50 s + 4 s Rückhören direkt aus der WAV (ohne AudioContext) ────
{
  const bodies = [];
  globalThis.fetch = async (url, opt) => {
    if (url.includes('oauth2')) return json(200, { access_token: 'tok', expires_in: 3600 });
    const b = JSON.parse(opt.body); bodies.push(b);
    const texte = ['eins zwei drei vier fünf sechs sieben acht', 'fünf sechs sieben acht neun zehn'];
    return json(200, { results: [{ alternatives: [{ transcript: texte[bodies.length - 1] }] }] });
  };
  const s = Int16Array.from({ length: 70 * 16000 }, (_, i) => (i % 200) - 100);
  const text = await transcribeAudio(wavFromInt16(s), true, { sttKey, phrasen });
  const laengen = bodies.map(b => { const bin = Buffer.from(b.content, 'base64'); return bin.readUInt32LE(40) / 2; });
  check(bodies.length === 2 && laengen[0] === 50 * 16000 && laengen[1] === 24 * 16000, '70-s-Diktat → 2 chirp_3-Segmente (50 s, 24 s)', laengen.join(','));
  const zweites = Buffer.from(bodies[1].content, 'base64');
  check(zweites.readInt16LE(44) === s[46 * 16000] && zweites.readUInt32LE(24) === 16000, 'Segment 2 beginnt bei 46 s (4 s Rückhören), 16 kHz');
  check(text === 'eins zwei drei vier fünf sechs sieben acht neun zehn', 'Überlappung zusammengefügt', text);
}

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

// ── 3b. Gemini-Kette der Web-App (Umbau Schritt 18): Prompts = Snapshot, Call 1 + Call 2, Abbruch ──────
{
  const snap = (f) => readFileSync(new URL('../tests/offline/snapshots/' + f, import.meta.url), 'utf8');
  check(validationPrompt('${rawDictation}', '${generatedReport}') === snap('val_prompt.txt'), 'validationPrompt = Snapshot (Text unverändert)');
  check(correctionPrompt('${MISHEARD_PROMPT_BLOCK}', '${rawText}') === snap('call0_prompt.txt'), 'correctionPrompt (Call 0) = Snapshot');
  const lies = (rel) => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8'));
  const templates = lies('../templates.json');
  const ctxBasis = { apiKey: 'AQ.dummy', prompt: readFileSync(new URL('../radiology_prompt.txt', import.meta.url), 'utf8'),
    status: () => {}, templates, vorrang: lies('../vorlagen_vorrang.json'),
    displayNames: Object.values(templates).map(t => t.display_name) };
  const C1 = '## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nVerschmälerung des medialen Gelenkspaltes mit Osteophyten.\n\n## Ergebnis\nMäßiggradige Gonarthrose rechts.';
  const C2 = C1.replace('Osteophyten.', 'Osteophyten und subchondraler Sklerosierung.');
  const bodies = [];
  globalThis.fetch = async (url, opt) => {
    bodies.push({ url, headers: opt.headers, body: JSON.parse(opt.body) });
    const text = bodies.length === 1 ? C1 : C2;
    return json(200, { candidates: [{ content: { parts: [{ text: text.slice(0, 7) }, { text: text.slice(7) }] }, finishReason: 'STOP' }] });
  };
  const seg = 'Knie rechts mäßiggradige Gonarthrose';
  const rep = await befundAusDiktat(seg, ctxBasis);
  check(rep === nachbearbeiten(C2) && bodies.length === 2, 'LLM-Pfad: Call 1 + Call 2, Ergebnis = nachbearbeitete Validierung', rep);
  check(bodies.every(b => b.url === VERTEX_ENDPOINT && b.headers['x-goog-api-key'] === 'AQ.dummy'), 'beide Aufrufe: EU-Endpoint + Schlüssel');
  const p1 = bodies[0].body.contents[0].parts[0].text;
  check(bodies[0].body.systemInstruction.parts[0].text === SYS_MSG && p1.includes('<untersuchung>Kniegelenk in 2 Ebenen</untersuchung>')
        && p1.includes(seg) && !p1.includes('RAKSCRIBE_PROMPT_VERSION'), 'Call 1: SYS_MSG, Vorlage, Diktat, ohne Versionsmarker');
  check(bodies[1].body.contents[0].parts[0].text === validationPrompt(seg, C1), 'Call 2 = validationPrompt(Diktat, Call-1-Befund)');

  // Abbruch während Call 1: darf nicht als „Validierung fehlgeschlagen“ weiterlaufen
  const ac2 = new AbortController();
  globalThis.fetch = (url, opt) => new Promise((_, rej) => opt.signal.addEventListener('abort', () => { const e = new Error('abgebrochen'); e.name = 'AbortError'; rej(e); }));
  const lauf = befundAusDiktat(seg, { ...ctxBasis, signal: ac2.signal });
  setTimeout(() => ac2.abort(), 10);
  let e2 = null;
  try { await lauf; } catch (e) { e2 = e; }
  check(e2 && e2.name === 'AbortError', 'Abbruch während Gemini → AbortError (kein Befund)');
  const ac3 = new AbortController();
  const korr = correctTranscriptionWithGemini('Knie rechts', { ...ctxBasis, signal: ac3.signal });
  setTimeout(() => ac3.abort(), 10);
  let e3 = null;
  try { await korr; } catch (e) { e3 = e; }
  check(e3 && e3.name === 'AbortError', 'Call 0: Abbruch wird durchgereicht (nicht still der Rohtext)');
  globalThis.fetch = async () => json(200, { error: { message: 'kaputt' } });
  check(await correctTranscriptionWithGemini('Knie rechts', ctxBasis) === 'Knie rechts', 'Call 0: Fehlerantwort → Rohtext (wie bisher)');
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
