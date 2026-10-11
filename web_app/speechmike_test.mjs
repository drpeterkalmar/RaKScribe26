// speechmike_test.mjs — v3.8.0: SpeechMike-Dekodierung, LED-Bytes, Belegung und Zustandstabelle der Web-App gegen
// DIESELBEN Fälle wie die EXE (../tests/offline/speechmike_faelle.txt; Python-Gegenstück tests/offline/test_speechmike.py).
// Dazu die WebHID-Verbindung mit einem nachgebauten navigator.hid (ohne Browser).
//   cd web_app && node --experimental-strip-types --no-warnings speechmike_test.mjs
import { readFileSync } from 'node:fs';
import { Dekodierer, LED, ledFuer, BELEGUNG, TASTEN, sendefaehig, hexBytes, SpeechMikeVerbindung, HID_FILTER, webHid } from './src/speechmike.ts';
import { uiAktion } from './src/lauf.ts';
import { diktatAnzeige } from './src/segmente.ts';

const F = JSON.parse(readFileSync(new URL('../tests/offline/speechmike_faelle.txt', import.meta.url), 'utf8'));
let fail = 0, n = 0;
const check = (ok, label, detail = '') => { n++; if (!ok) fail++; if (!ok || process.argv.includes('-v')) console.log(ok ? 'PASS' : 'FAIL', '|', label, ok ? '' : `\n      ${detail}`); };
const bytes = h => h.split(' ').map(x => parseInt(x, 16));
const gleich = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. Dekodierung (gleiche Fälle wie Python)
for (const fall of F.dekodieren) {
  const d = new Dekodierer();
  fall.berichte.forEach(([zeit, hex, erwartet], i) => {
    const got = d.bericht(bytes(hex), zeit);
    check(gleich(got, erwartet), `dekodieren: ${fall.name} #${i + 1}`, `${hex} → ${JSON.stringify(got)} statt ${JSON.stringify(erwartet)}`);
  });
}
// 2. LED-Bytes, LED je Zustand, Belegung, EOL-Prüfung
for (const [name, hex] of Object.entries(F.led)) check(hexBytes(LED[name]) === hex, `LED ${name}`, hexBytes(LED[name] ?? []));
check(Object.keys(LED).length === Object.keys(F.led).length, 'LED: keine zusätzlichen Zustände');
for (const [z, wartet, led] of F.led_fuer) check(ledFuer(z, wartet) === led, `LED für ${z}/${wartet}`, ledFuer(z, wartet));
for (const [taste, ereignis] of Object.entries(F.belegung)) check((BELEGUNG[taste] ?? null) === ereignis, `Belegung ${taste}`, BELEGUNG[taste]);
check(TASTEN.every(([t]) => t in F.belegung), 'jede Taste steht in der Belegungstabelle');
for (const [text, ok] of F.sendefaehig) check(sendefaehig(text) === ok, `sendefähig: ${JSON.stringify(text.slice(0, 40))}`, String(sendefaehig(text)));
// 3. Zustandstabelle (= jobstate.py vorschau)
for (const [z, e, aktion] of F.zustand) check(uiAktion(z, e) === aktion, `Zustand ${z} + ${e}`, `${uiAktion(z, e)} statt ${aktion}`);

// 4. Anzeige während der Aufnahme: reparierte Abschnitte ersetzen den Live-Text ihres Abschnitts
{
  const chunks = ['Knie rechts', 'Erguss', 'Bänder', 'intakt'];
  const segs = [{ chunkVon: 0, chunkBis: 2, text: 'Kniegelenk rechts, Erguss.' }];
  check(diktatAnzeige('', [], chunks, 0) === 'Knie rechts Erguss Bänder intakt', 'Anzeige ohne Pause = alle Chunks (wie bisher)');
  check(diktatAnzeige('', segs, chunks, 2) === 'Kniegelenk rechts, Erguss. Bänder intakt', 'Anzeige: Abschnitt 1 repariert, Abschnitt 2 live');
  check(diktatAnzeige('Schulter links unauffällig.', segs, chunks, 4) === 'Schulter links unauffällig. Kniegelenk rechts, Erguss.',
    'Anzeige mit bisherigem Diktat (Nachdiktat) und leerem laufendem Abschnitt');
  check(diktatAnzeige('', [{ chunkVon: 0, chunkBis: 2, text: null }], chunks, 2) === 'Knie rechts Erguss Bänder intakt',
    'Anzeige: Reparatur noch offen → Live-Text bleibt');
  check(diktatAnzeige('', [], ['', 'Knie', ' '], 0) === 'Knie', 'Anzeige: leere Chunks fallen weg');
}

// 5. WebHID-Verbindung mit nachgebautem navigator.hid
class FakeDevice extends EventTarget {
  constructor(o) { super(); Object.assign(this, { opened: false, vendorId: 0x0911, productId: 0x0c1c, productName: 'SpeechMike Premium', collections: [{ usagePage: 0xffa0, usage: 1 }], sent: [] }, o); }
  async open() { this.opened = true; }
  async close() { this.opened = false; }
  async sendReport(id, data) { if (this.sendFehler) throw new Error('NotAllowedError'); this.sent.push([id, Array.from(data)]); }
  druecken(hex) { const e = new Event('inputreport'); const u = new Uint8Array(bytes(hex)); Object.assign(e, { device: this, reportId: 0, data: new DataView(u.buffer) }); this.dispatchEvent(e); }
}
class FakeHid extends EventTarget {
  constructor(devs) { super(); this.devs = devs; this.anfragen = []; }
  async getDevices() { return this.devs; }
  async requestDevice(o) { this.anfragen.push(o); return this.devs; }
  verbinden(d) { const e = new Event('connect'); e.device = d; this.devs.push(d); this.dispatchEvent(e); }
  trennen(d) { const e = new Event('disconnect'); e.device = d; this.devs = this.devs.filter(x => x !== d); this.dispatchEvent(e); }
}
const warte = () => new Promise(r => setTimeout(r, 20));
{
  const dev = new FakeDevice(), hid = new FakeHid([dev]);
  const tasten = [], status = [];
  const v = new SpeechMikeVerbindung(hid, { taste: (t, g, roh) => tasten.push([t, g, roh]), status: s => status.push(s), log: () => {} });
  await v.start(); await warte();
  check(dev.opened && v.verbunden && status.at(-1) === 'SpeechMike Premium (0911:0c1c)', 'getDevices: frühere Freigabe → automatisch verbunden', JSON.stringify(status));
  check(gleich(dev.sent.at(-1), [0, F.led.aus.split(' ').map(x => parseInt(x, 16))]), 'nach dem Verbinden: LED-Zustand gesendet (aus)', JSON.stringify(dev.sent));
  dev.druecken('80 00 00 00 00 00 00 00 01'); dev.druecken('80 00 00 00 00 00 00 00 00');
  check(gleich(tasten, [['RECORD', true, '80 00 00 00 00 00 00 00 01'], ['RECORD', false, '80 00 00 00 00 00 00 00 00']]), 'inputreport → Taste Record gedrückt/losgelassen', JSON.stringify(tasten));
  v.led('aufnahme'); await warte();
  check(gleich(dev.sent.at(-1), [0, bytes(F.led.aufnahme)]), 'LED Aufnahme → sendReport(0, 02 … 0c …)', JSON.stringify(dev.sent.at(-1)));
  const vorher = dev.sent.length; v.led('aufnahme'); await warte();
  check(dev.sent.length === vorher, 'gleicher LED-Zustand wird nicht doppelt gesendet');
  dev.sendFehler = true; v.led('pause'); await warte();
  check(v.verbunden, 'LED-Fehler ist nicht fatal (Verbindung bleibt)');
  dev.sendFehler = false;
  hid.trennen(dev); await warte();
  check(!v.verbunden && status.at(-1) === null, 'Abstecken → getrennt gemeldet', JSON.stringify(status));
  const dev2 = new FakeDevice(); hid.verbinden(dev2); await warte();
  check(v.verbunden && dev2.opened && gleich(dev2.sent.at(-1), [0, bytes(F.led.pause)]), 'Wieder anstecken → verbunden, aktueller LED-Zustand gesendet', JSON.stringify(dev2.sent));
  tasten.length = 0; dev2.druecken('80 00 00 00 00 00 00 00 40');
  check(gleich(tasten.map(t => t[0]), ['INS']), 'nach dem Wiederverbinden kommen Tasten an (INS)');
  v.stop();
  check(gleich(dev2.sent.at(-1), [0, bytes(F.led.aus)]), 'stop() → LED aus');
}
{
  const fremd = new FakeDevice({ vendorId: 0x046d, productId: 0xc52b, productName: 'Maus' });
  const tastatur = new FakeDevice({ collections: [{ usagePage: 1, usage: 6 }] });
  const hid = new FakeHid([fremd, tastatur]);
  const status = [];
  const v = new SpeechMikeVerbindung(hid, { taste: () => {}, status: s => status.push(s), log: () => {} });
  await v.start(); await warte();
  check(!v.verbunden && !fremd.opened && !tastatur.opened, 'fremde Geräte / andere Schnittstellen des SpeechMike werden nicht geöffnet');
  const ok = await v.verbinden();
  check(!ok && gleich(hid.anfragen[0].filters, HID_FILTER) && HID_FILTER.length === 4 && HID_FILTER.every(f => f.usagePage === 0xffa0 && f.vendorId === 0x0911),
    'SpeechMike verbinden: requestDevice mit den 4 SpeechMike-Filtern (Usage-Page 0xFFA0)', JSON.stringify(hid.anfragen));
}
check(webHid() === null, 'ohne navigator.hid (Node, Safari) → webHid() = null');

console.log(`${fail ? 'FAIL' : 'PASS'} ${n - fail}/${n} SpeechMike-Fälle (Web)`);
process.exit(fail ? 1 : 0);
