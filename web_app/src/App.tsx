import React, { useState, useEffect, useRef } from 'react';
import {
  Aperture,
  Mic,
  MicOff,
  Copy,
  Check,
  LogOut,
  Lock,
  ArrowRight,
  Sparkles,
  X,
  Upload,
  Download
} from 'lucide-react';
import templatesData from './templates.json';

// Types
type Template = {
  display_name: string;
  body: string;
};

type TemplatesMap = {
  [key: string]: Template;
};

const templates = templatesData as TemplatesMap;

// Vertex AI endpoint for Gemini 2.5 Flash
const VERTEX_ENDPOINT = 'https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent';

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
  "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung",
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
  "Flachbogig", "S-förmige",
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
  "flachbogig", "flachbogige", "S-förmige Skoliose", "rechtskonvex", "linkskonvex",
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
function isNormalFinding(text: string): boolean {
  const textLower = text.toLowerCase();
  const pathologyKeywords = [
    "arthrose", "fraktur", "osteo", "spondyl", "tendin", "calcarea", "bursitis",
    "tenosynovitis", "teppich", "ruptur", "luxation", "skoliose", "kyphose",
    "impression", "edgren", "scheuermann", "bi-rads", "morb", "thrombose",
    "mondor", "tumor", "metastas", "entzünd", "ödem", "erguss",
    "verschmäler", "skleros", "osteophyt", "beckenschief", "beinlängen",
    "listhesis", "chondr", "fissur", "kontusion", "depression", "n. ulnaris",
    "anconeus", "epitrochlear", "guyon", "flachbogig", "cobb", "schmorl",
    "patholog", "verdacht", "suspekt", "läsion", "herd", "verkalkung",
    "kalk", "fremdkörper", "emphysem", "infiltrat", "stauung",
    "thromb", "vene", "axillär", "axillar"
  ];
  const negationPhrases = [
    "kein ", "keine ", "keinem ", "keinen ", "keiner ", "kein nachweis",
    "nicht nachweisbar", "nicht vorhanden", "ausschluss", "frei von",
    "ohne nachweis", "ohne patholog", "ohne fraktur", "ohne arthrose",
    "kein hinweis", "keine zeichen", "nicht nachweis"
  ];
  const hasPathology = pathologyKeywords.some(kw => {
    const idx = textLower.indexOf(kw);
    if (idx === -1) return false;
    const before = textLower.substring(Math.max(0, idx - 30), idx);
    const isNegated = negationPhrases.some(neg => before.includes(neg));
    return !isNegated;
  });
  if (hasPathology) return false;
  const normalKeywords = ["unauffällig", "normal", "regelrecht", "ohne befund", "kein nachweis", "unauffaellig"];
  const hasNormal = normalKeywords.some(kw => textLower.includes(kw));
  const isShort = textLower.split(/\s+/).filter(Boolean).length < 12;
  return hasNormal && isShort;
}


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


export default function App() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [authError, setAuthError] = useState<string>('');

  // Configuration States
  const [vertexApiKey, setVertexApiKey] = useState<string>('');
  const [sttKeyJson, setSttKeyJson] = useState<any>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const audioUploadRef = useRef<HTMLInputElement>(null);
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
      await navigator.clipboard.writeText(text);
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

  // RAG mock dataset
  const ragDatabase: string[] = [
    "Befund: HWS in 2 Ebenen. Harmonischer Achsenverlauf. Keine Spondylolisthesis. Keine Höhenminderung der Intervertebralräume. Ergebnis: Unauffälliger HWS-Befund.",
    "Befund: Thorax in 2 Ebenen. Zwerchfellkuppen glatt begrenzt, Sinus frei. Lungenfelder regelrecht belüftet. Cor normal groß. Ergebnis: Herz-Lungen-Befund ohne pathologischen Befund.",
    "Befund: Kniegelenk rechts in 2 Ebenen. Regelrechter Gelenkspalt, keine arthrotischen Randwülste. Intakter Knorpel. Ergebnis: Altersentsprechender Normalbefund."
  ];

  // Particle background Canvas Ref
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

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
    const savedPrompt = localStorage.getItem('system_prompt');
    const savedAuth = localStorage.getItem('is_authenticated');
    const savedDeviceId = localStorage.getItem('selected_audio_device_id');

    if (savedVertexKey) setVertexApiKey(savedVertexKey);
    if (savedAuth === 'true') setIsAuthenticated(true);
    if (savedDeviceId) setSelectedDeviceId(savedDeviceId);

    // Auto-Load Vertex AI API key from local file if not in localStorage
    if (!savedVertexKey) {
      // Fallback 1: vertex-key.txt (Klartext, lokale Dev-Datei)
      (async () => {
        try {
          const resp = await fetch(`${import.meta.env.BASE_URL}vertex-key.txt`);
          if (resp.ok) {
            const keyData = (await resp.text()).trim();
            if (keyData) {
              localStorage.setItem('vertex_api_key', keyData);
              setVertexApiKey(keyData);
              console.log('[AUTO-LOAD] Vertex API Key automatisch aus vertex-key.txt geladen');
            }
          }
        } catch (e) {
          console.log('[AUTO-LOAD] Kein vertex-key.txt gefunden:', e);
        }
      })();

      // Fallback 2: vertex-key.b64 (Base64, von CI neben index.html abgelegt)
      (async () => {
        try {
          const resp = await fetch(`${import.meta.env.BASE_URL}vertex-key.b64`);
          if (resp.ok) {
            const b64 = (await resp.text()).trim();
            const bin = atob(b64);
            const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
            const keyData = new TextDecoder().decode(bytes).trim();
            if (keyData) {
              localStorage.setItem('vertex_api_key', keyData);
              setVertexApiKey(keyData);
              console.log('[AUTO-LOAD] Vertex API Key automatisch aus vertex-key.b64 geladen');
            }
          }
        } catch (e) {
          console.log('[AUTO-LOAD] Kein vertex-key.b64 gefunden:', e);
        }
      })();

      // Fallback 3: STT-Service-Account (stt-key.b64 = CI-injiziert, stt-key.txt = lokal)
      (async () => {
        try {
          const resp = await fetch(`${import.meta.env.BASE_URL}stt-key.b64`);
          if (resp.ok) {
            const bin = atob((await resp.text()).trim());
            const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
            const json = JSON.parse(new TextDecoder().decode(bytes));
            if (json && json.private_key) {
              setSttKeyJson(json);
              console.log('[AUTO-LOAD] STT Service-Account-Key geladen (stt-key.b64)');
              return;
            }
          }
        } catch (e) {
          console.log('[AUTO-LOAD] Kein stt-key.b64 gefunden:', e);
        }
        try {
          const resp = await fetch(`${import.meta.env.BASE_URL}stt-key.txt`);
          if (resp.ok) {
            const json = JSON.parse(await resp.text());
            if (json && json.private_key) {
              setSttKeyJson(json);
              console.log('[AUTO-LOAD] STT Service-Account-Key geladen (stt-key.txt)');
            }
          }
        } catch (e) {
          console.log('[AUTO-LOAD] Kein stt-key.txt gefunden — STT faellt auf Whisper zurueck');
        }
      })();
    }
    
    const newDefaultPrompt = 
      `<role>Radiologie-Assistent der Praxis "Röntgen am Kai" – Dr. P. Kalmar / Dr. G. Riegler</role>\n` +
      `<instructions>\n` +
      `Du bist ein präziser radiologischer Befundungsassistent für die Praxis "Röntgen am Kai" in Graz. Deine Aufgabe ist es, das diktierte Stichwortprotokoll des Arztes in einen formalen, professionellen radiologischen Befund zu strukturieren, der sich EXAKT an den historischen Befundvorlagen der Praxis orientiert.\n\n` +
      `## STRIKTE FORMATREGELN:\n` +
      `1. Erstelle IMMER exakt zwei Hauptabschnitte: '## Befund' und '## Ergebnis'. Kein weiterer Text, keine Kommentare, keine Erklärungen außerhalb dieser Abschnitte.\n` +
      `2. Gib NUR den fertigen Befundtext aus – keine Einleitung, kein Schlusswort.\n\n` +
      `## ABSCHNITT "## Befund":\n` +
      `- Nutze das bereitgestellte Normalbefund-Template (\`<normalbefund_template>\`) als genaue strukturelle Basis.\n` +
      `- Passe gezielt die Sätze an, bei denen das Diktat pathologische Befunde nennt (z.B. Arthrose, Fraktur, TEP, Spondylarthrose, Osteochondrose, Beckenschiefstand).\n` +
      `- Behalte ALLE nicht genannten Regionen und Sätze des Templates UNVERÄNDERT.\n` +
      `- Übernimm Messwerte (z.B. 'Beckenschiefstand nach links um 4 mm', '-1,2 cm Beinlängendifferenz') exakt aus dem Diktat.\n` +
      `- Schreibe im radiologischen Nominalstil (z.B. 'Kein Nachweis von Lockerungszeichen.', 'Intakte Hüft-TEP rechts.').\n\n` +
      `## ABSCHNITT "## Ergebnis":\n` +
      `- Fasse alle diagnosewesentlichen Pathologien kurz und stichpunktartig zusammen.\n` +
      `- Schreibe präzise Diagnosen im Stil der Praxis: z.B. 'Intakte Hüft-TEP rechts.', 'Coxarthrose links.', 'STT-Arthrose beidseits.', 'Osteochondrosis pubis.', 'Beckenschiefstand nach links um 4 mm bei Beinlängendifferenz links -4 mm.'.\n` +
      `- Bei Normalbefund: 'Unauffälliger Befund.' oder der entsprechende Kurztext.\n` +
      `## KONSISTENZ-REGELN (STRIKT):\n` +
      `1. JEDER pathologische Befund aus dem Diktat MUSS im "## Ergebnis" genannt werden. Keine Diagnose darf fehlen.\n` +
      `2. JEDER pathologische Befund aus dem "## Ergebnis" MUSS auch im "## Befund" beschrieben sein. Keine Diagnose darf nur in einem Abschnitt stehen.\n` +
      `3. KEINE WIDERSPRÜCHE: Wenn im Befund eine Pathologie beschrieben wird, darf das Ergebnis nicht "unauffällig" lauten.\n` +
      `4. KEINE WIDERSPRÜCHE: Wenn das Ergebnis eine Diagnose nennt, muss der Befund die entsprechenden morphologischen Kriterien beschreiben.\n` +
      `5. Keine Diagnose darf ERFUNDEN werden, die nicht im Diktat genannt wurde. Du strukturierst, du diagnostizierst nicht.\n` +
      `6. "ansonsten unauffällig" bezieht sich nur auf nicht genannte Bereiche – es darf NICHT das gesamte Ergebnis als unauffällig markieren wenn Pathologien vorhanden sind.\n\n` +
      `## KONFLIKT-REGELN (NORMALBEFUND vs. PATHOLOGIE) — STRIKT EINZUHALTEN:\n` +
      `Wenn das Diktat eine Pathologie nennt, MÜSSEN die entsprechenden Normalbefund-Sätze aus dem Template ENTFERNT oder ANGEPASST werden. KEINE WIDERSPRÜCHE im Befundtext!\n\n` +
      `Spezifische Regeln:\n` +
      `- Osteochondrose/Diskopathie in Segment X: ENTFERNE "Bandscheibenräume normal hoch" für dieses Segment. Schreibe stattdessen Deskriptoren: "Verschmälerung des Intervertebralraums [Segment] mit subchondraler Sklerosierung der Abschlussplatten". Schreibe NICHT "Osteochondrose" als Wort in den Befundtext — nur Deskriptoren.\n` +
      `- Spondylosis deformans/Spondylophyten in Segment X: ERGÄNZE "Spondylophytenbildung [Segment]" im Befundtext.\n` +
      `- Unkovertebralgelenksarthrose/Uncovertebralarthrose in Segment X: FÜGE HINZU "Degenerative Veränderungen der Unkovertebralgelenke [Segment] mit Gelenkspaltverschmälerung, subchondraler Sklerosierung und Osteophytenbildung". Die "kleinen Zwischenwirbelgelenke" (Facettengelenke) sind ANDERE Gelenke und bleiben "ohne Auffälligkeiten" wenn nicht genannt.\n` +
      `- Facettengelenksarthrose/Spondylarthrose in Segment X: ERSETZE "kleinen Zwischenwirbelgelenke ohne Auffälligkeiten" durch "Degenerative Veränderungen der kleinen Wirbelgelenke [Segment]".\n` +
      `- Anterolisthese/Retrolisthese: Ersetze die normale Achsenverlaufsbeschreibung für das betroffene Segment durch die Listhese-Beschreibung.\n` +
      `- Skoliose/skoliotische Fehlhaltung: ERSETZE "Normaler Achsenverlauf" durch die Skoliose-Beschreibung.\n` +
      `- Streckhaltung: ERSETZE "Normaler Achsenverlauf" durch "Streckhaltung der HWS".\n` +
      `- Fraktur: ENTFERNE "Alle Wirbelkörper von normaler Form und Höhe" und ersetze durch Frakturbeschreibung.\n` +
      `- Gelenksarthrose (Omarthrose/Coxarthrose/Gonarthrose/Arthrose etc.): ENTFERNE "Normale Form und Struktur der Gelenkkörper", "Die Gelenkflächen glatt und kongruent", "Die Gelenkränder unauffällig", "Die Gelenksspalten normal weit" — ALLE diese Normalbefund-Sätze MÜSSEN gestrichen werden wenn eine Arthrose vorliegt. Stattdessen arthrotische Deskriptoren: "Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung der Gelenkflächen und osteophytärer Randwulstbildung". NIEMALS "Normale Form und Struktur der Gelenkkörper" + arthrotische Deskriptoren im selben Satz (kein "bei ansonsten normaler Form").\n` +
      `- Humeruskopfhochstand/Femurkopfhochstand: Ersetze die normale Gelenkpartner-Stellung durch den Hochstand. KEIN "bei ansonsten normaler Form und Struktur" — der Hochstand IST die Abweichung.\n` +
      `- TEP/Prothese: ERSETZE "Normale Form und Struktur der Gelenkkörper" durch Prothesenbeschreibung.\n` +
      `- Knochenzyste/Lyse/Tumor: ERSETZE "Knochenstruktur unauffällig" / "Mineralgehalt und Knochenstruktur regelrecht" durch pathologische Beschreibung.\n` +
      `- Kalzifikation/Tendinosis calcarea: ERGÄNZE Verkalkungsbeschreibung im Befundtext.\n\n` +
      `GRUNDREGEL: Wenn ein Normalbefund-Satz durch eine Pathologie hinfällig wird, MUSS er gestrichen oder ersetzt werden. Ein Befundtext darf NIEMALS eine Struktur als "normal/unauffällig/ordnungsgemäß" beschreiben UND GLEICHZEITIG als pathologisch verändert einstufen.\n` +
      `BESCHREIBUNGSTEXT = NUR MORPHOLOGIE/DESKRIPTOREN. Diagnosen, Differentialdiagnosen und Diagnose-Namen gehören NUR ins Ergebnis, NICHT in den Befundtext.\n\n` +
      `## VERBOTENE MUSTER (Anti-Patterns) — diese Fehler macht Gemini Flash oft, sie MÜSSEN vermieden werden:\n` +
      `❌ FALSCH: "Normale Form und Struktur der Gelenkkörper. Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung und Osteophytenbildung." (Widerspruch: erst normal, dann arthrotisch — der erste Satz MUSS WEG)\n` +
      `✅ RICHTIG: "Verschmälerung des Gelenkspaltes mit subchondraler Sklerosierung der Gelenkflächen und osteophytärer Randwulstbildung." (nur arthrotische Deskriptoren)\n` +
      `❌ FALSCH: "Die Gelenkflächen glatt und kongruent. Die Gelenkränder unauffällig. Die Gelenksspalten normal weit. Medialbetonte Gelenkspaltverschmälerung." (Widerspruch: 3 Normalbefund-Sätze + 1 arthrotischer Befund — die 3 Normalbefund-Sätze MÜSSEN WEG)\n` +
      `✅ RICHTIG: "Medialbetonte Gelenkspaltverschmälerung. Die periartikuläre Weichteilzone o. B." (nur arthrotische Deskriptoren + Weichteil-Normalbefund, da dieser nicht betroffen ist)\n` +
      `❌ FALSCH: "Hochstand des Humeruskopfes bei ansonsten normaler Form und Struktur der Gelenkkörper." (Widerspruch: Hochstand + normale Form — "bei ansonsten normaler Form" MUSS WEG)\n` +
      `✅ RICHTIG: "Hochstand des Humeruskopfes." (Hochstand ist die Abweichung, kein "bei ansonsten normaler Form")\n` +
      `❌ FALSCH: "Normale Form und Struktur der Gelenkkörper. Dislozierte Kontinuitätsunterbrechung im Bereich des Collum chirurgicum." (Widerspruch: erst normale Form, dann Fraktur — der erste Satz MUSS WEG)\n` +
      `✅ RICHTIG: "Dislozierte Kontinuitätsunterbrechung im Bereich des Collum chirurgicum humeri." (nur Frakturbeschreibung)\n` +
      `❌ FALSCH: "Artikulierende Flächen regelrecht konfiguriert, glatt und scharf begrenzt, allseits normal weit zueinander." (nach Fraktur eines Gelenkpartners — fehlender Qualifikator, impliziert ALLE Flächen normal)\n` +
      `✅ RICHTIG: "Artikulierende Flächen im Übrigen regelrecht konfiguriert, glatt und scharf begrenzt, allseits normal weit zueinander." ("im Übrigen" qualifiziert: der frakturierte Teil ist ausgenommen)\n` +
      `❌ FALSCH: "Mineralgehalt und Knochenstruktur regelrecht. Nicht dislozierte Kontinuitätsunterbrechung im Bereich der Kahnbeintaille." (Widerspruch: Knochenstruktur als regelrecht bezeichnet, dann Fraktur — "und Knochenstruktur" MUSS WEG)\n` +
      `✅ RICHTIG: "Mineralgehalt regelrecht. Nicht dislozierte Kontinuitätsunterbrechung im Bereich der Kahnbeintaille." (Mineralgehalt darf normal bleiben, Knochenstruktur nicht bei Fraktur)\n` +
      `❌ FALSCH: "Flachbogige linkskonvexe Skoliose." oder "Retrolisthese von L4 gegenüber L5." (Befundtext — Diagnosename statt Morphologie)\n` +
      `✅ RICHTIG: "Flachbogige linkskonvexe Seitausbiegung." bzw. "Dorsaler Versatz von L4 gegenüber L5." (Morphologie im Befundtext, Diagnose "Skoliose"/"Retrolisthese" nur im Ergebnis)\n` +
      `## ERGEBNIS-REGELN:\n` +
      `- Schreibe NUR Diagnosen die im Diktat genannt wurden. Keine ERFUNDENEN Begriffe wie "Fehlhaltung" wenn das Diktat "Streckhaltung" sagt.\n` +
      `- Verwende EXAKT die Begriffe aus dem Diktat. Wenn das Diktat "Streckhaltung" sagt, schreibe "Streckhaltung" — nicht "Fehlhaltung".\n` +
      `- Diagnose-Namen dürfen NICHT umformuliert werden. "Osteochondrose" bleibt "Osteochondrose", nicht "Diskopathie". "Coxarthrose" bleibt "Coxarthrose", nicht "Hüftgelenksarthrose".\n` +
      `- Wenn das Diktat nur Deskriptoren nennt (z.B. "Schleimhautschwellung, Spiegelbildung") schreibe diese als Befund, aber erfinde KEINE Diagnose (z.B. nicht "Sinusitis") für das Ergebnis — nur das Diktat entscheidet ob eine Diagnose gestellt wird.\n` +
      `- Wenn im Diktat "vereinbar mit [Diagnose]" gesagt wird, schreibe im Ergebnis IMMER "Bild wie bei [Diagnose]" (z.B. "vereinbar mit CIDP" → "Bild wie bei CIDP"). "Vereinbar mit" ist NUR eine Diktat-Formulierung und darf NICHT wörtlich ins Ergebnis übernommen werden.\n` +
      `- Querschnittsfläche (CSA): NUR in den Befundtext aufnehmen, wenn sie EXPLIZIT im Diktat genannt wird. Wenn das Diktat keine CSA nennt, LASS die CSA-Erwähnung aus dem Template KOMPLETT WEG (kein Platzhalter, kein Normwert, nichts). Dies gilt für ALLE Nerven-Templates.\n` +
      `## SCHREIBSTIL – orientiere dich strikt an diesen Praxis-Beispielen:\n` +
      `- 'Intakte Hüft-TEP rechts, soweit in einer Ebene beurteilbar. Pfannenkomponente und Schaftkomponente in regelrechter Position. Kein periprothetischer Aufhellungssaum.'\n` +
      `- 'Coxarthrose links mit deutlicher Gelenkspaltverschmälerung, subchondraler Sklerosierung und osteophytären Randwülsten.'\n` +
      `- 'STT-Arthrose (Scaphoid-Trapezium-Trapezoideum) beidseits. Gelenkspaltverschmälerung und Sklerose.'\n` +
      `- 'Osteochondrosis pubis. Unregelmäßigkeit der Symphysenfuge mit subchondraler Sklerose.'\n` +
      `- 'Diskreter/ausgeprägter Beckenschiefstand nach links/rechts um X mm bei Beinlängendifferenz links/rechts -X mm.'\n` +
      `- 'Unauffälliger HWS-Befund.' / 'Unauffälliger Befund.'\n` +
      `</instructions>\n` +
      `<normalbefund_template>\n` +
      `{template_body}\n` +
      `</normalbefund_template>\n\n` +
      `{examples}\n\n` +
      `<diktat>\n` +
      `{roh_text}\n` +
      `</diktat>`;

    if (!savedPrompt || savedPrompt.includes("## Beurteilung") || savedPrompt.includes("Radiologe-Assistent</role>")) {
      setSystemPrompt(newDefaultPrompt);
      localStorage.setItem('system_prompt', newDefaultPrompt);
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

  // Particle Canvas Background Logic
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Array<{ x: number; y: number; vx: number; vy: number; r: number }> = [];

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      initParticles();
    };

    const initParticles = () => {
      particles = [];
      const count = Math.min(120, Math.floor((canvas.width * canvas.height) / 12000));
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * 0.2,
          vy: (Math.random() - 0.5) * 0.2,
          r: Math.random() * 5 + 2.5
        });
      }
    };

    const draw = () => {
      if (statusRef.current === 'recording') {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        animationFrameId = requestAnimationFrame(draw);
        return;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = 'rgba(140, 82, 255, 0.35)';
      ctx.strokeStyle = 'rgba(140, 82, 255, 0.08)';
      ctx.lineWidth = 1;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    draw();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // Save config changes
  // Config auto-saved on change

  // Login Handler
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const pw = password.trim();
    if (false && username.trim() !== '' && pw === 'rakscribe') {
      setIsAuthenticated(true);
      localStorage.setItem('is_authenticated', 'true');
      setAuthError('');
    } else if (pw.startsWith('{') && pw.includes('BEGIN PRIVATE KEY')) {
      // Praxis-Key: Die STT-JSON-Datei (aus dem RaKScribe-Drive-Ordner) als Passwort
      // in das Passwortfeld ziehen/einfuegen — Inhalt ist der Login.
      try {
        const json = JSON.parse(pw);
        if (json.type === 'service_account' && json.private_key) {
          setSttKeyJson(json);
          setIsAuthenticated(true);
          localStorage.setItem('is_authenticated', 'true');
          setAuthError('');
          console.log('[LOGIN] STT-Key via Praxis-JSON erkannt');
        } else {
          setAuthError('JSON erkannt, aber keine gültige Service-Account-Datei.');
        }
      } catch {
        setAuthError('Ungültige Anmeldedaten.');
      }
    } else {
      setAuthError('Ungültige Anmeldedaten.');
    }
  };

  // Logout Handler
  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('is_authenticated');
  };



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
    const hasCervical  = textLower.includes("hws") || textLower.includes("zervik")
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
      if (textLower.includes("beinven") || textLower.includes("v. femoralis") || textLower.includes("poplitea") || textLower.includes("fibularis") || textLower.includes("venen")) {
        return "sonografie_beinvenen";
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

    if (textLower.includes("opg") || textLower.includes("zahnröntgen") || textLower.includes("zahnstatus") || textLower.includes("orthopantomogramm")) {
      return "orthopantomogramm_des_kiefer-_und_gesichtsschädels";
    }

    if (textLower.includes("dexa") || textLower.includes("knochendichte") || textLower.includes("densitometrie") || textLower.includes("odm")) {
      return "knochendichtemessung_dexa";
    }

    if (textLower.includes("mammo")) {
      // Mammasonographie (Ultraschall) vs Mammographie (Röntgen)
      if (textLower.includes("sono") || textLower.includes("schall") || textLower.includes("ultraschall") || textLower.includes("mammasono")) {
        return "mammasonographie_beidseits";
      }
      return "mammographie_beidseits";
    }

    if (textLower.includes("fernröntgen") || textLower.includes("fern-röntgen") || textLower.includes("frs")) {
      return "schädelfernröntgen";
    }

    if (textLower.includes("breischluck") || textLower.includes("ösophagus") || textLower.includes("schluckakt")) {
      return "durchleuchtung:_ösophagus-breischluck";
    }
    if (textLower.includes("mdp") || textLower.includes("magen-darm") || textLower.includes("magen")) {
      return "durchleuchtung:_magen-darm-passage_mdp";
    }
    if (textLower.includes("urogramm") || textLower.includes("ivu") || textLower.includes("ivp")) {
      return "intravenöses_urogramm";
    }
    if (textLower.includes("phlebographie") || textLower.includes("phlebo")) {
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
      ["thorax_in_2_ebenen", ["thorax", "lunge", "herz", "rö-th", "rö thor"]],
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
  const getFewShotExamples = (text: string): string => {
    const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 3);
    if (words.length === 0) return "";

    const matches = ragDatabase.filter(report => {
      return words.some(word => report.toLowerCase().includes(word));
    }).slice(0, 2);

    if (matches.length === 0) return "";

    return "\n### BEISPIELE FÜR TYPISCHE BERICHTE DIESER PRAXIS:\n" + 
      matches.map((m, idx) => `Beispiel ${idx + 1}:\n${m}\n---`).join("\n");
  };

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

  // Chunk-Transkription (7s-Chunks, latest_short)
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
          enableAutomaticPunctuation: true, model: 'latest_short', useEnhanced: true,
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

  // FULL-AUDIO Transkription (komplettes Diktat; ≤59s sync/latest_short, >60s longrunning/latest_long)
  const transcribeFullAudioWithGoogle = async (wavBlob: Blob): Promise<string> => {
    const { url, headers } = await buildSttAuth();
    const base64Data = await blobToBase64(wavBlob);

    // Duration: 16000 samples/s * 2 bytes/sample = 32000 bytes/s (base64 ~4/3)
    const binarySize = Math.floor(base64Data.length * 3 / 4);
    const estimatedDurationSec = binarySize / 32000;
    console.log(`[FULL-AUDIO] ${binarySize} bytes, ~${estimatedDurationSec.toFixed(1)}s`);

    const buildSttConfig = (useLongModel: boolean) => ({
      encoding: 'LINEAR16' as const,
      sampleRateHertz: 16000,
      languageCode: 'de-DE',
      enableAutomaticPunctuation: true,
      model: useLongModel ? 'latest_long' : 'latest_short',
      useEnhanced: true,
      speechContexts: [{ phrases: MEDICAL_PHRASES, boost: 15.0 }],
    });

    if (estimatedDurationSec <= 59) {
      setStatusText('Volltranskription läuft (komplettes Diktat, Google STT)...');
      const response = await fetchWithRetry(url, {
        method: 'POST', headers,
        body: JSON.stringify({ config: buildSttConfig(false), audio: { content: base64Data } }),
      }, 120_000, 3);
      const data = await response.json();
      if (data.error) throw new Error(data.error.message || 'Google STT Fehler bei Volltranskription.');
      const results = data.results || [];
      return results.map((r: any) => r.alternatives[0].transcript).join(' ');
    }

    // >60s: longrunningrecognize + polling
    console.log('[FULL-AUDIO] longrunningrecognize (>60s)');
    setStatusText('Volltranskription läuft (langes Diktat, bitte warten)...');
    const startResponse = await fetchWithRetry('https://speech.googleapis.com/v1/speech:longrunningrecognize', {
      method: 'POST', headers,
      body: JSON.stringify({ config: buildSttConfig(true), audio: { content: base64Data } }),
    }, 120_000, 3);
    const startData = await startResponse.json();
    if (startData.error) throw new Error(startData.error.message || 'Fehler beim Starten der Long-Running-Erkennung.');

    const operationName = startData.name;
    const maxAttempts = 60;
    const pollInterval = 5000;
    let lastProgress = 0;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));

      // Token ggf. erneuern (langer Betrieb)
      const freshToken = await getGoogleBearerToken(sttKeyJson, 'https://www.googleapis.com/auth/cloud-platform');
      const pollResponse = await fetchWithRetry(`https://speech.googleapis.com/v1/operations/${operationName}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${freshToken}` },
      }, 30_000, 3);

      const pollData = await pollResponse.json();
      if (pollData.error) throw new Error(pollData.error.message || 'Fehler beim Abrufen des Transkriptionsergebnisses.');

      if (pollData.done) {
        const response = pollData.response;
        if (!response || !response.results) return '';
        const fullText = response.results
          .map((r: any) => r.alternatives[0].transcript)
          .join(' ');
        console.log(`[FULL-AUDIO] Long-running complete: ${fullText.length} chars`);
        return fullText;
      }

      const progress = pollData.metadata?.progressPercent;
      if (progress && progress !== lastProgress) {
        lastProgress = progress;
        setStatusText(`Volltranskription läuft... ${progress}%`);
      } else {
        setStatusText(`Volltranskription läuft... (Versuch ${attempt + 1}/${maxAttempts})`);
      }
    }
    throw new Error('Zeitüberschreitung bei der Volltranskription (5 Minuten).');
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
  const correctTranscriptionWithGemini = async (rawText: string): Promise<string> => {
    if (!vertexApiKey) {
      return rawText; // No LLM available, return raw
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    const correctionPrompt = `Du bist ein medizinischer Lektor für radiologische Diktate. Korrigiere Spracherkennungsfehler.

## BEKANNTE STT-FEHLER (automatisch korrigieren):
- "Genusse pinnatus" / "Genusses pinnatus" / "pinnatus" → "Supraspinatussehne" / "Supraspinatus"
- "Szene Partie" / "Partie" → "Tendinopathie"
- "Bizeps Szene" / "Szene" (nach Bizeps/Sehne) → "Bizepssehne" / "Sehne"
- "nur noch völlig" → "unauffällig"
- "begleitet ist" / "begleitend" / "begleitet" → "mit Begleitbursitis" / "mit begleitender Bursitis"
- "Kalkschulter" → "Tendinosis calcarea"
- "Kalkspick" / "Kalkspick" → "Kalkeinlagerung"
- "Pirates" / "Pirates 2" / "Pirats" → "BI-RADS 2"
- "Pirates 1" / "Pirates 3" / "Pirates 4" / "Pirates 5" → "BI-RADS 1" / "BI-RADS 3" / "BI-RADS 4" / "BI-RADS 5"
- "Pirates 0" / "Pirates 6" → "BI-RADS 0" / "BI-RADS 6"
- "Hypertropha Musculus Anconeus Epidrochearis" → "hypertropher M. anconeus epitrochlearis"
- "Epidrochearis" / "Epitrochlearis" → "epitrochlearis"
- "Edelbogenflexion" → "Ellbogenflexion"
- "Edelbogen" → "Ellbogen"
- "Quadratmillimeter" / "Quadrat Millimeter" → "mm²"
- "Sulcus Nervi" → "Sulcus nervi ulnaris"
- "fast zirkulär" / "fastzirkulär" / "fast zirkular" → "faszikulär"
- "Nerventechistenz" / "Nerventechistenz" → "Nervendehiszenz"
- "Elbungs" → "Ellbogens"
- "Kilo-Nevin" → "Kiloh-Nevin"
- "Einigung" (bei Nerv/Sehne) → "Einengung"
- "Nervus Lunaris" / "N. Lunaris" → "Nervus ulnaris" / "N. ulnaris"
- "Hypothenamuskulatur" → "Hypothenarmuskulatur"
- "Sulkus" → "Sulcus"
- "Aktion not mesis" / "Aktionotmesis" → "Axonotmesis"
- "messigradige" / "messiggradige" → "mäßiggradige"
- "Succus" → "Sulcus"
- "Platnoster Synthese" / "Platnostersynthese" → "Plattenosteosynthese"
- "Rhamus" → "Ramus"
- "perinorale" → "perineurale"
- "hoffmann die nählzeichen" / "hoffmann die nähzeichen" → "Hoffmann-Tinel-Zeichen"
- "bizeps sinnen naht" → "Bizepssehnennaht"

## PRAXIS-JARGON (Dr. Kalmar / Dr. Riegler Shortcut-Phrasen):
- "Baustein Gelenkschema" / "Baustein Gelenkschirma" / "Baustein Gelenk Schema" → "unauffällig"
- "Baustein Gelenkschema 0" / "Baustein Gelenkschema 1" / "Baustein Gelenkschema 2" → "unauffällig"
- "Baustein" (alleine, am Ende eines Diktats) → "unauffällig"
- "im Übrigen Baustein" → "im Übrigen unauffällig"

## WICHTIGE REGELN:
1. Behalte ALLE Pathologien bei — verliere NIEMALS eine Diagnose
2. "mit" + unklarer Begriff nach Sehnen-Untersuchung → "mit Begleitbursitis"
3. VERÄNDERE KEINE ZAHLEN! "18 mm" bleibt "18 mm", nicht "1,8 mm". "15 mm²" bleibt "15 mm²". Messwerte sind heilig.
4. VERÄNDERE KEINE ANATOMISCHEN LOKALISATIONEN! "axillär" bleibt "axillär", nicht "lateral". 
5. Gib NUR den korrigierten Text aus, keine Erklärungen

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
          generationConfig: { temperature: 0.0 }
        })
      }, 120_000, 3);

      const data = await response.json();
      if (data.error) {
        console.warn('[CORRECT] Gemini correction error:', data.error.message);
        return rawText;
      }

      const corrected = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';
      console.log(`[CORRECT] Raw: "${rawText.substring(0, 100)}..."`);
      console.log(`[CORRECT] Corrected: "${corrected.substring(0, 100)}..."`);
      return corrected || rawText;
    } catch (e: any) {
      console.warn('[CORRECT] Correction failed:', e.message);
      return rawText;
    }
  };

  // Call Gemini API to Structure the Transcript (Aligned 1:1 with EXE parameters)
  const callGeminiLLM = async (rawText: string, templateBody: string, regionName: string, examples: string): Promise<string> => {
    if (!vertexApiKey) {
      throw new Error("Es ist kein Vertex AI API-Key konfiguriert. Bitte in den Einstellungen eintragen.");
    }

    const url = VERTEX_ENDPOINT;
    const authHeaders: Record<string, string> = { 'Content-Type': 'application/json', 'x-goog-api-key': vertexApiKey };

    setStatusText("Strukturiere mit Gemini...");

    let promptText = systemPrompt
      .replace("{roh_text}", rawText)
      .replace("{template_body}", templateBody)
      .replace("{region_name}", regionName);

    if (promptText.includes("{examples}")) {
      promptText = promptText.replace("{examples}", examples);
    } else {
      promptText = promptText + "\n\n" + examples;
    }

    const sysMsg = "Du bist ein präziser Radiologie-Assistent. Strukturiere das Diktat unter Verwendung des bereitgestellten Normalbefund-Templates. Nutze ## Befund und ## Ergebnis als Haupttitel.";

    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        contents: [{
          role: "user",
          parts: [{
            text: promptText
          }]
        }],
        systemInstruction: {
          parts: [{
            text: sysMsg
          }]
        },
        generationConfig: {
          temperature: 0.0
        }
      })
    }, 120_000, 3);

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error.message || "Gemini API Fehler.");
    }

    const outputText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
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
5. KEINE ERFUNDENE DIAGNOSE: Der Befund darf keine Diagnosen enthalten, die im Diktat nicht erwähnt wurden.
6. ZAHLEN UND MESSWERTE: Alle Zahlen aus dem Diktat müssen exakt im Befund stehen (Cobb-Winkel, mm, BI-RADS etc.).
7. SPRACHERKENNUNGSKORREKTUR: Prüfe ob offensichtliche Spracherkennungsfehler im Diktat korrekt interpretiert wurden (z.B. "Antibiotik" → "Antelisthese", "Strichunkelvertebalatosen" → "Unkovertebralgelenksarthrosen", "Flachbügelingskonvexe" → "flachbogige Konvexität").

Wenn der Befund FEHLERFREI ist, gib ihn UNVERÄNDERT zurück.
Wenn es FEHLER gibt, korrigiere den Befund und gib die korrigierte Version zurück.
Gib NUR den fertigen Befundtext aus (mit ## Befund und ## Ergebnis), keine Erklärungen.

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
          generationConfig: { temperature: 0.0 }
        })
      }, 120_000, 3);

      const data = await response.json();
      if (data.error) {
        console.warn('[VALIDATE] Validation error:', data.error.message);
        return generatedReport;
      }

      const validated = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';
      if (!validated || !validated.includes('## Befund')) {
        console.warn('[VALIDATE] Validation output invalid, using original');
        return generatedReport;
      }

      // Check if validation changed anything
      if (validated.trim() === generatedReport.trim()) {
        console.log('[VALIDATE] Befund war bereits fehlerfrei ✅');
      } else {
        console.log('[VALIDATE] Befund wurde korrigiert ⚠️');
      }
      return validated;
    } catch (e: any) {
      console.warn('[VALIDATE] Validation failed:', e.message);
      return generatedReport;
    }
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

      // 1:1 Matching logic from EXE version
      const detectedKey = detectTemplate(finalRawText);
      const activeTemplate = templates[detectedKey] || templates['allgemein'] || {
        display_name: "Allgemeine Untersuchung",
        body: "Befund der untersuchten Region entsprechend dem Standardvorgehen.\nErgebnis der radiologischen Pathologien."
      };
      if (detectedKey === 'allgemein') {
        console.warn('[TEMPLATE] Region nicht erkannt — verwende Allgemein-Template');
        setStatusText('⚠️ Region nicht erkannt — Allgemein-Template wird verwendet');
      }

      // RAG-Bypass-Shortcut for pure normal findings (1:1 from EXE version)
      if (isNormalFinding(finalRawText)) {
        console.log(`[BYPASS] Normalbefund erkannt. Generiere direkt aus Template.`);
        let formattedRaw = finalRawText.trim();
        if (formattedRaw) {
          formattedRaw = formattedRaw[0].toUpperCase() + formattedRaw.slice(1);
          if (!formattedRaw.endsWith('.')) {
            formattedRaw += '.';
          }
        }
        
        const report = `## Befund\n${activeTemplate.body}\n\n## Ergebnis\n${formattedRaw}`;
        setStructuredReport(report);
        setStatus('ready');
        setStatusText('Bereit');
        
        await copyTextToClipboard(report);
        return;
      }

      // Normal path: structure with LLM
      const examples = getFewShotExamples(finalRawText);
      if (!vertexApiKey) {
        throw new Error("KI-Strukturierung nicht möglich: Es ist kein Vertex AI API-Key konfiguriert.");
      }

      const structuredText = await callGeminiLLM(
        finalRawText, 
        activeTemplate.body, 
        activeTemplate.display_name, 
        examples
      );

      // Step 3: Konsistenz-Validierung gegen das Diktat
      setStatusText('Validiere Befund-Konsistenz...');
      const validatedReport = await validateReportConsistency(finalRawText, structuredText);

      setStructuredReport(validatedReport);
      setStatus('ready');
      setStatusText('Bereit');

      await copyTextToClipboard(validatedReport);

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

      // Step 2: Template detection + LLM structuring (same as stopRecording)
      const detectedKey = detectTemplate(finalRawText);
      const activeTemplate = templates[detectedKey] || templates['allgemein'] || {
        display_name: "Allgemeine Untersuchung",
        body: "Befund der untersuchten Region entsprechend dem Standardvorgehen.\nErgebnis der radiologischen Pathologien."
      };
      if (detectedKey === 'allgemein') {
        console.warn('[TEMPLATE] Region nicht erkannt — verwende Allgemein-Template');
        setStatusText('⚠️ Region nicht erkannt — Allgemein-Template wird verwendet');
      }

      // Normalbefund-Bypass
      if (isNormalFinding(finalRawText)) {
        console.log(`[UPLOAD] Normalbefund erkannt. Generiere direkt aus Template.`);
        let formattedRaw = finalRawText.trim();
        if (formattedRaw) {
          formattedRaw = formattedRaw[0].toUpperCase() + formattedRaw.slice(1);
          if (!formattedRaw.endsWith('.')) {
            formattedRaw += '.';
          }
        }
        const report = `## Befund\n${activeTemplate.body}\n\n## Ergebnis\n${formattedRaw}`;
        setStructuredReport(report);
        setStatus('ready');
        setStatusText('Bereit');
        await copyTextToClipboard(report);
        return;
      }

      // Normal path: structure with LLM
      const examples = getFewShotExamples(finalRawText);
      if (!vertexApiKey) {
        throw new Error("KI-Strukturierung nicht möglich: Es ist kein Vertex AI API-Key konfiguriert.");
      }

      setStatusText('KI-Strukturierung läuft (Gemini Flash)...');
      const structuredText = await callGeminiLLM(
        finalRawText,
        activeTemplate.body,
        activeTemplate.display_name,
        examples
      );

      // Step 3: Konsistenz-Validierung gegen das Diktat
      setStatusText('Validiere Befund-Konsistenz...');
      const validatedReport = await validateReportConsistency(finalRawText, structuredText);

      setStructuredReport(validatedReport);
      setStatus('ready');
      setStatusText('Bereit');
      await copyTextToClipboard(validatedReport);

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F10') {
        e.preventDefault();
        if (statusRef.current === 'recording') {
          stopRecordingRef.current();
        } else if (statusRef.current === 'ready') {
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


  // Render Login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="login-container">
        {/* Canvas background for login */}
        <canvas ref={canvasRef} id="particle-canvas" />

        <div className="login-card" style={{ zIndex: 1 }}>
          <div className="login-header">
            <div className="login-icon">
              <Aperture size={40} />
            </div>
            <h1 className="login-title">RaKScribe26 Web</h1>
            <p className="login-subtitle">Radiologische Befundungssoftware im Browser</p>
          </div>

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Benutzername (Praxis-Login)</label>
              <input 
                type="text" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="z.B. dr.kalmar"
                className="form-input"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Passwort</label>
              <div className="password-wrapper">
                <input 
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onDrop={async e => {
                    e.preventDefault();
                    const f = e.dataTransfer.files?.[0];
                    if (f) {
                      const txt = await f.text();
                      setPassword(txt);
                    }
                  }}
                  onDragOver={e => e.preventDefault()}
                  placeholder="Passwort eingeben (oder JSON-Key hierher ziehen)"
                  className="form-input"
                  required
                />
                <Lock className="password-icon" size={18} />
              </div>
            </div>

            {authError && (
              <div className="login-error">
                {authError}
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', height: '48px', marginTop: '10px' }}>
              Anmelden <ArrowRight size={18} />
            </button>
          </form>

          <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #1E2235', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Benötigen Sie Hilfe? Kontaktieren Sie die Praxis-IT. <br />
            <span style={{ fontStyle: 'italic', display: 'block', marginTop: '4px' }}>Alternativ: Praxis-JSON-Key (Drive → RaKScribe) in das Passwortfeld ziehen</span>
          </div>
        </div>
      </div>
    );
  }

  // Render workspace dashboard
  return (
    <div className="flex-grow flex flex-col" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)', position: 'relative' }}>
      {/* Background canvas for particles */}
      <canvas ref={canvasRef} id="particle-canvas" />

      {/* Header bar */}
      <header className="app-header" style={{ zIndex: 1 }}>
        <div className="brand-section">
          <div className="brand-icon">
            <Aperture size={24} />
          </div>
          <div className="brand-title-group">
            <div className="brand-name">
              <span>RaKScribe26</span>
              <span className="brand-badge">Web Beta v2.9.2</span>
            </div>
            <span className="brand-desc">Befundungsassistent</span>
          </div>
        </div>

        {/* Status indicator & selectors */}
        <div className="header-actions">
          <div className="status-badge" style={{ color: status === 'recording' ? 'var(--recording-red)' : status === 'processing' ? 'var(--warning-yellow)' : 'var(--ready-green)' }}>
            <span className={`status-dot ${status === 'recording' ? 'recording' : status === 'processing' ? 'processing' : 'ready'}`} />
            <span>{statusText.toUpperCase()}</span>
          </div>

          {/* Download Desktop EXE */}
          <a
            href="https://github.com/drpeterkalmar/RaKScribe26/releases/latest/download/rakscribe26.exe"
            target="_blank"
            rel="noopener noreferrer"
            className="icon-btn"
            title="Windows Desktop-App herunterladen"
            style={{ textDecoration: 'none' }}
          >
            <Download size={20} />
          </a>

          {/* Logout button */}
          <button 
            onClick={handleLogout}
            className="icon-btn logout"
            title="Abmelden"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      {/* Configuration Control Panel */}
      <div className="status-bar" style={{ zIndex: 1, padding: '16px 24px' }}>
        {/* Microphone Dropdown Selector */}
        <div className="status-bar-item">
          <span className="status-bar-label">Mikrofon:</span>
          <select
            value={selectedDeviceId}
            onChange={e => {
              setSelectedDeviceId(e.target.value);
              localStorage.setItem('selected_audio_device_id', e.target.value);
            }}
            className="select-input"
            style={{ 
              background: 'var(--bg-input)', 
              color: '#fff', 
              border: '1px solid var(--border-color)', 
              borderRadius: '6px', 
              padding: '6px 24px 6px 10px', 
              fontSize: '13px',
              fontFamily: 'var(--sans-font)',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="">Standard-Mikrofon</option>
            {audioDevices.map(device => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Mikrofon (${device.deviceId.slice(0, 8)}...)`}
              </option>
            ))}
          </select>
        </div>

        {/* Vertex AI API Key Input */}
        <div className="status-bar-item">
          <span className="status-bar-label">Vertex AI API Key:</span>
          {vertexApiKey ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="status-bar-value success">
                <Check size={14} className="status-bar-icon" /> LLM aktiv
              </span>
              <span className={sttKeyJson ? "status-bar-value success" : "status-bar-value danger"} style={{ pointerEvents: 'none' }}>
                STT: {sttKeyJson ? 'Google Cloud' : 'nur Whisper (Server nötig)'}
              </span>
              <button
                className="icon-btn logout"
                style={{ padding: '4px 8px', height: '26px', minWidth: 'unset', display: 'flex', alignItems: 'center' }}
                onClick={() => {
                  setVertexApiKey('');
                  localStorage.removeItem('vertex_api_key');
                }}
                title="API-Key entfernen"
              >
                🗑
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="text"
                placeholder="Vertex AI API-Key eingeben"
                className="select-input"
                style={{
                  background: 'var(--bg-input)',
                  color: '#fff',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  fontSize: '13px',
                  fontFamily: 'var(--sans-font)',
                  outline: 'none',
                  width: '300px'
                }}
                onChange={e => {
                  const val = e.target.value.trim();
                  setVertexApiKey(val);
                  if (val) localStorage.setItem('vertex_api_key', val);
                  else localStorage.removeItem('vertex_api_key');
                }}
              />
              <span className={sttKeyJson ? "status-bar-value success" : "status-bar-value danger"} style={{ pointerEvents: 'none' }}>
                <X size={14} className="status-bar-icon" /> STT: {sttKeyJson ? 'Google Cloud aktiv' : 'nur Whisper (Server nötig)'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Workspace */}
      <main className="workspace-grid" style={{ zIndex: 1 }}>
        {/* Left Side: Live Transcription & Controls */}
        <section className="workspace-card">
          <div className="card-header">
            <div className="card-title-group">
              <Mic className="card-icon" size={18} />
              <h2 className="card-title">Live-Diktat & Spracherkennung</h2>
            </div>
            <span className="card-badge">
              Engine: WHISPER (lokal)
            </span>
          </div>

          <div className="card-body">
            <textarea
              value={transcript + (isTranscribingChunk ? " [..]" : "")}
              onChange={e => {
                const cleanVal = e.target.value.endsWith(" [..]")
                  ? e.target.value.slice(0, -5)
                  : e.target.value;
                setTranscript(cleanVal);
              }}
              placeholder="Hier erscheint das Live-Diktat... Sie können das Diktat auch manuell bearbeiten oder kopieren."
              className="text-editor"
            />

            {/* Level meter during recording */}
            {status === 'recording' && (
              <div className="level-meter-container">
                <span className="level-meter-label">Pegel</span>
                <div className="level-meter-track">
                  <div 
                    className="level-meter-bar"
                    style={{ width: `${micLevel}%` }}
                  />
                </div>
                <span className="level-meter-value">{micLevel}%</span>
              </div>
            )}
          </div>

          <div className="card-footer">
            <button onClick={handleReset} className="btn btn-secondary btn-large-action">
              Zurücksetzen
            </button>

            {status === 'recording' ? (
              <button onClick={stopRecording} className="btn btn-danger btn-large-action pulse-recording">
                <MicOff size={18} /> Aufnahme Stoppen
              </button>
            ) : (
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button onClick={startRecording} disabled={status === 'processing'} className="btn btn-primary btn-large-action">
                  <Mic size={18} /> Aufnahme Starten
                </button>
                <button
                  onClick={() => audioUploadRef.current?.click()}
                  disabled={status === 'processing'}
                  className="btn btn-secondary btn-large-action"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  title="Sprachnachricht oder Audio-Datei hochladen"
                >
                  <Upload size={18} /> Audio hochladen
                </button>
                <input
                  ref={audioUploadRef}
                  type="file"
                  accept="audio/*,.ogg,.mp3,.wav,.m4a,.opus,.webm"
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files?.[0]) {
                      handleAudioUpload(e.target.files[0]);
                      e.target.value = ''; // reset so same file can be re-uploaded
                    }
                  }}
                />
              </div>
            )}
          </div>
        </section>

        {/* Right Side: Structured Report */}
        <section className="workspace-card">
          <div className="card-header">
            <div className="card-title-group">
              <Sparkles className="card-icon" size={18} />
              <h2 className="card-title">Strukturierter Befund</h2>
            </div>
            
            {isCopied && (
              <span className="copied-badge">
                <Check size={12} /> Kopiert!
              </span>
            )}
          </div>

          <div className="card-body">
            <textarea
              value={structuredReport}
              readOnly
              placeholder="Der strukturierte Bericht wird nach Abschluss des Diktats hier eingefügt."
              className="text-editor"
            />
          </div>

          <div className="card-footer">
            <span className="footer-info">Kopieren Sie das Ergebnis für RIS oder Word.</span>
            
            <button
              onClick={handleCopyReport}
              disabled={!structuredReport}
              className="btn btn-primary btn-large-action"
            >
              <Copy size={16} /> Befund Kopieren
            </button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer style={{ padding: '12px 24px', borderTop: '1px solid var(--border-color)', zIndex: 1, textAlign: 'center', fontSize: '11px', color: 'var(--text-secondary)' }}>
        <span>&copy; {new Date().getFullYear()} Praxis "Röntgen am Kai" &bull; RaKScribe26</span>
      </footer>
    </div>
  );
}
