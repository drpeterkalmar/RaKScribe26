// llm_anbieter_test.mjs — Web: Anbieter-Weiche (src/llmAnbieter.ts) in den echten Aufrufen von src/gemini.ts, ohne Netz
// (fetch-Attrappe). Standard Gemini unverändert; anthropic = maskiert, Antwort zurückgesetzt; Rückfall auf Gemini.
//   cd web_app && node --experimental-strip-types llm_anbieter_test.mjs
import { callGeminiLLM, correctTranscriptionWithGemini, validateReportConsistency } from './src/gemini.ts';
import { kiAnbieterAusSpeicher, maskieren, KORR_KOPF, zaehlen, anthropicSchluesselNachladen, DRIVE_BEREICH, OhneKi, OHNE_KI_ZEILE, ANTHROPIC_FRIST_MS } from './src/llmAnbieter.ts';
import { befundAusDiktat } from './src/pipeline.ts';

let fail = 0, n = 0;
const check = (ok, label, got) => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      got ${JSON.stringify(got)?.slice(0, 400)}`); };
const PROMPT = 'Regeln …\n<normalbefund_template>\n{template_body}\n</normalbefund_template>\n\n{examples}\n\n<diktat>\n{roh_text}\n</diktat>\n';
const DIKTAT = 'Kniegelenk rechts, Vergleich mit der Voruntersuchung vom 12.03.2025, mäßiggradige Gonarthrose.';
const BEFUND = (x) => `## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nGelenkspaltverschmälerung medial${x}.\n\n## Ergebnis\n1. Mäßiggradige Gonarthrose rechts.`;
let aufrufe = [];
const gem = (text) => ({ ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text }] }, finishReason: 'STOP' }] }) });
const anth = (text, stop = 'end_turn') => ({ ok: true, status: 200, json: async () => ({ stop_reason: stop, content: [{ type: 'text', text }] }) });
let anthAntwort = (body) => {
  const rest = body.messages[0].content.at(-1).text;
  const ph = rest.match(/⟦[PDNAE]\d+⟧/g) || [];
  return anth(BEFUND(', Vergleich ' + ph.join(' ')));
};
globalThis.fetch = async (url, opt) => {
  const body = JSON.parse(opt.body);
  aufrufe.push({ url, body, headers: opt.headers });
  return url.includes('anthropic') ? anthAntwort(body) : gem(BEFUND(' (Gemini)'));
};
console.warn = () => {};
console.log = ((log) => (...a) => { if (String(a[0]).startsWith('PASS') || String(a[0]).startsWith('FAIL') || /PASS \(/.test(a[0])) log(...a); })(console.log);
const ctx = (ki) => ({ apiKey: 'AQ.test', prompt: PROMPT, status: () => {}, ki });
const KI = { anbieter: 'anthropic', korrektur: 'anthropic', modell: 'claude-sonnet-5-5', anthropicKey: 'sk-test', fristMs: 5000, pauseMs: 0 };
// ohne-gemini-n1: KI_AN = 'ki_rueckfall' = 'an' (alter Weg/Rückweg, ein Versuch, dann Gemini)
const KI_AN = { ...KI, rueckfall: true };

aufrufe = [];
let t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(undefined));
check(aufrufe.length === 1 && aufrufe[0].url.includes('aiplatform') && t.includes('(Gemini)'), 'ohne ki → Gemini wie bisher', aufrufe.map(a => a.url));

aufrufe = [];
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
const a0 = aufrufe[0];
check(aufrufe.length === 1 && a0.url.includes('anthropic') && t.includes('12.03.2025') && !t.includes('⟦'), 'anthropic: ein Aufruf, Datum zurückgesetzt', t);
check(!JSON.stringify(a0.body).includes('12.03.2025'), 'Ausgang ohne Datum');
check(a0.body.messages[0].content[0].cache_control?.type === 'ephemeral' && a0.body.messages[0].content[0].cache_control?.ttl === '1h' && a0.body.messages[0].content[0].text.endsWith('<normalbefund_template>\n')
  && a0.body.thinking.type === 'between_tools' && !('temperature' in a0.body) && a0.body.system[0].text.startsWith('Du bist ein präziser'),
  'Body: Cache-Breakpoint, Nachdenken aus, System', a0.body);
check(a0.headers['anthropic-dangerous-direct-browser-access'] === 'true' && a0.headers['x-api-key'] === 'sk-test', 'Header Browser-Zugriff + Schlüssel');

aufrufe = []; anthAntwort = () => anth(BEFUND(''));
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI_AN));
check(aufrufe.length === 2 && aufrufe[1].url.includes('aiplatform') && t.includes('(Gemini)'), 'ki_rueckfall = an: Platzhalter fehlt → Gemini', aufrufe.map(a => a.url));
aufrufe = []; anthAntwort = () => { throw new Error('Netz weg'); };
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI_AN));
check(t.includes('(Gemini)'), 'ki_rueckfall = an: Ausfall → Gemini', t);
aufrufe = []; anthAntwort = (b) => anth(BEFUND(' ' + (b.messages[0].content.at(-1).text.match(/⟦[PDNAE]\d+⟧/g) || []).join(' ')), 'max_tokens');
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI_AN));
check(t.includes('(Gemini)'), 'ki_rueckfall = an: abgeschnitten (max_tokens) → Gemini', t);

// ── ohne-gemini-n1 (Standard): nie Gemini — zweiter Anthropic-Versuch, dann OhneKi (Spion: Gemini-URL nie gerufen) ──
const ohne = async (name, antwortFn, kat, versuche = 2) => {
  aufrufe = []; anthAntwort = antwortFn;
  let e = null;
  try { await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI)); } catch (x) { e = x; }
  check(e instanceof OhneKi && e.grund === kat && aufrufe.length === versuche && aufrufe.every(a => a.url.includes('anthropic')),
    `ki_rueckfall aus: ${name} → ${versuche} Versuch(e), OhneKi(${kat}), kein Gemini`, { e: String(e), urls: aufrufe.map(a => a.url) });
};
await ohne('Platzhalter fehlt', () => anth(BEFUND('')), 'Platzhalter');
await ohne('Netz weg', () => { throw new TypeError('Failed to fetch'); }, 'Netz');
await ohne('HTTP 529', () => ({ ok: false, status: 529, json: async () => ({}) }), 'HTTP 529');
await ohne('HTTP 429', () => ({ ok: false, status: 429, json: async () => ({}) }), 'HTTP 429');
await ohne('HTTP 400 (kein zweiter Versuch)', () => ({ ok: false, status: 400, json: async () => ({}) }), 'HTTP 400', 1);
await ohne('abgeschnitten', (b) => anth(BEFUND(' ' + (b.messages[0].content.at(-1).text.match(/⟦[PDNAE]\d+⟧/g) || []).join(' ')), 'max_tokens'), 'abgebrochen');
{
  aufrufe = []; let nr = 0;
  anthAntwort = (b) => (++nr === 1 ? ({ ok: false, status: 529, json: async () => ({}) })
    : anth(BEFUND(', Vergleich ' + (b.messages[0].content.at(-1).text.match(/⟦[PDNAE]\d+⟧/g) || []).join(' '))));
  const t2 = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
  check(aufrufe.length === 2 && t2.includes('12.03.2025') && aufrufe.every(a => a.url.includes('anthropic')), 'ki_rueckfall aus: 529, dann zweiter Versuch gut → Claude-Befund', t2);
}
{
  aufrufe = [];
  let e = null;
  try { await callGeminiLLM(DIKTAT.replace('mäßiggradige', '⟦X⟧ mäßiggradige'), 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI)); } catch (x) { e = x; }
  check(e instanceof OhneKi && e.grund === 'Maske unsicher' && aufrufe.length === 0, 'ki_rueckfall aus: Maske unsicher → nichts gesendet, kein Gemini, OhneKi', { e: String(e), n: aufrufe.length });
}
// Befund-Kette: ohne KI → Diktat unverändert, ohneKi-Meldung (Prüfzeile)
{
  aufrufe = []; anthAntwort = () => anth(BEFUND(''));
  const tpl = { knie: { body: 'Kniegelenk:\nNormal.', display_name: 'Kniegelenk', ergebnis: 'Unauffällig.' },
    allgemein: { body: 'Allgemein:\nNormal.', display_name: 'Allgemein', ergebnis: 'Unauffällig.' } };
  const gemeldet = [];
  const r = await befundAusDiktat(DIKTAT, { ...ctx(KI), templates: tpl, vorrang: { widersprueche: [], kurzsaetze: [] }, displayNames: [],
    ohneKi: (g) => gemeldet.push(g) }).catch(e => 'FEHLER ' + e);
  check(r === DIKTAT && gemeldet.length === 1 && gemeldet[0] === 'Platzhalter' && aufrufe.every(a => a.url.includes('anthropic'))
    && OHNE_KI_ZEILE === 'KI nicht verfügbar – Diktat unformatiert übernommen, bitte prüfen.',
    'Befund ohne KI: Diktat unverändert zurück, Prüfzeile gemeldet, kein Gemini', { r, gemeldet, urls: aufrufe.map(a => a.url) });
}

// Call 0
aufrufe = []; anthAntwort = (b) => {
  const r = b.messages[0].content.at(-1).text;
  return anth(r.split('<diktat>\n')[1].split('\n</diktat>')[0].replace('mäßiggradige', 'Mäßiggradige'));
};
t = await correctTranscriptionWithGemini(DIKTAT, ctx(KI));
check(t.includes('Mäßiggradige') && t.includes('12.03.2025') && aufrufe.length === 1 && aufrufe[0].body.messages[0].content[0].text.endsWith(KORR_KOPF),
  'Call 0 anthropic: <diktat>-Form, korrigiert, Datum zurück', t);
aufrufe = []; anthAntwort = () => anth('Bitte gib mir den Text, den du korrigiert haben möchtest, danke sehr vielmals.');
t = await correctTranscriptionWithGemini(DIKTAT, ctx(KI_AN));
check(aufrufe.length === 2 && aufrufe[1].url.includes('aiplatform'), 'ki_rueckfall = an: Call 0 Rückfrage statt Korrektur → Gemini', aufrufe.map(a => a.url));
aufrufe = [];
t = await correctTranscriptionWithGemini(DIKTAT, ctx(KI));
check(t === DIKTAT && aufrufe.length === 2 && aufrufe.every(a => a.url.includes('anthropic')), 'ki_rueckfall aus: Call 0 zweimal Rückfrage → Rohtext, kein Gemini', aufrufe.map(a => a.url));
aufrufe = [];
t = await correctTranscriptionWithGemini(DIKTAT, ctx({ ...KI, korrektur: 'gemini' }));
check(aufrufe.length === 1 && aufrufe[0].url.includes('aiplatform'), 'korrektur = gemini → Call 0 über Gemini');

// Call 2
aufrufe = []; anthAntwort = (b) => anth(BEFUND(', Vergleich ' + (b.messages[0].content.at(-1).text.split('</diktat>')[0].match(/⟦[PDNAE]\d+⟧/g) || []).join(' ')));
t = await validateReportConsistency(DIKTAT, BEFUND(''), ctx(KI));
check(aufrufe.length === 1 && aufrufe[0].url.includes('anthropic') && t.includes('12.03.2025'), 'Validator anthropic', t);
aufrufe = []; anthAntwort = () => { throw new TypeError('Failed to fetch'); };
t = await validateReportConsistency(DIKTAT, BEFUND(' (Call 1)'), ctx(KI));
check(t === BEFUND(' (Call 1)') && aufrufe.length === 2 && aufrufe.every(a => a.url.includes('anthropic')), 'ki_rueckfall aus: Prüfung ohne KI → Befund bleibt, Prüfung entfällt, kein Gemini', aufrufe.map(a => a.url));

// Einstellung
check(kiAnbieterAusSpeicher({ getItem: () => null })?.anthropicKey === '', 'webapp-schluessel-n1: ohne Schlüssel → Anbieter ohne Schlüssel (gezählter Rückfall)');
const sd = kiAnbieterAusSpeicher({ getItem: (k) => (k === 'anthropic_api_key' ? 'sk' : null) });
check(sd?.rueckfall === false && sd?.fristMs === 45_000 && ANTHROPIC_FRIST_MS === 45_000
  && kiAnbieterAusSpeicher({ getItem: (k) => ({ anthropic_api_key: 'sk', ki_rueckfall: 'an' })[k] ?? null })?.rueckfall === true,
  'ohne-gemini-n1: Standard Rückfall aus, Frist 45 s; ki_rueckfall = an schaltet den alten Weg ein', sd);
check(sd?.anbieter === 'anthropic' && sd?.korrektur === 'anthropic' && sd?.modell === 'claude-sonnet-5-5',
  'sonnet-n2: Standard = anthropic/Sonnet 5.5, sobald der Schlüssel geladen ist', sd);
check(kiAnbieterAusSpeicher({ getItem: (k) => ({ anthropic_api_key: 'sk', llm_anbieter: 'gemini' })[k] ?? null }) === undefined,
  'llm_anbieter = gemini schaltet von Hand zurück');
const sp = (o) => ({ getItem: (k) => o[k] ?? null });
check(kiAnbieterAusSpeicher(sp({ llm_anbieter: 'anthropic' }))?.anthropicKey === '', 'anthropic ohne Schlüssel → Anbieter ohne Schlüssel');
const k = kiAnbieterAusSpeicher(sp({ llm_anbieter: 'anthropic', anthropic_api_key: 'sk' }));
check(k?.anbieter === 'anthropic' && k?.korrektur === 'anthropic' && k?.modell === 'claude-sonnet-5-5', 'anthropic + Schlüssel → Sonnet 5.5', k);
const h = kiAnbieterAusSpeicher(sp({ llm_anbieter: 'gemini', llm_anbieter_korrektur: 'anthropic', anthropic_api_key: 'sk' }));
check(h?.anbieter === 'gemini' && h?.korrektur === 'anthropic', 'Hybrid: nur Call 0 anthropic', h);
check(maskieren('x\n<normalbefund_template>\nT\n</normalbefund_template>\n<diktat>\nDr. Huber 12.3.2025\n</diktat>').pflicht.length === 1, 'maskieren: Pflicht = nur das Datum aus <diktat> (Name darf fehlen)');
{
  const m = new Map(); const st = { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) };
  zaehlen('anthropic', st, '2026-11-16'); zaehlen('anthropic', st, '2026-11-16'); zaehlen('rueckfall', st, '2026-11-16');
  check(JSON.parse(m.get('ki_nutzung'))['2026-11-16'].anthropic === 2 && JSON.parse(m.get('ki_nutzung'))['2026-11-16'].rueckfall === 1,
    'Zähler je Tag (anthropic/rueckfall)', m.get('ki_nutzung'));
}
// webapp-schluessel-n1: ohne Schlüssel → Gemini, aber als Rückfall gezählt
{
  const m = new Map(); globalThis.localStorage = { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) };
  aufrufe = [];
  const t0 = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(kiAnbieterAusSpeicher(sp({ ki_rueckfall: 'an' }))));
  const heute = Object.values(JSON.parse(m.get('ki_nutzung') || '{}'))[0] || {};
  check(aufrufe.length === 1 && aufrufe[0].url.includes('aiplatform') && t0.includes('(Gemini)') && heute.rueckfall === 1 && !heute.anthropic,
    'ki_rueckfall = an, ohne Schlüssel: Gemini, gezählter Rückfall', { urls: aufrufe.map(a => a.url), heute });
  m.clear(); aufrufe = [];
  let e = null;
  try { await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(kiAnbieterAusSpeicher(sp({})))); } catch (x) { e = x; }
  const h2 = Object.values(JSON.parse(m.get('ki_nutzung') || '{}'))[0] || {};
  check(e instanceof OhneKi && e.grund === 'Schlüssel' && aufrufe.length === 0 && h2.ohne_ki === 1 && !h2.rueckfall,
    'ohne-gemini-n1: ohne Schlüssel → ohne KI gezählt, kein Gemini', { e: String(e), h2 });
  delete globalThis.localStorage;
}
// webapp-schluessel-n1: Claude-Schlüssel beim Start aus Drive nachladen (fetch-Attrappe für die Drive-API)
{
  const alt = globalThis.fetch;
  const drv = []; let antwort = { anthropic_api_key: 'sk-ant-drive' }; let liste = [{ id: 'neu' }, { id: 'alt' }];
  globalThis.fetch = async (url, opt) => {
    drv.push({ url, auth: opt?.headers?.authorization });
    if (url.includes('?q=')) return { ok: true, status: 200, json: async () => ({ files: liste }) };
    return { ok: true, status: 200, text: async () => JSON.stringify(antwort) };
  };
  const st = (o) => { const m = new Map(Object.entries(o)); return { m, getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) }; };
  const bereiche = []; const tok = async (b) => { bereiche.push(b); return 'tok'; };
  let s = st({});
  check(await anthropicSchluesselNachladen(tok, s) === 'geladen' && s.m.get('anthropic_api_key') === 'sk-ant-drive'
    && bereiche[0] === DRIVE_BEREICH && drv.length === 2 && drv.every(d => d.auth === 'Bearer tok')
    && decodeURIComponent(drv[0].url).includes("name = 'rakscribe-praxis-key.json' and trashed = false") && drv[1].url.endsWith('/neu?alt=media'),
    'Nachladen: neueste Drive-Datei, Schlüssel gespeichert', drv);
  drv.length = 0; s = st({ anthropic_api_key: 'sk-schon' });
  check(await anthropicSchluesselNachladen(tok, s) === 'da' && drv.length === 0 && s.m.get('anthropic_api_key') === 'sk-schon', 'Schlüssel schon da → kein Drive-Aufruf');
  drv.length = 0; s = st({ llm_anbieter: 'gemini' });
  check(await anthropicSchluesselNachladen(tok, s) === 'aus' && drv.length === 0, 'llm_anbieter = gemini → kein Nachladen');
  antwort = { vertex_api_key: 'AQ.x' }; s = st({});
  let fehler = '';
  try { await anthropicSchluesselNachladen(tok, s); } catch (e) { fehler = e.message; }
  check(fehler === 'Drive-Datei ohne anthropic_api_key' && !s.m.has('anthropic_api_key'), 'Drive-Datei ohne Claude-Schlüssel → Fehler, nichts gespeichert', fehler);
  liste = []; fehler = '';
  try { await anthropicSchluesselNachladen(tok, st({})); } catch (e) { fehler = e.message; }
  check(fehler.startsWith('Drive-Datei nicht gefunden'), 'nicht freigegeben → Fehler', fehler);
  globalThis.fetch = alt;
}
console.log(`${n - fail}/${n} PASS (llm_anbieter)`);
process.exit(fail ? 1 : 0);
