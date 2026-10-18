// Befund-Kette der Web-App (Umbau Schritt 18): je Region Normalbefund-Bypass oder Gemini (Call 1 + Call 2),
// Nachbearbeitung, Regionen zusammenfügen. Aus App.tsx herausgelöst, Inhalt unverändert.
// Sync: source_code/pipeline.py (EXE). Test: web_app/pipeline_test.mjs.
import { callGeminiLLM, validateReportConsistency, type GenKontext } from './gemini.ts';
import { detectTemplate, deriveUntersuchungsTitel, type TemplatesMap } from './detect.ts';
import { splitRegionen, nachbearbeiten, befundeZusammenfuegen, ergebnisMitSeite, titelMitSeite, rhoErkennen, rhoEinfuegen, widerspruchBefunde, widerspruchPrompt, widersprucheBereinigen, kurzsaetzeSichern, type VorrangDaten } from './befundRegeln.ts';
import { isPureNormalFinding } from './normalbypass.ts';
import { diktatLog } from './protokoll.ts';
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
export const befundFuerSegment = async (seg: string, ctx: PipelineKontext): Promise<string> => {
  const [segOhne, score, rho] = rhoErkennen(seg);
  if (!rho) return befundFuerSegmentKern(seg, ctx);
  console.log(`[RHO] Textbaustein (Score ${score || '–'})`);
  return rhoEinfuegen(await befundFuerSegmentKern(segOhne, ctx), score);
};

const befundFuerSegmentKern = async (seg: string, ctx: PipelineKontext): Promise<string> => {
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
    return kurzsaetzeSichern(widersprucheBereinigen(nachbearbeiten(await validateReportConsistency(seg, roh, ctx)), seg, wid)[0], seg, ctx.vorrang.kurzsaetze)[0];  // v3.15.5, v3.16.6
  }
  const detectedKey = detectTemplate(seg, ctx.templates, ctx.vorrang);
  const activeTemplate = ctx.templates[detectedKey] || ctx.templates['allgemein'];  // templates.json enthält „allgemein“
  if (detectedKey === 'allgemein') {
    console.warn('[TEMPLATE] Region nicht erkannt — verwende Allgemein-Template');
    ctx.status('⚠️ Region nicht erkannt — Allgemein-Template wird verwendet');
  }

  // RAG-Bypass-Shortcut für reine Normalbefunde (1:1 wie EXE)
  if (isPureNormalFinding(seg, ctx.displayNames) && detectedKey !== 'allgemein') {
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
  const widBlock = widerspruchPrompt(widerspruchBefunde(seg, wid), activeTemplate.body, wid);
  const structuredText = await callGeminiLLM(seg, activeTemplate.body, activeTemplate.display_name, widBlock, activeTemplate.ergebnis || 'Unauffälliger Befund.', ctx);
  // Step 3: Konsistenz-Validierung gegen das Diktat
  ctx.status('Validiere Befund-Konsistenz...');
  const validatedReport = await validateReportConsistency(seg, structuredText, ctx);
  // v3.15.5: übrig gebliebene widersprechende Normalsätze → „Im Übrigen …“, Befund/Ergebnis nennen den Befund
  const [bereinigt, aend] = widersprucheBereinigen(nachbearbeiten(validatedReport), seg, wid);
  if (aend.length) console.log(`[WIDERSPRUCH] ${aend.length} Korrektur(en) nach der KI`);
  // v3.16.6 (Peter 18.10.): diktierte Empfehlungs-/Einschränkungssätze, die der KI verloren gingen, wörtlich zurück (Sync: pipeline.py)
  const [gesichert, kurz] = kurzsaetzeSichern(bereinigt, seg, ctx.vorrang.kurzsaetze);
  if (kurz.length) console.log(`[KURZSATZ] ${kurz.length} diktierte(r) Satz/Sätze ergänzt`);
  return gesichert;
};

export const befundAusDiktat = async (text: string, ctx: PipelineKontext): Promise<string> => {
  text = saetzeEinsetzen(text, ctx.bausteine ?? ORDI_BAUSTEINE);  // v3.3: „Baustein A1“, „Baustein Fraktur“ → Satz
  const segmente = splitRegionen(text);
  if (segmente.length > 1) {
    console.log(`[MULTI] ${segmente.length} Regionen: ${segmente.map(diktatLog).join(' | ')}`);
    ctx.status(`Strukturiere ${segmente.length} Regionen mit Gemini...`);
  }
  const teile = await Promise.all(segmente.map(seg => befundFuerSegment(seg, ctx)));
  return befundeZusammenfuegen(teile);
};

// v3.4.0 (Peter 07.10., „manchmal ist weniger mehr“): Nur-Text-Modus — rechts nur die korrigierte Spracherkennung
// (Fehlhör-Liste + Call 0 sind schon gelaufen), kein Befund. Satz-Bausteine werden trotzdem eingesetzt.
// Sync: source_code/pipeline.py nur_text_aus_diktat.
export const nurTextAusDiktat = (text: string, ctx: Pick<PipelineKontext, 'bausteine'>): string =>
  saetzeEinsetzen(text.trim(), ctx.bausteine ?? ORDI_BAUSTEINE);
