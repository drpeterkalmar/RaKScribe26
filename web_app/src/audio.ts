// Audio-Pfad der Web-App (Umbau Schritt 9, Gutachten P2-8): das Mikrofon-Signal wird schon im Callback auf
// 16 kHz Int16 reduziert und in EINEN wachsenden Puffer geschrieben. Chunk- und Voll-WAV entstehen durch
// Ausschneiden aus diesem Puffer — kein AudioContext/decodeAudioData mehr im Aufnahmepfad, 6× weniger Speicher
// (5-min-Diktat: ~9,6 MB statt ~57 MB Float32 bei 48 kHz plus Kopien beim Stopp).
// Rechnet exakt wie der bisherige Weg (downsampleBuffer → Float32 → audioBufferToWav): gleiche Bytes
// (web_app/audio_test.mjs).

export const ZIEL_RATE = 16000;

// float → Int16 wie audioBufferToWav: clamp, negativ ×0x8000, positiv ×0x7FFF, Nachkommastellen abgeschnitten
const zuInt16 = (f: number): number => {
  const s = Math.max(-1, Math.min(1, f));
  return s < 0 ? s * 0x8000 : s * 0x7FFF;
};

/** Ganzer Puffer auf einmal (z. B. Upload): Mittelwert-Downsampling wie downsampleBuffer, dann Int16. */
export function float32ToInt16At16k(buffer: Float32Array, inRate: number): Int16Array {
  const r = new Resampler16k(inRate);
  const a = r.push(buffer);
  const b = r.flush();
  const out = new Int16Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

/** Schrittweises Downsampling (Audio-Callback, Blöcke beliebiger Länge). Ergebnis über alle push() + flush()
 *  = downsampleBuffer() über die gesamte Aufnahme. Bei inRate <= 16 kHz unverändert (wie bisher). */
export class Resampler16k {
  private ratio: number;
  private durch: boolean;
  private k = 0;        // Index des nächsten Ausgabe-Samples
  private ende = 0;     // erstes Eingabe-Sample, das nicht mehr zu Ausgabe k gehört
  private acc = 0;
  private cnt = 0;
  private pos = 0;      // Anzahl bisher gelesener Eingabe-Samples

  constructor(inRate: number) {
    this.ratio = inRate / ZIEL_RATE;
    this.durch = inRate <= ZIEL_RATE;
    this.ende = Math.round(this.ratio);
  }

  push(chunk: Float32Array): Int16Array {
    if (this.durch) {
      const out = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) out[i] = zuInt16(chunk[i]);
      this.pos += chunk.length;
      return out;
    }
    const out = new Int16Array(Math.ceil(chunk.length / this.ratio) + 2);
    let n = 0;
    for (let j = 0; j < chunk.length; j++) {
      const i = this.pos + j;
      while (i >= this.ende) {
        out[n++] = zuInt16(this.cnt > 0 ? Math.fround(this.acc / this.cnt) : 0);
        this.k++;
        this.acc = 0;
        this.cnt = 0;
        this.ende = Math.round((this.k + 1) * this.ratio);
      }
      this.acc += chunk[j];
      this.cnt++;
    }
    this.pos += chunk.length;
    return out.subarray(0, n);
  }

  /** Aufnahme-Ende: restliche Ausgabe-Samples bis round(N / ratio) (wie downsampleBuffer). */
  flush(): Int16Array {
    if (this.durch) return new Int16Array(0);
    const gesamt = Math.round(this.pos / this.ratio);
    const rest = Math.max(0, gesamt - this.k);
    const out = new Int16Array(rest);
    for (let n = 0; n < rest; n++) {
      out[n] = n === 0 && this.cnt > 0 ? zuInt16(Math.fround(this.acc / this.cnt)) : 0;
    }
    this.k += rest;
    this.acc = 0;
    this.cnt = 0;
    return out;
  }
}

/** Wachsender Int16-Puffer (Kapazität verdoppelt sich, keine Liste von Einzelblöcken). */
export class Int16Puffer {
  private daten = new Int16Array(ZIEL_RATE * 30);
  laenge = 0;

  anhaengen(samples: Int16Array): void {
    if (this.laenge + samples.length > this.daten.length) {
      let neu = this.daten.length * 2;
      while (neu < this.laenge + samples.length) neu *= 2;
      const groesser = new Int16Array(neu);
      groesser.set(this.daten.subarray(0, this.laenge));
      this.daten = groesser;
    }
    this.daten.set(samples, this.laenge);
    this.laenge += samples.length;
  }

  ansicht(): Int16Array {
    return this.daten.subarray(0, this.laenge);
  }
}

/** PCM16-Mono-WAV (44-Byte-Header wie audioBufferToWav). */
export function wavBytes(samples: Int16Array, sampleRate: number = ZIEL_RATE): Uint8Array {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buf);
  const ws = (o: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
  ws(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  ws(8, 'WAVE');
  ws(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);              // PCM
  view.setUint16(22, 1, true);              // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);              // block align
  view.setUint16(34, 16, true);             // bits per sample
  ws(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) view.setInt16(44 + i * 2, samples[i], true);
  return new Uint8Array(buf);
}

export const wavFromInt16 = (samples: Int16Array, sampleRate: number = ZIEL_RATE): Blob =>
  new Blob([wavBytes(samples, sampleRate) as Uint8Array<ArrayBuffer>], { type: 'audio/wav' });

/** Ausschnitt [fromSample, toSample) des Aufnahme-Puffers als WAV (Chunk für die Live-Anzeige, chirp_3-Segment). */
export const sliceWav = (buffer: Int16Array, fromSample: number, toSample: number): Blob =>
  wavFromInt16(buffer.subarray(fromSample, toSample));

/** Eigene 16-kHz-PCM16-Mono-WAV wieder in Samples (für die chirp_3-Segmentierung > 59 s) — ohne AudioContext,
 *  also unabhängig davon, ob das Gerät { sampleRate: 16000 } beachtet (Gutachten P2-8c). */
export async function int16AusWav(wav: Blob): Promise<Int16Array> {
  const buf = await wav.arrayBuffer();
  const view = new DataView(buf);
  const text = (o: number, n: number) => String.fromCharCode(...new Uint8Array(buf, o, n));
  if (buf.byteLength < 44 || text(0, 4) !== 'RIFF' || text(8, 4) !== 'WAVE' || view.getUint16(20, true) !== 1
      || view.getUint16(22, true) !== 1 || view.getUint16(34, true) !== 16 || view.getUint32(24, true) !== ZIEL_RATE) {
    throw new Error('Audio ist kein 16-kHz-PCM16-Mono-WAV — Segmentierung nicht möglich.');
  }
  const n = Math.floor((buf.byteLength - 44) / 2);
  const out = new Int16Array(n);
  for (let i = 0; i < n; i++) out[i] = view.getInt16(44 + i * 2, true);
  return out;
}
