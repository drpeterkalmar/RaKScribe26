// Gemini-Aufrufe der Web-App (Umbau Schritt 18): Call 0 (STT-Korrektur), Call 1 (Befund), Call 2 (Validierung),
// Schlüsselprüfung. Aus App.tsx herausgelöst — Prompts und Requests unverändert (Snapshots: tests/offline/snapshots).
// Sync: source_code/gemini.py (SYS_MSG, parts-Join, Vollständigkeit), tools/prod_pipeline.py liest validationPrompt hier.
import { fetchWithRetry, istAbbruch, fehlermeldung } from './net.ts';
import { applyMisheard, type Compiled } from './misheard.ts';
import { stripPromptMarker } from './befundRegeln.ts';
import { diktatLog } from './protokoll.ts';

// Vertex AI endpoint for Gemini 2.5 Flash
// v2.11.0 (26.09.2026): gemini-3.5-flash am EU-Multi-Region-Endpoint (EU-Datenresidenz + EU-Verarbeitung).
// A/B 54 Fall-Läufe: Normalbefund-Treue 84,5 % → 93,7 %, fehlende '## Befund'-Überschrift 6 → 0, FAIL 0.
// gemini-2.5-flash wird von Google abgeschaltet (Phase 1: 20.10.2026).
// v2.11.1 HOTFIX: Gemini 3.5 teilt Antworten gelegentlich in mehrere parts auf ('## L' | 'endenwirbelsäule…').
// Immer ALLE Text-parts zusammensetzen (Thinking-parts ausgenommen) — nie nur parts[0] lesen.
// Antwort-Typen von generateContent (nur die gelesenen Felder)
export type GeminiPart = { text?: unknown; thought?: boolean };
export type GeminiAntwort = {
  candidates?: { content?: { parts?: GeminiPart[] }; finishReason?: string }[];
  error?: { message?: string };
};
export const joinGeminiText = (data: GeminiAntwort): string =>
  (data?.candidates?.[0]?.content?.parts || [])
    .filter((p): p is GeminiPart & { text: string } => typeof p?.text === 'string' && !p?.thought)
    .map(p => p.text)
    .join('');

// v2.11.1: Ein Befund gilt nur als vollständig, wenn '## Befund' UND ein nicht-leeres '## Ergebnis' vorhanden sind
// und Gemini regulär beendet hat (finishReason STOP). Sonst: Retry bzw. Fallback — NIE Halb-Befunde ausgeben.
export const geminiFinishedOk = (data: GeminiAntwort): boolean => {
  const fr = data?.candidates?.[0]?.finishReason;
  return !fr || fr === 'STOP';
};
// Vollständig = nicht-leeres '## Ergebnis' mit Befundtext davor ('## Befund' fehlt beim Prod-Prompt gelegentlich — kein Abbruchgrund).
export const befundSection = (t: string): string => {
  const pre = t.split('## Ergebnis')[0];
  const body = pre.includes('## Befund') ? pre.split('## Befund')[1] : pre.split('\n').filter(l => !l.trim().startsWith('#')).join('\n');
  return body.trim();
};
export const isCompleteReport = (t: string): boolean =>
  t.includes('## Ergebnis') && t.split('## Ergebnis')[1].trim().length > 5 && befundSection(t).length > 20;

export const VERTEX_ENDPOINT = 'https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/locations/eu/publishers/google/models/gemini-3.5-flash:generateContent';

// systemInstruction — WORTGLEICH zu SYS_MSG in source_code/gemini.py (tests/offline/befund_regeln_test.py prüft das)
export const SYS_MSG =
  "Du bist ein präziser Radiologie-Assistent der Praxis 'Röntgen am Kai' – Dr. P. Kalmar / Dr. G. Riegler. " +
  "Strukturiere das Diktat nach den Regeln im Prompt mit dem Normalbefund-Template als vollständigem Gerüst. " +
  "Ausgabe: zuerst '## ' + kanonische Untersuchungsbezeichnung mit diktierter Seite, dann '## Befund' als Fließtext " +
  "ohne Labels und '## Ergebnis' nummeriert (1. 2. 3.) mit den diktierten Begriffen 1:1 inklusive Grad und Messwerten. " +
  "Gib ausschließlich den fertigen Befundtext aus – keine Kommentare, keine Einleitung.";

// Schlüsselprüfung (1-Token-Aufruf). Umbau Schritt 8 (Gutachten P2-9): einmal nach dem Laden des Schlüssels statt
// vor jeder Aufnahme — das Mikrofon öffnet sofort, die ersten Silben gehen nicht mehr verloren.
export async function testGeminiAPI(apiKey: string): Promise<void> {
  if (!apiKey) {
    throw new Error("Es ist kein Vertex AI API-Key konfiguriert.");
  }
  const response = await fetchWithRetry(VERTEX_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: "Hi" }] }],
      generationConfig: { maxOutputTokens: 1 }
    })
  }, 30_000, 2);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const errMsg = data.error?.message || `HTTP Fehler ${response.status}`;
    throw new Error(`Gemini API Fehler: ${errMsg}`);
  }
}

// Kontext eines Gemini-Aufrufs: Schlüssel, Gen-Prompt, Abbruch-Signal des Laufs, Statuszeile (nur solange der Lauf
// aktuell ist), Fehlhör-Liste (auto-Regeln + Prompt-Block für Call 0)
export type GenKontext = {
  apiKey: string;
  prompt: string;
  signal?: AbortSignal;
  status: (text: string) => void;
  misheard?: { compiled: Compiled[]; block: string };
};

// Call 0 — STT-Korrektur. Text unverändert aus App.tsx (tools/call0_prompt.py liest ihn hier per Regex).
export const correctionPrompt = (MISHEARD_PROMPT_BLOCK: string, rawText: string): string => `Du bist ein medizinischer Lektor für radiologische Diktate. Korrigiere Spracherkennungsfehler.

${MISHEARD_PROMPT_BLOCK}

## WICHTIGE REGELN:
1. Behalte ALLE Pathologien bei — verliere NIEMALS eine Diagnose
2. "mit" + unklarer Begriff nach Sehnen-Untersuchung → "mit Begleitbursitis"
3. VERÄNDERE KEINE ZAHLEN! "18 mm" bleibt "18 mm", nicht "1,8 mm". "15 mm²" bleibt "15 mm²". Messwerte sind heilig.
4. VERÄNDERE KEINE ANATOMISCHEN LOKALISATIONEN! "axillär" bleibt "axillär", nicht "lateral". 
5. KORRIGIERE NUR ECHTE SPRACHERKENNUNGSFEHLER (Unsinnswörter, falsch gehörte Silben). Ein korrekt erkannter Fachbegriff bleibt WÖRTLICH stehen — NIEMALS durch einen "präziseren" oder anderen Fachbegriff ersetzen ("Gelenksarthrose" bleibt "Gelenksarthrose", NICHT "Uncovertebralarthrose"; "Diskopathie" bleibt "Diskopathie"). NIEMALS zwei diktierte Befunde zusammenziehen ("flachbogige Skoliose nach links, kyphotische Fehlhaltung" bleiben ZWEI Befunde).
6. Gib NUR den korrigierten Text aus, keine Erklärungen

## FEW-SHOT BEISPIELE:
Roh: "Tendinopathie und den Genusses pinnatus Sehne mit begleitet ist, ansonsten nur noch völlig"
Korrigiert: "Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis, ansonsten unauffällig"

Roh: "Mammasonographie beidseits, thrombosierte Hautvenen links im axillären Quadranten, auslaufend in die linke Axilla bis 18 mm Durchmesser im Sinne eines Morbus Mondor, ansonsten beidseits unauffällig, Pirates 2"
Korrigiert: "Mammasonographie beidseits: Thrombosierte Hautvenen links im axillären Quadranten, auslaufend in die linke Axilla bis 18 mm Durchmesser im Sinne eines Morbus Mondor, ansonsten beidseits unauffällig. BI-RADS 2."

Roh: "Röntgen und der Sonographie des linken Schultergelenkes tenosynovitis der langen Bizepssehne tendinopathie und den Genusses pinnatus Sehne mit begleitet ist, ansonsten nur noch völlig"
Korrigiert: "Röntgen und Sonographie des linken Schultergelenkes: Tenosynovitis der langen Bizepssehne, Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis, ansonsten unauffällig"

Roh: ${rawText}

Korrigiert:`;

// Call 2 — Validierung. Text unverändert aus App.tsx (tools/prod_pipeline.py liest ihn hier per Regex).
export const validationPrompt = (rawDictation: string, generatedReport: string): string => `Du bist ein radiologischer Qualitätskontrolleur. Du erhältst das ursprüngliche Diktat und den daraus generierten Befund. Prüfe STRENG:

1. VOLLSTÄNDIGKEIT: Jede Pathologie/Diagnose aus dem Diktat muss im Befund (## Befund) UND im Ergebnis (## Ergebnis) vorkommen. Liste fehlende Diagnosen auf.
2. WIDERSPRUCHSFREIHEIT: Befund und Ergebnis dürfen sich nicht widersprechen. Wenn Befund eine Pathologie beschreibt, darf Ergebnis nicht "unauffällig" sein.
3. WIDERSPRUCHSFREIHEIT IM BEFUNDTEXT: Ein Normalbefund-Satz darf NICHT bestehen bleiben, wenn die entsprechende Struktur pathologisch verändert ist. Spezifisch:
   - "Bandscheibenräume normal hoch" MUSS gestrichen/angepasst werden wenn Osteochondrose/Diskopathie in einem Segment vorliegt.
   - "kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" MUSS angepasst werden wenn Facettengelenksarthrose vorliegt (NICHT bei Unkovertebralgelenksarthrose — das sind unterschiedliche Gelenke!).
   - "Normaler Achsenverlauf" MUSS ersetzt werden bei Skoliose, Streckhaltung, Anterolisthese oder anderen Achsenabweichungen.
   - "Alle Wirbelkörper von normaler Form und Höhe" MUSS angepasst werden bei Fraktur, Anterolisthese oder anderen Formveränderungen.
4. BESCHREIBUNGSTEXT = NUR MORPHOLOGIE: Im "## Befund" Abschnitt dürfen KEINE Diagnosenamen stehen (z.B. nicht "Osteochondrose im Segment C5/C6"). Stattdessen Deskriptoren: "Verschmälerung des Intervertebralraums C5/C6 mit subchondraler Sklerosierung der Abschlussplatten". Diagnosen NUR im "## Ergebnis".
5. KEINE ERFUNDENE DIAGNOSE: Der Befund darf keine Diagnosen enthalten, die im Diktat nicht erwähnt wurden. Umgekehrt MÜSSEN Arthrose-Diagnosen im Ergebnis nach Kellgren & Lawrence graduiert sein ("Grad [1-4] nach Kellgren & Lawrence"), wenn das betroffene Gelenk zur K&L-Liste gehört (Schulter/Ellbogen/Hand/Handgelenk/Hüfte/Knie/Sprunggelenk/Fuß — NICHT AC-Gelenk/ISG/Symphyse). Fehlt die Graduierung, ergänze sie im Format "(Arthrose Grad X nach Kellgren & Lawrence)" aus dem diktierten Adjektiv bzw. den Deskriptoren: beginnend/geringe Osteophyten=1, gering(gradig)=2, mäßig(gradig)/mittelgradig=3, hochgradig/aufgehobener Gelenkspalt=4. Beim Knie Femorotibial- und Patellofemoral-Kompartiment getrennt gradieren.
6. ZAHLEN UND MESSWERTE: Alle Zahlen aus dem Diktat müssen exakt im Befund stehen (Cobb-Winkel, mm, BI-RADS etc.).
7. SPRACHERKENNUNGSKORREKTUR: Prüfe nur, ob OFFENSICHTLICHE Spracherkennungsfehler im Diktat korrekt interpretiert wurden (z.B. "Antibiotik" → "Antelisthese", "Strichunkelvertebalatosen" → "Unkovertebralgelenksarthrosen"). Korrigiere NUR Wörter, die es medizinisch nicht gibt. ERFINDE NIEMALS Beschreibungen, die im Diktat nicht stehen: Wenn das Diktat keine Haltungs-/Achsenabweichung nennt, darf KEIN "Flachbogige Konvexität" o. ä. ergänzt werden. Und übernimm KEIN STT-Nonsense-Wort in den Befund: "Flachprofil" existiert nicht (korrekt: "flachbogige Skoliose" bzw. "flachbogige Seitausbiegung").

9. NORMALBEFUND ERHALTEN: Entferne NIEMALS Template-/Normalbefund-Sätze, die keiner diktierten Pathologie widersprechen — auch nicht zur Kürzung (z.B. Oberarm-/Unterarm-Abschnitte einer Nervensonographie bleiben vollständig stehen).
10. DIAGNOSEBEGRIFFE NIE ERSETZEN: Jede diktierte Diagnose bleibt im Ergebnis in der DIKTIERTEN Wortwahl als eigener Punkt ("Gelenksarthrose C3 bis C5" bleibt so — NICHT "Facettengelenksarthrose" oder "Uncovertebralarthrose"). "Bild wie bei [Diagnose]" bleibt "Bild wie bei", NIE zurück zu "vereinbar mit". Diktiertes "Verdacht auf [Diagnose]" bleibt WÖRTLICH "Verdacht auf [Diagnose]" (NIE "Bild wie bei"); die diktierte Seite bleibt in seitenbezogenen Ergebnis-Punkten stehen. Messwerte wie CSA gehören NICHT ins Ergebnis. AUSNAHME zur Wortwahl: Steht im generierten Ergebnis "Bild wie bei [Diagnose]", ist das die PFLICHT-Umsetzung von diktiertem "vereinbar mit"/"kompatibel mit" — NIEMALS entfernen, sonst wird aus einer Verdachtsdiagnose eine gesicherte.
8. UNTERSUCHUNGS-ÜBERSCHRIFT: Die Untersuchungsbezeichnung muss als eigene Markdown-Überschrift ('## [Untersuchungsart]') direkt VOR '## Befund' stehen (z.B. "## Kniegelenk links in 2 Ebenen", "## Schultergelenk rechts in 2 Ebenen") und darf NICHT als erster Satz im Befundtext stehen. Fehlt sie oder ist sie eine roh diktierte Kurzform ohne Formulierungsbestandteile (z.B. nur "Kniegelenk" oder "Schulter rechts in 2 Ebenen"), ergänze sie vollständig mit übernommener diktierter Seite. Enthält die Überschrift '(Allgemein)', ersetze sie durch die aus dem Diktat abgeleitete Untersuchungsbezeichnung (ohne Befundworte wie 'unauffällig') — '(Allgemein)' selbst darf nie als Titel stehen.

11. ERGEBNIS NUMMERIERT UND VOLLSTÄNDIG: Ergebnis-Punkte stehen je in einer Zeile, nummeriert "1. 2. 3." (Ausnahme: kompletter Normalbefund = EIN unnummerierter Satz). Diktierte Grad-Adjektive (geringgradig/mäßiggradig/hochgradig), Messwerte (z.B. "17 mm messendem Kalkdepot") und die Klammer "(Arthrose Grad X nach Kellgren & Lawrence)" MÜSSEN im Ergebnis stehen bleiben — NIE wegkürzen. Ein Befund mit seiner diktierten Deutung ("als indirekter Hinweis für …") bleibt EIN Punkt.
14. ERGEBNIS NIE DAS DIKTAT ABSCHREIBEN: Das Ergebnis besteht aus strukturierten Diagnosen (nummeriert), nicht aus dem Diktattext (z.B. NIE "Knie rechts unauffällig."). Nennt das Diktat KEINE Pathologie, steht im Ergebnis das zur Untersuchung passende Normal-Ergebnis (z.B. "Regelrechte Darstellung des Kniegelenkes rechts.", Thorax "Unauffälliger Befund.").
15. SEITE IM ERGEBNIS (gilt NUR für den Abschnitt ## Ergebnis): Jeder Ergebnis-Punkt mit seitenbezogener Diagnose (Extremität/Gelenk) nennt die diktierte Seite — z.B. "Verdacht auf Syndesmosenruptur rechts.". Entferne eine vorhandene Seite NIE; ergänzt du einen Ergebnis-Punkt, schreibe die Seite dazu. Im Befundtext steht die Seite in der Überschrift — dort KEINE Sätze wegen der Seite ergänzen, duplizieren oder umstellen; der Weichteil-Satz des Templates bleibt unverändert am Ende.
12. FLIESSTEXT: Im Befund stehen KEINE Abschnitts-Labels ("Skelett:", "Knochenstruktur:", "Gelenkflächen:", "Weichteile:") und keine Fettschrift — entferne sie, der Satz bleibt. Der Weichteil-Satz steht am Ende des Befundtextes.
13. STANDARDTEXT: Die Normalbefund-Sätze des Templates bleiben wörtlich stehen, sofern sie keiner Pathologie widersprechen — ersetze sie NIE durch eigene Formulierungen. Bei Arthrose steht der Kellgren-&-Lawrence-Deskriptor des Grades an der Stelle der Gelenkspalt-/Gelenkflächen-Normalsätze (Ellbogen danach "Ansonsten die artikulierenden Gelenkflächen regelrecht konfiguriert, glatt und scharf begrenzt.").

Wenn der Befund FEHLERFREI ist, gib ihn UNVERÄNDERT zurück.
Wenn es FEHLER gibt, korrigiere den Befund und gib die korrigierte Version zurück.
Gib NUR den fertigen Befundtext aus (mit Untersuchungs-Überschrift, ## Befund und ## Ergebnis), keine Erklärungen. KEINE Markdown-Codezäune (\`\`\`), keine Fettmarken. Stil-Formulierungen wie "o. B." NICHT umschreiben — korrigiere nur inhaltliche Fehler.

<diktat>
${rawDictation}
</diktat>

<generierter_befund>
${generatedReport}
</generierter_befund>

Korrigierter Befund:`;

// Correct STT errors using Gemini Flash (standalone, no external dependency)
export const correctTranscriptionWithGemini = async (rawTextIn: string, ctx: GenKontext): Promise<string> => {
  // v3.1: deterministische Fehlhör-Korrektur zuerst (misheard_words.json, mode 'auto')
  const rawText = ctx.misheard ? applyMisheard(rawTextIn, ctx.misheard.compiled) : rawTextIn;
  if (rawText !== rawTextIn) console.log(`[MISHEARD] auto-korrigiert: ${diktatLog(rawTextIn)} → ${diktatLog(rawText)}`);
  if (!ctx.apiKey) {
    return rawText; // No LLM available, return raw
  }

  const url = VERTEX_ENDPOINT;
  const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': ctx.apiKey };

  const correctionPromptText = correctionPrompt(ctx.misheard?.block ?? '', rawText);

  try {
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        contents: [{
          role: "user",
          parts: [{ text: correctionPromptText }]
        }],
        generationConfig: { temperature: 0.0, thinkingConfig: { thinkingBudget: 0 } }
      }),
      signal: ctx.signal,
    }, 120_000, 3);

    const data = await response.json();
    if (data.error) {
      console.warn('[CORRECT] Gemini correction error:', data.error.message);
      return rawText;
    }

    const corrected = joinGeminiText(data).trim();
    console.log(`[CORRECT] Raw: ${diktatLog(rawText)}`);
    console.log(`[CORRECT] Corrected: ${diktatLog(corrected)}`);
    // v2.11.1: abgeschnittene/verkürzte Korrektur NIE übernehmen (sonst fehlt der Diktat-Rest stillschweigend)
    if (!corrected || !geminiFinishedOk(data) || corrected.length < rawText.trim().length * 0.6) {
      console.warn('[CORRECT] Korrektur unvollständig/verkürzt — verwende Rohtext');
      return rawText;
    }
    return corrected;
  } catch (e: unknown) {
    if (istAbbruch(e)) throw e;  // Abbruch (Neu/F9) nicht als „Korrektur fehlgeschlagen“ weiterlaufen lassen
    console.warn('[CORRECT] Correction failed:', fehlermeldung(e));
    return rawText;
  }
};

// Call Gemini API to Structure the Transcript (Aligned 1:1 with EXE parameters)
export const stripCodeFences = (text: string): string =>
  text.replace(/^```[a-zA-Z]*\s*\n?/, '').replace(/\n?```\s*$/, '').trim();

export const callGeminiLLM = async (rawText: string, templateBody: string, regionName: string, examples: string, normalErgebnis: string, ctx: GenKontext): Promise<string> => {
  if (!ctx.apiKey) {
    throw new Error("Es ist kein Vertex AI API-Key konfiguriert. Bitte in den Einstellungen eintragen.");
  }

  const url = VERTEX_ENDPOINT;
  const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': ctx.apiKey };

  ctx.status("Strukturiere mit Gemini...");

  // v2.10.13 (K3-Review Befund 2): Der LLM-Pfad bekommt die KANONISCHE Bezeichnung
  // (display_name, inkl. "(Allgemein)"), damit die "(Allgemein)"-Ausnahme im
  // Gen-Prompt ECHT feuern kann — bei pathologischen (Allgemein)-Diktaten leitet
  // das LLM die Überschrift aus dem Diktat (ohne Befundworte), statt den
  // Volltext als Titel zu bekommen. Der Bypass-Pfad (ohne LLM) bleibt bei
  // deriveUntersuchungsTitel — dort muss der Titel deterministisch entstehen.
  let promptText = stripPromptMarker(ctx.prompt)
    .replace("{roh_text}", () => rawText)
    .replace("{template_body}", () => templateBody)
    .replace("{region_name}", () => regionName);

  // Kanonische Untersuchungsbezeichnung als expliziter Block (Task 08.09.: roh diktierte
  // Kurzformen wie "Kniegelenk" dürfen die Bezeichnung nicht verdrängen)
  promptText = promptText + `\n<untersuchung>${regionName}</untersuchung>\n`;
  // v3.2 (Peter 05.10.): Normal-Ergebnis der Untersuchung — fürs Ergebnis, wenn das Diktat keine Pathologie nennt
  promptText = promptText + `<normal_ergebnis>${normalErgebnis}</normal_ergebnis>\n`;

  if (promptText.includes("{examples}")) {
    promptText = promptText.replace("{examples}", () => examples);
  } else {
    promptText = promptText + "\n\n" + examples;
  }


  const lastGenBody = JSON.stringify({
      contents: [{
        role: "user",
        parts: [{
          text: promptText
        }]
      }],
      systemInstruction: {
        parts: [{
          text: SYS_MSG
        }]
      },
      generationConfig: {
        temperature: 0.0,
        thinkingConfig: { thinkingBudget: 0 }
      }
    });
  const response = await fetchWithRetry(url, {
    method: 'POST',
    headers: authHeaders,
    body: lastGenBody,
    signal: ctx.signal,
  }, 120_000, 3);

  const data = await response.json();
  if (data.error) {
    throw new Error(data.error.message || "Gemini API Fehler.");
  }

  let outputText = stripCodeFences(joinGeminiText(data));
  // v2.11.1: unvollständige Antwort (kein ## Ergebnis / abgebrochen) → EINMAL neu anfordern, sonst Fehler statt Halb-Befund
  if (!isCompleteReport(outputText) || !geminiFinishedOk(data)) {
    console.warn('[GEN] Befund unvollständig — zweiter Versuch');
    const r2 = await fetchWithRetry(url, { method: 'POST', headers: authHeaders, body: lastGenBody, signal: ctx.signal }, 120_000, 2);
    const d2 = await r2.json();
    const t2 = d2.error ? '' : stripCodeFences(joinGeminiText(d2));
    if (!isCompleteReport(t2)) {
      throw new Error('Gemini lieferte zweimal einen unvollständigen Befund (Ergebnis fehlt). Bitte Diktat erneut strukturieren.');
    }
    outputText = t2;
  }
  return outputText;
};

// ─────────────────────────────────────────────────────────────────────────
// VALIDATION: 2nd Gemini Call — prüft Befund gegen Diktat auf Vollständigkeit & Widerspruchsfreiheit
export const validateReportConsistency = async (rawDictation: string, generatedReport: string, ctx: GenKontext): Promise<string> => {
  if (!ctx.apiKey) {
    return generatedReport; // No LLM available, skip validation
  }

  const url = VERTEX_ENDPOINT;
  const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': ctx.apiKey };


  try {
    console.log('[VALIDATE] Prüfe Befund-Konsistenz...');
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: validationPrompt(rawDictation, generatedReport) }] }],
        generationConfig: { temperature: 0.0, thinkingConfig: { thinkingBudget: 0 } }
      }),
      signal: ctx.signal,
    }, 120_000, 3);

    const data = await response.json();
    if (data.error) {
      console.warn('[VALIDATE] Validation error:', data.error.message);
      return generatedReport;
    }

    const validated = joinGeminiText(data).trim();
    // v2.11.1 (Prüfbericht K2): Validator kürzte bei Nervensono 1245 → 152 Zeichen (Normalbefund weg) → verwerfen
    const befLenIn = befundSection(generatedReport).length;
    const befLenOut = befundSection(validated).length;
    if (validated && isCompleteReport(validated) && befLenIn > 0 && befLenOut < befLenIn * 0.7) {
      console.warn(`[VALIDATE] Befund zu stark gekürzt (${befLenIn} → ${befLenOut}) — verwende Call-#1-Befund`);
      return generatedReport;
    }
    if (!validated || !isCompleteReport(validated) || !geminiFinishedOk(data)) {
      console.warn('[VALIDATE] Validation output invalid, using original');
      return generatedReport;
    }

    // Markdown-Zäune strippen (Gemini wickelt Befunde gelegentlich in ``` ein)
    const clean = stripCodeFences(validated);

    // v2.11.1: 'Bild wie bei' (= diktiertes 'vereinbar mit') darf der Validator NIE entfernen — sonst wird aus
    // einer Verdachtsdiagnose eine gesicherte (Test: 'vereinbar mit Karpaltunnelsyndrom' → Call2 'Karpaltunnelsyndrom').
    const restoreBildWieBei = (orig: string, val: string): string => {
      if (!orig.includes('## Ergebnis') || !val.includes('## Ergebnis')) return val;
      const [valHead, valErgRaw] = [val.split('## Ergebnis')[0], val.split('## Ergebnis').slice(1).join('## Ergebnis')];
      let valErg = valErgRaw;
      const origErg = orig.split('## Ergebnis').slice(1).join('## Ergebnis');
      for (const m of origErg.matchAll(/Bild wie bei ([^.\n]+)/g)) {
        const diag = m[1].trim();
        if (!diag || valErg.includes('Bild wie bei ' + diag)) continue;
        const idx = valErg.indexOf(diag);
        if (idx >= 0) valErg = valErg.slice(0, idx) + 'Bild wie bei ' + valErg.slice(idx);
      }
      return valHead + '## Ergebnis' + valErg;
    };
    const restored = restoreBildWieBei(generatedReport, clean);
    if (restored !== clean) console.warn('[VALIDATE] "Bild wie bei" wiederhergestellt');

    // Check if validation changed anything
    if (restored.trim() === generatedReport.trim()) {
      console.log('[VALIDATE] Befund war bereits fehlerfrei ✅');
    } else {
      console.log('[VALIDATE] Befund wurde korrigiert ⚠️');
    }
    return restored;
  } catch (e: unknown) {
    if (istAbbruch(e)) throw e;
    console.warn('[VALIDATE] Validation failed:', fehlermeldung(e));
    return generatedReport;
  }
};
