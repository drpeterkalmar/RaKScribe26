// audio_test.mjs — neuer Audio-Pfad (src/audio.ts, Umbau Schritt 9) gegen den bisherigen Weg
// (downsampleBuffer → Float32-AudioBuffer → audioBufferToWav). Der alte Encoder steht hier als Referenz.
//   cd web_app && node --experimental-strip-types audio_test.mjs
import { Resampler16k, Int16Puffer, float32ToInt16At16k, wavBytes, sliceWav, int16AusWav } from './src/audio.ts';

let fail = 0, n = 0;
const check = (ok, label, detail = '') => { n++; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      ${detail}`); };

// ── Referenz: bisheriger Code aus App.tsx (v3.2.3) ──────────────────────────────────────────────────────
function mergeFloat32Arrays(chunks) {
  const totalLength = chunks.reduce((acc, val) => acc + val.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const c of chunks) { merged.set(c, offset); offset += c.length; }
  return merged;
}
function downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
  if (inputSampleRate === outputSampleRate) return buffer;
  if (inputSampleRate < outputSampleRate) return buffer;
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0, offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) { accum += buffer[i]; count++; }
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}
function audioBufferToWav(buffer) {  // buffer: { sampleRate, getChannelData(0) } wie AudioBuffer
  const sampleRate = buffer.sampleRate, result = buffer.getChannelData(0);
  const view = new DataView(new ArrayBuffer(44 + result.length * 2));
  const ws = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
  ws(0, 'RIFF'); view.setUint32(4, 36 + result.length * 2, true); ws(8, 'WAVE'); ws(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); ws(36, 'data'); view.setUint32(40, result.length * 2, true);
  let offset = 44;
  for (let i = 0; i < result.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, result[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return new Uint8Array(view.buffer);
}
const alterWeg = (f32, rate) => {  // copyToChannel in einen 16-kHz-AudioBuffer = Float32
  const res = Float32Array.from(downsampleBuffer(f32, rate, 16000));
  return { res, wav: audioBufferToWav({ sampleRate: 16000, getChannelData: () => res }) };
};
const gleich = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const sinus = (len, rate, hz = 440, amp = 0.6) => Float32Array.from({ length: len }, (_, i) => amp * Math.sin(2 * Math.PI * hz * i / rate));
// Mikrofon-Callback: Blöcke à 4096 (ScriptProcessor), Rest als kürzerer Block
const bloecke = (f32, groesse = 4096) => { const b = []; for (let i = 0; i < f32.length; i += groesse) b.push(f32.subarray(i, i + groesse)); return b; };
const streamen = (f32, rate, groesse) => {
  const r = new Resampler16k(rate), p = new Int16Puffer();
  for (const b of bloecke(f32, groesse)) p.anhaengen(r.push(b));
  p.anhaengen(r.flush());
  return p.ansicht();
};

// ── 1. Sinus 440 Hz bei 48 kHz → 16 kHz ─────────────────────────────────────────────────────────────────
{
  const n48 = 48000 * 3;
  const f32 = sinus(n48, 48000);
  const neu = streamen(f32, 48000, 4096);
  check(neu.length === n48 / 3, 'Länge = n/3 (48 kHz → 16 kHz)', neu.length);
  const alt = alterWeg(f32, 48000);
  const wavNeu = wavBytes(neu);
  check(gleich(wavNeu, alt.wav), 'Voll-WAV: neue Bytes = alter Weg (Block-Callback 4096)');
  const v = new DataView(wavNeu.buffer);
  const txt = (o, l) => String.fromCharCode(...wavNeu.subarray(o, o + l));
  check(txt(0, 4) === 'RIFF' && txt(8, 4) === 'WAVE' && txt(12, 4) === 'fmt ' && txt(36, 4) === 'data', 'WAV-Header: RIFF/WAVE/fmt /data');
  check(v.getUint32(4, true) === 36 + neu.length * 2 && v.getUint32(40, true) === neu.length * 2, 'WAV-Header: Längenfelder');
  check(v.getUint16(20, true) === 1 && v.getUint16(22, true) === 1 && v.getUint32(24, true) === 16000
        && v.getUint32(28, true) === 32000 && v.getUint16(32, true) === 2 && v.getUint16(34, true) === 16, 'WAV-Header: PCM, mono, 16 kHz, 16 Bit');
  check(gleich(float32ToInt16At16k(f32, 48000), neu), 'float32ToInt16At16k (ganzer Puffer) = gestreamt');
  // sliceWav = audioBufferToWav auf dem entsprechenden Ausschnitt
  for (const [a, b] of [[0, 16000], [16000, 112000], [95999, 48000], [47000, 47001]]) {
    const ref = audioBufferToWav({ sampleRate: 16000, getChannelData: () => alt.res.subarray(a, b) });
    const got = new Uint8Array(await sliceWav(neu, a, b).arrayBuffer());
    check(gleich(got, ref), `sliceWav(${a}, ${b}) = audioBufferToWav(Ausschnitt)`);
  }
}
// ── 2. andere Raten und Blockgrößen (iPhone 44,1/48 kHz, krumme Längen) ─────────────────────────────────
for (const [rate, len, gr] of [[44100, 44100 * 2 + 777, 4096], [48000, 48000 + 1, 1024], [44100, 999, 256], [96000, 96000 + 5, 4096], [22050, 22050 + 3, 512]]) {
  const f32 = sinus(len, rate, 1000, 0.9);
  const neu = streamen(f32, rate, gr);
  const alt = alterWeg(f32, rate);
  check(gleich(wavBytes(neu), alt.wav), `${rate} Hz, ${len} Samples, Blöcke ${gr}: Bytes = alter Weg`, `${neu.length} vs ${alt.res.length}`);
}
// ── 3. Grenzfälle: Übersteuerung, 16 kHz (unverändert), leer ────────────────────────────────────────────
{
  const f32 = Float32Array.from({ length: 48000 }, (_, i) => (i % 7 === 0 ? 1.7 : i % 5 === 0 ? -1.3 : (i % 11) / 11 - 0.5));
  check(gleich(wavBytes(streamen(f32, 48000, 4096)), alterWeg(f32, 48000).wav), 'Übersteuerung (|x| > 1) wird gleich begrenzt');
  const f16 = sinus(16000 + 9, 16000);
  check(gleich(wavBytes(streamen(f16, 16000, 4096)), alterWeg(f16, 16000).wav), '16 kHz: unverändert durchgereicht (wie bisher)');
  check(streamen(new Float32Array(0), 48000, 4096).length === 0, 'leere Aufnahme → 0 Samples');
}
// ── 4. Puffer wächst über die Startkapazität (30 s) hinaus ──────────────────────────────────────────────
{
  const p = new Int16Puffer();
  const block = Int16Array.from({ length: 16000 }, (_, i) => i - 8000);
  for (let s = 0; s < 75; s++) p.anhaengen(block);
  const a = p.ansicht();
  check(a.length === 75 * 16000 && a[0] === -8000 && a[74 * 16000 + 15999] === 7999, 'Int16Puffer: 75 s angehängt, Inhalt intakt');
}
// ── 5. WAV wieder einlesen (chirp_3-Segmentierung > 59 s ohne AudioContext) ─────────────────────────────
{
  const s = Int16Array.from({ length: 70 * 16000 }, (_, i) => ((i * 37) % 65536) - 32768);
  const zurueck = await int16AusWav(new Blob([wavBytes(s)]));
  check(gleich(zurueck, s), 'int16AusWav(wavBytes(x)) = x (70 s)');
  let fehler = null;
  try { await int16AusWav(new Blob([wavBytes(s.subarray(0, 100), 48000)])); } catch (e) { fehler = e; }
  check(fehler && /16-kHz/.test(fehler.message), 'fremde Abtastrate → klare Fehlermeldung statt falscher Geschwindigkeit');
}

console.log(`${n - fail}/${n} PASS (audio)`);
process.exit(fail ? 1 : 0);
