// KaiScribe-Übungsmodus (kaiscribe-uebung-n1, Peter/Georg 25.11.2026): ein vergangener Ordi-Tag zum Üben – „nichts wird
// irgendwo hin geschickt“. Die Fälle kommen zur Laufzeit vom Übungsdienst auf der Ordi-VM (nur Tailnet, Anmeldung je
// Kürzel kp/rg), nie aus dem Bundle (öffentlich auf GitHub Pages).
//
// HARTE SPERRE (im Code, keine Einstellung): Im Übungsmodus darf die App nur noch mit der Spracherkennung (Google),
// der Befund-KI (Claude maskiert / Gemini EU), dem Schlüssel-Nachladen (Drive, nur lesen) und dem Übungsdienst reden.
// Alles andere – Zwischenablage (der Weg ins CAS), sendBeacon, WebSocket, XHR/fetch zu anderen Zielen (lokaler Whisper,
// Brücke, Plaza …), window.open – wird abgefangen, nicht ausgeführt und gezählt. Test: web_app/uebung_test.mjs.

export const UEBUNG_BALKEN = 'ÜBUNG – nichts wird gesendet';
export const UEBUNG_KUERZEL = ['kp', 'rg'] as const;

// Ziele, die im Übungsmodus erreichbar bleiben (Host genau, https)
export const ERLAUBTE_HOSTS = [
  'oauth2.googleapis.com',            // STT-Token
  'eu-speech.googleapis.com',         // Live-Anzeige + chirp_3 (EU)
  'aiplatform.eu.rep.googleapis.com', // Gemini EU (Korrektur/Rückfall)
  'api.anthropic.com',                // Claude Sonnet maskiert (Befund-KI)
  'www.googleapis.com',               // Drive: Claude-Schlüssel nachladen (nur lesen)
];

/** ?uebung (Dienst = eigene Herkunft, App vom Übungsdienst ausgeliefert) bzw. ?uebung=https://… (App von Pages,
 *  Dienst im Tailnet). null = kein Übungsmodus. Nur https (oder http auf localhost für Tests). */
export function uebungBasis(href: string): string | null {
  let u: URL;
  try { u = new URL(href); } catch { return null; }
  if (!u.searchParams.has('uebung')) return null;
  const wert = (u.searchParams.get('uebung') || '').trim();
  if (!wert || wert === '1') return u.origin;
  try {
    const d = new URL(wert);
    const lokal = d.hostname === 'localhost' || d.hostname === '127.0.0.1';
    if (d.protocol !== 'https:' && !(lokal && d.protocol === 'http:')) return null;
    return d.origin;
  } catch {
    return null;
  }
}

export type Versuch = { art: string; ziel: string };

/** Sperre an einem Fenster-Objekt (Browser: window; Test: Attrappe) einrichten. Gibt die Liste der abgefangenen
 *  Versuche zurück (live). Doppelt einrichten ist harmlos. */
export function sperreEinrichten(w: Record<string, unknown>, dienst: string): Versuch[] {
  const g = w as unknown as {
    __uebungSperre?: Versuch[]; fetch?: typeof fetch; navigator?: { sendBeacon?: unknown; clipboard?: Record<string, unknown> };
    XMLHttpRequest?: { prototype: { open: (...a: unknown[]) => unknown } }; WebSocket?: unknown; open?: unknown;
    location?: { origin?: string };
  };
  if (g.__uebungSperre) return g.__uebungSperre;
  const versuche: Versuch[] = [];
  g.__uebungSperre = versuche;
  const dienstHerkunft = new URL(dienst).origin;
  const eigen = g.location?.origin || '';
  const erlaubt = (ziel: string): boolean => {
    let u: URL;
    try { u = new URL(ziel, eigen || dienstHerkunft); } catch { return false; }
    if (u.origin === dienstHerkunft) return true;
    if (eigen && u.origin === eigen && !u.pathname.startsWith('/api/')) return true;   // App-Dateien (Bundle) der eigenen Herkunft
    return u.protocol === 'https:' && ERLAUBTE_HOSTS.includes(u.hostname);
  };
  const gesperrt = (art: string, ziel: string) => {
    versuche.push({ art, ziel: String(ziel).slice(0, 120) });
    return new Error(`${UEBUNG_BALKEN} (${art} gesperrt)`);
  };
  const echtesFetch = g.fetch;
  if (echtesFetch) {
    g.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const ziel = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
      if (!erlaubt(ziel)) return Promise.reject(gesperrt('fetch', ziel));
      return echtesFetch.call(w, input, init);
    }) as typeof fetch;
  }
  const xhr = g.XMLHttpRequest;
  if (xhr?.prototype?.open) {
    const echtOpen = xhr.prototype.open;
    xhr.prototype.open = function (this: unknown, ...a: unknown[]) {
      if (!erlaubt(String(a[1]))) throw gesperrt('xhr', String(a[1]));
      return echtOpen.apply(this, a);
    };
  }
  if (g.navigator) {
    if ('sendBeacon' in g.navigator) {
      try {
        Object.defineProperty(g.navigator, 'sendBeacon', { configurable: true, value: (z: string) => { gesperrt('beacon', z); return false; } });
      } catch { /* schreibgeschützt: bleibt, App nutzt sendBeacon nicht */ }
    }
    const cb = g.navigator.clipboard;
    if (cb) {
      for (const k of ['write', 'writeText']) {
        try {
          Object.defineProperty(cb, k, { configurable: true, value: () => Promise.reject(gesperrt('zwischenablage', k)) });
        } catch { /* Attrappe ohne defineProperty */ }
      }
    }
  }
  if (g.WebSocket) {
    g.WebSocket = function (ziel: string) { throw gesperrt('websocket', ziel); } as unknown;
  }
  if (typeof g.open === 'function') {
    const echtOpen = g.open as (...a: unknown[]) => unknown;
    g.open = (ziel?: string, ...rest: unknown[]) => {
      if (!ziel || !erlaubt(String(ziel))) { gesperrt('fenster', String(ziel)); return null; }
      return echtOpen.call(w, ziel, ...rest);
    };
  }
  return versuche;
}

// ───────────────────────────── Dienst ─────────────────────────────
export type Leistung = { kurz?: string; text?: string; modalitaet?: string | null };
export type UebungFallKurz = { id: string; zeit?: string; untersuchungen?: string[]; alter?: number | null; geschlecht?: string; abgegeben?: boolean };
export type UebungFall = UebungFallKurz & {
  leistungen?: Leistung[]; ibl?: { modul: string; text: string }[]; senf?: string | null;
  vorbefund?: { datum?: string; kurz?: string; text?: string } | null; zuweisung?: string | null; hinweise?: string[];
};
export type DiffOp = ['=' | '-' | '+', string];
export type Zahlen = { gleich: number; fehlt: number; neu: number; aehnlich_prozent: number };

export class UebungDienst {
  basis: string;
  token = '';
  kuerzel = '';
  variante = 'anonym';
  sttRestS = 0;
  private f: typeof fetch;

  constructor(basis: string, f: typeof fetch = (...a) => fetch(...a)) {
    this.basis = basis.replace(/\/$/, '');
    this.f = f;
  }

  private async rufen<T>(pfad: string, init: RequestInit = {}): Promise<T> {
    const kopf: Record<string, string> = { ...(init.headers as Record<string, string> || {}) };
    if (this.token) kopf.Authorization = 'Bearer ' + this.token;
    if (init.body) kopf['Content-Type'] = 'application/json';
    const r = await this.f(this.basis + pfad, { ...init, headers: kopf });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(({ 401: 'Bitte neu anmelden', 403: j.fehler === 'erst abgeben' ? 'Erst abgeben, dann Lösung' : 'Kennwort falsch',
      429: 'Zu viele Versuche – 15 min gesperrt', 404: 'Nicht gefunden' } as Record<number, string>)[r.status] || `Übungsdienst: Fehler ${r.status}`);
    return j as T;
  }

  async anmelden(kuerzel: string, kennwort: string) {
    const j = await this.rufen<{ token: string; kuerzel: string; variante: string; stt_rest_s: number }>('/api/anmelden',
      { method: 'POST', body: JSON.stringify({ kuerzel, kennwort }) });
    this.token = j.token; this.kuerzel = j.kuerzel; this.variante = j.variante; this.sttRestS = j.stt_rest_s;
    return j;
  }
  tage() { return this.rufen<{ tage: string[]; stt_rest_s: number }>('/api/tage'); }
  faelle(tag: string) { return this.rufen<{ faelle: UebungFallKurz[]; variante: string }>(`/api/faelle?tag=${tag}`); }
  fall(tag: string, id: string) { return this.rufen<{ fall: UebungFall }>(`/api/fall?tag=${tag}&id=${encodeURIComponent(id)}`); }
  async stt(sekunden: number) {
    const j = await this.rufen<{ stt_rest_s: number; faktor: number }>('/api/stt', { method: 'POST', body: JSON.stringify({ sekunden }) });
    this.sttRestS = j.stt_rest_s;
    return j;
  }
  abgabe(tag: string, id: string, befund: string, diktat: string) {
    return this.rufen<{ ok: boolean; ablage: string; versuch: number; zahlen: Zahlen }>('/api/abgabe',
      { method: 'POST', body: JSON.stringify({ tag, id, befund, diktat }) });
  }
  loesung(tag: string, id: string) { return this.rufen<{ loesung: string; diff: DiffOp[]; zahlen: Zahlen }>(`/api/loesung?tag=${tag}&id=${encodeURIComponent(id)}`); }
  async word(tag: string, id: string): Promise<Blob> {
    const r = await this.f(`${this.basis}/api/word?tag=${tag}&id=${encodeURIComponent(id)}`, { headers: { Authorization: 'Bearer ' + this.token } });
    if (!r.ok) throw new Error('Word nicht verfügbar');
    return r.blob();
  }
}

/** Uhrzeit in ms (eigene Funktion: Aufnahmedauer für den Übungs-Deckel). */
export const jetztMs = (): number => Date.now();

export const tagAnzeige = (t: string) => (/^\d{8}$/.test(t) ? `${t.slice(6, 8)}.${t.slice(4, 6)}.${t.slice(0, 4)}` : t);
