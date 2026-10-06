// Befund-Kette der Web-App (Umbau Schritt 18): je Region Normalbefund-Bypass oder Gemini (Call 1 + Call 2),
// Nachbearbeitung, Regionen zusammenfügen. Aus App.tsx herausgelöst, Inhalt unverändert.
// Sync: source_code/pipeline.py (EXE). Test: web_app/pipeline_test.mjs.
import { callGeminiLLM, validateReportConsistency, type GenKontext } from './gemini.ts';
import { detectTemplate, deriveUntersuchungsTitel, type Template, type TemplatesMap } from './detect.ts';
import { splitRegionen, nachbearbeiten, befundeZusammenfuegen, ergebnisMitSeite, titelMitSeite, type VorrangDaten } from './befundRegeln.ts';
import { isPureNormalFinding } from './normalbypass.ts';

export type PipelineKontext = GenKontext & {
  templates: TemplatesMap;
  vorrang: VorrangDaten;
  displayNames: string[];
  fallback: Template;
};

// v3.2: Befund aus dem (korrigierten) Diktat — dieselbe Kette wie die EXE (RaKScribe.py _befund_fuer_segment):
// Diktat mit mehreren Regionen ("Schulter rechts … Ellbogen rechts …") → je Region ein eigener Befund mit eigenem
// Template und eigenem Ergebnis (parallel), danach Ergebnis deterministisch nummeriert.
export const befundFuerSegment = async (seg: string, ctx: PipelineKontext): Promise<string> => {
  const detectedKey = detectTemplate(seg, ctx.templates, ctx.vorrang);
  const activeTemplate = ctx.templates[detectedKey] || ctx.templates['allgemein'] || ctx.fallback;
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
  const structuredText = await callGeminiLLM(seg, activeTemplate.body, activeTemplate.display_name, '', activeTemplate.ergebnis || 'Unauffälliger Befund.', ctx);
  // Step 3: Konsistenz-Validierung gegen das Diktat
  ctx.status('Validiere Befund-Konsistenz...');
  const validatedReport = await validateReportConsistency(seg, structuredText, ctx);
  return nachbearbeiten(validatedReport);
};

export const befundAusDiktat = async (text: string, ctx: PipelineKontext): Promise<string> => {
  const segmente = splitRegionen(text);
  if (segmente.length > 1) {
    console.log(`[MULTI] ${segmente.length} Regionen: ${segmente.map(x => x.slice(0, 40)).join(' | ')}`);
    ctx.status(`Strukturiere ${segmente.length} Regionen mit Gemini...`);
  }
  const teile = await Promise.all(segmente.map(seg => befundFuerSegment(seg, ctx)));
  return befundeZusammenfuegen(teile);
};
