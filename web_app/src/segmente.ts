// Diktat-Anzeige während einer SpeechMike-Aufnahme mit Pausen (v3.8.0, Peter 11.10. Nachtrag 1). Sync: source_code/segmente.py.
// Bei jeder Pause wird der Abschnitt seit Start/Weiter sofort mit chirp_3 + Fehlhör-Liste repariert und ersetzt in der
// Anzeige den Live-Text (6-s-Chunks) dieses Abschnitts. Der Endtext für den Befund kommt weiterhin aus der Transkription
// der GANZEN Aufnahme (Messung 11.10.: kurze Abschnitte ohne Zusammenhang verhören sich, z. B. „Befund Nervus ulnaris“ →
// „Power Stange Busulnaris“; docs/benchmarks/pause_segmente_2026-10-11.txt) — die Reparatur dient nur der Anzeige.

export type Abschnitt = {
  chunkVon: number;          // erster Live-Chunk dieses Abschnitts
  chunkBis: number;          // erster Chunk danach (bei der Pause festgelegt)
  text: string | null;       // reparierter Text (null = Reparatur läuft noch oder ist gescheitert)
};

const live = (chunks: string[], von: number, bis?: number): string =>
  chunks.slice(von, bis).map(t => t.trim()).filter(Boolean).join(' ');

/** Text für das Diktat-Feld: bisheriges Diktat (Nachdiktat) + je geschlossenem Abschnitt der reparierte Text oder
 *  sein Live-Text + Live-Text des laufenden Abschnitts (ab Chunk laufendVon). Ohne Pause = alle Chunks wie bisher. */
export function diktatAnzeige(basis: string, abschnitte: Abschnitt[], chunks: string[], laufendVon: number): string {
  const teile = [basis.trim()];
  for (const a of abschnitte) teile.push((a.text ?? live(chunks, a.chunkVon, a.chunkBis)).trim());
  teile.push(live(chunks, laufendVon));
  return teile.filter(Boolean).join(' ');
}
