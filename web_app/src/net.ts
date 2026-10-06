// ─────────────────────────────────────────────────────────────────────────
// fetchWithRetry — robust fetch with timeout + automatic retry
// Prevents silent failures when Google Cloud APIs are slow or flaky.
// The web app must handle this autonomously — no Hermes to the rescue.
// Umbau Schritt 8 (Gutachten P2-7): ein von außen übergebenes options.signal bricht sofort ab (kein Retry) —
// so beendet „Neu“/F9 eine laufende Kette, statt dass sie später Befund und Zwischenablage überschreibt.
// ─────────────────────────────────────────────────────────────────────────

export class AbbruchFehler extends Error {
  constructor() {
    super('Abgebrochen');
    this.name = 'AbortError';
  }
}

export const istAbbruch = (err: unknown): boolean =>
  err instanceof Error && err.name === 'AbortError';

/** Meldungstext eines Fehlers (catch-Variable ist unknown). */
export const fehlermeldung = (err: unknown): string => (err instanceof Error ? err.message : String(err));

export async function fetchWithRetry(
  url: string,
  options: RequestInit,
  timeoutMs: number = 120_000,
  maxRetries: number = 3
): Promise<Response> {
  const extern = options.signal || undefined;
  const warten = (ms: number) => new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    extern?.addEventListener('abort', () => { clearTimeout(t); reject(new AbbruchFehler()); }, { once: true });
  });
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    if (extern?.aborted) throw new AbbruchFehler();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    const weiterreichen = () => controller.abort();
    extern?.addEventListener('abort', weiterreichen, { once: true });

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      extern?.removeEventListener('abort', weiterreichen);

      // Retry on 429 (rate limit), 500, 502, 503, 504
      if (response.status === 429 || response.status >= 500) {
        const waitSec = Math.min(2 ** attempt, 8);
        if (attempt < maxRetries) {
          console.warn(`[FETCH] HTTP ${response.status}, retry ${attempt}/${maxRetries} in ${waitSec}s...`);
          await warten(waitSec * 1000);
          continue;
        }
      }
      return response;
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      extern?.removeEventListener('abort', weiterreichen);
      if (extern?.aborted) throw new AbbruchFehler();
      if (istAbbruch(err) && attempt < maxRetries) {
        const waitSec = Math.min(2 ** attempt, 8);
        console.warn(`[FETCH] Timeout (${timeoutMs}ms), retry ${attempt}/${maxRetries} in ${waitSec}s...`);
        await warten(waitSec * 1000);
        continue;
      }
      throw err;
    }
  }
  throw new Error(`fetchWithRetry: Max retries (${maxRetries}) exceeded for ${url}`);
}
