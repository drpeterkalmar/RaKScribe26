import React, { useState, useEffect, useRef } from 'react';
import {
  Mic, MicOff, Copy, Check, Upload, Download, Sparkles, X, KeyRound, Menu, Trash2,
  RotateCcw, ShieldCheck, FileKey, LoaderCircle, CircleAlert, AudioLines
} from 'lucide-react';
import templatesData from './templates.json';
// v3.1: Fehlhör-Liste — EINE Quelle für Web + EXE (Repo-Root /misheard_words.json, kein Spiegel)
import misheardData from '../../misheard_words.json';
import { compileMisheard, applyMisheard, misheardPromptBlock, type MisheardFile } from './misheard';
// v3.2: EIN Befund-Prompt für Web + EXE (Repo-Root /radiology_prompt.txt, versioniert) + gemeinsame
// deterministische Regeln (Sync: source_code/befund_regeln.py, Fixtures: befund_regeln_fixtures.json)
import genPromptRaw from '../../radiology_prompt.txt?raw';
import {
  splitRegionen, nachbearbeiten, befundeZusammenfuegen, ergebnisMitSeite, titelMitSeite,
  promptVersion, stripPromptMarker
} from './befundRegeln';
// v3.2 (Peter 05.10.): strenger Normalbefund-Bypass (Sync: source_code/normalbypass.py, normal_bypass_tests.json)
import { isPureNormalFinding } from './normalbypass';

// Types
type Template = {
  display_name: string;
  body: string;
  ergebnis?: string;  // v3.2: Normal-Ergebnis der Untersuchung (Bypass + <normal_ergebnis> im LLM-Pfad)
};

type TemplatesMap = {
  [key: string]: Template;
};

const templates = templatesData as TemplatesMap;
const DISPLAY_NAMES = Object.values(templates).map(t => t.display_name);
// v3.2 (Peter 05.10.): Region nicht erkannt → KEIN Skelett-Standardtext (Lungenröntgen wurde sonst als Skelett befundet)
const ALLGEMEIN_FALLBACK: Template = {
  display_name: "Allgemeine Untersuchung",
  body: "Allgemeine Untersuchung\n\nKein Nachweis pathologischer Veränderungen.",
  ergebnis: "Unauffälliger Befund.",
};

// Vertex AI endpoint for Gemini 2.5 Flash
// v2.11.0 (26.09.2026): gemini-3.5-flash am EU-Multi-Region-Endpoint (EU-Datenresidenz + EU-Verarbeitung).
// A/B 54 Fall-Läufe: Normalbefund-Treue 84,5 % → 93,7 %, fehlende '## Befund'-Überschrift 6 → 0, FAIL 0.
// gemini-2.5-flash wird von Google abgeschaltet (Phase 1: 20.10.2026).
// v2.11.1 HOTFIX: Gemini 3.5 teilt Antworten gelegentlich in mehrere parts auf ('## L' | 'endenwirbelsäule…').
// Immer ALLE Text-parts zusammensetzen (Thinking-parts ausgenommen) — nie nur parts[0] lesen.
const joinGeminiText = (data: any): string =>
  (data?.candidates?.[0]?.content?.parts || [])
    .filter((p: any) => typeof p?.text === 'string' && !p?.thought)
    .map((p: any) => p.text)
    .join('');

// v2.11.1: Ein Befund gilt nur als vollständig, wenn '## Befund' UND ein nicht-leeres '## Ergebnis' vorhanden sind
// und Gemini regulär beendet hat (finishReason STOP). Sonst: Retry bzw. Fallback — NIE Halb-Befunde ausgeben.
const geminiFinishedOk = (data: any): boolean => {
  const fr = data?.candidates?.[0]?.finishReason;
  return !fr || fr === 'STOP';
};
// Vollständig = nicht-leeres '## Ergebnis' mit Befundtext davor ('## Befund' fehlt beim Prod-Prompt gelegentlich — kein Abbruchgrund).
const befundSection = (t: string): string => {
  const pre = t.split('## Ergebnis')[0];
  const body = pre.includes('## Befund') ? pre.split('## Befund')[1] : pre.split('\n').filter(l => !l.trim().startsWith('#')).join('\n');
  return body.trim();
};
const isCompleteReport = (t: string): boolean =>
  t.includes('## Ergebnis') && t.split('## Ergebnis')[1].trim().length > 5 && befundSection(t).length > 20;

const VERTEX_ENDPOINT = 'https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/locations/eu/publishers/google/models/gemini-3.5-flash:generateContent';

// Speech-Context Phrasen für Google STT (medizinischer Jargon, boost 15.0)
const MEDICAL_PHRASES = [
  "Hochauflösender Nervenschall", "Thorax pa/seitlich", "MRT", "MR", "CT", "Computertomografie", "DXA", "Knochendichtemessung",
  "Humerus", "Femur", "Tibia", "Fibula", "Patella", "Karpaltunnel", "Rotatorenmanschette",
  "Achillessehne", "Kalkaneus", "Acromioclaviculargelenk", "Sacroiliacalgelenk", "Halswirbelsäule (HWS)",
  "Brustwirbelsäule (BWS)", "Lendenwirbelsäule (LWS)", "Kreuzband", "Tarsus", "Metatarsus",
  "Fraktur", "Spondylarthrose", "Spondylarthrosen", "Spondylodese", "Spondyolyse", "Spondylosis deformans", "Spondylose", "pontifizierend", "pontifizierende", "Arthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Hinterhorn-Läsion",
  "Korbhenkelriss", "Bandscheibenprolaps", "Spinalkanalstenose", "Osteochondrose", "Osteochondrosen", "Nearthrosis interspinosa",
  "Osteomyelitis", "Rheumatoide Arthritis", "Kapsel-Band-Läsion", "Osteoporose", "Bakerzyste",
  "Knochenödem", "Einklemmungssyndrom", "Arthrographie", "Szintigraphie", "Vertebroplastie",
  "Facetteninfiltration", "CT-gesteuerte Biopsie", "MR-Arthrographie", "Skelettaufnahme", "Ganzbeinaufnahme",
  "Gelenkspaltverschmälerung", "Subluxation", "Wirbelkörperkompression", "Rotatorenmanschettenruptur",
  "Labrumläsion", "Subchondrale Sklerosierung", "Nervus medianus", "Nervus radialis",
  "Liquor", "Zerebrospinalflüssigkeit", "Kortex", "Großhirnrinde", "Weiße Substanz", "Basalganglien",
  "Hypophyse", "Corpus callosum", "Sinus cavernosus", "Aorta", "Arteria carotis interna", "Arteria carotis externa",
  "Pulmonalarterie", "Vena cava superior", "Vena cava inferior", "A. vertebralis",
  "Aneurysma", "Intrakranielles Aneurysma", "Ischämie", "Ischämischer Infarkt", "Intracranielle Blutung",
  "Subarachnoidalblutung (SAB)", "Subduralhämatom (SDH)", "Epiduralhämatom (EDH)", "Multiple Sklerose (MS)",
  "Hypophysenadenom", "Hydrozephalus", "Normaldruckhydrozephalus", "Vaskulitis", "Stenose", "Carotisstenose",
  "Koronarstenose", "Dissektion", "Aortendissektion", "Thrombus", "Thrombose", "Embolie", "PAE", "Plaqubildung", "Softplaque",
  "gemischte Plaqueformation", "IMT-Komplex", "Intima-Media-Hyperplasie", "Intimahyperplasie",
  "Varizen", "T1-gewichtete Sequenz", "T2-gewichtete Sequenz", "Flair-Sequenz", "Diffusion-weighted Imaging (DWI)",
  "Time-of-Flight (TOF) Angio", "MRA", "CTA", "Kontrastmittel (KM)", "Plaque", "Atherosklerotische Plaque",
  "Angioplastie", "Sakkuläres Aneurysma", "Gefäßokklusion",
  "Lunge", "Oberlappen", "Unterlappen", "Trachea", "Bronchien", "Mediastinum", "Herz", "Ventrikel",
  "Perikard", "Leber", "Gallenblase", "Pankreas", "Niere", "Milz", "Uterus", "Adnexe", "Appendix",
  "Schilddrüse", "Infiltrat", "Pulmonales Infiltrat", "Pleuraerguss", "Pneumothorax", "Spannungspneumothorax",
  "Kardiomegalie", "Aortenklappeninsuffizienz", "Leberzirrhose", "Cholezystitis", "Pankreatitis",
  "Nierenstein", "Ureterstein", "Nephrolithiasis", "Adnexitis", "Ovarielle Zyste", "Lymphknoten",
  "Lymphadenopathie", "Appendizitis", "Struma", "Verschattung", "Milzruptur", "Hernie", "Hiatushernie",
  "Inguinalhernie", "Dilatation", "Aszites", "Zystische Läsion", "Liquidation", "Faszienverdickung",
  "Hydronephrose", "Peritonealkarzinose", "Fokale Raumforderung (FRF)", "Hyperdens", "Hypodens", "Isodens",
  "Echoarm", "Echogen",
  "Malignität", "Benignität", "Tumor", "Karzinom", "Metastase", "Läsion", "Atypisch", "unspezifisch",
  "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung", "Fibroostose", "Fibroostosen", "Neoarthrosis interspinosa", "Neoarthrosen interspinosa", "Thorax p.a.", "Thorax p.a./seitlich",
  "Sklerosierung", "Nekrose", "Atrophie", "Randscharf", "unscharf begrenzt", "Rückbildung", "Progression",
  "V. a.", "Verdacht auf", "Differenzialdiagnose (DD)", "Interventionell", "Biopsie", "Drainage",
  "Normalbefund", "kein Nachweis für", "Axial", "koronar", "sagittal", "Anamnese", "Indikation",
  "Kontraindikation", "Artefakt", "Pixel", "Voxel", "Echoarmut", "Echogenität", "Hyperintens", "Hypointens",
  "Dosis-Längen-Produkt (DLP)", "Field of View (FOV)", "Standard-Abweichung (SD)", "Flüssigkeitsspiegel",
  "Röntgen-Thorax", "Projektionsaufnahme", "Z.n.", "Zustand nach", "Adenokarzinom", "Cholangiokarzinom",
  "Fibrose", "Hämangiom", "Atelektase", "Bronchiektasen", "Emphysem", "Sarkom", "Neurofibrom", "Lipom",
  "Aortenaneurysma", "Klaustrophobie", "Sequester", "Vollbild", "Partialruptur", "Tendinose", "Impingement",
  "zerviko", "torako", "thoraco", "lumbal", "zervikothorakal", "zervikolumbal", "zervikotorakolumbal",
  "zervikal", "thorakal", "Skoliose", "Retrolisthese", "Retrolisthesis", "Foramenstenose", "Foramenstenosen",
  "Foraminalstenose", "Foraminalstenosen", "Ganzaufnahme", "Ganzaufnahmen", "L4 gegenüber L5", "L5/S1",
  "Flachbogig", "S-förmige", "Discopathiezeichen", "Diskopathiezeichen",
  // ── Schulter/Sonographie-spezifisch ──
  "Tenosynovitis", "Tenosynovitis der langen Bizepssehne", "Bizepssehne", "Bizepssehnenscheide",
  "Tendinopathie", "Tendinose", "Tendinosis", "Tendinosis calcarea",
  "Supraspinatussehne", "Supraspinatus", "Infraspinatussehne", "Infraspinatus",
  "Subscapularis", "Subscapularissehne", "Teres minor", "Teres-minor-Sehne",
  "Rotatorenmanschette", "Rotatorenmanschettenruptur", "Rotatorenmanschetten-Tendinose",
  "Bursitis", "Bursitis subacromialis", "Subacromialbursa", "Subakromialbursa",
  "begleitende Bursitis", "Begleitbursitis", "begleitbursitis",
  "Kalkschulter", "Kalkspick", "Kalkablagerung", "Verkalkung der Supraspinatussehne",
  "Impingement", "Impingementsyndrom", "subacromiales Impingement",
  "Akromion", "Akromioklavikulargelenk", "AC-Gelenk", "Klavikula",
  "Coracoid", "Processus coracoideus", "Labrum glenoidale", "Labrumläsion",
  "SLAP-Läsion", "Bankart-Läsion", "Hill-Sachs-Läsion",
  "Glenohumeralgelenk", "Glenoid", "Bizepssehnenanker",
  "Lange Bizepssehne", "Lange-Bizeps-Sehne", "Bizepslongussehne",
  "Schultergelenksonographie", "Schultersonographie", "Schulterultraschall",
  "Röntgen und Sonographie des Schultergelenkes",
  "Röntgen und der Sonographie",
  "Kalkeinlagerung", "Kalkdepot", "Kalkherd",
  "Sehnenkalkeinlagerung", "Tendinosis calcarea der Supraspinatussehne",
  "Partialruptur der Supraspinatussehne", "Full-Thickness-Ruptur",
  "Gelenkerguss", "Gelenkspalt", "Gelenkkapsel",
  // ── Allgemein radiologische Begriffe (ergänzt) ──
  "unauffällig", "Unauffällig", "unauffälliger Befund",
  "analog zur Gegenseite", "seitengleich", "seitensymmetrisch",
  "regelrecht", "Regelrecht", "regelrechte Darstellung",
  "ohne pathologischen Befund", "kein pathologischer Befund",
  "Echostruktur", "Echotextur", "echonormal", "echoreich", "echoarm", "echogen",
  "Parenchym", "Binnenstruktur", "Homogen", "homogen",
  "Weichteile", "Weichteilmantel", "Weichteilschwellung",
  "Röntgen und Sonographie", "Röntgen und der Sonographie",
  "des linken Schultergelenkes", "des rechten Schultergelenkes",
  "des linken Kniegelenkes", "des rechten Kniegelenkes",
  "des linken Hüftgelenkes", "des rechten Hüftgelenkes",
  "des linken Sprunggelenkes", "des rechten Sprunggelenkes",
  "des linken Ellbogengelenkes", "des rechten Ellbogengelenkes",
  "des linken Handgelenkes", "des rechten Handgelenkes",
  // ── Praxis-Jargon / Shortcut-Phrasen ──
  "Baustein Gelenkschema", "Baustein Gelenkschirma", "Baustein Gelenk Schema",
  "Frakturnachweis", "kein Frakturnachweis", "Fraktur", "Fissur",
  "Zehe", "Zehen", "zweite Zehe", "dritte Zehe", "Großzehe",
  "Metatarsale", "Phalanx", "Basis",
  // ── Mamma/Mammasonographie-spezifisch ──
  "Mammasonographie", "Mammasonografie", "Mammasonographie beidseits",
  "Mammographie", "Mammografie", "Mammographie beidseits",
  "Drüsenparenchym", "Brustdrüse", "Mamma",
  "BI-RADS", "BI-RADS 0", "BI-RADS 1", "BI-RADS 2", "BI-RADS 3", "BI-RADS 4", "BI-RADS 5", "BI-RADS 6",
  "BIRADS", "BIRADS 0", "BIRADS 1", "BIRADS 2", "BIRADS 3", "BIRADS 4", "BIRADS 5",
  "Morbus Mondor", "Mondor", "Mondor-Disease",
  "Hautvene", "Hautvenen", "thrombosierte Hautvene", "thrombosierte Hautvenen",
  "kutane Venenthrombose", "Venenthrombose",
  "axillär", "axillärer Quadrant", "axillären Quadranten", "Axilla",
  "Axillen", "Axillen beidseits frei",
  "Subcutis", "Cutis", "Mikrokalk", "Mikrokalkansammlungen",
  "Architekturstörung", "Architekturstörungen",
  "Herdbefund", "Herdbefunde", "suspekter Herdbefund",
  "Zyste", "Zysten", "solide Läsion", "solide Läsionen",
  "Lymphknoten", "Lymphknoten axillär", "pathologisch vergrößerte Lymphknoten",
  "Inspektion und Palpation", "Palpationsbefund",
  "Durchmesser", "mm Durchmesser",
  // ── Nervus-ulnaris / Neurosonographie-spezifisch ──
  "Nervus ulnaris", "N. ulnaris", "Sulcus nervi ulnaris", "Sulcus ulnaris",
  "Loge de Guyon", "Guyon-Loge", "Ramus dorsalis", "Ramus superficialis", "Ramus profundus",
  "Querschnittsfläche", "Querschnittsflaeche", "Quadratmillimeter", "mm²",
  "M. anconeus", "Musculus anconeus", "M. anconeus epitrochlearis", "anconeus epitrochlearis",
  "hypertropher M. anconeus", "hypertrophe Musculus anconeus",
  "Epicondylus medialis humeri", "Epicondylus medialis", "mediales Septum intermusculare",
  "Osborne Ligament", "Osborne-Ligament", "Osborne Faszie", "Retinaculum",
  "M. flexor carpi ulnaris", "Flexor carpi ulnaris", "FCU",
  "Ellbogenflexion", "Ellbogenstreckung", "Ellbogengelenk",
  "Aggravation", "Kompression des Nervs", "Nervenkompression",
  "faszikulär", "faszikulaer", "nervale Auftreibung", "Denervation",
  "Hypothenarmuskulatur", "Lumbricalmuskulatur", "M. adductor pollicis", "Muskel-Faszikulationen",
  "Echogenitätssteigerung", "Atrophie", "seitensymmetrisch",
  "Schnappen des Nervs", "Loge de Guyon unauffällig",
  "N. radialis", "Nervus radialis", "Ramus profundus", "Ramus superficialis",
  "Frohse-Arkade", "Frohse Arkade", "Supinator", "M. supinator", "Musculus supinator",
  "Wartenberg-Syndrom", "Wartenberg", "Arteria radialis recurrens",
  "Sulcus n. radialis", "Strecksehnenfach", "4. Strecksehnenfaches",
  "N. cutaneus brachii lateralis inferior", "N. cutaneus antebrachii posterior",
  "M. brachioradialis", "Handgelenksextensoren",
  // ── BWS/Skoliose/Morbus Scheuermann-spezifisch ──
  "flachbogig", "flachbogige", "flachbogige Skoliose", "S-förmige Skoliose", "rechtskonvex", "linkskonvex",
  "HWS", "HWK",
  "Kyphose", "kyphotische Fehlhaltung", "Fehlhaltung",
  "Kellgren", "Lawrence", "Kellgren & Lawrence", "Kellgren-Lawrence",
  "Skoliose", "Cobb-Winkel", "Cobb Winkel", "lateraler Kopfwinkel", "Copfwinkel",
  "Oberkante", "Unterkante", "TH4", "TH8", "Th4", "Th8", "TH12", "Lendenwirbel",
  "Schmorl'sche Impressionen", "Schmorlsche Impressionen", "Schmorl-Impressionen",
  "multisegmentale", "Schmalsche Impressionen", "Deckplattenimpressionen",
  "Edgren-Vaino-Zeichen", "Edgren Vaino Zeichen", "Edgren-Vaino Zeichen",
  "Morbus Scheuermann", "Scheuermann", "Scheuermann-Krankheit",
  "Kyphose", "hyperkyphotisch", "harmonische Kyphose",
  "Bogenwurzeln", "Dornfortsätze", "Querfortsätze", "Processus articulares",
  "Articulationes costotransversales", "Articulationes costovertebrales",
  "Spatien intervertebralia", "Canalis spinalis", "Platae terminales",
  "BWS-Röntgen", "BWS in 2 Ebenen", "Brustwirbelsäule", "BWS",
  // ── Allgemein radiologische Begriffe (ergänzt) ──
  "unauffällig", "Unauffällig", "unauffälliger Befund",
  "analog zur Gegenseite", "seitengleich", "seitensymmetrisch",
  "regelrecht", "Regelrecht", "regelrechte Darstellung",
  "ohne pathologischen Befund", "kein pathologischer Befund",
  "Echostruktur", "Echotextur", "echonormal", "echoreich", "echoarm", "echogen",
  "Parenchym", "Binnenstruktur", "Homogen", "homogen",
  "Weichteile", "Weichteilmantel", "Weichteilschwellung",
  "Röntgen und Sonographie", "Röntgen und der Sonographie",
  "des linken Schultergelenkes", "des rechten Schultergelenkes",
  "des linken Kniegelenkes", "des rechten Kniegelenkes",
  "des linken Hüftgelenkes", "des rechten Hüftgelenkes",
  "des linken Sprunggelenkes", "des rechten Sprunggelenkes",
  "des linken Ellbogengelenkes", "des rechten Ellbogengelenkes",
  "des linken Handgelenkes", "des rechten Handgelenkes",
  // ── Praxis-Jargon / Shortcut-Phrasen ──
  "Baustein Gelenkschema", "Baustein Gelenkschirma", "Baustein Gelenk Schema",
  "Frakturnachweis", "kein Frakturnachweis", "Fraktur", "Fissur",
  "Zehe", "Zehen", "zweite Zehe", "dritte Zehe", "Großzehe",
  "Metatarsale", "Phalanx", "Basis",
  // ── Mamma/Mammasonographie-spezifisch ──
  "Mammasonographie", "Mammasonografie", "Mammasonographie beidseits",
  "Mammographie", "Mammografie", "Mammographie beidseits",
  "Drüsenparenchym", "Brustdrüse", "Mamma",
  "BI-RADS", "BI-RADS 0", "BI-RADS 1", "BI-RADS 2", "BI-RADS 3", "BI-RADS 4", "BI-RADS 5", "BI-RADS 6",
  "BIRADS", "BIRADS 0", "BIRADS 1", "BIRADS 2", "BIRADS 3", "BIRADS 4", "BIRADS 5",
  "Morbus Mondor", "Mondor", "Mondor-Disease",
  "Hautvene", "Hautvenen", "thrombosierte Hautvene", "thrombosierte Hautvenen",
  "kutane Venenthrombose", "Venenthrombose",
  "axillär", "axillärer Quadrant", "axillären Quadranten", "Axilla",
  "Axillen", "Axillen beidseits frei",
  "Subcutis", "Cutis", "Mikrokalk", "Mikrokalkansammlungen",
  "Architekturstörung", "Architekturstörungen",
  "Herdbefund", "Herdbefunde", "suspekter Herdbefund",
  "Zyste", "Zysten", "solide Läsion", "solide Läsionen",
  "Lymphknoten", "Lymphknoten axillär", "pathologisch vergrößerte Lymphknoten",
  "Inspektion und Palpation", "Palpationsbefund",
  "Durchmesser", "mm Durchmesser",
];




// ─────────────────────────────────────────────────────────────────────────
// isNormalFinding — erkennt reine Normalbefunde für RAG-Bypass (kein LLM nötig)
// Wird von Recording- und Upload-Pfad verwendet. Negations-aware.
// ─────────────────────────────────────────────────────────────────────────
// deriveUntersuchungsTitel — Befundtitel für Bypass & <untersuchung>-Embed (Sync mit RaKScribe.py, v2.10.12).
// Generische Sammel-Templates ('(Allgemein)') dürfen ihren internen Namen NICHT als
// Befundtitel ausgeben (Peter 09.09.) → Titel aus dem Diktat, Befund-Worte gestrippt.
function deriveUntersuchungsTitel(raw: string, displayName: string): string {
  if (!/\(allgemein\)/i.test(displayName || "")) return displayName;
  // v2.10.13 (K3-Review): optionale Umlaut-Gruppe (STT-Typo "unauffllig"), Negations-Guard
  // ("nicht unauffällig" kappselt das NICHT), Newline-Falt, ':'-Strip, (Allgemein)-Leak, Cap 80.
  let t = (raw || "").trim().replace(/\bHW\b/g, "HWS").replace(/\s+/g, " ").replace(/[.?!]\s*$/, "").trim();
  const findings = ["unauff(?:ae|ä)?llig", "o\\.?\\s?B\\.?", "ohne pathologischen Befund", "ohne pathologischem Befund", "kein pathologischer Befund", "regelrecht", "normal"];
  for (let round = 0; round < 3; round++) {
    let stripped = false;
    for (const f of findings) {
      const m = t.match(new RegExp("(?:^|[\\s,])" + f + "\\s*$", "i"));
      if (m) {
        const pre = t.slice(0, (m.index ?? 0)).trim();
        if (/\bnicht\s*$/i.test(pre)) continue; // Negation: "nicht unauffällig" nicht kappseln
        t = pre; stripped = true;
      }
    }
    if (!stripped) break;
  }
  t = t.replace(/[.,?!:]+$/, "").replace(/\(\s*allgemein\s*\)/gi, "").trim();
  if (t.length > 80) t = t.slice(0, 80).trim();
  return t || displayName.replace(/\s*\(Allgemein\)/i, "").trim();
}

// (v3.2: Bypass-Entscheidung = isPureNormalFinding in normalbypass.ts — gleiche Semantik wie die EXE, gemeinsame Fixtures)

// ─────────────────────────────────────────────────────────────────────────
// fetchWithRetry — robust fetch with timeout + automatic retry
// Prevents silent failures when Google Cloud APIs are slow or flaky.
// The web app must handle this autonomously — no Hermes to the rescue.
// ─────────────────────────────────────────────────────────────────────────
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  timeoutMs: number = 120_000,
  maxRetries: number = 3
): Promise<Response> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      // Retry on 429 (rate limit), 500, 502, 503, 504
      if (response.status === 429 || response.status >= 500) {
        const waitSec = Math.min(2 ** attempt, 8);
        if (attempt < maxRetries) {
          console.warn(`[FETCH] HTTP ${response.status}, retry ${attempt}/${maxRetries} in ${waitSec}s...`);
          await new Promise(r => setTimeout(r, waitSec * 1000));
          continue;
        }
      }
      return response;
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError' && attempt < maxRetries) {
        const waitSec = Math.min(2 ** attempt, 8);
        console.warn(`[FETCH] Timeout (${timeoutMs}ms), retry ${attempt}/${maxRetries} in ${waitSec}s...`);
        await new Promise(r => setTimeout(r, waitSec * 1000));
        continue;
      }
      throw err;
    }
  }
  throw new Error(`fetchWithRetry: Max retries (${maxRetries}) exceeded for ${url}`);
}

// Helper to encode AudioBuffer to WAV
function audioBufferToWav(buffer: AudioBuffer): Blob {
  const numOfChan = 1; // mono
  const sampleRate = buffer.sampleRate;
  const format = 1; // raw PCM
  const bitDepth = 16;
  const result = buffer.getChannelData(0);
  
  const arrayBuffer = new ArrayBuffer(44 + result.length * 2);
  const view = new DataView(arrayBuffer);
  
  // RIFF identifier
  writeString(view, 0, 'RIFF');
  // file length
  view.setUint32(4, 36 + result.length * 2, true);
  // RIFF type
  writeString(view, 8, 'WAVE');
  // format chunk identifier
  writeString(view, 12, 'fmt ');
  // format chunk length
  view.setUint32(16, 16, true);
  // sample format (raw)
  view.setUint16(20, format, true);
  // channel count
  view.setUint16(22, numOfChan, true);
  // sample rate
  view.setUint32(24, sampleRate, true);
  // byte rate
  view.setUint32(28, sampleRate * numOfChan * (bitDepth / 8), true);
  // block align
  view.setUint16(32, numOfChan * (bitDepth / 8), true);
  // bits per sample
  view.setUint16(34, bitDepth, true);
  // data chunk identifier
  writeString(view, 36, 'data');
  // chunk length
  view.setUint32(40, result.length * 2, true);
  
  // float to 16-bit PCM
  let offset = 44;
  for (let i = 0; i < result.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, result[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  
  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function mergeFloat32Arrays(chunks: any[]): Float32Array {
  const totalLength = chunks.reduce((acc, val) => acc + val.length, 0);
  const mergedArray = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    mergedArray.set(chunk, offset);
    offset += chunk.length;
  }
  return mergedArray;
}

function downsampleBuffer(buffer: any, inputSampleRate: number, outputSampleRate: number): Float32Array {
  if (inputSampleRate === outputSampleRate) {
    return buffer;
  }
  if (inputSampleRate < outputSampleRate) {
    return buffer;
  }
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}


// v3.0: Kein Login mehr. Die App ist gesperrt, bis der Praxis-Schlüssel geladen ist (Drag & Drop irgendwo
// ins Fenster oder Menü → „Schlüssel laden“). Erkennt praxis-key.json, SA-JSON (roh/Base64) und AQ.-Keys.
// Beide Schlüssel bleiben lokal im Browser (localStorage) — nichts verlässt das Gerät außer zu Google.

// Key-Generation-Marker: Bei Key-Rotation diesen Wert hochzählen. Gespeicherte
// Keys mit älterer Markierung werden beim Start verworfen (Fix für veraltete
// localStorage-Keys, die den frischen Key blockiert haben — vgl. 401 in der EXE).
const KEY_VERSION = '2';
// PROMPT_VERSION: bump → neuer Default-Prompt überschreibt in ALLEN Browsern den gespeicherten
// localStorage-Prompt (ohne Bump sieht ein bestehender Browser Prompt-Updates NIE).
// v3.2: Version = Marker der gemeinsamen Prompt-Datei (<!-- RAKSCRIBE_PROMPT_VERSION: … -->) — Prompt-Änderung
// heißt Marker hochsetzen, dann rollt sie in Web (localStorage) UND EXE (versionierte Prompt-Wahl) aus.
const PROMPT_VERSION = promptVersion(genPromptRaw) || 'ohne-marker';
const GEN_PROMPT = stripPromptMarker(genPromptRaw);
// systemInstruction — WORTGLEICH zu SYS_MSG in source_code/RaKScribe.py (befund_regeln_test.py prüft das)
const SYS_MSG =
  "Du bist ein präziser Radiologie-Assistent der Praxis 'Röntgen am Kai' – Dr. P. Kalmar / Dr. G. Riegler. " +
  "Strukturiere das Diktat nach den Regeln im Prompt mit dem Normalbefund-Template als vollständigem Gerüst. " +
  "Ausgabe: zuerst '## ' + kanonische Untersuchungsbezeichnung mit diktierter Seite, dann '## Befund' als Fließtext " +
  "ohne Labels und '## Ergebnis' nummeriert (1. 2. 3.) mit den diktierten Begriffen 1:1 inklusive Grad und Messwerten. " +
  "Gib ausschließlich den fertigen Befundtext aus – keine Kommentare, keine Einleitung.";
// v3.1: Fehlhör-Liste — auto-Regeln laufen deterministisch VOR Call 0 (auch ohne Gemini),
// llm-Regeln landen als Tabelle im Call-0-Prompt. Pflege NUR in /misheard_words.json.
const MISHEARD: MisheardFile = misheardData as MisheardFile;
const MISHEARD_COMPILED = compileMisheard(MISHEARD);
const MISHEARD_PROMPT_BLOCK = misheardPromptBlock(MISHEARD);

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
    const json = JSON.parse(candidate);
    if (json.type === 'service_account' && json.private_key) {
      // STT-Key global verfügbar machen (App setzt ihn beim Mount via Event)
      (window as any).__praxisSttKey = json;
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
      (window as any).__praxisSttKey = json.stt;
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

  // Configuration States
  const [vertexApiKey, setVertexApiKey] = useState<string>('');
  const [sttKeyJson, setSttKeyJson] = useState<any>(null);
  const keysReady = !!vertexApiKey && !!(sttKeyJson && sttKeyJson.private_key);
  const keysReadyRef = useRef(keysReady);
  keysReadyRef.current = keysReady;
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const audioUploadRef = useRef<HTMLInputElement>(null);
  const keyFileRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');

  // Application States
  const [status, setStatus] = useState<'ready' | 'recording' | 'processing' | 'copied'>('ready');
  const statusRef = useRef(status);
  statusRef.current = status;
  const [statusText, setStatusText] = useState<string>('Bereit');
  const [transcript, setTranscript] = useState<string>('');
  const [structuredReport, setStructuredReport] = useState<string>('');
  const [micLevel, setMicLevel] = useState<number>(0);
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
  const audioChunksRef = useRef<Float32Array[]>([]);

  // States and refs for chunked transcription feedback
  const [isTranscribingChunk, setIsTranscribingChunk] = useState<boolean>(false);
  const chunkIntervalRef = useRef<any>(null);
  const lastProcessedIndexRef = useRef<number>(0);
  const chunkTranscriptsRef = useRef<string[]>([]);
  const pendingPromisesRef = useRef<Promise<any>[]>([]);
  const activeRequestsCountRef = useRef<number>(0);
  const actualSampleRateRef = useRef<number>(16000);


  // Load configuration from local storage
  useEffect(() => {
    const savedVertexKey = localStorage.getItem('vertex_api_key');
    const savedKeyVersion = localStorage.getItem('key_version');
    const savedPrompt = localStorage.getItem('system_prompt');
    const savedPromptVersion = localStorage.getItem('system_prompt_version');
    const savedDeviceId = localStorage.getItem('selected_audio_device_id');

    // Stale-Key-Schutz: Gespeicherte Keys aus einer älteren Key-Generation verwerfen.
    if (savedVertexKey && savedKeyVersion !== KEY_VERSION) {
      console.log('[INIT] Veralteter gespeicherter Key (alte Key-Generation) verworfen');
      localStorage.removeItem('vertex_api_key');
      localStorage.removeItem('praxis_stt_key');
      setVertexApiKey('');
    } else if (savedVertexKey) {
      setVertexApiKey(savedVertexKey);
    }
    window.addEventListener('vertex-key-external', () => {
      const k = localStorage.getItem('vertex_api_key');
      if (k) setVertexApiKey(k);
    });
    // v3.0: STT-Schlüssel aus dem letzten Laden wiederherstellen (kein erneutes Reinziehen nötig)
    const savedStt = localStorage.getItem('praxis_stt_key');
    if (savedStt && savedKeyVersion === KEY_VERSION) {
      try { const j = JSON.parse(savedStt); if (j && j.private_key) (window as any).__praxisSttKey = j; } catch { /* ignorieren */ }
    }
    localStorage.removeItem('is_authenticated');
    if (savedDeviceId) setSelectedDeviceId(savedDeviceId);

    // Praxis-Login: STT-Key aus dem Login-Vorgang übernehmen
    const onPraxisKey = () => {
      const k = (window as any).__praxisSttKey;
      if (k && k.private_key) setSttKeyJson(k);
    };
    window.addEventListener('praxis-stt-key', onPraxisKey);
    if ((window as any).__praxisSttKey) onPraxisKey();

    // (v3.0: frühere Auto-Load-Fallbacks vertex-key.txt/.b64/stt-key.* entfernt — Schlüssel kommen nur per Drag & Drop/Menü)

    // v3.2: Default-Prompt = gemeinsame Datei radiology_prompt.txt (kein zweiter Prompt-Text mehr in App.tsx)
    const defaultPrompt = GEN_PROMPT;

    if (!savedPrompt || savedPromptVersion !== PROMPT_VERSION || savedPrompt.includes("## Beurteilung") || savedPrompt.includes("Radiologe-Assistent</role>")) {
      setSystemPrompt(defaultPrompt);
      localStorage.setItem('system_prompt', defaultPrompt);
      localStorage.setItem('system_prompt_version', PROMPT_VERSION);
    } else {
      setSystemPrompt(savedPrompt);
    }
  }, []);

  const loadAudioDevices = async (requestPermission = false) => {
    try {
      if (requestPermission) {
        const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        tempStream.getTracks().forEach(track => track.stop());
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(device => device.kind === 'audioinput');
      setAudioDevices(audioInputs);
    } catch (err) {
      console.error("Fehler beim Laden der Audiogeräte:", err);
    }
  };

  useEffect(() => {
    loadAudioDevices(true);
    const handleDeviceChange = () => loadAudioDevices(false);
    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
    return () => {
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
    (window as any).__praxisSttKey = null;
    setVertexApiKey('');
    setSttKeyJson(null);
    setMenuOpen(false);
  };

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
  }, []);

  // Menü schließen bei Klick außerhalb / Esc
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    window.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('mousedown', onDown); window.removeEventListener('keydown', onKey); };
  }, [menuOpen]);





  // Detect modality template based on text keywords (1:1 from EXE Version)
  const detectTemplate = (text: string): string => {
    const textLower = text.toLowerCase();
    
    // Combined / complex templates check
    if (textLower.includes("becken") || textLower.includes("wecken") || textLower.includes("pelvis")) {
      if (textLower.includes("tep") || textLower.includes("prothese") || textLower.includes("endoprothese") || textLower.includes("h-tep")) {
        if (textLower.includes("beidseits") || textLower.includes("bds") || textLower.includes("beide")) {
          return "beckenübersicht_mit_beidseitiger_hüftprothese";
        } else {
          return "beckenübersicht_mit_einseitiger_hüftprothese";
        }
      } else if (textLower.includes("hüfte") || textLower.includes("hüftgelenk") || textLower.includes("hfte") || textLower.includes("hft")) {
        return "beckenübersicht_und_hüfte";
      }
    }

    // ── Full-spine detection (expanded keywords) ──────────────────────────────
    // Covers: "Wirbelsäulen ganz Aufnahme", "Ganzwirbelsäule", "Gesamtwirbelsäule",
    //         "zerviko-thorako-lumbal", "cervico-thoracal-lumbal", "toracco lumbal", etc.
    const hasCervical  = textLower.includes("hws") || textLower.includes("hwk") || /\bhw\b/.test(textLower) || textLower.includes("zervik")
                   || textLower.includes("zerviko") || textLower.includes("cervik")
                   || textLower.includes("cervico") || textLower.includes("halswirbel");
    const hasThoracic  = textLower.includes("bws") || textLower.includes("thorakal")
                      || textLower.includes("thorako") || textLower.includes("thoraco")
                      || textLower.includes("toracco") || textLower.includes("brustwirbel");
    const hasLumbar    = textLower.includes("lws") || textLower.includes("lumbal")
                      || textLower.includes("lendenwirbel");
    const isFullSpineExam = textLower.includes("ganzaufnahme")
                      || textLower.includes("gesamtwirbel")
                      || textLower.includes("ganzwirbel")
                      || (textLower.includes("ganz") && textLower.includes("wirbels"))
                      || (textLower.includes("gesamt") && textLower.includes("wirbel"))
                      || (textLower.includes("komplett") && textLower.includes("wirbel"));

    // Ganzaufnahme a.-p. hat eigenes Template — vor wirbelsäule_gesamt prüfen!
    if (textLower.includes("ganzaufnahme") && !hasCervical) {
      return "ganzaufnahme_der_wirbelsäule_a-p";
    }

    if (isFullSpineExam || (hasCervical && hasThoracic && hasLumbar)) {
      return "wirbelsäule_gesamt";
    }
    if (hasCervical && hasLumbar) {
      return "hws_und_lws";
    }
    if (hasCervical && hasThoracic) {
      return "wirbelsäule_gesamt";
    }
    if (/\bhw\b/.test(textLower)) {
      // STT schreibt HWS oft nur als "HW" (z.B. "HW ist unauffällig")
      return "halswirbelsäule_in_2_ebenen";
    }
    // ─────────────────────────────────────────────────────────────────────────

    if (textLower.includes("hws") && textLower.includes("lws")) {
      if (textLower.includes("bws")) {
        return "wirbelsäule_gesamt";
      } else {
        return "hws_und_lws";
      }
    }
    
    if (textLower.includes("sono") || textLower.includes("schall") || textLower.includes("ultraschall") || textLower.includes("duplex")) {
      // ── Schulter-Sonographie (vor allem anderen prüfen!) ──
      if (textLower.includes("schulter") || textLower.includes("supraspinatus") || textLower.includes("infraspinatus") || textLower.includes("bizepssehne") || textLower.includes("rotatorenmanschette") || textLower.includes("subacromial") || textLower.includes("subakromial") || textLower.includes("bursitis subacromialis")) {
        return "sonografie_schultergelenk";
      }
      if (textLower.includes("bauchdeck") || textLower.includes("hernie") || textLower.includes("rektusdiastase") || textLower.includes("rectusdiastase")) {
        return "sonografie_bauchdecke";
      }
      if (textLower.includes("abdomen") || textLower.includes("bauch") || textLower.includes("abd")) {
        if (textLower.includes("weiblich")) {
          return "sonografie_abdomen_weiblich";
        } else {
          return "sonografie_abdomen_maennlich";
        }
      }
      if (textLower.includes("carotis") || textLower.includes("halsgef") || textLower.includes("halsart") || textLower.includes("extracran") || textLower.includes("commun")) {
        return "sonografie_halsgefaesse";
      }
      if (textLower.includes("varizen") || textLower.includes("variko") || textLower.includes("variz")) {
        return "varizensonografie";
      }
      if (textLower.includes("mamma")) {
        if (textLower.includes("sono") || textLower.includes("schall") || textLower.includes("ultraschall") || textLower.includes("mammasono")) {
          return "mammasonographie_beidseits";
        }
        return "mammographie_beidseits";
      }
      if (textLower.includes("beinven") || textLower.includes("v. femoralis") || textLower.includes("poplitea") || textLower.includes("fibularis") || textLower.includes("venen")) {
        return "sonografie_beinvenen";
      }
      if (textLower.includes("muskel") || textLower.includes("muskul") || textLower.includes("gastrocnem") || textLower.includes("soleus") || textLower.includes("quadriceps") || textLower.includes("ischio") || textLower.includes("faserriss")) {
        if (textLower.includes("dorsal") && textLower.includes("unterschenkel")) {
          return "sonografie_dorsaler_unterschenkel";
        }
        if (textLower.includes("gastrocnem")) {
          return "sonografie_gastrocnemius_medialis";
        }
        if (textLower.includes("dorsal") && textLower.includes("oberschenkel")) {
          return "sonografie_dorsaler_oberschenkel";
        }
        if (textLower.includes("anterior") && textLower.includes("oberschenkel")) {
          return "sonografie_anteriorer_oberschenkel";
        }
        return "sonografie_weichteile";
      }
      if (textLower.includes("halsweichteil") || textLower.includes("hals-weichteil")) {
        return "sonografie_halsweichteile";
      }
      if (textLower.includes("schilddr") || textLower.includes("sd-")) {
        return "sonografie_schilddrüse";
      }
      if (textLower.includes("weichteil")) {
        return "sonografie_weichteile";
      }
      if (textLower.includes("medianus") || textLower.includes("karpal") || textLower.includes("cts")) {
        return "sonografie_nerv_medianus";
      }
      if (textLower.includes("ulnaris") || textLower.includes("sulcus") || textLower.includes("loge") || textLower.includes("guyon")) {
        return "sonografie_nerv_ulnaris";
      }
      if (textLower.includes("radialis") || textLower.includes("supinator") || textLower.includes("frohse") || textLower.includes("wartenberg")) {
        return "sonografie_nerv_radialis";
      }
      if (textLower.includes("plexus")) {
        return "sonografie_plexus_brachialis";
      }
      if (textLower.includes("nerv") || textLower.includes("neuro") || textLower.includes("suralis") || textLower.includes("peroneus") || textLower.includes("tibialis")) {
        return "sonografie_nerv_allgemein";
      }
      if (textLower.includes("unterschenkel")) {
        return "sonografie_unterschenkel";
      }
      return "sonografie_allgemein";
    }

    if (textLower.includes("dvt") || textLower.includes("volumentomographie")) {
      if (textLower.includes("oberkiefer") || textLower.includes("ok")) {
        return "dvt_oberkiefer";
      }
      if (textLower.includes("unterkiefer") || textLower.includes("uk")) {
        return "dvt_unterkiefer";
      }
      return "dvt_oberkiefer";
    }

    if (textLower.includes("orbita") || textLower.includes("orbitae")) {
      return "orbita_pa_aufnahme";
    }

    if (textLower.includes("calcaneus") || textLower.includes("kalkaneus") || textLower.includes("ferse")) {
      if (textLower.includes("seitlich") && !textLower.includes("2 ebenen")) {
        return "calcaneus_seitlich";
      }
      return "calcaneus_in_2_ebenen";
    }

    if (textLower.includes("mortise")) {
      return "sprunggelenk_mortise_view";
    }

    if (textLower.includes("gehaltene")) {
      return "sprunggelenk_gehaltene_aufnahmen";
    }

    if ((textLower.includes("sprunggelenk") || textLower.includes("osg")) && (textLower.includes("fuß") || textLower.includes("fuss"))) {
      return "sprunggelenk_mit_fuss";
    }

    if (textLower.includes("naviculare") || textLower.includes("skaphoid") || textLower.includes("scaphoid") || textLower.includes("kahnbein")) {
      return "naviculareserie";
    }

    if (textLower.includes("opg") || textLower.includes("zahnröntgen") || textLower.includes("zahnstatus") || textLower.includes("orthopantomogramm")) {
      return "orthopantomogramm_des_kiefer-_und_gesichtsschädels";
    }

    if (textLower.includes("dexa") || textLower.includes("knochendichte") || textLower.includes("densitometrie") || textLower.includes("odm")) {
      return "knochendichtemessung_dexa";
    }

    if (textLower.includes("mamma")) {
      // Mammasonographie (Ultraschall) vs Mammographie (Röntgen) — 'mamma' als Trigger,
      // denn 'Mammasonographie' enthält 'mamma' aber NIE 'mammo' (v2.10.13-Fix)
      
      if (textLower.includes("sono") || textLower.includes("schall") || textLower.includes("ultraschall") || textLower.includes("mammasono")) {
        return "mammasonographie_beidseits";
      }
      return "mammographie_beidseits";
    }

    if (textLower.includes("fernröntgen") || textLower.includes("fern-röntgen") || textLower.includes("frs")) {
      return "schädelfernröntgen";
    }

    if (textLower.includes("visa") || textLower.includes("wiederschluck") || textLower.includes("videokinematographie")) {
      // Peters Diktat-Kürzel: "Visa" = Videokinematographie des Schluckaktes (Konvention 3x)
      return "videokinematographie_schluckakt";
    }

    if (textLower.includes("breischluck") || textLower.includes("ösophagus") || textLower.includes("schluckakt")) {
      if (textLower.includes("videokinematographie") || textLower.includes("video") || textLower.includes("vis-a-vis") || textLower.includes("wiederschluck") || textLower.includes("visa")) {
        return "videokinematographie_schluckakt";
      }
      if (textLower.includes("magen") || textLower.includes("duodenum") || textLower.includes("magenduodenum")) {
        return "oesophagus_magenduodenum_doppelkontrast";
      }
      return "durchleuchtung:_ösophagus-breischluck";
    }
    if (textLower.includes("mdp") || textLower.includes("magen-darm") || textLower.includes("magen")) {
      return "durchleuchtung:_magen-darm-passage_mdp";
    }
    if (textLower.includes("urogramm") || textLower.includes("ivu") || textLower.includes("ivp")) {
      return "intravenöses_urogramm";
    }
    if (textLower.includes("phlebographie") || textLower.includes("phlebo")) {
      if (textLower.includes("press") || textLower.includes("aszendier") || textLower.includes("aufsteigend")) {
        return "aszendierende_pressphlebographie";
      }
      return "beinphlebographie";
    }
    if (textLower.includes("hsg") || textLower.includes("hysterosalpingographie")) {
      return "hysterosalpingographie";
    }

    const mappings: [string, string[]][] = [
      ["beckenübersicht_stehend", ["becken", "wecken", "pelvis"]],
      ["varizensonografie", ["varizen", "variko", "variz"]],
      ["schulterprothese", ["schulterprothese", "schulter-tep", "schulter tep", "schulterendoprothese"]],
      ["daumensattelprothese", ["daumensattel", "sattelprothese", "sattelgelenk"]],
      ["knieprothese", ["knieprothese", "knie-tep", "knie tep", "knieendoprothese"]],
      ["hüftprothese", ["hüftprothese", "hüft-tep", "hüft tep", "hüftendoprothese", "h-tep"]],
      ["mr_des_gehirnschädels:", ["mrt schädel", "mr schädel", "mrt kopf", "mr kopf", "mrt gehirn", "mr gehirn"]],
      ["mr_der_lendenwirbelsäule:", ["mrt lws", "mr lws"]],
      ["mr_der_halswirbelsäule:", ["mrt hws", "mr hws"]],
      ["mr_des_kniegelenkes:", ["mrt knie", "mr knie"]],
      ["mr_des_schultergelenkes:", ["mrt schulter", "mr schulter"]],
      ["mr_handgelenk:", ["mrt handgelenk", "mr handgelenk"]],
      ["mr_hüftgelenk:", ["mrt hüfte", "mr hüfte", "mrt hüftgelenk", "mr hüftgelenk"]],
      ["cct:", ["cct", "craniales ct", "ct kopf", "ct schädel", "ct gehirn"]],
      ["ct_thorax:", ["ct thorax", "ct lunge", "ct brustkorb"]],
      ["ct_abdomen:", ["ct abdomen", "ct bauch"]],
      ["lendenwirbelsäule_in_2_ebenen", ["lws", "lumbal", "lendenwirbel"]],
      ["halswirbelsäule_in_2_ebenen", ["hws", "cervical", "halswirbel"]],
      ["brustwirbelsäule_in_2_ebenen", ["bws", "thorakal", "brustwirbel"]],
      // v3.2: knöcherner Hemithorax VOR Thorax ("Hemithorax" enthält "thorax")
      ["knöcherner_hemithorax", ["hemithorax", "rippenaufnahme", "rippenserie", "rippen in 2"]],
      ["thorax_in_2_ebenen", ["thorax", "torax", "lunge", "pulmo", "brustkorb", "herz", "rö-th", "rö thor"]],
      ["handgelenk_in_2_ebenen", ["handgelenk"]],
      ["finger_in_2_ebenen", ["finger", "daumen", "kleinfinger", "zeigefinger", "mittelfinger", "ringfinger"]],
      ["hand_in_2_ebenen", ["hand", "mittelhand"]],
      ["ellbogengelenk_in_2_ebenen", ["ellbogen", "ellenbogen"]],
      ["unterarm_in_2_ebenen", ["unterarm", "radius", "ulna"]],
      ["oberarm_in_2_ebenen", ["oberarm", "humerus"]],
      ["schultergelenk_in_2_ebenen", ["schulter", "omarthrose"]],
      ["sprunggelenk_in_2_ebenen", ["sprunggelenk", "osg", "usg", "malleolar", "malleolus"]],
      ["fuß_in_2_ebenen", ["fuß", "fuss", "mittelfuß", "vorfuß", "rückfuß"]],
      ["zehe_in_2_ebenen", ["zehe", "großzehe"]],
      ["kniegelenk_in_2_ebenen", ["knie", "gonarthrose"]],
      ["hüftgelenk_in_2_ebenen", ["hüfte", "hft", "coxarthrose"]]
    ];

    for (const [key, keywords] of mappings) {
      for (const kw of keywords) {
        if (textLower.includes(kw)) {
          return key;
        }
      }
    }

    for (const key of Object.keys(templates)) {
      const searchKey = key.replace(/_/g, ' ');
      if (textLower.includes(searchKey)) {
        return key;
      }
    }

    return "allgemein";
  };

  // Run full-text search simulation in the local report list

  // ─────────────────────────────────────────────────────────────────────────
  // GOOGLE CLOUD STT — Service-Account (rakscribe-stt@) → JWT → Bearer Token
  // Primary STT (beste medizinische Erkennung, $10 GCP-Credit). Whisper = Fallback.
  // ─────────────────────────────────────────────────────────────────────────
  const sttTokensRef = useRef<{ [scope: string]: { token: string; expiry: number } }>({});

  const toBase64Url = (buffer: ArrayBuffer): string =>
    btoa(String.fromCharCode(...new Uint8Array(buffer)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

  const signJwt = async (payload: object, privateKeyPem: string): Promise<string> => {
    const header = { alg: 'RS256', typ: 'JWT' };
    const pemBody = privateKeyPem
      .replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\n|\r/g, '');
    const derBinary = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
    const cryptoKey = await crypto.subtle.importKey(
      'pkcs8', derBinary.buffer as ArrayBuffer,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false, ['sign']
    );
    const enc = new TextEncoder();
    const headerB64  = toBase64Url(enc.encode(JSON.stringify(header)).buffer as ArrayBuffer);
    const payloadB64 = toBase64Url(enc.encode(JSON.stringify(payload)).buffer as ArrayBuffer);
    const signingInput = `${headerB64}.${payloadB64}`;
    const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', cryptoKey, enc.encode(signingInput));
    return `${signingInput}.${toBase64Url(sig)}`;
  };

  // Get a valid Bearer token for the STT service account (cached, auto-refresh)
  const getGoogleBearerToken = async (keyJson: any, scope: string): Promise<string> => {
    const now = Math.floor(Date.now() / 1000);
    const cached = sttTokensRef.current[scope];
    if (cached && cached.expiry > now + 60) {
      return cached.token;
    }
    const jwt = await signJwt({
      iss: keyJson.client_email,
      scope: scope,
      aud: 'https://oauth2.googleapis.com/token',
      iat: now,
      exp: now + 3600,
    }, keyJson.private_key);
    const resp = await fetchWithRetry('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
    }, 30_000, 3);
    const data = await resp.json();
    if (!data.access_token) throw new Error('Google OAuth Fehler: ' + JSON.stringify(data));
    sttTokensRef.current[scope] = {
      token: data.access_token,
      expiry: now + (data.expires_in || 3600)
    };
    return data.access_token;
  };

  const buildSttAuth = async (): Promise<{ url: string; headers: Record<string, string> }> => {
    if (!sttKeyJson) {
      throw new Error('STT-Schluessel nicht geladen (stt-key.b64 / stt-key.txt fehlt).');
    }
    const token = await getGoogleBearerToken(sttKeyJson, 'https://www.googleapis.com/auth/cloud-platform');
    return {
      url: 'https://speech.googleapis.com/v1/speech:recognize',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    };
  };

  const blobToBase64 = (wavBlob: Blob): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
      reader.onerror = () => reject(new Error('Fehler beim Lesen der Audiodatei.'));
      reader.readAsDataURL(wavBlob);
    });

  // Chunk-Transkription (7s-Chunks, latest_long)
  const transcribeWithGoogle = async (wavBlob: Blob): Promise<string> => {
    const { url, headers } = await buildSttAuth();
    setStatusText('Transkribiere (Google Cloud STT)...');
    const base64Data = await blobToBase64(wavBlob);
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        config: {
          encoding: 'LINEAR16', sampleRateHertz: 16000, languageCode: 'de-DE',
          enableAutomaticPunctuation: true, model: 'latest_long', useEnhanced: true,  // WER-Test 03.09.: short verliert Material
          speechContexts: [{ phrases: MEDICAL_PHRASES, boost: 15.0 }],
        },
        audio: { content: base64Data },
      }),
    }, 120_000, 3);
    const data = await response.json();
    if (data.error) throw new Error(data.error.message || 'Google STT Fehler.');
    const results = data.results || [];
    return results.map((r: any) => r.alternatives[0].transcript).join(' ');
  };

  // FULL-AUDIO Transkription (v2.9.10): chirp_3 via STT v2 (Location eu).
  // WER-Test 04.09.: chirp_3 = 2,4% (auch bei Echo/Daempfung) vs latest_long = 16,7%.
  // Kein Phrasen-Boost in chirp_3, dafuer Dragon-Niveau. Segmentierung >60s:
  // 50s-Segmente + 4s Rueckhoeren, Ueberlappung per Wortvergleich gestitched.
  const chirpTokenCacheRef = useRef<{ token: string; exp: number } | null>(null);
  const getSttAccessToken = async (): Promise<string> => {
    const now = Date.now() / 1000;
    if (chirpTokenCacheRef.current && chirpTokenCacheRef.current.exp > now + 120) {
      return chirpTokenCacheRef.current.token;
    }
    if (!sttKeyJson) throw new Error('STT-Schluessel nicht geladen.');
    const token = await getGoogleBearerToken(sttKeyJson, 'https://www.googleapis.com/auth/cloud-platform');
    chirpTokenCacheRef.current = { token, exp: now + 3000 };
    return token;
  };

  // v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation). A/B echte + synthetische Diktate:
// Termini 41/47 → 45/47 (flachbogig, Cobb-Winkel, Mammasonographie, Discopathiezeichen, Fibroostosen,
// Rhizarthrose, Arthro-Broström). BEWUSST KURZ — die 692er-Liste verschlechterte chirp_3 (25/29 statt 26/29).
const CHIRP_PHRASES: string[] = [
  "flachbogig",
  "flachbogige Skoliose",
  "rechtskonvex",
  "linkskonvex",
  "Cobb-Winkel",
  "Th1",
  "Th2",
  "Th3",
  "Th4",
  "Th5",
  "Th6",
  "Th7",
  "Th8",
  "Th9",
  "Th10",
  "Th11",
  "Th12",
  "Schmorlsche Impressionen",
  "Edgren-Vaino-Zeichen",
  "Morbus Scheuermann",
  "Osteochondrose",
  "Spondylosis deformans",
  "Spondylarthrose",
  "Unkovertebralgelenksarthrose",
  "Facettengelenksarthrose",
  "Discopathiezeichen",
  "Diskopathie",
  "Antelisthese",
  "Retrolisthese",
  "Neoarthrosis interspinosa",
  "kyphotische Fehlhaltung",
  "Streckhaltung",
  "Fibroostosen",
  "Kellgren und Lawrence",
  "Gonarthrose",
  "Coxarthrose",
  "Omarthrose",
  "Rhizarthrose",
  "Retropatellararthrose",
  "Femorotibialkompartiment",
  "Scaphoidtaille",
  "Kahnbeintaille",
  "Collum chirurgicum",
  "Radiusköpfchen",
  "Humeruskopfhochstand",
  "Garden",
  "Supraspinatussehne",
  "Infraspinatussehne",
  "Subscapularissehne",
  "lange Bizepssehne",
  "Tenosynovitis",
  "Tendinopathie",
  "Tendinosis calcarea",
  "Begleitbursitis",
  "Enthesiopathie",
  "Plantarfaszie",
  "Arthro-Broström",
  "Mammasonographie",
  "BI-RADS",
  "Morbus Mondor",
  "Sulcus nervi ulnaris",
  "Nervus ulnaris",
  "Musculus anconeus epitrochlearis",
  "Hoffmann-Tinel-Zeichen",
  "Kiloh-Nevin",
  "Hypothenarmuskulatur",
  "faszikulär",
  "Thorax p.a.",
];

const chirp3Recognize = async (token: string, wavB64: string): Promise<string> => {
    const url = 'https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize';
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        config: {
          languageCodes: ['de-DE'],
          model: 'chirp_3',
          autoDecodingConfig: {},
          features: { enableAutomaticPunctuation: true },
          adaptation: { phraseSets: [{ inlinePhraseSet: { phrases: CHIRP_PHRASES.map(value => ({ value, boost: 10 })) } }] },
        },
        content: wavB64,
      }),
    }, 120_000, 3);
    const data = await response.json();
    if (data.error) throw new Error(data.error.message || 'chirp_3 Fehler.');
    const results = data.results || [];
    return results.map((r: any) => r.alternatives[0].transcript).join(' ');
  };

  const stitchOverlaps = (a: string, b: string, window = 14): string => {
    const aw: string[] = a.split(' ');
    const bw: string[] = b.split(' ');
    let best = 0;
    for (let L = Math.min(window, aw.length, bw.length); L > 0; L--) {
      const tail = aw.slice(-L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
      const head = bw.slice(0, L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
      if (tail.filter((w, i) => w === head[i]).length >= Math.floor(L * 0.8)) { best = L; break; }
    }
    return best ? a + ' ' + bw.slice(best).join(' ') : a + ' ' + b;
  };

  const transcribeFullAudioWithGoogle = async (wavBlob: Blob): Promise<string> => {
    const token = await getSttAccessToken();
    const base64Data = await blobToBase64(wavBlob);

    // Duration: 16000 samples/s * 2 bytes/sample = 32000 bytes/s (base64 ~4/3)
    const binarySize = Math.floor(base64Data.length * 3 / 4);
    const estimatedDurationSec = binarySize / 32000;
    console.log(`[FULL-AUDIO] ${binarySize} bytes, ~${estimatedDurationSec.toFixed(1)}s`);

    // <=59s: EIN chirp_3-Request
    if (estimatedDurationSec <= 59) {
      setStatusText('Volltranskription läuft (chirp_3, komplettes Diktat)...');
      return await chirp3Recognize(token, base64Data);
    }

    // >60s: Segmentierung 50s + 4s Rueckhoeren, dann Overlap-Stitch
    console.log('[FULL-AUDIO] chirp_3 Segmentierung (>60s)');
    setStatusText('Volltranskription läuft (langes Diktat, chirp_3, bitte warten)...');
    // WAV decodieren → Float32 → s16le-PCM
    const arrayBuffer = await wavBlob.arrayBuffer();
    const ctxTemp = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    const audioBuf = await ctxTemp.decodeAudioData(arrayBuffer);
    ctxTemp.close();
    const f32 = audioBuf.getChannelData(0);
    const s16 = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      const s = Math.max(-1, Math.min(1, f32[i]));
      s16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    const SR = 16000, SEG = 50 * SR, OV = 4 * SR;
    const texts: string[] = [];
    let start = 0;
    while (start < s16.length) {
      const end = Math.min(start + SEG, s16.length);
      const seg = s16.slice(start, end);
      // Int16 → WAV-Container
      const wav = new ArrayBuffer(44 + seg.length * 2);
      const view = new DataView(wav);
      const ws = (o: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
      ws(0, 'RIFF'); view.setUint32(4, 36 + seg.length * 2, true); ws(8, 'WAVE');
      ws(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
      view.setUint16(22, 1, true); view.setUint32(24, SR, true);
      view.setUint32(28, SR * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
      ws(36, 'data'); view.setUint32(40, seg.length * 2, true);
      new Int16Array(wav, 44).set(seg);
      const b64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
        reader.onerror = () => reject(new Error('WAV-Encoding fehlgeschlagen.'));
        reader.readAsDataURL(new Blob([wav], { type: 'audio/wav' }));
      });
      texts.push(await chirp3Recognize(token, b64));
      if (end >= s16.length) break;
      start = end - OV;
    }
    let full = texts[0];
    for (let i = 1; i < texts.length; i++) full = stitchOverlaps(full, texts[i]);
    return full;
  };

  // Wrapper: Google primary, Whisper fallback (lokaler Server auf Praxis-PC)
  const transcribeAudio = async (wavBlob: Blob, isFull: boolean): Promise<string> => {
    try {
      return isFull ? await transcribeFullAudioWithGoogle(wavBlob) : await transcribeWithGoogle(wavBlob);
    } catch (sttErr: any) {
      console.warn('[STT] Google fehlgeschlagen, Whisper-Fallback:', sttErr.message);
      return await transcribeWithWhisper(wavBlob);
    }
  };

  // Beliebige Audiodatei (OGG/MP3/WAV) → mono 16kHz WAV (für Google STT)
  const decodeFileToWavBlob = async (file: File | Blob): Promise<Blob> => {
    const arrayBuffer = await file.arrayBuffer();
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const decodedAudio = await audioContext.decodeAudioData(arrayBuffer);
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
    const resampled = downsampleBuffer(channelData, decodedAudio.sampleRate, 16000);
    if (resampled.length === 0) {
      await audioContext.close();
      throw new Error('Audiodatei ist leer oder zu kurz.');
    }
    const ctxWav = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    const audioBuf = ctxWav.createBuffer(1, resampled.length, 16000);
    audioBuf.copyToChannel(resampled as any, 0);
    const wavBlob = audioBufferToWav(audioBuf);
    ctxWav.close();
    await audioContext.close();
    return wavBlob;
  };

  const transcribeWithWhisper = async (audioBlob: Blob): Promise<string> => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.ogg');

    console.log('[WHISPER] Sende Audio an lokalen Whisper-Server...');
    const response = await fetchWithRetry('http://localhost:8765/whisper', {
      method: 'POST',
      body: formData,
    }, 120_000, 3);

    const data = await response.json();
    if (data.error) {
      throw new Error('Whisper STT Fehler: ' + data.error);
    }
    const text = (data.text || '').trim();
    console.log(`[WHISPER] Fertig in ${data.elapsed_seconds}s: "${text.substring(0, 100)}..."`);
    return text;
  };

  // ─────────────────────────────────────────────────────────────────────────

  // Correct STT errors using Gemini Flash (standalone, no external dependency)
  const correctTranscriptionWithGemini = async (rawTextIn: string): Promise<string> => {
    // v3.1: deterministische Fehlhör-Korrektur zuerst (misheard_words.json, mode 'auto')
    const rawText = applyMisheard(rawTextIn, MISHEARD_COMPILED);
    if (rawText !== rawTextIn) console.log(`[MISHEARD] auto-korrigiert: "${rawTextIn.substring(0, 120)}" → "${rawText.substring(0, 120)}"`);
    if (!vertexApiKey) {
      return rawText; // No LLM available, return raw
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    const correctionPrompt = `Du bist ein medizinischer Lektor für radiologische Diktate. Korrigiere Spracherkennungsfehler.

${MISHEARD_PROMPT_BLOCK}

## WICHTIGE REGELN:
1. Behalte ALLE Pathologien bei — verliere NIEMALS eine Diagnose
2. "mit" + unklarer Begriff nach Sehnen-Untersuchung → "mit Begleitbursitis"
3. VERÄNDERE KEINE ZAHLEN! "18 mm" bleibt "18 mm", nicht "1,8 mm". "15 mm²" bleibt "15 mm²". Messwerte sind heilig.
4. VERÄNDERE KEINE ANATOMISCHEN LOKALISATIONEN! "axillär" bleibt "axillär", nicht "lateral". 
5. KORRIGIERE NUR ECHTE SPRACHERKENNUNGSFEHLER (Unsinnswörter, falsch gehörte Silben). Ein korrekt erkannter Fachbegriff bleibt WÖRTLICH stehen — NIEMALS durch einen \"präziseren\" oder anderen Fachbegriff ersetzen (\"Gelenksarthrose\" bleibt \"Gelenksarthrose\", NICHT \"Uncovertebralarthrose\"; \"Diskopathie\" bleibt \"Diskopathie\"). NIEMALS zwei diktierte Befunde zusammenziehen (\"flachbogige Skoliose nach links, kyphotische Fehlhaltung\" bleiben ZWEI Befunde).
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

    try {
      const response = await fetchWithRetry(url, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          contents: [{
            role: "user",
            parts: [{ text: correctionPrompt }]
          }],
          generationConfig: { temperature: 0.0, thinkingConfig: { thinkingBudget: 0 } }
        })
      }, 120_000, 3);

      const data = await response.json();
      if (data.error) {
        console.warn('[CORRECT] Gemini correction error:', data.error.message);
        return rawText;
      }

      const corrected = joinGeminiText(data).trim();
      console.log(`[CORRECT] Raw: "${rawText.substring(0, 100)}..."`);
      console.log(`[CORRECT] Corrected: "${corrected.substring(0, 100)}..."`);
      // v2.11.1: abgeschnittene/verkürzte Korrektur NIE übernehmen (sonst fehlt der Diktat-Rest stillschweigend)
      if (!corrected || !geminiFinishedOk(data) || corrected.length < rawText.trim().length * 0.6) {
        console.warn('[CORRECT] Korrektur unvollständig/verkürzt — verwende Rohtext');
        return rawText;
      }
      return corrected;
    } catch (e: any) {
      console.warn('[CORRECT] Correction failed:', e.message);
      return rawText;
    }
  };

  // Call Gemini API to Structure the Transcript (Aligned 1:1 with EXE parameters)
  const stripCodeFences = (text: string): string =>
    text.replace(/^```[a-zA-Z]*\s*\n?/, '').replace(/\n?```\s*$/, '').trim();

  const callGeminiLLM = async (rawText: string, templateBody: string, regionName: string, examples: string, normalErgebnis = 'Unauffälliger Befund.'): Promise<string> => {
    if (!vertexApiKey) {
      throw new Error("Es ist kein Vertex AI API-Key konfiguriert. Bitte in den Einstellungen eintragen.");
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    setStatusText("Strukturiere mit Gemini...");

    // v2.10.13 (K3-Review Befund 2): Der LLM-Pfad bekommt die KANONISCHE Bezeichnung
    // (display_name, inkl. "(Allgemein)"), damit die "(Allgemein)"-Ausnahme im
    // Gen-Prompt ECHT feuern kann — bei pathologischen (Allgemein)-Diktaten leitet
    // das LLM die Überschrift aus dem Diktat (ohne Befundworte), statt den
    // Volltext als Titel zu bekommen. Der Bypass-Pfad (ohne LLM) bleibt bei
    // deriveUntersuchungsTitel — dort muss der Titel deterministisch entstehen.
    let promptText = stripPromptMarker(systemPrompt)
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
    }, 120_000, 3);

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error.message || "Gemini API Fehler.");
    }

    let outputText = stripCodeFences(joinGeminiText(data));
    // v2.11.1: unvollständige Antwort (kein ## Ergebnis / abgebrochen) → EINMAL neu anfordern, sonst Fehler statt Halb-Befund
    if (!isCompleteReport(outputText) || !geminiFinishedOk(data)) {
      console.warn('[GEN] Befund unvollständig — zweiter Versuch');
      const r2 = await fetchWithRetry(url, { method: 'POST', headers: authHeaders, body: lastGenBody }, 120_000, 2);
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
  const validateReportConsistency = async (rawDictation: string, generatedReport: string): Promise<string> => {
    if (!vertexApiKey) {
      return generatedReport; // No LLM available, skip validation
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    const validationPrompt = `Du bist ein radiologischer Qualitätskontrolleur. Du erhältst das ursprüngliche Diktat und den daraus generierten Befund. Prüfe STRENG:

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
10. DIAGNOSEBEGRIFFE NIE ERSETZEN: Jede diktierte Diagnose bleibt im Ergebnis in der DIKTIERTEN Wortwahl als eigener Punkt (\"Gelenksarthrose C3 bis C5\" bleibt so — NICHT \"Facettengelenksarthrose\" oder \"Uncovertebralarthrose\"). \"Bild wie bei [Diagnose]\" bleibt \"Bild wie bei\", NIE zurück zu \"vereinbar mit\". Diktiertes \"Verdacht auf [Diagnose]\" bleibt WÖRTLICH \"Verdacht auf [Diagnose]\" (NIE \"Bild wie bei\"); die diktierte Seite bleibt in seitenbezogenen Ergebnis-Punkten stehen. Messwerte wie CSA gehören NICHT ins Ergebnis. AUSNAHME zur Wortwahl: Steht im generierten Ergebnis \"Bild wie bei [Diagnose]\", ist das die PFLICHT-Umsetzung von diktiertem \"vereinbar mit\"/\"kompatibel mit\" — NIEMALS entfernen, sonst wird aus einer Verdachtsdiagnose eine gesicherte.
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

    try {
      console.log('[VALIDATE] Prüfe Befund-Konsistenz...');
      const response = await fetchWithRetry(url, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: validationPrompt }] }],
          generationConfig: { temperature: 0.0, thinkingConfig: { thinkingBudget: 0 } }
        })
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
    } catch (e: any) {
      console.warn('[VALIDATE] Validation failed:', e.message);
      return generatedReport;
    }
  };

  // v3.2: Befund aus dem (korrigierten) Diktat — dieselbe Kette wie die EXE (RaKScribe.py _befund_fuer_segment):
  // Diktat mit mehreren Regionen ("Schulter rechts … Ellbogen rechts …") → je Region ein eigener Befund mit eigenem
  // Template und eigenem Ergebnis (parallel), danach Ergebnis deterministisch nummeriert.
  const befundFuerSegment = async (seg: string): Promise<string> => {
    const detectedKey = detectTemplate(seg);
    const activeTemplate = templates[detectedKey] || templates['allgemein'] || ALLGEMEIN_FALLBACK;
    if (detectedKey === 'allgemein') {
      console.warn('[TEMPLATE] Region nicht erkannt — verwende Allgemein-Template');
      setStatusText('⚠️ Region nicht erkannt — Allgemein-Template wird verwendet');
    }

    // RAG-Bypass-Shortcut für reine Normalbefunde (1:1 wie EXE)
    if (isPureNormalFinding(seg, DISPLAY_NAMES) && detectedKey !== 'allgemein') {
      console.log(`[BYPASS] Normalbefund erkannt. Generiere direkt aus Template.`);
      // v3.2 (Peter 05.10.): Ergebnis = Normal-Ergebnis der Untersuchung (+ Seite) — NIE das Diktat abschreiben
      const ergebnis = ergebnisMitSeite(activeTemplate.ergebnis || '', seg);
      const tplLines = activeTemplate.body.split('\n');
      const tplTitle = titelMitSeite(deriveUntersuchungsTitel(seg, (tplLines[0] || '').trim().replace(/:$/, '')), seg);
      const tplBody = tplLines.slice(1).join('\n');
      return `## ${tplTitle}\n\n## Befund\n${tplBody}\n\n## Ergebnis\n${ergebnis}`;
    }

    if (!vertexApiKey) {
      throw new Error("KI-Strukturierung nicht möglich: Es ist kein Vertex AI API-Key konfiguriert.");
    }
    const structuredText = await callGeminiLLM(seg, activeTemplate.body, activeTemplate.display_name, '', activeTemplate.ergebnis || 'Unauffälliger Befund.');
    // Step 3: Konsistenz-Validierung gegen das Diktat
    setStatusText('Validiere Befund-Konsistenz...');
    const validatedReport = await validateReportConsistency(seg, structuredText);
    return nachbearbeiten(validatedReport);
  };

  const befundAusDiktat = async (text: string): Promise<string> => {
    const segmente = splitRegionen(text);
    if (segmente.length > 1) {
      console.log(`[MULTI] ${segmente.length} Regionen: ${segmente.map(x => x.slice(0, 40)).join(' | ')}`);
      setStatusText(`Strukturiere ${segmente.length} Regionen mit Gemini...`);
    }
    const teile = await Promise.all(segmente.map(befundFuerSegment));
    return befundeZusammenfuegen(teile);
  };

  const testGeminiAPI = async (): Promise<void> => {
    if (!vertexApiKey) {
      throw new Error("Es ist kein Vertex AI API-Key konfiguriert.");
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: authHeaders,
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
  };

  // Helper function to process the next chunk of recorded audio
  const processNextAudioChunk = async () => {
    const currentChunks = audioChunksRef.current;
    const lastProcessedIndex = lastProcessedIndexRef.current;
    
    if (currentChunks.length > lastProcessedIndex) {
      const segmentChunks = currentChunks.slice(lastProcessedIndex);
      lastProcessedIndexRef.current = currentChunks.length;
      
      const merged = mergeFloat32Arrays(segmentChunks);
      const currentSampleRate = actualSampleRateRef.current;
      const resampled = downsampleBuffer(merged, currentSampleRate, 16000);
      
      if (resampled.length === 0) return;
      
      const ctxTemp = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const audioBuf = ctxTemp.createBuffer(1, resampled.length, 16000);
      audioBuf.copyToChannel(resampled as any, 0);
      const wavBlob = audioBufferToWav(audioBuf);
      ctxTemp.close();
      
      const chunkIdx = chunkTranscriptsRef.current.length;
      chunkTranscriptsRef.current.push(''); // placeholder
      
      activeRequestsCountRef.current++;
      setIsTranscribingChunk(true);
      
      const p = transcribeAudio(wavBlob, false).then(text => {
        chunkTranscriptsRef.current[chunkIdx] = text.trim();
        const fullText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
        setTranscript(fullText);
        return text.trim();
      }).catch(err => {
        console.error("Fehler bei Chunk-Transkription:", err);
        return '';
      }).finally(() => {
        activeRequestsCountRef.current--;
        if (activeRequestsCountRef.current <= 0) {
          setIsTranscribingChunk(false);
        }
      });
      
      pendingPromisesRef.current.push(p);
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

      setStatusText("Verifiziere API-Key...");
      setStatus('processing');

      // Validate Vertex AI API key
      try {
        await testGeminiAPI();
      } catch (verifyErr: any) {
        setStatus('ready');
        setStatusText('API-Key ungültig');
        alert("Fehler bei der Key-Verifikation:\n\n" + verifyErr.message + "\n\nBitte überprüfen Sie Ihren API-Key in den Einstellungen.");
        return;
      }

      setTranscript('');
      setStructuredReport('');
      setStatus('recording');
      setStatusText('Aufnahme läuft...');
      audioChunksRef.current = [];
      
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

      // Start AudioContext at native preferred hardware sample rate (avoids resampling dropouts)
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass();
      audioContextRef.current = audioContext;
      actualSampleRateRef.current = audioContext.sampleRate;
      console.log(`[AUDIO] AudioContext initialized at native sample rate: ${audioContext.sampleRate} Hz`);

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioChunksRef.current.push(new Float32Array(inputData));
        
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
        setMicLevel(Math.min(100, Math.round(Math.sqrt(sum / inputData.length) * 400)));
      };

      // Set up chunked interval for real-time visual feedback
      if (chunkIntervalRef.current) {
        clearInterval(chunkIntervalRef.current);
      }
      chunkIntervalRef.current = setInterval(async () => {
        await processNextAudioChunk();
      }, 6000);

    } catch (err: any) {
      console.error(err);
      setStatus('ready');
      setStatusText('Fehler beim Mikrofonzugriff.');
      alert("Mikrofonzugriff verweigert oder nicht verfügbar: " + err.message);
    }
  };

  // Stop Audio Recording & Process Result
  const stopRecording = async () => {
    if (status !== 'recording') return;

    setStatus('processing');
    setStatusText('Verarbeite Audio...');
    setMicLevel(0);

    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }

    // Process any remaining audio since the last interval tick BEFORE closing context
    const currentChunks = audioChunksRef.current;
    const lastProcessedIndex = lastProcessedIndexRef.current;
    
    if (currentChunks.length > lastProcessedIndex) {
      const segmentChunks = currentChunks.slice(lastProcessedIndex);
      lastProcessedIndexRef.current = currentChunks.length;
      
      const merged = mergeFloat32Arrays(segmentChunks);
      const currentSampleRate = actualSampleRateRef.current;
      const resampled = downsampleBuffer(merged, currentSampleRate, 16000);
      
      if (resampled.length > 0) {
        const ctxTemp = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        const audioBuf = ctxTemp.createBuffer(1, resampled.length, 16000);
        audioBuf.copyToChannel(resampled as any, 0);
        const wavBlob = audioBufferToWav(audioBuf);
        ctxTemp.close();
        
        const chunkIdx = chunkTranscriptsRef.current.length;
        chunkTranscriptsRef.current.push(''); // placeholder
        
        activeRequestsCountRef.current++;
        setIsTranscribingChunk(true);
        
        const p = transcribeAudio(wavBlob, false).then(text => {
          chunkTranscriptsRef.current[chunkIdx] = text.trim();
          const fullText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
          setTranscript(fullText);
          return text.trim();
        }).catch(err => {
          console.error("Fehler bei verbleibender Chunk-Transkription:", err);
          return '';
        }).finally(() => {
          activeRequestsCountRef.current--;
          if (activeRequestsCountRef.current <= 0) {
            setIsTranscribingChunk(false);
          }
        });
        
        pendingPromisesRef.current.push(p);
      }
    }

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    try {
      // Wait for any active/pending chunk requests to finish
      if (pendingPromisesRef.current.length > 0) {
        setStatusText('Warte auf ausstehende Chunk-Transkriptionen...');
        await Promise.all(pendingPromisesRef.current);
      }

      // ─────────────────────────────────────────────────────────────────────
      // FULL-AUDIO RE-TRANSCRIPTION (the key fix for medical term recognition)
      // Re-transcribe the ENTIRE recording as one piece so Whisper has full
      // context across the whole dictation.
      // ─────────────────────────────────────────────────────────────────────
      let finalRawText = '';

      try {
        // Merge ALL recorded audio chunks into one continuous buffer
        const allChunks = audioChunksRef.current;
        if (allChunks.length > 0) {
          const mergedAll = mergeFloat32Arrays(allChunks);
          const currentSampleRate = actualSampleRateRef.current;
          const resampledAll = downsampleBuffer(mergedAll, currentSampleRate, 16000);

          if (resampledAll.length > 0) {
            const ctxFull = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            const audioBufFull = ctxFull.createBuffer(1, resampledAll.length, 16000);
            audioBufFull.copyToChannel(resampledAll as any, 0);
            const fullWavBlob = audioBufferToWav(audioBufFull);
            ctxFull.close();

            console.log(`[FULL-AUDIO] Re-transcribing complete recording (${resampledAll.length} samples, ${(resampledAll.length / 16000).toFixed(1)}s)`);

            // Run full-audio transcription via Whisper
            setStatusText('Volltranskription läuft (komplettes Diktat)...');
            const fullTranscript = await transcribeAudio(fullWavBlob, true);
            finalRawText = fullTranscript.trim();
          }
        }
      } catch (fullAudioErr: any) {
        console.warn('[FULL-AUDIO] Re-transcription failed, falling back to chunk transcripts:', fullAudioErr.message);
        // Fallback: use concatenated chunk transcripts
        finalRawText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
      }

      // If full-audio transcription returned empty, also fall back
      if (!finalRawText.trim()) {
        console.warn('[FULL-AUDIO] Empty result, falling back to chunk transcripts.');
        finalRawText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
      }

      setTranscript(finalRawText);

      if (!finalRawText.trim()) {
        throw new Error("Es wurde kein gesprochener Text erkannt.");
      }

      // LLM-Korrektur der STT-Ergebnisse
      setStatusText('Korrigiere medizinische Fachbegriffe (Gemini Flash)...');
      const correctedText = await correctTranscriptionWithGemini(finalRawText);
      finalRawText = correctedText;
      setTranscript(finalRawText);

      // v3.2: gleiche Kette wie die EXE (Regionen trennen → je Region Bypass oder Gemini → Ergebnis nummerieren)
      const report = await befundAusDiktat(finalRawText);
      setStructuredReport(report);
      setStatus('ready');
      setStatusText('Bereit');

      await copyTextToClipboard(report);

    } catch (err: any) {
      console.error(err);
      setStatus('ready');
      setStatusText('Fehler bei der Verarbeitung.');
      alert("Fehler bei der Transkription oder KI-Strukturierung: " + err.message);
    }
  };

  // Manual Copy Result
  const handleCopyReport = async () => {
    if (!structuredReport) return;
    await copyTextToClipboard(structuredReport);
  };

  // Audio File Upload Handler — feeds uploaded audio through the same STT + Gemini pipeline
  const handleAudioUpload = async (file: File) => {
    setStatus('processing');
    setStatusText('Verarbeite hochgeladenes Audio...');
    setTranscript('');
    setStructuredReport('');

    try {
      // Step 1: Transkription via Google Cloud STT (Whisper nur als Fallback)
      let finalRawText = '';
      try {
        setStatusText('Spracherkennung läuft (Google Cloud STT)...');
        finalRawText = await transcribeFullAudioWithGoogle(await decodeFileToWavBlob(file));
      } catch (sttErr: any) {
        console.warn('[UPLOAD] Google STT fehlgeschlagen, Whisper-Fallback:', sttErr.message);
        setStatusText('Spracherkennung läuft (Whisper, Fallback)...');
        finalRawText = await transcribeWithWhisper(file);
      }

      finalRawText = finalRawText.trim();

      if (!finalRawText) {
        throw new Error('Es wurde kein gesprochener Text erkannt.');
      }

      // Step 1.5: LLM-Korrektur der STT-Ergebnisse
      setStatusText('Korrigiere medizinische Fachbegriffe (Gemini Flash)...');
      finalRawText = await correctTranscriptionWithGemini(finalRawText);

      setTranscript(finalRawText);
      console.log(`[UPLOAD] Transcription (corrected): ${finalRawText.substring(0, 200)}...`);

      // Step 2: v3.2 — dieselbe Kette wie Aufnahme und EXE (Regionen trennen → Bypass/Gemini → Ergebnis nummerieren)
      setStatusText('KI-Strukturierung läuft (Gemini Flash)...');
      const report = await befundAusDiktat(finalRawText);
      setStructuredReport(report);
      setStatus('ready');
      setStatusText('Bereit');
      await copyTextToClipboard(report);

    } catch (err: any) {
      console.error('[UPLOAD] Error:', err?.message || err?.name || JSON.stringify(err), err?.stack?.substring(0, 200) || '');
      setStatus('ready');
      setStatusText('Fehler bei der Verarbeitung.');
      alert("Fehler bei Audio-Upload-Verarbeitung: " + (err?.message || err?.name || 'Unbekannter Fehler'));
    }
  };

  // Reset fields
  const handleReset = () => {
    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }
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

  // Refs to avoid stale closures in global keyboard event listeners
  const startRecordingRef = useRef(startRecording);
  startRecordingRef.current = startRecording;
  const stopRecordingRef = useRef(stopRecording);
  stopRecordingRef.current = stopRecording;
  const handleResetRef = useRef(handleReset);
  handleResetRef.current = handleReset;
  const handleAudioUploadRef = useRef(handleAudioUpload);
  handleAudioUploadRef.current = handleAudioUpload;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F10') {
        e.preventDefault();
        if (statusRef.current === 'recording') {
          stopRecordingRef.current();
        } else if (statusRef.current === 'ready' && keysReadyRef.current) {
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
  }, []);

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
          <span className="version-chip">v3.2.1</span>
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
                <div className="level-track"><div className="level-bar" style={{ width: `${micLevel}%` }} /></div>
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
            placeholder="Das Diktat erscheint hier live und kann bearbeitet werden."
            className="editor"
            disabled={!keysReady}
          />
          <div className="panel-foot">
            {status === 'recording' ? (
              <button onClick={stopRecording} className="btn btn-record is-recording">
                <MicOff size={18} /> Aufnahme stoppen <kbd>F10</kbd>
              </button>
            ) : (
              <button onClick={startRecording} disabled={status === 'processing' || !keysReady} className="btn btn-record">
                <Mic size={18} /> Aufnahme starten <kbd>F10</kbd>
              </button>
            )}
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
            <div className="seg" role="tablist" aria-label="Ansicht">
              <button role="tab" aria-selected={reportView === 'formatiert'} className={reportView === 'formatiert' ? 'on' : ''} onClick={() => setReportView('formatiert')}>Formatiert</button>
              <button role="tab" aria-selected={reportView === 'text'} className={reportView === 'text' ? 'on' : ''} onClick={() => setReportView('text')}>Text</button>
            </div>
          </div>
          {reportView === 'formatiert' ? (
            structuredReport
              ? <div className="report-view" dangerouslySetInnerHTML={{ __html: reportToHtml(structuredReport) }} />
              : <div className="report-view report-empty">Der strukturierte Befund erscheint hier nach dem Diktat und wird automatisch kopiert.</div>
          ) : (
            <textarea value={structuredReport} readOnly className="editor editor-report" placeholder="Noch kein Befund." />
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
