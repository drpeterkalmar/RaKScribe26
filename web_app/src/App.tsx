import React, { useState, useEffect, useRef } from 'react';
import { useLatest } from './useLatest.ts';
import {
  Mic, MicOff, Copy, Check, Upload, Download, Sparkles, X, KeyRound, Menu, Trash2,
  RotateCcw, ShieldCheck, FileKey, LoaderCircle, CircleAlert, AudioLines, WandSparkles
} from 'lucide-react';
// Umbau Schritt 20 (Gutachten P2-13): Vorlagen nur noch EINMAL im Repo-Root (wie misheard_words.json)
import templatesData from '../../templates.json';
// Umbau Schritt 20: Phrasenlisten der Spracherkennung — EINE Datei für EXE + Web
import phrasesData from '../../phrases.json';
// v3.1: Fehlhör-Liste — EINE Quelle für Web + EXE (Repo-Root /misheard_words.json, kein Spiegel)
import misheardData from '../../misheard_words.json';
import { compileMisheard, misheardPromptBlock, applyMisheard, type MisheardFile } from './misheard';
// v3.2: EIN Befund-Prompt für Web + EXE (Repo-Root /radiology_prompt.txt, versioniert) + gemeinsame
// deterministische Regeln (Sync: source_code/befund_regeln.py, Fixtures: befund_regeln_fixtures.json)
import genPromptRaw from '../../radiology_prompt.txt?raw';
// Umbau Schritt 21 (Gutachten P2-12): Versionsnummer aus der Datei /VERSION (eine Quelle für EXE, Web, Release)
import appVersionRaw from '../../VERSION?raw';
import { stripPromptMarker, type VorrangDaten } from './befundRegeln';
import vorrangData from '../../vorlagen_vorrang.json';
// Umbau Schritt 17: Vorlagen-Erkennung + Befundtitel (src/detect.ts); Bypass/Regeln nutzt src/pipeline.ts
import { type TemplatesMap } from './detect.ts';
// Umbau Schritt 8 (Gutachten P2-7/P2-9/P2-10): Netz mit Abbruch, Spracherkennung, Lauf-Verwaltung
import { istAbbruch, fehlermeldung } from './net.ts';
// Umbau Schritt 18: Gemini-Aufrufe (Call 0/1/2, Schlüsselprüfung) und Befund-Kette als Module
import { correctTranscriptionWithGemini, testGeminiAPI } from './gemini.ts';
import { befundAusDiktat, nurTextAusDiktat, type PipelineKontext } from './pipeline.ts';
import { einfuegen, markdownOffset } from './einfuegen.ts';
import { transcribeAudio, transcribeFullAudioWithGoogle, mitFallback, type SttKontext, type SttSchluessel, type Phrasen } from './stt.ts';
import { LaufVerwaltung, befundLauf, type Lauf, type BefundUi } from './lauf.ts';
// Umbau Schritt 9 (Gutachten P2-8): 16 kHz Int16 schon im Audio-Callback, WAV per Ausschnitt
import { Resampler16k, Int16Puffer, float32ToInt16At16k, wavFromInt16, sliceWav } from './audio.ts';

// Types: Template / TemplatesMap in src/detect.ts

const templates = templatesData as TemplatesMap;
const DISPLAY_NAMES = Object.values(templates).map(t => t.display_name);
// Region nicht erkannt → Vorlage „allgemein“ aus templates.json (Umbau Schritt 24: doppelte Kopie ALLGEMEIN_FALLBACK entfällt)

// Phrasenlisten (phrases.json): 6-s-Chunks mit medical_web, chirp_3 mit chirp (wie bisher, ohne Doppelte)
const PHRASEN: Phrasen = { medical: phrasesData.medical_web, chirp: phrasesData.chirp };




// ─────────────────────────────────────────────────────────────────────────
// isNormalFinding — erkennt reine Normalbefunde für RAG-Bypass (kein LLM nötig)
// Wird von Recording- und Upload-Pfad verwendet. Negations-aware.
// ─────────────────────────────────────────────────────────────────────────
// (v3.2: Bypass-Entscheidung = isPureNormalFinding in normalbypass.ts — gleiche Semantik wie die EXE, gemeinsame Fixtures)

// (WAV/Downsampling: src/audio.ts — Umbau Schritt 9; alter Encoder als Referenz in web_app/audio_test.mjs)


// v3.0: Kein Login mehr. Die App ist gesperrt, bis der Praxis-Schlüssel geladen ist (Drag & Drop irgendwo
// ins Fenster oder Menü → „Schlüssel laden“). Erkennt praxis-key.json, SA-JSON (roh/Base64) und AQ.-Keys.
// Beide Schlüssel bleiben lokal im Browser (localStorage) — nichts verlässt das Gerät außer zu Google.

// Key-Generation-Marker: Bei Key-Rotation diesen Wert hochzählen. Gespeicherte
// Keys mit älterer Markierung werden beim Start verworfen (Fix für veraltete
// localStorage-Keys, die den frischen Key blockiert haben — vgl. 401 in der EXE).
const KEY_VERSION = '2';
// Gen-Prompt = gemeinsame Datei radiology_prompt.txt (Versionsmarker entfernt). Seit Umbau Schritt 19 (Gutachten P3-2)
// immer direkt aus dem Bundle — der frühere localStorage-Prompt (Editor gibt es seit v3.0 nicht mehr) entfällt.
const GEN_PROMPT = stripPromptMarker(genPromptRaw);
const APP_VERSION = appVersionRaw.trim();
// v3.1: Fehlhör-Liste — auto-Regeln laufen deterministisch VOR Call 0 (auch ohne Gemini),
// llm-Regeln landen als Tabelle im Call-0-Prompt. Pflege NUR in /misheard_words.json.
const MISHEARD: MisheardFile = misheardData as MisheardFile;
const MISHEARD_COMPILED = compileMisheard(MISHEARD);
const MISHEARD_PROMPT_BLOCK = misheardPromptBlock(MISHEARD);

// Umbau Schritt 19: getypter Zugriff auf Fenster-Erweiterungen (statt `window as any`)
type PraxisFenster = Window & { __praxisSttKey?: SttSchluessel | null; webkitAudioContext?: typeof AudioContext };
const fenster = window as PraxisFenster;
const AudioKontextKlasse = (): typeof AudioContext => window.AudioContext || (fenster.webkitAudioContext as typeof AudioContext);
type PraxisSchluessel = { type?: string; private_key?: string; vertex_api_key?: string; stt?: SttSchluessel };

// Gespeicherte Schlüssel beim Start (vorher im Mount-Effect). Stale-Key-Schutz: Schlüssel einer älteren
// Key-Generation verwerfen (Fix für veraltete localStorage-Keys, die den frischen Key blockiert haben).
function gespeicherterVertexKey(): string {
  const k = localStorage.getItem('vertex_api_key');
  // v3.3.2 (Gutachten P3-8): auch ein allein liegender STT-Schlüssel alter Generation wird entfernt
  if ((k || localStorage.getItem('praxis_stt_key')) && localStorage.getItem('key_version') !== KEY_VERSION) {
    console.log('[INIT] Veralteter gespeicherter Key (alte Key-Generation) verworfen');
    localStorage.removeItem('vertex_api_key');
    localStorage.removeItem('praxis_stt_key');
    return '';
  }
  return k || '';
}
// v3.0: STT-Schlüssel aus dem letzten Laden wiederherstellen (kein erneutes Reinziehen nötig)
function gespeicherterSttKey(): SttSchluessel | null {
  const s = localStorage.getItem('praxis_stt_key');
  if (s && localStorage.getItem('key_version') === KEY_VERSION) {
    try {
      const j = JSON.parse(s) as SttSchluessel;
      if (j && j.private_key) {
        fenster.__praxisSttKey = j;
        return j;
      }
    } catch { /* ignorieren */ }
  }
  return null;
}

async function audioEingaenge(requestPermission: boolean): Promise<MediaDeviceInfo[] | null> {
  try {
    if (requestPermission) {
      const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      tempStream.getTracks().forEach(track => track.stop());
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.filter(device => device.kind === 'audioinput');
  } catch (err) {
    console.error("Fehler beim Laden der Audiogeräte:", err);
    return null;
  }
}

async function loadPraxisKey(pw: string): Promise<boolean> {
  if (!pw) return false;
  let candidate = pw;

  // Base64-Hülle erkennen (stt-key.b64 / vertex-key.b64): kein '{', aber Base64-Zeichensatz
  if (!candidate.startsWith('{') && !candidate.startsWith('AQ.')) {
    try {
      const bin = atob(candidate.replace(/\s+/g, ''));
      const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
      const decoded = new TextDecoder().decode(bytes).trim();
      if (decoded.startsWith('{')) candidate = decoded;
    } catch { /* kein Base64 — weiter als roher Text */ }
  }

  if (candidate.startsWith('AQ.')) {
    // Vertex-API-Key (Gemini) — als LLM-Key übernehmen
    localStorage.setItem('vertex_api_key', candidate);
    localStorage.setItem('key_version', KEY_VERSION);
    window.dispatchEvent(new Event('vertex-key-external'));
    console.log('[KEY] Vertex API-Key erkannt');
    return true;
  }

  try {
    const json = JSON.parse(candidate) as PraxisSchluessel;
    if (json.type === 'service_account' && json.private_key) {
      // STT-Key global verfügbar machen (App setzt ihn beim Mount via Event)
      fenster.__praxisSttKey = json as SttSchluessel;
      localStorage.setItem('praxis_stt_key', JSON.stringify(json));
      localStorage.setItem('key_version', KEY_VERSION);
      window.dispatchEvent(new Event('praxis-stt-key'));
      console.log('[KEY] STT Service-Account-Key erkannt');
      return true;
    }
    if (json.vertex_api_key && json.stt && json.stt.private_key) {
      // Kombinierter Praxis-Key: EIN Login setzt LLM- und STT-Key (Drive: rakscribe-praxis-key.json)
      localStorage.setItem('vertex_api_key', json.vertex_api_key);
      localStorage.setItem('key_version', KEY_VERSION);
      fenster.__praxisSttKey = json.stt;
      localStorage.setItem('praxis_stt_key', JSON.stringify(json.stt));
      window.dispatchEvent(new Event('vertex-key-external'));
      window.dispatchEvent(new Event('praxis-stt-key'));
      console.log('[KEY] Kombinierter Praxis-Key erkannt (LLM + STT)');
      return true;
    }
  } catch { /* kein JSON */ }
  return false;
}

// v3.0: Befund formatiert anzeigen/kopieren. Bewusst minimal (nur ##, Listen, Absätze, **fett**), kein HTML aus dem Modell.
const escapeHtml = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function reportToHtml(md: string): string {
  const out: string[] = [];
  let list: 'ol' | 'ul' | null = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  const inline = (t: string) => escapeHtml(t).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    if (!line) { closeList(); continue; }
    const h = line.match(/^#{1,4}\s+(.*)$/);
    const ol = line.match(/^\d+[.)]\s+(.*)$/);
    const ul = line.match(/^[-*•]\s+(.*)$/);
    if (h) { closeList(); out.push(`<h3>${inline(h[1])}</h3>`); }
    else if (ol) { if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; } out.push(`<li>${inline(ol[1])}</li>`); }
    else if (ul) { if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; } out.push(`<li>${inline(ul[1])}</li>`); }
    else { closeList(); out.push(`<p>${inline(line)}</p>`); }
  }
  closeList();
  return out.join('');
}

export default function App() {
  // v3.0 Key-Gate (ersetzt den Login)
  const [keyError, setKeyError] = useState<string>('');
  const [menuOpen, setMenuOpen] = useState<boolean>(false);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [pasteOpen, setPasteOpen] = useState<boolean>(false);
  const [pasteValue, setPasteValue] = useState<string>('');
  const [reportView, setReportView] = useState<'formatiert' | 'text'>('formatiert');
  // v3.4.0 (Peter 07.10.): Schalter „Nur Text“ — rechts nur die korrigierte Spracherkennung, kein Befund
  const [nurText, setNurText] = useState<boolean>(() => localStorage.getItem('nur_text') === '1');
  const nurTextRef = useLatest(nurText);

  // Configuration States
  const [vertexApiKey, setVertexApiKey] = useState<string>(gespeicherterVertexKey);
  const [sttKeyJson, setSttKeyJson] = useState<SttSchluessel | null>(gespeicherterSttKey);
  const keysReady = !!vertexApiKey && !!(sttKeyJson && sttKeyJson.private_key);
  // Umbau Schritt 8 (Gutachten P2-9): Ergebnis der einmaligen Schlüsselprüfung je geladenem Gemini-Schlüssel
  const [keyPruefung, setKeyPruefung] = useState<{ key: string; stand: 'ok' | 'fehler'; meldung?: string }>({ key: '', stand: 'ok' });
  useEffect(() => {
    if (!vertexApiKey) return;
    let aktiv = true;
    testGeminiAPI(vertexApiKey)
      .then(() => { if (aktiv) setKeyPruefung({ key: vertexApiKey, stand: 'ok' }); })
      .catch((e: Error) => {
        console.warn('[KEY] Schlüsselprüfung fehlgeschlagen:', e.message);
        if (aktiv) setKeyPruefung({ key: vertexApiKey, stand: 'fehler', meldung: e.message });
      });
    return () => { aktiv = false; };
  }, [vertexApiKey]);
  const keysReadyRef = useLatest(keysReady);
  const audioUploadRef = useRef<HTMLInputElement>(null);
  const keyFileRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(() => localStorage.getItem('selected_audio_device_id') || '');

  // Application States
  const [status, setStatus] = useState<'ready' | 'recording' | 'processing' | 'copied'>('ready');
  const statusRef = useLatest(status);
  const [statusText, setStatusText] = useState<string>('Bereit');
  const [transcript, setTranscript] = useState<string>('');
  const [structuredReport, setStructuredReport] = useState<string>('');
  // v3.5.0 (Peter 07.10.): Befund bearbeitbar; Diktat an der Cursor-Stelle einfügen bzw. Markierung überschreiben
  const structuredReportRef = useLatest(structuredReport);
  const reportEditorRef = useRef<HTMLTextAreaElement>(null);
  const einfuegeZielRef = useRef<[number, number] | null>(null);    // beim Start der Aufnahme gemerkte Stelle
  const [cursorSetzen, setCursorSetzen] = useState<[number, number] | null>(null);  // nach Render in den Editor
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [pendingCopyText, setPendingCopyText] = useState<string>('');

  // Auto-copy helper with fallback
  const copyTextToClipboard = async (text: string): Promise<boolean> => {
    if (!text) return false;
    try {
      if (typeof ClipboardItem !== 'undefined' && navigator.clipboard.write) {
        const html = `<html><head><meta charset="utf-8"></head><body>${reportToHtml(text)}</body></html>`;
        await navigator.clipboard.write([new ClipboardItem({
          'text/plain': new Blob([text], { type: 'text/plain' }),
          'text/html': new Blob([html], { type: 'text/html' }),
        })]);
      } else {
        await navigator.clipboard.writeText(text);
      }
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 3000);
      setPendingCopyText(''); // Clear any pending copy
      return true;
    } catch (err) {
      console.warn("Auto-copy failed, saving for when tab is focused:", err);
      setPendingCopyText(text); // Save for later when window is focused
      return false;
    }
  };

  // Listen for window focus to trigger pending copies
  useEffect(() => {
    const handleWindowFocus = () => {
      if (pendingCopyText) {
        copyTextToClipboard(pendingCopyText);
      }
    };
    window.addEventListener('focus', handleWindowFocus);
    return () => window.removeEventListener('focus', handleWindowFocus);
  }, [pendingCopyText]);

  // (v3.2: Mock-RAG-Beispiele entfernt — unnummerierte Spielzeug-Befunde matchten fast jedes Diktat und
  //  verdrängten Template-Format und Nummerierung; die Telegram-Referenz arbeitet ohne Beispiele.)


  // Audio recording refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  // Umbau Schritt 9: EIN wachsender 16-kHz-Int16-Puffer statt Liste von Float32-Blöcken in nativer Rate
  const pufferRef = useRef<Int16Puffer>(new Int16Puffer());
  const resamplerRef = useRef<Resampler16k | null>(null);
  // Pegel ohne React-State (Gutachten P2-8a): Callback schreibt in die Ref, requestAnimationFrame zeichnet
  const micLevelRef = useRef<number>(0);
  const levelBarRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);

  // States and refs for chunked transcription feedback
  const [isTranscribingChunk, setIsTranscribingChunk] = useState<boolean>(false);
  const chunkIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastProcessedIndexRef = useRef<number>(0);  // Umbau Schritt 9: Sample-Index im Puffer
  const chunkTranscriptsRef = useRef<string[]>([]);
  const pendingPromisesRef = useRef<Promise<string>[]>([]);
  const activeRequestsCountRef = useRef<number>(0);
  const actualSampleRateRef = useRef<number>(16000);


  // Schlüssel aus Datei/Drag & Drop/Einfügen übernehmen (loadPraxisKey meldet per Event) — Umbau Schritt 19:
  // Startwerte kommen aus gespeicherterVertexKey/gespeicherterSttKey, Listener werden wieder abgemeldet (P3-2)
  useEffect(() => {
    const onVertexKey = () => {
      const k = localStorage.getItem('vertex_api_key');
      if (k) setVertexApiKey(k);
    };
    const onPraxisKey = () => {
      const k = fenster.__praxisSttKey;
      if (k && k.private_key) setSttKeyJson(k);
    };
    window.addEventListener('vertex-key-external', onVertexKey);
    window.addEventListener('praxis-stt-key', onPraxisKey);
    localStorage.removeItem('is_authenticated');
    // P3-2: der Prompt kommt immer aus radiology_prompt.txt — alte localStorage-Kopie entfernen
    localStorage.removeItem('system_prompt');
    localStorage.removeItem('system_prompt_version');
    // (v3.0: frühere Auto-Load-Fallbacks vertex-key.txt/.b64/stt-key.* entfernt — Schlüssel kommen nur per Drag & Drop/Menü)
    return () => {
      window.removeEventListener('vertex-key-external', onVertexKey);
      window.removeEventListener('praxis-stt-key', onPraxisKey);
    };
  }, []);

  useEffect(() => {
    let aktiv = true;
    const laden = (requestPermission: boolean) => {
      audioEingaenge(requestPermission).then(g => { if (aktiv && g) setAudioDevices(g); });
    };
    laden(true);
    const handleDeviceChange = () => laden(false);
    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
    return () => {
      aktiv = false;
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);
    };
  }, []);

  // Save config changes
  // Config auto-saved on change

  // v3.0: Schlüssel laden (Datei, Drag & Drop oder Einfügen) — ersetzt Login/Logout
  const applyKeyText = async (txt: string) => {
    setKeyError('');
    const ok = await loadPraxisKey(txt.trim());
    if (!ok) {
      setKeyError('Schlüssel nicht erkannt. Bitte rakscribe-praxis-key.json aus dem Drive-Ordner „RaKScribe“ verwenden.');
      return false;
    }
    setMenuOpen(false); setPasteOpen(false); setPasteValue('');
    return true;
  };

  const handleKeyFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    try { await applyKeyText(await f.text()); }
    catch { setKeyError('Datei konnte nicht gelesen werden.'); }
  };

  const removeKeys = () => {
    localStorage.removeItem('vertex_api_key');
    localStorage.removeItem('praxis_stt_key');
    localStorage.removeItem('key_version');
    fenster.__praxisSttKey = null;
    setVertexApiKey('');
    setSttKeyJson(null);
    setMenuOpen(false);
  };


  // v3.3.2 (Gutachten P3-4): Esc schließt auch den Dialog „Schlüssel einfügen“
  useEffect(() => {
    if (!pasteOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setPasteOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [pasteOpen]);

  // Menü schließen bei Klick außerhalb / Esc
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    window.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('mousedown', onDown); window.removeEventListener('keydown', onKey); };
  }, [menuOpen]);





  // (Vorlagen-Erkennung: src/detect.ts — Umbau Schritt 17)

  // Run full-text search simulation in the local report list

  // (Google STT / chirp_3 / Whisper: src/stt.ts — Umbau Schritt 8)

  // Beliebige Audiodatei (OGG/MP3/WAV) → mono 16kHz WAV (für Google STT)
  const decodeFileToWavBlob = async (file: File | Blob): Promise<Blob> => {
    const arrayBuffer = await file.arrayBuffer();
    const audioContext = new (AudioKontextKlasse())();
    try {
      const decodedAudio = await audioContext.decodeAudioData(arrayBuffer);
      // Gutachten P2-8c: Rate prüfen — unter 16 kHz würde das Audio sonst als 16 kHz (zu schnell) verschickt
      if (decodedAudio.sampleRate < 16000) {
        throw new Error(`Audiodatei mit ${decodedAudio.sampleRate} Hz wird nicht unterstützt (mindestens 16 kHz).`);
      }
      let channelData: Float32Array;
      if (decodedAudio.numberOfChannels > 1) {
        const length = decodedAudio.length;
        channelData = new Float32Array(length);
        for (let ch = 0; ch < decodedAudio.numberOfChannels; ch++) {
          const chData = decodedAudio.getChannelData(ch);
          for (let i = 0; i < length; i++) {
            channelData[i] += chData[i] / decodedAudio.numberOfChannels;
          }
        }
      } else {
        channelData = decodedAudio.getChannelData(0);
      }
      const samples = float32ToInt16At16k(channelData, decodedAudio.sampleRate);
      if (samples.length === 0) {
        throw new Error('Audiodatei ist leer oder zu kurz.');
      }
      return wavFromInt16(samples);  // Umbau Schritt 9: ohne zweiten AudioContext (gleiche Bytes)
    } finally {
      await audioContext.close();
    }
  };

  // ─────────────────────────────────────────────────────────────────────────

  // (Gemini-Aufrufe: src/gemini.ts, Befund-Kette: src/pipeline.ts — Umbau Schritt 18)

  // Umbau Schritt 8 (Gutachten P2-7): jede Aufnahme / jeder Upload = ein Lauf mit AbortController.
  // „Neu“/F9 bricht ab; ein abgebrochener oder überholter Lauf schreibt nichts mehr und kopiert nichts.
  const laeufeRef = useRef(new LaufVerwaltung());
  const aufnahmeLaufRef = useRef<Lauf | null>(null);
  const sttKontext = (lauf: Lauf): SttKontext => ({ sttKey: sttKeyJson, phrasen: PHRASEN, signal: lauf.signal, status: lauf.nurAktuell(setStatusText) });
  // Umbau Schritt 18: Kontext für Gemini-Aufrufe (src/gemini.ts) und Befund-Kette (src/pipeline.ts)
  const genKontext = (lauf: Lauf, signal: AbortSignal): PipelineKontext => ({
    apiKey: vertexApiKey, prompt: GEN_PROMPT, signal, status: lauf.nurAktuell(setStatusText),
    misheard: { compiled: MISHEARD_COMPILED, block: MISHEARD_PROMPT_BLOCK },
    templates, vorrang: vorrangData as VorrangDaten, displayNames: DISPLAY_NAMES,
  });
  // v3.5.0: Steht der Cursor im Befund-Editor (und ist ein Befund da), wird das nächste Diktat dort eingefügt.
  // Aufruf VOR dem Fokuswechsel (F10-keydown bzw. mousedown auf dem Aufnahme-Knopf).
  const einfuegeZielMerken = () => {
    const ed = reportEditorRef.current;
    einfuegeZielRef.current = ed && document.activeElement === ed && structuredReportRef.current.trim()
      ? [ed.selectionStart, ed.selectionEnd] : null;
  };

  // Klick/Markierung in der formatierten Ansicht → Text-Ansicht (bearbeitbar) mit Cursor an derselben Stelle
  const formatiertAngeklickt = (e: React.MouseEvent<HTMLDivElement>) => {
    const md = structuredReportRef.current;
    const sel = window.getSelection();
    const knoten = (n: Node | null) => {
      if (!n || n.nodeType !== Node.TEXT_NODE) return null;
      const alle: Node[] = [];
      const w = document.createTreeWalker(e.currentTarget, NodeFilter.SHOW_TEXT);
      for (let t = w.nextNode(); t; t = w.nextNode()) alle.push(t);
      const i = alle.indexOf(n);
      if (i < 0) return null;
      const txt = n.textContent ?? '';
      // Vorkommen des gleichen Textstücks in den Textknoten davor (wie indexOf im Markdown weiterzählt)
      const vorkommen = txt ? alle.slice(0, i).reduce((s, t) => s + ((t.textContent ?? '').split(txt).length - 1), 0) : 0;
      return { txt, vorkommen };
    };
    let a = md.length, b = md.length;
    if (sel && sel.rangeCount) {
      const r = sel.getRangeAt(0);
      const ka = knoten(r.startContainer), kb = knoten(r.endContainer);
      const oa = ka ? markdownOffset(md, ka.txt, r.startOffset, ka.vorkommen) : null;
      const ob = kb ? markdownOffset(md, kb.txt, r.endOffset, kb.vorkommen) : null;
      if (oa !== null) { a = oa; b = ob !== null && ob >= oa ? ob : oa; }
    }
    setReportView('text');
    setCursorSetzen([a, b]);
  };
  useEffect(() => {
    const ed = reportEditorRef.current;
    if (!cursorSetzen || !ed) return;
    ed.focus();
    ed.setSelectionRange(cursorSetzen[0], cursorSetzen[1]);
    setCursorSetzen(null);
  }, [cursorSetzen, reportView]);

  // Befund (Regionen → Bypass | Call 1 + 2) oder im Nur-Text-Modus nur der korrigierte Text (Call 0 lief schon)
  // v3.5.0: mit gemerkter Cursor-Stelle → korrigierter Text in den bestehenden Befund (Ergebnis = ganzer Befund)
  const befundOderText = (text: string, ctx: PipelineKontext, ziel: [number, number] | null = null): Promise<string> => {
    if (ziel) {
      const [neu, cursor] = einfuegen(structuredReportRef.current, ziel[0], ziel[1], nurTextAusDiktat(text, ctx));
      setReportView('text');
      setCursorSetzen([cursor, cursor]);
      return Promise.resolve(neu);
    }
    return nurTextRef.current ? Promise.resolve(nurTextAusDiktat(text, ctx)) : befundAusDiktat(text, ctx);
  };
  const befundUi = (): BefundUi => ({
    transkript: setTranscript,
    befund: setStructuredReport,
    status: setStatusText,
    fertig: () => { setStatus('ready'); setStatusText('Bereit'); },
    fehler: (meldung: string) => { setStatus('ready'); setStatusText('Fehler bei der Verarbeitung.'); alert(meldung); },
    kopieren: copyTextToClipboard,
  });

  // Helper function to process the next chunk of recorded audio (Live-Anzeige)
  const processNextAudioChunk = (lauf: Lauf) => {
    const samples = pufferRef.current.ansicht();
    const lastProcessedIndex = lastProcessedIndexRef.current;

    if (samples.length > lastProcessedIndex) {
      // Umbau Schritt 9: Chunk = Ausschnitt aus dem 16-kHz-Puffer (kein AudioContext je Chunk)
      const wavBlob = sliceWav(samples, lastProcessedIndex, samples.length);
      lastProcessedIndexRef.current = samples.length;

      const chunkIdx = chunkTranscriptsRef.current.length;
      chunkTranscriptsRef.current.push(''); // placeholder
      
      activeRequestsCountRef.current++;
      setIsTranscribingChunk(true);
      
      const p = transcribeAudio(wavBlob, false, sttKontext(lauf)).then(text => {
        if (!lauf.aktuell()) return '';
        chunkTranscriptsRef.current[chunkIdx] = text.trim();
        const fullText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
        setTranscript(fullText);
        return text.trim();
      }).catch(err => {
        if (!istAbbruch(err)) console.error("Fehler bei Chunk-Transkription:", err);
        return '';
      }).finally(() => {
        if (!lauf.aktuell()) return;
        activeRequestsCountRef.current--;
        if (activeRequestsCountRef.current <= 0) {
          setIsTranscribingChunk(false);
        }
      });
      
      pendingPromisesRef.current.push(p);
    }
  };

  // Mikrofon, Audio-Graph und Stream schließen (Stopp und Neu/F9)
  const audioStoppen = () => {
    if (processorRef.current) {
      processorRef.current.onaudioprocess = null;  // keine verspäteten Blöcke nach dem Stopp
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    cancelAnimationFrame(rafRef.current);
    micLevelRef.current = 0;
    if (levelBarRef.current) levelBarRef.current.style.width = '0%';
    // Gutachten P2-8d: Bildschirmsperre wieder erlauben
    wakeLockRef.current?.release().catch(() => {});
    wakeLockRef.current = null;
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
  };

  // Start Audio Recording
  const startRecording = async () => {
    try {
      if (!vertexApiKey) {
        alert("Fehler: Bitte tragen Sie Ihren Vertex AI API-Key in den Einstellungen ein!");
        setStatusText("Fehler: Vertex API-Key fehlt");
        setStatus('ready');
        return;
      }

      // Umbau Schritt 8 (Gutachten P2-9): Schlüssel wird einmal nach dem Laden geprüft. Nur wenn diese Prüfung
      // fehlschlug, vor dem Start erneut prüfen (Netzwackler beim Laden sperrt nicht dauerhaft).
      if (keyPruefung.key === vertexApiKey && keyPruefung.stand === 'fehler') {
        setStatusText("Verifiziere API-Key...");
        setStatus('processing');
        try {
          await testGeminiAPI(vertexApiKey);
          setKeyPruefung({ key: vertexApiKey, stand: 'ok' });
        } catch (verifyErr: unknown) {
          setKeyPruefung({ key: vertexApiKey, stand: 'fehler', meldung: fehlermeldung(verifyErr) });
          setStatus('ready');
          setStatusText('API-Key ungültig');
          alert("Fehler bei der Key-Verifikation:\n\n" + fehlermeldung(verifyErr) + "\n\nBitte überprüfen Sie Ihren API-Key in den Einstellungen.");
          return;
        }
      }

      const lauf = laeufeRef.current.neu();
      aufnahmeLaufRef.current = lauf;
      setTranscript('');
      if (!einfuegeZielRef.current) setStructuredReport('');  // v3.5.0: an der Cursor-Stelle → Befund bleibt
      setStatus('recording');
      setStatusText(einfuegeZielRef.current ? 'Aufnahme läuft — wird an der Cursor-Stelle im Befund eingefügt' : 'Aufnahme läuft...');
      pufferRef.current = new Int16Puffer();

      // Reset chunk refs
      lastProcessedIndexRef.current = 0;
      chunkTranscriptsRef.current = [];
      pendingPromisesRef.current = [];
      activeRequestsCountRef.current = 0;
      setIsTranscribingChunk(false);

      // Request microphone without DSP constraints to preserve raw speech quality
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        }
      });
      mediaStreamRef.current = stream;
      // Gutachten P2-8d: Bildschirm bleibt während der Aufnahme an (iPhone beendet sonst die Aufnahme)
      navigator.wakeLock?.request('screen').then(lock => {
        if (mediaStreamRef.current === stream) wakeLockRef.current = lock;
        else lock.release().catch(() => {});
      }).catch(() => { /* nicht unterstützt oder abgelehnt — Aufnahme läuft trotzdem */ });

      // Start AudioContext at native preferred hardware sample rate (avoids resampling dropouts)
      const AudioContextClass = AudioKontextKlasse();
      const audioContext = new AudioContextClass();
      audioContextRef.current = audioContext;
      actualSampleRateRef.current = audioContext.sampleRate;
      resamplerRef.current = new Resampler16k(audioContext.sampleRate);
      console.log(`[AUDIO] AudioContext initialized at native sample rate: ${audioContext.sampleRate} Hz`);

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // Umbau Schritt 9: sofort auf 16 kHz Int16 — nur das landet im Puffer
        if (resamplerRef.current) pufferRef.current.anhaengen(resamplerRef.current.push(inputData));

        let sum = 0;
        for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
        micLevelRef.current = Math.min(100, Math.round(Math.sqrt(sum / inputData.length) * 400));
      };

      // Pegelanzeige: höchstens einmal pro Bildschirmbild, ohne React-Neuzeichnen der App
      const pegelZeichnen = () => {
        if (levelBarRef.current) levelBarRef.current.style.width = `${micLevelRef.current}%`;
        rafRef.current = requestAnimationFrame(pegelZeichnen);
      };
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(pegelZeichnen);

      // Set up chunked interval for real-time visual feedback
      if (chunkIntervalRef.current) {
        clearInterval(chunkIntervalRef.current);
      }
      chunkIntervalRef.current = setInterval(() => processNextAudioChunk(lauf), 6000);

    } catch (err: unknown) {
      console.error(err);
      setStatus('ready');
      setStatusText('Fehler beim Mikrofonzugriff.');
      alert("Mikrofonzugriff verweigert oder nicht verfügbar: " + fehlermeldung(err));
    }
  };

  // Stop Audio Recording & Process Result
  const stopRecording = async () => {
    if (status !== 'recording') return;
    const lauf = aufnahmeLaufRef.current ?? laeufeRef.current.neu();

    setStatus('processing');
    setStatusText('Verarbeite Audio...');

    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }

    // Rest des Resamplers in den Puffer, dann den letzten Chunk BEFORE closing context
    if (resamplerRef.current) pufferRef.current.anhaengen(resamplerRef.current.flush());
    resamplerRef.current = null;
    processNextAudioChunk(lauf);
    audioStoppen();

    const chunkText = () => chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
    const ziel = einfuegeZielRef.current;  // v3.5.0: gemerkte Cursor-Stelle (null = normaler Befund)
    einfuegeZielRef.current = null;
    await befundLauf(lauf, {
      transkribieren: async () => {
        const st = lauf.nurAktuell(setStatusText);
        // Wait for any active/pending chunk requests to finish
        if (pendingPromisesRef.current.length > 0) {
          st('Warte auf ausstehende Chunk-Transkriptionen...');
          await Promise.all(pendingPromisesRef.current);
        }

        // FULL-AUDIO RE-TRANSCRIPTION: das komplette Diktat noch einmal an chirp_3 (voller Kontext)
        let finalRawText = '';
        let sttFehler: unknown = null;
        try {
          // Das komplette Diktat liegt schon als 16-kHz-Int16 im Puffer (Umbau Schritt 9)
          const alle = pufferRef.current.ansicht();
          if (alle.length > 0) {
            const fullWavBlob = wavFromInt16(alle);
            console.log(`[FULL-AUDIO] Re-transcribing complete recording (${alle.length} samples, ${(alle.length / 16000).toFixed(1)}s)`);
            st('Volltranskription läuft (komplettes Diktat)...');
            finalRawText = (await transcribeAudio(fullWavBlob, true, sttKontext(lauf))).trim();
          }
        } catch (fullAudioErr: unknown) {
          if (istAbbruch(fullAudioErr)) throw fullAudioErr;
          console.warn('[FULL-AUDIO] Re-transcription failed, falling back to chunk transcripts:', fehlermeldung(fullAudioErr));
          sttFehler = fullAudioErr;
          finalRawText = chunkText();
        }

        // If full-audio transcription returned empty, also fall back
        if (!finalRawText.trim()) {
          console.warn('[FULL-AUDIO] Empty result, falling back to chunk transcripts.');
          finalRawText = chunkText();
        }
        // Gutachten P2-10: ohne verwertbaren Text die echte Google-Meldung zeigen statt „kein Text erkannt“
        if (!finalRawText.trim() && sttFehler) throw sttFehler;
        return finalRawText;
      },
      korrigieren: (text, signal) => correctTranscriptionWithGemini(text, genKontext(lauf, signal)),
      // v3.2: gleiche Kette wie die EXE (Regionen trennen → je Region Bypass oder Gemini → Ergebnis nummerieren)
      befundErstellen: (text, signal) => befundOderText(text, genKontext(lauf, signal), ziel),
    }, befundUi(), { transkriptVorPruefung: true, fehlerPrefix: 'Fehler bei der Transkription oder KI-Strukturierung: ' });
  };

  // Manual Copy Result
  const handleCopyReport = async () => {
    if (!structuredReport) return;
    await copyTextToClipboard(structuredReport);
  };

  // Audio File Upload Handler — feeds uploaded audio through the same STT + Gemini pipeline
  const handleAudioUpload = async (file: File) => {
    // Umbau Schritt 8 (Gutachten P2-7): keine zweite Kette parallel zu Aufnahme oder Verarbeitung
    if (statusRef.current === 'processing' || statusRef.current === 'recording') {
      setStatusText(statusRef.current === 'recording'
        ? 'Bitte zuerst die Aufnahme beenden — Audio-Datei nicht übernommen.'
        : 'Bitte warten — es wird gerade ein Befund erstellt. Audio-Datei nicht übernommen.');
      return;
    }
    const lauf = laeufeRef.current.neu();
    setStatus('processing');
    setStatusText('Verarbeite hochgeladenes Audio...');
    setTranscript('');
    setStructuredReport('');

    await befundLauf(lauf, {
      // Step 1: Transkription via Google Cloud STT (Whisper nur lokal als Fallback)
      transkribieren: async () => {
        lauf.nurAktuell(setStatusText)('Spracherkennung läuft (Google Cloud STT)...');
        const ctx = sttKontext(lauf);
        return mitFallback(async () => transcribeFullAudioWithGoogle(await decodeFileToWavBlob(file), ctx), file, ctx);
      },
      // Step 1.5: LLM-Korrektur der STT-Ergebnisse
      korrigieren: (text, signal) => correctTranscriptionWithGemini(text, genKontext(lauf, signal)),
      // Step 2: v3.2 — dieselbe Kette wie Aufnahme und EXE (Regionen trennen → Bypass/Gemini → Ergebnis nummerieren)
      befundErstellen: (text, signal) => befundOderText(text, genKontext(lauf, signal)),
    }, befundUi(), { statusVorBefund: 'KI-Strukturierung läuft (Gemini Flash)...', fehlerPrefix: 'Fehler bei Audio-Upload-Verarbeitung: ' });
  };

  // v3.6.0 (Peter 07.10.): getippten/eingefügten Text im Diktat-Feld ohne Aufnahme strukturieren (Knopf bzw.
  // Strg+Enter). Gleiche Kette wie die EXE (befund_aus_text): Fehlhör-Liste → Befund; kein Call 0 (getippter Text hat
  // keine Spracherkennungsfehler), immer strukturiert — auch bei „Nur Text“.
  const befundAusText = async () => {
    if (statusRef.current === 'processing' || statusRef.current === 'recording' || !keysReadyRef.current) return;
    const text = transcript.trim();
    if (!text) { setStatusText('Bitte zuerst den Diktattext links eintippen oder einfügen.'); return; }
    const lauf = laeufeRef.current.neu();
    einfuegeZielRef.current = null;
    setStatus('processing');
    setStructuredReport('');
    await befundLauf(lauf, {
      transkribieren: async () => text,
      korrigieren: async t => applyMisheard(t, MISHEARD_COMPILED),
      befundErstellen: (t, signal) => befundAusDiktat(t, genKontext(lauf, signal)),
    }, befundUi(), { statusVorBefund: 'KI-Strukturierung läuft (Gemini Flash)...', fehlerPrefix: 'Fehler bei der KI-Strukturierung: ' });
  };

  // Reset fields — Umbau Schritt 8: bricht laufende Aufnahme/Verarbeitung ab (nichts wird mehr eingefügt)
  const handleReset = () => {
    laeufeRef.current.abbrechen();
    einfuegeZielRef.current = null;
    aufnahmeLaufRef.current = null;
    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }
    audioStoppen();
    resamplerRef.current = null;
    lastProcessedIndexRef.current = 0;
    chunkTranscriptsRef.current = [];
    pendingPromisesRef.current = [];
    activeRequestsCountRef.current = 0;
    setIsTranscribingChunk(false);

    setTranscript('');
    setStructuredReport('');
    setStatus('ready');
    setStatusText('Bereit');
  };

  // Refs to avoid stale closures in global keyboard event listeners (Umbau Schritt 19: useLatest)
  const startRecordingRef = useLatest(startRecording);
  const stopRecordingRef = useLatest(stopRecording);
  const handleResetRef = useLatest(handleReset);
  const einfuegeZielMerkenRef = useLatest(einfuegeZielMerken);
  const handleAudioUploadRef = useLatest(handleAudioUpload);

  // Drag & Drop irgendwo ins Fenster
  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types || []).includes('Files');
    const onEnter = (e: DragEvent) => { if (!hasFiles(e)) return; e.preventDefault(); depth++; setDragActive(true); };
    const onOver = (e: DragEvent) => { if (hasFiles(e)) e.preventDefault(); };
    const onLeave = (e: DragEvent) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) setDragActive(false); };
    const onDrop = async (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault(); depth = 0; setDragActive(false);
      const f = e.dataTransfer?.files?.[0];
      if (!f) return;
      if (/^audio\//.test(f.type) || /\.(ogg|mp3|wav|m4a|opus|webm)$/i.test(f.name)) {
        if (keysReadyRef.current) handleAudioUploadRef.current(f);
        else setKeyError('Bitte zuerst den Praxis-Schlüssel laden — danach können Audio-Dateien verarbeitet werden.');
        return;
      }
      try { await applyKeyText(await f.text()); } catch { setKeyError('Datei konnte nicht gelesen werden.'); }
    };
    window.addEventListener('dragenter', onEnter);
    window.addEventListener('dragover', onOver);
    window.addEventListener('dragleave', onLeave);
    window.addEventListener('drop', onDrop);
    return () => {
      window.removeEventListener('dragenter', onEnter);
      window.removeEventListener('dragover', onOver);
      window.removeEventListener('dragleave', onLeave);
      window.removeEventListener('drop', onDrop);
    };
  }, [keysReadyRef, handleAudioUploadRef]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F10') {
        e.preventDefault();
        if (statusRef.current === 'recording') {
          stopRecordingRef.current();
        } else if (statusRef.current === 'ready' && keysReadyRef.current) {
          einfuegeZielMerkenRef.current();
          startRecordingRef.current();
        }
      } else if (e.key === 'F9') {
        e.preventDefault();
        handleResetRef.current();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [statusRef, keysReadyRef, startRecordingRef, stopRecordingRef, handleResetRef, einfuegeZielMerkenRef]);

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (chunkIntervalRef.current) {
        clearInterval(chunkIntervalRef.current);
      }
    };
  }, []);


  // ── v3.0 Render ────────────────────────────────────────────────────────────
  const stateLabel = !keysReady ? 'Gesperrt' : status === 'recording' ? 'Aufnahme' : status === 'processing' ? 'Verarbeitung' : status === 'copied' ? 'Kopiert' : 'Bereit';
  const partialKey = !keysReady && (!!vertexApiKey || !!sttKeyJson);

  return (
    <div className={`app ${keysReady ? '' : 'is-locked'}`}>
      {/* Top bar */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true"><AudioLines size={18} /></div>
          <div className="brand-text">
            <span className="brand-name">RaKScribe</span>
            <span className="brand-sub">Röntgen am Kai</span>
          </div>
          <span className="version-chip">v{APP_VERSION}</span>
        </div>

        <div className={`state-pill state-${keysReady ? status : 'locked'}`} title={statusText}>
          <span className="state-dot" />
          <span className="state-label">{stateLabel}</span>
          {keysReady && statusText && statusText !== 'Bereit' && <span className="state-detail">{statusText}</span>}
        </div>

        <div className="topbar-actions">
          <span className={`key-chip ${keysReady ? 'ok' : 'missing'}`}>
            {keysReady ? <ShieldCheck size={14} /> : <KeyRound size={14} />}
            {keysReady ? 'Schlüssel aktiv' : 'Kein Schlüssel'}
          </span>

          <select
            value={selectedDeviceId}
            onChange={e => {
              setSelectedDeviceId(e.target.value);
              localStorage.setItem('selected_audio_device_id', e.target.value);
            }}
            className="mic-select"
            title="Mikrofon"
            aria-label="Mikrofon"
          >
            <option value="">Standard-Mikrofon</option>
            {audioDevices.map(device => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Mikrofon (${device.deviceId.slice(0, 8)}…)`}
              </option>
            ))}
          </select>

          <div className="menu" ref={menuRef}>
            <button className="icon-button" onClick={() => setMenuOpen(o => !o)} aria-label="Menü" aria-expanded={menuOpen}>
              <Menu size={20} />
            </button>
            {menuOpen && (
              <div className="menu-panel" role="menu">
                <label className="menu-item" role="menuitem">
                  <FileKey size={16} /> Schlüssel-Datei laden…
                  <input type="file" className="visually-hidden" onChange={handleKeyFile} />
                </label>
                <button className="menu-item" role="menuitem" onClick={() => { setPasteOpen(true); setMenuOpen(false); }}>
                  <KeyRound size={16} /> Schlüssel einfügen…
                </button>
                {(vertexApiKey || sttKeyJson) && (
                  <button className="menu-item danger" role="menuitem" onClick={removeKeys}>
                    <Trash2 size={16} /> Schlüssel entfernen
                  </button>
                )}
                <div className="menu-sep" />
                <a className="menu-item" role="menuitem" href="https://github.com/drpeterkalmar/RaKScribe26/releases/latest/download/rakscribe26.exe" target="_blank" rel="noopener noreferrer">
                  <Download size={16} /> Windows-App herunterladen
                </a>
                <div className="menu-foot">
                  <span>STT: {sttKeyJson ? 'Google chirp_3' : '—'}</span>
                  <span>LLM: {vertexApiKey ? 'Gemini 3.5 Flash (EU)' : '—'}</span>
                  <span><kbd>F10</kbd> Aufnahme · <kbd>F9</kbd> Zurücksetzen</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Workspace */}
      <main className="workspace" aria-hidden={!keysReady}>
        <section className="panel">
          <div className="panel-head">
            <h2><Mic size={16} /> Diktat</h2>
            {status === 'recording' && (
              <div className="level" aria-label="Pegel">
                <div className="level-track"><div className="level-bar" ref={levelBarRef} style={{ width: '0%' }} /></div>
              </div>
            )}
            {isTranscribingChunk && <LoaderCircle size={16} className="spin muted" />}
          </div>
          <textarea
            value={transcript + (isTranscribingChunk ? ' [..]' : '')}
            onChange={e => {
              const v = e.target.value.endsWith(' [..]') ? e.target.value.slice(0, -5) : e.target.value;
              setTranscript(v);
            }}
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); befundAusText(); }
            }}
            placeholder="Das Diktat erscheint hier live. Du kannst auch Text eintippen oder einfügen und mit „Befund aus Text“ (Strg+Enter) strukturieren lassen."
            className="editor"
            disabled={!keysReady}
          />
          <div className="panel-foot">
            {status === 'recording' ? (
              <button onClick={stopRecording} className="btn btn-record is-recording">
                <MicOff size={18} /> Aufnahme stoppen <kbd>F10</kbd>
              </button>
            ) : (
              <button onMouseDown={einfuegeZielMerken} onClick={startRecording} disabled={status === 'processing' || !keysReady} className="btn btn-record">
                <Mic size={18} /> Aufnahme starten <kbd>F10</kbd>
              </button>
            )}
            <button
              onClick={befundAusText}
              disabled={status === 'processing' || status === 'recording' || !keysReady || !transcript.trim()}
              className="btn btn-ghost"
              title="Getippten oder eingefügten Text zu einem strukturierten Befund machen (Strg+Enter)"
            >
              <WandSparkles size={16} /> Befund aus Text
            </button>
            <button
              onClick={() => audioUploadRef.current?.click()}
              disabled={status === 'processing' || status === 'recording' || !keysReady}
              className="btn btn-ghost"
              title="Sprachnachricht oder Audio-Datei hochladen (auch per Drag & Drop)"
            >
              <Upload size={16} /> Audio
            </button>
            <input
              ref={audioUploadRef}
              type="file"
              accept="audio/*,.ogg,.mp3,.wav,.m4a,.opus,.webm"
              className="visually-hidden"
              onChange={e => {
                if (e.target.files?.[0]) {
                  handleAudioUpload(e.target.files[0]);
                  e.target.value = '';
                }
              }}
            />
            <button onClick={handleReset} className="btn btn-ghost" title="Zurücksetzen (F9)" disabled={!keysReady}>
              <RotateCcw size={16} /> Neu
            </button>
          </div>
        </section>

        <section className="panel panel-report">
          <div className="panel-head">
            <h2><Sparkles size={16} /> Befund</h2>
            {isCopied && <span className="copied"><Check size={13} /> Kopiert</span>}
            {status === 'processing' && <LoaderCircle size={16} className="spin muted" />}
            <label className="switch" title="Nur die korrigierte Spracherkennung übernehmen, ohne strukturierten Befund">
              <input type="checkbox" checked={nurText} onChange={e => {
                setNurText(e.target.checked);
                localStorage.setItem('nur_text', e.target.checked ? '1' : '0');
              }} />
              <span className="switch-track" aria-hidden="true"><span className="switch-thumb" /></span>
              Nur Text
            </label>
            <div className="seg" role="tablist" aria-label="Ansicht">
              <button role="tab" aria-selected={reportView === 'formatiert'} className={reportView === 'formatiert' ? 'on' : ''} onClick={() => setReportView('formatiert')}>Formatiert</button>
              <button role="tab" aria-selected={reportView === 'text'} className={reportView === 'text' ? 'on' : ''} onClick={() => setReportView('text')} title="Befund mit der Tastatur bearbeiten">Bearbeiten</button>
            </div>
          </div>
          {reportView === 'formatiert' ? (
            structuredReport
              ? <div className="report-view" title="Klicken zum Bearbeiten oder um an dieser Stelle zu diktieren" onMouseUp={formatiertAngeklickt} dangerouslySetInnerHTML={{ __html: reportToHtml(structuredReport) }} />
              : <div className="report-view report-empty">Der strukturierte Befund erscheint hier nach dem Diktat und wird automatisch kopiert.</div>
          ) : (
            <textarea ref={reportEditorRef} value={structuredReport} onChange={e => setStructuredReport(e.target.value)}
              className="editor editor-report" placeholder="Noch kein Befund."
              title="Befund bearbeiten. Cursor setzen oder Text markieren und F10: das Diktat wird an dieser Stelle eingefügt." />
          )}
          <div className="panel-foot">
            <span className="hint">Für RIS oder Word</span>
            <button onClick={handleCopyReport} disabled={!structuredReport} className="btn btn-primary">
              <Copy size={16} /> Befund kopieren
            </button>
          </div>
        </section>
      </main>

      {/* Key-Gate: App gesperrt, bis der Praxis-Schlüssel geladen ist */}
      {!keysReady && (
        <div className="gate" role="dialog" aria-modal="true" aria-labelledby="gate-title">
          <div className="gate-card">
            <h1 id="gate-title">Praxis-Schlüssel laden</h1>
            <p className="gate-text">Die App ist gesperrt, bis der Schlüssel geladen ist.</p>
            <div className="gate-drop">
              <KeyRound size={26} />
              <span><strong>rakscribe-praxis-key.json</strong> hierher ziehen</span>
              <small>aus dem Drive-Ordner „RaKScribe“</small>
            </div>
            <label className="btn btn-primary btn-wide">
              <FileKey size={18} /> Schlüssel-Datei wählen
              <input ref={keyFileRef} type="file" className="visually-hidden" onChange={handleKeyFile} />
            </label>
            <button className="btn btn-ghost btn-wide" onClick={() => setPasteOpen(true)}>
              <KeyRound size={16} /> Schlüssel einfügen
            </button>
            {partialKey && !keyError && (
              <div className="gate-note">
                <CircleAlert size={15} /> Nur ein Teilschlüssel geladen ({vertexApiKey ? 'Spracherkennung' : 'Befund-KI'} fehlt) — bitte die kombinierte praxis-key.json laden.
              </div>
            )}
            {keyError && <div className="gate-error"><CircleAlert size={15} /> {keyError}</div>}
            <p className="gate-foot">Einmal laden genügt — der Schlüssel bleibt in diesem Browser gespeichert.<br />iPhone: im Dateidialog „Durchsuchen → Google Drive“.</p>
          </div>
        </div>
      )}

      {/* Schlüssel einfügen */}
      {pasteOpen && (
        <div className="gate gate-top" role="dialog" aria-modal="true" onMouseDown={e => { if (e.target === e.currentTarget) setPasteOpen(false); }}>
          <div className="gate-card">
            <button className="icon-button gate-close" onClick={() => setPasteOpen(false)} aria-label="Schließen"><X size={18} /></button>
            <h1>Schlüssel einfügen</h1>
            <p className="gate-text">Inhalt der praxis-key.json (oder Base64 / AQ.-Key) einfügen.</p>
            <textarea className="paste-area" value={pasteValue} onChange={e => setPasteValue(e.target.value)} placeholder='{"vertex_api_key": …, "stt": {…}}' autoFocus />
            {keyError && <div className="gate-error"><CircleAlert size={15} /> {keyError}</div>}
            <button className="btn btn-primary btn-wide" disabled={!pasteValue.trim()} onClick={() => applyKeyText(pasteValue)}>
              <Check size={16} /> Übernehmen
            </button>
          </div>
        </div>
      )}

      {/* Drag-Overlay */}
      {dragActive && (
        <div className="drop-overlay">
          <div className="drop-box">
            <Upload size={32} />
            <span>{keysReady ? 'Loslassen — Schlüssel oder Audio-Datei' : 'Loslassen, um den Schlüssel zu laden'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
