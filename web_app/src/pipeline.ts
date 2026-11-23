// Befund-Kette der Web-App (Umbau Schritt 18): je Region Normalbefund-Bypass oder Gemini (Call 1 + Call 2),
// Nachbearbeitung, Regionen zusammenfügen. Aus App.tsx herausgelöst, Inhalt unverändert.
// Sync: source_code/pipeline.py (EXE). Test: web_app/pipeline_test.mjs.
import { callGeminiLLM, validateReportConsistency, type GenKontext } from './gemini.ts';
import { detectTemplate, deriveUntersuchungsTitel, type TemplatesMap } from './detect.ts';
import { splitRegionen, nachbearbeiten, befundeZusammenfuegen, ergebnisMitSeite, titelMitSeite, rhoErkennen, rhoEinfuegen, widerspruchBefunde, widerspruchPrompt, widersprucheBereinigen, abschnitteBereinigen, kurzsaetzeSichern, klBereinigen, arthroseBereinigen, saetzeMitLage, vorlageNormalisieren, VORLAGEN_ALTFORMEN, type VorrangDaten, grundregeln, rhoAnsEnde, osteopenErsetzen, teileZusammenlegen, nurTextUeberschriften } from './befundRegeln.ts';
import { isPureNormalFinding } from './normalbypass.ts';
import { diktatLog } from './protokoll.ts';
import { bloecke, blockText, umbauSegment, umbauBlock, titelUebernehmen, vorrang, saetze, fehlende, ergaenzen, pruefzeile, streichen, ergebnisFehlt, verneintVorrang } from './befundfeld.ts';
import { ORDI_BAUSTEINE, befundBaustein, nurBaustein, bericht as bausteinBericht, vorlage as bausteinVorlage, kiHinweis, saetzeEinsetzen, type Bausteine } from './bausteine.ts';

export type PipelineKontext = GenKontext & {
  templates: TemplatesMap;
  vorrang: VorrangDaten;
  displayNames: string[];
  bausteine?: Bausteine;  // v3.3: Ordi-Textbausteine (Standard: ordi_bausteine.json)
};

// v3.2: Befund aus dem (korrigierten) Diktat — dieselbe Kette wie die EXE (RaKScribe.py _befund_fuer_segment):
// Diktat mit mehreren Regionen ("Schulter rechts … Ellbogen rechts …") → je Region ein eigener Befund mit eigenem
// Template und eigenem Ergebnis (parallel), danach Ergebnis deterministisch nummeriert.
// v3.9.0 (Georg 13.10.): Rho-Auslöser raus aus dem Diktat, Rho-Baustein danach rein. Sync: pipeline.py
// 3.19.16: umbau = <umbau>-Hinweis von Restructure (befundfeld.ts umbauBlock); '' = wie bisher
// weg = vorher gestrichene Normalsätze (vor den Wächtern heraus, wie pipeline.py ctx.umbau_weg)
export const befundFuerSegment = async (seg: string, ctx: PipelineKontext, umbau = '', weg: string[] = []): Promise<string> => {
  const [segOhne, score, rho] = rhoErkennen(seg);
  if (!rho) return befundFuerSegmentKern(seg, ctx, umbau, weg);
  console.log(`[RHO] Textbaustein (Score ${score || '–'})`);
  return rhoEinfuegen(await befundFuerSegmentKern(segOhne, ctx, umbau, weg), score);
};

const befundFuerSegmentKern = async (seg: string, ctx: PipelineKontext, umbau = '', weg: string[] = []): Promise<string> => {
  // v3.3 (Peter 06.10.): „Baustein Mammo 1“ → Ordi-Textbaustein statt Vorlage (1:1 wie EXE pipeline.py)
  const bausteine = ctx.bausteine ?? ORDI_BAUSTEINE;
  const [bKey, bRest] = befundBaustein(seg, bausteine);
  if (bKey) {
    if (nurBaustein(bRest)) {
      console.log(`[BAUSTEIN] '${bKey}' wörtlich (ohne KI).`);
      return nachbearbeiten(bausteinBericht(bKey, bausteine, seg), false);  // v3.7.2: wörtlich = Layout der Ordi unverändert
    }
    if (!ctx.apiKey) throw new Error("KI-Strukturierung nicht möglich: Es ist kein Vertex AI API-Key konfiguriert.");
    const v = bausteinVorlage(bKey, bausteine, seg);
    const wid = ctx.vorrang.widersprueche;
    const hinweis = [kiHinweis(bKey), widerspruchPrompt(widerspruchBefunde(seg, wid), v.body, wid)].filter(Boolean).join('\n');
    const roh = await callGeminiLLM(seg, v.body, v.display_name, hinweis, v.ergebnis, ctx);
    ctx.status('Validiere Befund-Konsistenz...');
    const out = kurzsaetzeSichern(abschnitteBereinigen(widersprucheBereinigen(nachbearbeiten(await validateReportConsistency(seg, roh, ctx)), seg, wid)[0], seg, ctx.templates, wid)[0], seg, ctx.vorrang.kurzsaetze)[0];  // v3.15.5, v3.18.13, v3.16.6
    return klWaechter(out, seg, wid, ctx.templates);
  }
  const detectedKey = detectTemplate(seg, ctx.templates, ctx.vorrang);
  const activeTemplate = ctx.templates[detectedKey] || ctx.templates['allgemein'];  // templates.json enthält „allgemein“
  if (detectedKey === 'allgemein') {
    console.warn('[TEMPLATE] Region nicht erkannt — verwende Allgemein-Template');
    ctx.status('⚠️ Region nicht erkannt — Allgemein-Template wird verwendet');
  }

  // RAG-Bypass-Shortcut für reine Normalbefunde (1:1 wie EXE)
  if (isPureNormalFinding(seg, ctx.displayNames) && detectedKey !== 'allgemein' && !umbau) {   // Restructure: immer KI
    console.log(`[BYPASS] Normalbefund erkannt. Generiere direkt aus Template.`);
    // v3.2 (Peter 05.10.): Ergebnis = Normal-Ergebnis der Untersuchung (+ Seite) — NIE das Diktat abschreiben
    const ergebnis = ergebnisMitSeite(activeTemplate.ergebnis || '', seg);
    const tplLines = activeTemplate.body.split('\n');
    const tplTitle = titelMitSeite(deriveUntersuchungsTitel(seg, (tplLines[0] || '').trim().replace(/:$/, '')), seg);
    const tplBody = tplLines.slice(1).join('\n');
    return nachbearbeiten(`## ${tplTitle}\n\n## Befund\n${tplBody}\n\n## Ergebnis\n${ergebnis}`);  // v3.2.2: CSA-Platzhalter raus
  }

  if (!ctx.apiKey) {
    throw new Error("KI-Strukturierung nicht möglich: Es ist kein Vertex AI API-Key konfiguriert.");
  }
  // v3.15.5 (Peter 15.10.): diktierte umschriebene Befunde + die widersprechenden Normalsätze der Vorlage (Sync: pipeline.py)
  const wid = ctx.vorrang.widersprueche;
  // 3.19.16 Restructure: Vorrang-Hinweis vor <widersprueche> an der Stelle {examples} (Sync: pipeline.py)
  const widBlock = [umbau, widerspruchPrompt(widerspruchBefunde(seg, wid), activeTemplate.body, wid)].filter(Boolean).join('\n');
  const structuredText = await callGeminiLLM(seg, activeTemplate.body, activeTemplate.display_name, widBlock, activeTemplate.ergebnis || 'Unauffälliger Befund.', ctx);
  // Step 3: Konsistenz-Validierung gegen das Diktat
  ctx.status('Validiere Befund-Konsistenz...');
  const validatedReport = await validateReportConsistency(seg, structuredText, ctx);
  // v3.15.5: übrig gebliebene widersprechende Normalsätze → „Im Übrigen …“, Befund/Ergebnis nennen den Befund
  const nb = nachbearbeiten(validatedReport);
  const [bereinigt, aend] = widersprucheBereinigen(weg.length ? streichen(nb, weg) : nb, seg, wid);
  if (aend.length) console.log(`[WIDERSPRUCH] ${aend.length} Korrektur(en) nach der KI`);
  // v3.18.13 (Peter 14.11.2026, #314): Abschnitt nennt selbst einen Befund ↔ Normalsatz daneben, fremder Vorlagensatz (Sync: pipeline.py)
  const [geprueft, abschn] = abschnitteBereinigen(bereinigt, seg, ctx.templates, wid);
  if (abschn.length) console.log(`[ABSCHNITT] ${abschn.length} Korrektur(en): ${abschn.map(x => x.slice(0, 50)).join(' · ')}`);
  // v3.16.6 (Peter 18.10.): diktierte Empfehlungs-/Einschränkungssätze, die der KI verloren gingen, wörtlich zurück (Sync: pipeline.py)
  const [gesichert, kurz] = kurzsaetzeSichern(geprueft, seg, ctx.vorrang.kurzsaetze);
  if (kurz.length) console.log(`[KURZSATZ] ${kurz.length} diktierte(r) Satz/Sätze ergänzt`);
  return klWaechter(gesichert, seg, wid, ctx.templates);
};

// v3.18.4 (Peter 12.11.2026, RH 38): K&L-Grad nur aus dem Diktat (die Web-App hat keine IB-Lab-Bausteine) — nicht
// gedeckte Grade der KI fallen weg. Sync: pipeline.py _kl_waechter.
const klWaechter = (report: string, seg: string, wid?: VorrangDaten['widersprueche'], templates?: TemplatesMap): string => {
  const [out, aend] = klBereinigen(report, seg);
  if (aend.length) console.log(`[K&L] ${aend.join(' · ')}`);
  // v3.18.5 (Nachtrag RH 99): ohne diktierte Arthrose keine Arthrose-Diagnose im Ergebnis (Sync: pipeline.py)
  const [out2, aend2] = arthroseBereinigen(out, seg, wid);
  if (aend2.length) console.log(`[ARTHROSE] ${aend2.join(' · ')}`);
  // kaiscribe-georg-2011-n1 (Georg 20.11.2026): Grundregeln (Sync: pipeline.py _grundregeln)
  const [out3, aend3] = grundregeln(out2, seg, templates);
  if (aend3.length) console.log(`[GRUNDREGEL] ${aend3.length} Korrektur(en): ${aend3.map(x => x.slice(0, 50)).join(' · ')}`);
  return out3;
};

export const befundAusDiktat = async (text: string, ctx: PipelineKontext): Promise<string> => {
  text = saetzeEinsetzen(text, ctx.bausteine ?? ORDI_BAUSTEINE);  // v3.3: „Baustein A1“, „Baustein Fraktur“ → Satz
  const segmente = splitRegionen(text);
  if (segmente.length > 1) {
    console.log(`[MULTI] ${segmente.length} Regionen: ${segmente.map(diktatLog).join(' | ')}`);
    ctx.status(`Strukturiere ${segmente.length} Regionen mit Gemini...`);
  }
  const teile = await Promise.all(segmente.map(seg => befundFuerSegment(seg, ctx)));
  // kaiscribe-schulter-ergebnis-n1 (Punkte 58a/64): nie doppelte Teile, kein nicht diktierter Unterarm (Sync: pipeline.py)
  return osteopen(rhoAnsEnde(teileZusammenlegen(befundeZusammenfuegen(teile), text)[0]), text);   // kaiscribe-georg-2011-n1 (Punkt 19): Rho-Befund immer am Schluss
};

// kaiscribe-rho-osteopen-n1 (Georg 22.11.2026): Rho ≥ 7 → „Osteopenischer Knochenaspekt.“ statt Mineralisations-
// Normalsatz in allen Untersuchungen, ganz am Schluss. Sync: pipeline.py _osteopen.
const osteopen = (report: string, diktat: string): string => {
  const [out, teile] = osteopenErsetzen(report, diktat);
  if (teile.length) console.log(`[RHO] Osteopenischer Knochenaspekt statt Mineralisations-Normalsatz in ${teile.length} Untersuchung(en)`);
  return out;
};

// v3.4.0 (Peter 07.10., „manchmal ist weniger mehr“): Nur-Text-Modus — rechts nur die korrigierte Spracherkennung
// (Fehlhör-Liste + Call 0 sind schon gelaufen), kein Befund. Satz-Bausteine werden trotzdem eingesetzt.
// Sync: source_code/pipeline.py nur_text_aus_diktat.
// kaiscribe-schulter-ergebnis-n1 (Punkte 49a/52): Überschriften auch im Nur-Text-Weg als „## …“ (fett)
export const nurTextAusDiktat = (text: string, ctx: Pick<PipelineKontext, 'bausteine'>): string =>
  nurTextUeberschriften(saetzeEinsetzen(text.trim(), ctx.bausteine ?? ORDI_BAUSTEINE));

// 3.19.16 Restructure (Peter 20.11.2026): aktuellen Text im Befundfeld über die Befundkette neu aufbauen, Peters
// Änderungen seit dem letzten KaiScribe-Stand (stand) haben Vorrang, Überschriften bleiben, unveränderte Abschnitte
// (mehrere Untersuchungen) bleiben Zeichen für Zeichen; danach Prüfung, dass nichts verloren ging (Prüfzeilen).
// Sync: pipeline.py befund_umbauen (ohne CAS/IB Lab — die gibt es nur in der EXE).
export type Umbau = { report: string; hinweise: string[]; leer: boolean };
export const befundUmbauen = async (aktuellIn: string, stand: string, ctx: PipelineKontext): Promise<Umbau> => {
  const text = (aktuellIn || '').trim();
  if (!text) return { report: '', hinweise: [], leer: true };
  const ohneStand = !(stand || '').trim();
  const vor = ohneStand ? [] : vorrang(stand, text);
  if (!vor.length && !ohneStand) return { report: text, hinweise: [], leer: true };
  const alle = bloecke(text);
  const bl = alle.filter(b => b.befund || b.ergebnis).length ? alle.filter(b => b.befund || b.ergebnis) : alle;
  const teile: string[] = [], titel: (string | null)[] = [];
  for (const b of bl) {
    const bt = blockText(text, b);
    const eigene = vor.filter(s => vorlageNormalisieren(bt).includes(vorlageNormalisieren(s)));
    if (bl.length > 1 && !eigene.length && !ohneStand) { teile.push(bt); titel.push(b.titel); continue; }
    const [seg, gestrichen] = umbauSegment(bt, eigene, ctx.vorrang.widersprueche);
    if (gestrichen.length) console.log(`[UMBAU] ${gestrichen.length} widersprechende(r) Normalsatz/Normalsätze vorher entfernt`);
    teile.push(streichen(await befundFuerSegment(seg, ctx, umbauBlock(eigene, gestrichen, ohneStand), gestrichen), gestrichen));
    titel.push(b.titel);
  }
  let report = osteopen(titelUebernehmen(befundeZusammenfuegen(teile), titel), vor.join(' '));
  const hinweise: string[] = [];
  const fehlt = fehlende(vor, report);
  for (const s of fehlt) { report = ergaenzen(report, s)[0]; hinweise.push(pruefzeile(s)); }
  hinweise.push(...ergebnisFehlt(vor, report).map(s => pruefzeile(s, true)));
  const vorlagen = new Set<string>();
  for (const t of Object.values(ctx.templates)) {
    const body = t?.body || '';
    for (const [a, e] of saetzeMitLage(body)) { const n = vorlageNormalisieren(body.slice(a, e)); if (n) vorlagen.add(n); }
  }
  for (const [neu, alte] of Object.entries(VORLAGEN_ALTFORMEN)) if (vorlagen.has(vorlageNormalisieren(neu))) alte.forEach(x => vorlagen.add(vorlageNormalisieren(x)));
  const eigeneAlt = saetze(text, false).map(([s]) => s).filter(s => !vorlagen.has(vorlageNormalisieren(s)) && !vor.includes(s));
  hinweise.push(...fehlende(eigeneAlt, report).filter(s => !verneintVorrang(s, vor)).map(s => pruefzeile(s)));
  console.log(`[UMBAU] ${vor.length} Änderung(en) mit Vorrang, ${teile.length} Abschnitt(e), ${fehlt.length} nachgetragen, ${hinweise.length} Prüfzeile(n)`);
  return { report, hinweise, leer: false };
};
