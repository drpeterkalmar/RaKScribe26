// misheard.ts — Fehlhör-Liste (misheard_words.json) für die Web-App.
// Gleiche Semantik wie source_code/misheard.py (EXE). Regeln NUR in der JSON pflegen.
//
//   auto-Regeln: deterministische Ersetzung (Wortgrenzen Unicode-sicher, Groß/Klein egal,
//                Leerzeichen tolerant) — läuft VOR Call 0, greift also auch ohne Gemini.
//   llm-Regeln : nur als Prompt-Hinweis (Call-0-Tabelle), weil kontextabhängig.

export interface MisheardRule {
  hear: string[];
  mean: string;
  mode: 'auto' | 'llm';
  regex?: boolean;
  show?: string[];
  mean_show?: string;
  note?: string;
  group?: 'stt' | 'jargon';
  source?: string;
}

export interface MisheardFile {
  version: string;
  rules: MisheardRule[];
}

export interface Compiled { re: RegExp; repl: string }

const B_LEFT = '(?<![\\p{L}\\p{N}_])';
const B_RIGHT = '(?![\\p{L}\\p{N}_])';

const escapeLiteral = (s: string): string =>
  s.trim().split(/\s+/).map(tok => tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+');

export function compileMisheard(file: MisheardFile): Compiled[] {
  const out: Compiled[] = [];
  for (const r of file.rules) {
    if (r.mode !== 'auto') continue;
    for (const h of r.hear) {
      const core = r.regex ? h : escapeLiteral(h);
      out.push({ re: new RegExp(B_LEFT + '(?:' + core + ')' + B_RIGHT, 'giu'), repl: r.mean });
    }
  }
  return out;
}

export function applyMisheard(text: string, compiled: Compiled[]): string {
  let t = text;
  for (const c of compiled) t = t.replace(c.re, c.repl);
  return t;
}

const fmt = (r: MisheardRule): string => {
  const shown = (r.show ?? r.hear).map(h => `"${h}"`).join(' / ');
  return `- ${shown} → "${r.mean_show ?? r.mean}"${r.note ? ` (${r.note})` : ''}`;
};

/** Prompt-Block für Call 0 (ersetzt die frühere handgepflegte Tabelle in App.tsx). */
export function misheardPromptBlock(file: MisheardFile): string {
  const stt = file.rules.filter(r => (r.group ?? 'stt') !== 'jargon');
  const jargon = file.rules.filter(r => r.group === 'jargon');
  return [
    '## BEKANNTE STT-FEHLER (automatisch korrigieren):',
    ...stt.map(fmt),
    '',
    '## PRAXIS-JARGON (Dr. Kalmar / Dr. Riegler Shortcut-Phrasen):',
    ...jargon.map(fmt),
  ].join('\n');
}
