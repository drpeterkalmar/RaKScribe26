// Diktat an der Cursor-Stelle in den Befund einfügen (v3.5.0, Peter 07.10.). Sync: source_code/einfuegen.py
// (gemeinsame Fälle: tests/offline/snapshots/einfuegen_faelle.txt).
const SATZZEICHEN = '.,;:!?)';

/** text[start:ende] durch neu ersetzen (start === ende: einfügen); Ränder mit Leerzeichen, kein doppelter Punkt. */
export const einfuegen = (textIn: string, startIn: number, endeIn: number, neuIn: string): [string, number] => {
  const text = textIn ?? '';
  const start = Math.max(0, Math.min(startIn, text.length));
  const ende = Math.max(start, Math.min(endeIn, text.length));
  let neu = (neuIn ?? '').trim();
  const vor = text.slice(0, start), nach = text.slice(ende);
  if (!neu) return [vor + nach, vor.length];
  if (['.', ',', ';', ':'].includes(nach.slice(0, 1)) && neu.endsWith('.')) neu = neu.slice(0, -1).trimEnd();
  if (vor && !/\s/.test(vor.slice(-1)) && !SATZZEICHEN.includes(neu[0])) neu = ' ' + neu;
  if (nach && !/\s/.test(nach[0]) && !SATZZEICHEN.includes(nach[0])) neu = neu + ' ';
  return [vor + neu + nach, vor.length + neu.replace(/ +$/, '').length];
};

/** Klick/Markierung in der formatierten Ansicht → Zeichen-Offset im Markdown-Text. Die formatierte Ansicht zeigt
 *  jede Markdown-Zeile ohne „## “ bzw. „1. “ und mit unveränderten Zeichen; der Textknoten wird daher in der
 *  Markdown-Zeile gesucht. vorkommen = wievieltes gleiches Textstück davor in der Ansicht stand. null = nicht gefunden. */
export const markdownOffset = (md: string, knotenText: string, offsetImKnoten: number, vorkommen = 0): number | null => {
  if (!knotenText) return null;
  let ab = 0;
  for (let i = 0; i <= vorkommen; i++) {
    const p = md.indexOf(knotenText, ab);
    if (p < 0) return null;
    if (i === vorkommen) return p + Math.max(0, Math.min(offsetImKnoten, knotenText.length));
    ab = p + knotenText.length;
  }
  return null;
};
