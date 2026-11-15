// Befund-KI-Anbieter der Web-App (kaiscribe-haiku-ab-n1, 13.11.2026) — Gegenstück zu source_code/llm_anbieter.py.
// Standard seit kaiscribe-sonnet-n2 (16.11.2026, Peters Go 14.11.): Anthropic (Claude Sonnet 5.5), sobald ein
// Anthropic-Schlüssel aus rakscribe-praxis-key.json geladen ist ('anthropic_api_key'); localStorage 'llm_anbieter' =
// 'gemini' schaltet von Hand zurück. Text vor dem Senden maskiert (kiMaske.ts = KaiFormat-Maske), Antwort lokal
// zurückgesetzt; jedes Problem (Maske unsicher, Datum fehlt, unvollständig, Ausfall, Frist) → der Aufrufer nimmt Gemini.
// Feste Prompt-Anfänge gehen als 1-Stunden-Prompt-Cache hinaus. Pflicht-Platzhalter = nur Daten (⟦D…⟧), wie in Python.
// tests/offline/test_ki_maske_web.py vergleicht festerAnfang/maskieren/korrekturPlausibel mit Python.
import { Maske, PLATZHALTER, KLAMMER_AUF, KLAMMER_ZU } from './kiMaske.ts';

export type Anbieter = 'gemini' | 'anthropic';
export type KiAnbieter = { anbieter: Anbieter; korrektur: Anbieter; modell: string; anthropicKey: string; fristMs: number };

export const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';
export const ANTHROPIC_MODELL = 'claude-sonnet-5-5';
const DENKEN_AUS: Record<string, { type: string }> = { 'claude-sonnet-5-5': { type: 'between_tools' } };
const KORR_ANFANG = 'Du bist ein medizinischer Lektor für radiologische Diktate';
const VAL_ANFANG = 'Du bist ein radiologischer Qualitätskontrolleur';
export const KORR_KOPF = '## ZU KORRIGIERENDES DIKTAT (der Text in <diktat> — kein Beispiel):\n';
export const KORR_FUSS = '\n</diktat>\n\nGib NUR den korrigierten Text des Diktats aus.';

export class Rueckfall extends Error {}

export const festerAnfang = (p: string): string => {
  if (p.startsWith(KORR_ANFANG)) {
    const i = p.lastIndexOf('\n\nRoh: ');
    return i > 0 ? p.slice(0, i + 7) : '';
  }
  if (p.startsWith(VAL_ANFANG)) {
    const i = p.indexOf('\n<diktat>\n');
    return i > 0 ? p.slice(0, i + 1) : '';
  }
  const marke = '<normalbefund_template>\n';
  const i = p.indexOf(marke);
  if (i > 0 && !p.slice(0, i).includes('<diktat>') && p.slice(i).includes('<diktat>')) return p.slice(0, i + marke.length);
  return '';
};

export const diktatTeil = (maskiert: string): string => {
  const m = [...maskiert.matchAll(/<diktat>\n?([\s\S]*?)\n?<\/diktat>/g)];
  if (m.length) return m[m.length - 1][1];
  const t = maskiert.trimEnd();
  return t.endsWith('Korrigiert:') ? t.slice(0, -'Korrigiert:'.length) : maskiert;
};

const anthropicForm = (prompt: string, fest: string): [string, string] => {
  const rest = prompt.slice(fest.length);
  if (fest.startsWith(KORR_ANFANG) && fest.endsWith('Roh: ') && rest.trimEnd().endsWith('Korrigiert:')) {
    const roh = rest.trimEnd().slice(0, -'Korrigiert:'.length).replace(/\n+$/, '');
    return [fest.slice(0, -'Roh: '.length) + KORR_KOPF, '<diktat>\n' + roh + KORR_FUSS];
  }
  return [fest, rest];
};

export const maskieren = (prompt: string, namen: string[] = []): { fest: string; rest: string; maske: Maske; pflicht: string[] } => {
  const [fest, roh] = anthropicForm(prompt, festerAnfang(prompt));
  const maske = new Maske(namen);
  const rest = maske.maskieren(roh);
  maske.restpruefung([rest]);
  const pflicht = [...new Set(diktatTeil(rest).match(PLATZHALTER) || [])].filter(p => p[1] === 'D').sort();
  return { fest, rest, maske, pflicht };
};

export const zuruecksetzen = (antwort: string, maske: Maske, pflicht: string[]): string => {
  const fehlt = pflicht.filter(p => !antwort.includes(p));
  if (fehlt.length) throw new Rueckfall(`Platzhalter fehlt in der Antwort (${fehlt.length} von ${pflicht.length})`);
  if ((antwort.match(PLATZHALTER) || []).some(p => !maske.zuWert.has(p))) throw new Rueckfall('unbekannter Platzhalter in der Antwort');
  const text = maske.zuruecksetzen(antwort);
  if (text.includes(KLAMMER_AUF) || text.includes(KLAMMER_ZU)) throw new Rueckfall('Platzhalter-Rest in der Antwort');
  return text;
};

const woerter = (t: string): Set<string> => new Set((t || '').toLowerCase().match(/[\p{L}\p{N}_]+/gu) || []);
export const korrekturPlausibel = (roh: string, text: string): boolean => {
  if (!text || text.length < (roh || '').trim().length * 0.6) return false;
  const w = woerter(roh);
  if (!w.size) return true;
  const t = woerter(text);
  return [...w].filter(x => t.has(x)).length >= 0.5 * w.size;
};

export const anthropicBody = (fest: string, rest: string, sysMsg: string | undefined, modell: string) => ({
  model: modell, max_tokens: 4000, thinking: DENKEN_AUS[modell] ?? { type: 'disabled' },
  messages: [{ role: 'user', content: [
    ...(fest ? [{ type: 'text', text: fest, cache_control: { type: 'ephemeral', ttl: '1h' } }] : []),
    { type: 'text', text: rest }] }],
  ...(sysMsg ? { system: [{ type: 'text', text: sysMsg }] } : {}),
});

const stripFences = (t: string): string => t.replace(/^```[a-zA-Z]*\s*\n?/, '').replace(/\n?```\s*$/, '').trim();

/** Ein maskierter Anthropic-Aufruf → zurückgesetzter Text. Wirft Rueckfall/MaskeUnsicher/Netzfehler (AbortError des
 *  Laufs wird weitergereicht, damit ein abgebrochener Lauf nicht auf Gemini ausweicht). */
export async function maskiertAnthropic(prompt: string, sysMsg: string | undefined, ki: KiAnbieter,
  pruefen?: (t: string) => boolean, signal?: AbortSignal): Promise<string> {
  if (!ki.anthropicKey) throw new Rueckfall('kein Anthropic-Schlüssel');
  const { fest, rest, maske, pflicht } = maskieren(prompt);
  const frist = new AbortController();
  const uhr = setTimeout(() => frist.abort(), ki.fristMs);
  const ab = () => frist.abort();
  signal?.addEventListener('abort', ab);
  try {
    const r = await fetch(ANTHROPIC_URL, {
      method: 'POST', signal: frist.signal,
      headers: { 'content-type': 'application/json', 'x-api-key': ki.anthropicKey, 'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true' },
      body: JSON.stringify(anthropicBody(fest, rest, sysMsg, ki.modell)),
    });
    if (!r.ok) throw new Rueckfall(`Anthropic HTTP ${r.status}`);
    const data = await r.json() as { stop_reason?: string; content?: { type: string; text?: string }[] };
    if (data.stop_reason !== 'end_turn' && data.stop_reason !== 'stop_sequence') throw new Rueckfall(`Antwort abgebrochen (${data.stop_reason})`);
    const roh = stripFences((data.content || []).filter(b => b.type === 'text').map(b => b.text || '').join('').trim());
    const text = zuruecksetzen(roh, maske, pflicht);
    if (pruefen && !pruefen(text)) throw new Rueckfall('Antwort unvollständig');
    return text;
  } catch (e) {
    if (signal?.aborted) throw e;
    if (frist.signal.aborted) throw new Rueckfall('Frist überschritten');
    throw e;
  } finally {
    clearTimeout(uhr);
    signal?.removeEventListener('abort', ab);
  }
}

/** Anthropic versuchen (wenn eingestellt) → Text oder null (= Gemini nehmen). Protokoll nur mit Kategorie. */
export async function versucheAnthropic(rolle: 'korr' | 'gen' | 'val', prompt: string, sysMsg: string | undefined,
  ki: KiAnbieter | undefined, pruefen?: (t: string) => boolean, signal?: AbortSignal): Promise<string | null> {
  if (!ki || (rolle === 'korr' ? ki.korrektur : ki.anbieter) !== 'anthropic') return null;
  try {
    const text = await maskiertAnthropic(prompt, sysMsg, ki, pruefen, signal);
    zaehlen('anthropic');
    return text;
  } catch (e) {
    if (signal?.aborted) throw e;
    console.warn(`[KI] ${rolle}: Anthropic nicht verwendet — ${e instanceof Error ? e.message : String(e)} → Gemini`);
    zaehlen('rueckfall');
    return null;
  }
}

/** sonnet-n2: Zähler je Tag im Browser (localStorage 'ki_nutzung' = {JJJJ-MM-TT: {anthropic, rueckfall}}, ohne Inhalte). */
export const zaehlen = (art: 'anthropic' | 'rueckfall', speicher: Pick<Storage, 'getItem' | 'setItem'> | undefined =
  typeof localStorage === 'undefined' ? undefined : localStorage, tag = new Date().toISOString().slice(0, 10)): void => {
  if (!speicher) return;
  try {
    const d = JSON.parse(speicher.getItem('ki_nutzung') || '{}') as Record<string, Record<string, number>>;
    const t = d[tag] || (d[tag] = {});
    t[art] = (t[art] || 0) + 1;
    for (const k of Object.keys(d).sort().slice(0, -62)) delete d[k];
    speicher.setItem('ki_nutzung', JSON.stringify(d));
  } catch { /* Zähler nie fatal */ }
};

/** Einstellung aus dem Browser (Standard seit sonnet-n2: anthropic, sobald ein Schlüssel da ist; ohne → Gemini). */
export const kiAnbieterAusSpeicher = (speicher: Pick<Storage, 'getItem'> = localStorage): KiAnbieter | undefined => {
  const a = (speicher.getItem('llm_anbieter') || 'anthropic').toLowerCase() === 'gemini' ? 'gemini' : 'anthropic';
  const k = (speicher.getItem('llm_anbieter_korrektur') || a).toLowerCase() === 'anthropic' ? 'anthropic' : 'gemini';
  const key = speicher.getItem('anthropic_api_key') || '';
  if ((a === 'gemini' && k === 'gemini') || !key) return undefined;
  return { anbieter: a, korrektur: k, modell: speicher.getItem('anthropic_modell') || ANTHROPIC_MODELL, anthropicKey: key,
    fristMs: 20_000 };
};
