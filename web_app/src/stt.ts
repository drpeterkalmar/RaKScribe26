// Spracherkennung der Web-App (Umbau Schritt 8): Google STT v1 (6-s-Chunks, Live-Anzeige), chirp_3 (STT v2,
// komplettes Diktat), Whisper-Fallback. Aus App.tsx herausgelöst, damit Abbruch und Fehlerweitergabe ohne Browser
// testbar sind (web_app/pipeline_test.mjs). Gleiche Requests wie vorher.
// Gutachten P2-10: Whisper (http://localhost:8765) nur noch, wenn die App selbst auf localhost läuft oder
// localStorage.whisper_fallback === '1' — sonst kommt die echte Google-Fehlermeldung beim Nutzer an.
import { fetchWithRetry, istAbbruch } from './net.ts';
import { int16AusWav, sliceWav } from './audio.ts';

export type SttSchluessel = { client_email: string; private_key: string };
// Phrasenlisten (Umbau Schritt 20, Gutachten P2-2): EINE Datei /phrases.json für EXE + Web. App.tsx importiert sie
// und gibt sie hier mit — medical = 6-s-Chunk-Boost (latest_long, 15.0), chirp = kuratiertes chirp_3-PhraseSet.
export type Phrasen = { medical: string[]; chirp: string[] };

export type SttKontext = {
  sttKey: SttSchluessel | null;
  phrasen: Phrasen;
  signal?: AbortSignal;
  status?: (text: string) => void;
};

// ── Base64 ohne FileReader (gleiches Ergebnis wie readAsDataURL, auch in Node testbar) ──
export function base64AusBytes(bytes: Uint8Array): string {
  let out = '';
  const STUECK = 3 * 16384; // Vielfaches von 3 (Base64 ohne Füllzeichen in der Mitte), < 65536 Argumente (Safari)
  for (let i = 0; i < bytes.length; i += STUECK) {
    out += btoa(String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + STUECK))));
  }
  return out;
}

export const blobToBase64 = async (blob: Blob): Promise<string> =>
  base64AusBytes(new Uint8Array(await blob.arrayBuffer()));

// ── GOOGLE CLOUD STT — Service-Account (rakscribe-stt@) → JWT → Bearer Token ──
const toBase64Url = (buffer: ArrayBuffer): string =>
  btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

async function signJwt(payload: object, privateKeyPem: string): Promise<string> {
  const header = { alg: 'RS256', typ: 'JWT' };
  const pemBody = privateKeyPem
    .replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\n|\r/g, '');
  const derBinary = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
  const cryptoKey = await crypto.subtle.importKey(
    'pkcs8', derBinary.buffer as ArrayBuffer,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false, ['sign']
  );
  const enc = new TextEncoder();
  const headerB64 = toBase64Url(enc.encode(JSON.stringify(header)).buffer as ArrayBuffer);
  const payloadB64 = toBase64Url(enc.encode(JSON.stringify(payload)).buffer as ArrayBuffer);
  const signingInput = `${headerB64}.${payloadB64}`;
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', cryptoKey, enc.encode(signingInput));
  return `${signingInput}.${toBase64Url(sig)}`;
}

const SCOPE = 'https://www.googleapis.com/auth/cloud-platform';
const tokenCache: { [clientEmail: string]: { token: string; expiry: number } } = {};

// Gültiges Bearer-Token für den STT-Service-Account (gecacht, Erneuerung 2 min vor Ablauf)
export async function getSttToken(keyJson: SttSchluessel | null, signal?: AbortSignal): Promise<string> {
  if (!keyJson) throw new Error('STT-Schluessel nicht geladen.');
  const now = Math.floor(Date.now() / 1000);
  const cached = tokenCache[keyJson.client_email];
  if (cached && cached.expiry > now + 120) return cached.token;
  const jwt = await signJwt({
    iss: keyJson.client_email,
    scope: SCOPE,
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  }, keyJson.private_key);
  const resp = await fetchWithRetry('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
    signal,
  }, 30_000, 3);
  const data = await resp.json();
  if (!data.access_token) throw new Error('Google OAuth Fehler: ' + JSON.stringify(data));
  tokenCache[keyJson.client_email] = { token: data.access_token, expiry: now + (data.expires_in || 3600) };
  return data.access_token;
}

type SttErgebnis = { results?: { alternatives: { transcript: string }[] }[]; error?: { message?: string } };
const transkriptAus = (data: SttErgebnis): string =>
  (data.results || []).map(r => r.alternatives[0].transcript).join(' ');

// Chunk-Transkription (6-s-Chunks während der Aufnahme, latest_long) — nur Live-Anzeige
export async function transcribeChunkWithGoogle(wavBlob: Blob, ctx: SttKontext): Promise<string> {
  const token = await getSttToken(ctx.sttKey, ctx.signal);
  ctx.status?.('Transkribiere (Google Cloud STT)...');
  const base64Data = await blobToBase64(wavBlob);
  const response = await fetchWithRetry('https://speech.googleapis.com/v1/speech:recognize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
      config: {
        encoding: 'LINEAR16', sampleRateHertz: 16000, languageCode: 'de-DE',
        enableAutomaticPunctuation: true, model: 'latest_long', useEnhanced: true,  // WER-Test 03.09.: short verliert Material
        speechContexts: [{ phrases: ctx.phrasen.medical, boost: 15.0 }],
      },
      audio: { content: base64Data },
    }),
    signal: ctx.signal,
  }, 120_000, 3);
  const data: SttErgebnis = await response.json();
  if (data.error) throw new Error(data.error.message || 'Google STT Fehler.');
  return transkriptAus(data);
}

// FULL-AUDIO Transkription (v2.9.10): chirp_3 via STT v2 (Location eu).
// WER-Test 04.09.: chirp_3 = 2,4% (auch bei Echo/Daempfung) vs latest_long = 16,7%.
// v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation), BEWUSST KURZ — die 692er-Liste verschlechterte chirp_3.
export async function chirp3Recognize(token: string, wavB64: string, chirpPhrasen: string[], signal?: AbortSignal): Promise<string> {
  const url = 'https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize';
  const response = await fetchWithRetry(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
      config: {
        languageCodes: ['de-DE'],
        model: 'chirp_3',
        autoDecodingConfig: {},
        features: { enableAutomaticPunctuation: true },
        adaptation: { phraseSets: [{ inlinePhraseSet: { phrases: chirpPhrasen.map(value => ({ value, boost: 10 })) } }] },
      },
      content: wavB64,
    }),
    signal,
  }, 120_000, 3);
  const data: SttErgebnis = await response.json();
  if (data.error) throw new Error(data.error.message || 'chirp_3 Fehler.');
  return transkriptAus(data);
}

export function stitchOverlaps(a: string, b: string, window = 14): string {
  const aw: string[] = a.split(' ');
  const bw: string[] = b.split(' ');
  let best = 0;
  for (let L = Math.min(window, aw.length, bw.length); L > 0; L--) {
    const tail = aw.slice(-L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
    const head = bw.slice(0, L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
    if (tail.filter((w, i) => w === head[i]).length >= Math.max(1, Math.floor(L * 0.8))) { best = L; break; }  // v3.3.2 (Sync: stt.py)
  }
  return best ? a + ' ' + bw.slice(best).join(' ') : a + ' ' + b;
}

// Komplettes Diktat (16-kHz-WAV) → chirp_3. <=59 s: EIN Request; länger: 50-s-Segmente + 4 s Rückhören, Overlap-Stitch.
export async function transcribeFullAudioWithGoogle(wavBlob: Blob, ctx: SttKontext): Promise<string> {
  const token = await getSttToken(ctx.sttKey, ctx.signal);
  const base64Data = await blobToBase64(wavBlob);

  // Duration: 16000 samples/s * 2 bytes/sample = 32000 bytes/s (base64 ~4/3)
  const binarySize = Math.floor(base64Data.length * 3 / 4);
  const estimatedDurationSec = binarySize / 32000;
  console.log(`[FULL-AUDIO] ${binarySize} bytes, ~${estimatedDurationSec.toFixed(1)}s`);

  if (estimatedDurationSec <= 59) {
    ctx.status?.('Volltranskription läuft (chirp_3, komplettes Diktat)...');
    return await chirp3Recognize(token, base64Data, ctx.phrasen.chirp, ctx.signal);
  }

  console.log('[FULL-AUDIO] chirp_3 Segmentierung (>60s)');
  ctx.status?.('Volltranskription läuft (langes Diktat, chirp_3, bitte warten)...');
  // Umbau Schritt 9 (Gutachten P2-8c): Samples direkt aus der eigenen 16-kHz-WAV lesen — kein AudioContext/
  // decodeAudioData mehr (auf Geräten, die { sampleRate: 16000 } ignorieren, kam sonst verlangsamtes Audio an)
  const s16 = await int16AusWav(wavBlob);
  const SR = 16000, SEG = 50 * SR, OV = 4 * SR;
  const texts: string[] = [];
  let start = 0;
  while (start < s16.length) {
    const end = Math.min(start + SEG, s16.length);
    texts.push(await chirp3Recognize(token, await blobToBase64(sliceWav(s16, start, end)), ctx.phrasen.chirp, ctx.signal));
    if (end >= s16.length) break;
    start = end - OV;
  }
  let full = texts[0];
  for (let i = 1; i < texts.length; i++) full = stitchOverlaps(full, texts[i]);
  return full;
}

// ── Whisper (lokaler Server auf dem Praxis-PC) — nur noch lokal (Gutachten P2-10) ──
export function whisperErlaubt(): boolean {
  try {
    if (typeof location !== 'undefined' && location.hostname === 'localhost') return true;
    return typeof localStorage !== 'undefined' && localStorage.getItem('whisper_fallback') === '1';
  } catch {
    return false;
  }
}

export async function transcribeWithWhisper(audioBlob: Blob, signal?: AbortSignal): Promise<string> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.ogg');
  console.log('[WHISPER] Sende Audio an lokalen Whisper-Server...');
  const response = await fetchWithRetry('http://localhost:8765/whisper', {
    method: 'POST',
    body: formData,
    signal,
  }, 120_000, 3);
  const data = await response.json();
  if (data.error) {
    throw new Error('Whisper STT Fehler: ' + data.error);
  }
  const text = (data.text || '').trim();
  console.log(`[WHISPER] Fertig in ${data.elapsed_seconds}s (${text.length} Zeichen)`);
  return text;
}

const fehlertext = (err: unknown): string => (err instanceof Error ? err.message : String(err));

// Google zuerst; Whisper nur lokal, sonst die Google-Meldung an den Nutzer (P2-10). Abbruch wird immer weitergereicht.
export async function mitFallback(google: () => Promise<string>, whisperAudio: Blob, ctx: SttKontext): Promise<string> {
  try {
    return await google();
  } catch (sttErr: unknown) {
    if (istAbbruch(sttErr)) throw sttErr;
    if (!whisperErlaubt()) {
      throw new Error(`Google-Spracherkennung fehlgeschlagen: ${fehlertext(sttErr)}`, { cause: sttErr });
    }
    console.warn('[STT] Google fehlgeschlagen, Whisper-Fallback:', fehlertext(sttErr));
    ctx.status?.('Spracherkennung läuft (Whisper, Fallback)...');
    return await transcribeWithWhisper(whisperAudio, ctx.signal);
  }
}

// Wrapper wie bisher: isFull = komplettes Diktat (chirp_3), sonst 6-s-Chunk (latest_long)
export const transcribeAudio = (wavBlob: Blob, isFull: boolean, ctx: SttKontext): Promise<string> =>
  mitFallback(() => (isFull ? transcribeFullAudioWithGoogle(wavBlob, ctx) : transcribeChunkWithGoogle(wavBlob, ctx)),
    wavBlob, ctx);
