// Konsolen-Protokoll der Web-App (Umbau Schritt 23, Gutachten P2-14): Diktat- und Befundtexte (können Patientennamen
// enthalten) nur mit localStorage.rakscribe_debug = '1' — sonst nur die Länge. Gegenstück: source_code/protokoll.py.
export function debugAktiv(): boolean {
  try {
    return typeof localStorage !== 'undefined' && localStorage.getItem('rakscribe_debug') === '1';
  } catch {
    return false;
  }
}

export const diktatLog = (text: string): string =>
  debugAktiv() ? JSON.stringify((text || '').slice(0, 200)) : `<${(text || '').length} Zeichen>`;
