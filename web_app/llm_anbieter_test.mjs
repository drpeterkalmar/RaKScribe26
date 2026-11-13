// llm_anbieter_test.mjs — Web: Anbieter-Weiche (src/llmAnbieter.ts) in den echten Aufrufen von src/gemini.ts, ohne Netz
// (fetch-Attrappe). Standard Gemini unverändert; anthropic = maskiert, Antwort zurückgesetzt; Rückfall auf Gemini.
//   cd web_app && node --experimental-strip-types llm_anbieter_test.mjs
import { callGeminiLLM, correctTranscriptionWithGemini, validateReportConsistency } from './src/gemini.ts';
import { kiAnbieterAusSpeicher, maskieren, KORR_KOPF } from './src/llmAnbieter.ts';

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
const KI = { anbieter: 'anthropic', korrektur: 'anthropic', modell: 'claude-haiku-5-5', anthropicKey: 'sk-test', fristMs: 5000 };

aufrufe = [];
let t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(undefined));
check(aufrufe.length === 1 && aufrufe[0].url.includes('aiplatform') && t.includes('(Gemini)'), 'ohne ki → Gemini wie bisher', aufrufe.map(a => a.url));

aufrufe = [];
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
const a0 = aufrufe[0];
check(aufrufe.length === 1 && a0.url.includes('anthropic') && t.includes('12.03.2025') && !t.includes('⟦'), 'anthropic: ein Aufruf, Datum zurückgesetzt', t);
check(!JSON.stringify(a0.body).includes('12.03.2025'), 'Ausgang ohne Datum');
check(a0.body.messages[0].content[0].cache_control?.type === 'ephemeral' && a0.body.messages[0].content[0].text.endsWith('<normalbefund_template>\n')
  && a0.body.thinking.type === 'disabled' && !('temperature' in a0.body) && a0.body.system[0].text.startsWith('Du bist ein präziser'),
  'Body: Cache-Breakpoint, Nachdenken aus, System', a0.body);
check(a0.headers['anthropic-dangerous-direct-browser-access'] === 'true' && a0.headers['x-api-key'] === 'sk-test', 'Header Browser-Zugriff + Schlüssel');

aufrufe = []; anthAntwort = () => anth(BEFUND(''));
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
check(aufrufe.length === 2 && aufrufe[1].url.includes('aiplatform') && t.includes('(Gemini)'), 'Platzhalter fehlt → Gemini', aufrufe.map(a => a.url));
aufrufe = []; anthAntwort = () => { throw new Error('Netz weg'); };
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
check(t.includes('(Gemini)'), 'Ausfall → Gemini', t);
aufrufe = []; anthAntwort = (b) => anth(BEFUND(' ' + (b.messages[0].content.at(-1).text.match(/⟦[PDNAE]\d+⟧/g) || []).join(' ')), 'max_tokens');
t = await callGeminiLLM(DIKTAT, 'Normalbefund.', 'Kniegelenk', '', 'Unauffällig.', ctx(KI));
check(t.includes('(Gemini)'), 'abgeschnitten (max_tokens) → Gemini', t);

// Call 0
aufrufe = []; anthAntwort = (b) => {
  const r = b.messages[0].content.at(-1).text;
  return anth(r.split('<diktat>\n')[1].split('\n</diktat>')[0].replace('mäßiggradige', 'Mäßiggradige'));
};
t = await correctTranscriptionWithGemini(DIKTAT, ctx(KI));
check(t.includes('Mäßiggradige') && t.includes('12.03.2025') && aufrufe.length === 1 && aufrufe[0].body.messages[0].content[0].text.endsWith(KORR_KOPF),
  'Call 0 anthropic: <diktat>-Form, korrigiert, Datum zurück', t);
aufrufe = []; anthAntwort = () => anth('Bitte gib mir den Text, den du korrigiert haben möchtest, danke sehr vielmals.');
t = await correctTranscriptionWithGemini(DIKTAT, ctx(KI));
check(aufrufe.length === 2 && aufrufe[1].url.includes('aiplatform'), 'Call 0 Rückfrage statt Korrektur → Gemini', aufrufe.map(a => a.url));
aufrufe = [];
t = await correctTranscriptionWithGemini(DIKTAT, ctx({ ...KI, korrektur: 'gemini' }));
check(aufrufe.length === 1 && aufrufe[0].url.includes('aiplatform'), 'korrektur = gemini → Call 0 über Gemini');

// Call 2
aufrufe = []; anthAntwort = (b) => anth(BEFUND(', Vergleich ' + (b.messages[0].content.at(-1).text.split('</diktat>')[0].match(/⟦[PDNAE]\d+⟧/g) || []).join(' ')));
t = await validateReportConsistency(DIKTAT, BEFUND(''), ctx(KI));
check(aufrufe.length === 1 && aufrufe[0].url.includes('anthropic') && t.includes('12.03.2025'), 'Validator anthropic', t);

// Einstellung
check(kiAnbieterAusSpeicher({ getItem: () => null }) === undefined, 'Einstellung fehlt → Gemini');
const sp = (o) => ({ getItem: (k) => o[k] ?? null });
check(kiAnbieterAusSpeicher(sp({ llm_anbieter: 'anthropic' })) === undefined, 'anthropic ohne Schlüssel → Gemini');
const k = kiAnbieterAusSpeicher(sp({ llm_anbieter: 'anthropic', anthropic_api_key: 'sk' }));
check(k?.anbieter === 'anthropic' && k?.korrektur === 'anthropic' && k?.modell === 'claude-haiku-5-5', 'anthropic + Schlüssel → Haiku 5.5', k);
const h = kiAnbieterAusSpeicher(sp({ llm_anbieter_korrektur: 'anthropic', anthropic_api_key: 'sk' }));
check(h?.anbieter === 'gemini' && h?.korrektur === 'anthropic', 'Hybrid: nur Call 0 anthropic', h);
check(maskieren('x\n<normalbefund_template>\nT\n</normalbefund_template>\n<diktat>\nDr. Huber 12.3.2025\n</diktat>').pflicht.length === 2, 'maskieren: Pflicht aus <diktat>');
console.log(`${n - fail}/${n} PASS (llm_anbieter)`);
process.exit(fail ? 1 : 0);
