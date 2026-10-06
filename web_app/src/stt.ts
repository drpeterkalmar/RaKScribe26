// Spracherkennung der Web-App (Umbau Schritt 8): Google STT v1 (6-s-Chunks, Live-Anzeige), chirp_3 (STT v2,
// komplettes Diktat), Whisper-Fallback. Aus App.tsx herausgelöst, damit Abbruch und Fehlerweitergabe ohne Browser
// testbar sind (web_app/pipeline_test.mjs). Gleiche Requests wie vorher.
// Gutachten P2-10: Whisper (http://localhost:8765) nur noch, wenn die App selbst auf localhost läuft oder
// localStorage.whisper_fallback === '1' — sonst kommt die echte Google-Fehlermeldung beim Nutzer an.
import { fetchWithRetry, istAbbruch } from './net.ts';

export type SttSchluessel = { client_email: string; private_key: string };
export type SttKontext = {
  sttKey: SttSchluessel | null;
  signal?: AbortSignal;
  status?: (text: string) => void;
};

// Speech-Context Phrasen für Google STT (medizinischer Jargon, boost 15.0)
export const MEDICAL_PHRASES: string[] = [
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


// v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation). A/B echte + synthetische Diktate:
// Termini 41/47 → 45/47 (flachbogig, Cobb-Winkel, Mammasonographie, Discopathiezeichen, Fibroostosen,
// Rhizarthrose, Arthro-Broström). BEWUSST KURZ — die 692er-Liste verschlechterte chirp_3 (25/29 statt 26/29).
export const CHIRP_PHRASES: string[] = [
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

// ── Base64 ohne FileReader (gleiches Ergebnis wie readAsDataURL, auch in Node testbar) ──
export function base64AusBytes(bytes: Uint8Array): string {
  let out = '';
  const STUECK = 3 * 16384; // Vielfaches von 3 (Base64 ohne Füllzeichen in der Mitte), < 65536 Argumente (Safari)
  for (let i = 0; i < bytes.length; i += STUECK) {
    out += btoa(String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + STUECK))));
  }
  return out;
}

export const blobToBase64 = async (blob: Blob): Promise<string> =>
  base64AusBytes(new Uint8Array(await blob.arrayBuffer()));

// ── GOOGLE CLOUD STT — Service-Account (rakscribe-stt@) → JWT → Bearer Token ──
const toBase64Url = (buffer: ArrayBuffer): string =>
  btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

async function signJwt(payload: object, privateKeyPem: string): Promise<string> {
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
  const headerB64 = toBase64Url(enc.encode(JSON.stringify(header)).buffer as ArrayBuffer);
  const payloadB64 = toBase64Url(enc.encode(JSON.stringify(payload)).buffer as ArrayBuffer);
  const signingInput = `${headerB64}.${payloadB64}`;
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', cryptoKey, enc.encode(signingInput));
  return `${signingInput}.${toBase64Url(sig)}`;
}

const SCOPE = 'https://www.googleapis.com/auth/cloud-platform';
const tokenCache: { [clientEmail: string]: { token: string; expiry: number } } = {};

// Gültiges Bearer-Token für den STT-Service-Account (gecacht, Erneuerung 2 min vor Ablauf)
export async function getSttToken(keyJson: SttSchluessel | null, signal?: AbortSignal): Promise<string> {
  if (!keyJson) throw new Error('STT-Schluessel nicht geladen.');
  const now = Math.floor(Date.now() / 1000);
  const cached = tokenCache[keyJson.client_email];
  if (cached && cached.expiry > now + 120) return cached.token;
  const jwt = await signJwt({
    iss: keyJson.client_email,
    scope: SCOPE,
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  }, keyJson.private_key);
  const resp = await fetchWithRetry('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
    signal,
  }, 30_000, 3);
  const data = await resp.json();
  if (!data.access_token) throw new Error('Google OAuth Fehler: ' + JSON.stringify(data));
  tokenCache[keyJson.client_email] = { token: data.access_token, expiry: now + (data.expires_in || 3600) };
  return data.access_token;
}

type SttErgebnis = { results?: { alternatives: { transcript: string }[] }[]; error?: { message?: string } };
const transkriptAus = (data: SttErgebnis): string =>
  (data.results || []).map(r => r.alternatives[0].transcript).join(' ');

// Chunk-Transkription (6-s-Chunks während der Aufnahme, latest_long) — nur Live-Anzeige
export async function transcribeChunkWithGoogle(wavBlob: Blob, ctx: SttKontext): Promise<string> {
  const token = await getSttToken(ctx.sttKey, ctx.signal);
  ctx.status?.('Transkribiere (Google Cloud STT)...');
  const base64Data = await blobToBase64(wavBlob);
  const response = await fetchWithRetry('https://speech.googleapis.com/v1/speech:recognize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
      config: {
        encoding: 'LINEAR16', sampleRateHertz: 16000, languageCode: 'de-DE',
        enableAutomaticPunctuation: true, model: 'latest_long', useEnhanced: true,  // WER-Test 03.09.: short verliert Material
        speechContexts: [{ phrases: MEDICAL_PHRASES, boost: 15.0 }],
      },
      audio: { content: base64Data },
    }),
    signal: ctx.signal,
  }, 120_000, 3);
  const data: SttErgebnis = await response.json();
  if (data.error) throw new Error(data.error.message || 'Google STT Fehler.');
  return transkriptAus(data);
}

// FULL-AUDIO Transkription (v2.9.10): chirp_3 via STT v2 (Location eu).
// WER-Test 04.09.: chirp_3 = 2,4% (auch bei Echo/Daempfung) vs latest_long = 16,7%.
export async function chirp3Recognize(token: string, wavB64: string, signal?: AbortSignal): Promise<string> {
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
    signal,
  }, 120_000, 3);
  const data: SttErgebnis = await response.json();
  if (data.error) throw new Error(data.error.message || 'chirp_3 Fehler.');
  return transkriptAus(data);
}

export function stitchOverlaps(a: string, b: string, window = 14): string {
  const aw: string[] = a.split(' ');
  const bw: string[] = b.split(' ');
  let best = 0;
  for (let L = Math.min(window, aw.length, bw.length); L > 0; L--) {
    const tail = aw.slice(-L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
    const head = bw.slice(0, L).map(w => w.toLowerCase().replace(/[.,:;]/g, ''));
    if (tail.filter((w, i) => w === head[i]).length >= Math.floor(L * 0.8)) { best = L; break; }
  }
  return best ? a + ' ' + bw.slice(best).join(' ') : a + ' ' + b;
}

// Komplettes Diktat (16-kHz-WAV) → chirp_3. <=59 s: EIN Request; länger: 50-s-Segmente + 4 s Rückhören, Overlap-Stitch.
export async function transcribeFullAudioWithGoogle(wavBlob: Blob, ctx: SttKontext): Promise<string> {
  const token = await getSttToken(ctx.sttKey, ctx.signal);
  const base64Data = await blobToBase64(wavBlob);

  // Duration: 16000 samples/s * 2 bytes/sample = 32000 bytes/s (base64 ~4/3)
  const binarySize = Math.floor(base64Data.length * 3 / 4);
  const estimatedDurationSec = binarySize / 32000;
  console.log(`[FULL-AUDIO] ${binarySize} bytes, ~${estimatedDurationSec.toFixed(1)}s`);

  if (estimatedDurationSec <= 59) {
    ctx.status?.('Volltranskription läuft (chirp_3, komplettes Diktat)...');
    return await chirp3Recognize(token, base64Data, ctx.signal);
  }

  console.log('[FULL-AUDIO] chirp_3 Segmentierung (>60s)');
  ctx.status?.('Volltranskription läuft (langes Diktat, chirp_3, bitte warten)...');
  // WAV decodieren → Float32 → s16le-PCM
  const arrayBuffer = await wavBlob.arrayBuffer();
  const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctxTemp = new AC({ sampleRate: 16000 });
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
    texts.push(await chirp3Recognize(token, base64AusBytes(new Uint8Array(wav)), ctx.signal));
    if (end >= s16.length) break;
    start = end - OV;
  }
  let full = texts[0];
  for (let i = 1; i < texts.length; i++) full = stitchOverlaps(full, texts[i]);
  return full;
}

// ── Whisper (lokaler Server auf dem Praxis-PC) — nur noch lokal (Gutachten P2-10) ──
export function whisperErlaubt(): boolean {
  try {
    if (typeof location !== 'undefined' && location.hostname === 'localhost') return true;
    return typeof localStorage !== 'undefined' && localStorage.getItem('whisper_fallback') === '1';
  } catch {
    return false;
  }
}

export async function transcribeWithWhisper(audioBlob: Blob, signal?: AbortSignal): Promise<string> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.ogg');
  console.log('[WHISPER] Sende Audio an lokalen Whisper-Server...');
  const response = await fetchWithRetry('http://localhost:8765/whisper', {
    method: 'POST',
    body: formData,
    signal,
  }, 120_000, 3);
  const data = await response.json();
  if (data.error) {
    throw new Error('Whisper STT Fehler: ' + data.error);
  }
  const text = (data.text || '').trim();
  console.log(`[WHISPER] Fertig in ${data.elapsed_seconds}s (${text.length} Zeichen)`);
  return text;
}

const fehlertext = (err: unknown): string => (err instanceof Error ? err.message : String(err));

// Google zuerst; Whisper nur lokal, sonst die Google-Meldung an den Nutzer (P2-10). Abbruch wird immer weitergereicht.
export async function mitFallback(google: () => Promise<string>, whisperAudio: Blob, ctx: SttKontext): Promise<string> {
  try {
    return await google();
  } catch (sttErr: unknown) {
    if (istAbbruch(sttErr)) throw sttErr;
    if (!whisperErlaubt()) {
      throw new Error(`Google-Spracherkennung fehlgeschlagen: ${fehlertext(sttErr)}`, { cause: sttErr });
    }
    console.warn('[STT] Google fehlgeschlagen, Whisper-Fallback:', fehlertext(sttErr));
    ctx.status?.('Spracherkennung läuft (Whisper, Fallback)...');
    return await transcribeWithWhisper(whisperAudio, ctx.signal);
  }
}

// Wrapper wie bisher: isFull = komplettes Diktat (chirp_3), sonst 6-s-Chunk (latest_long)
export const transcribeAudio = (wavBlob: Blob, isFull: boolean, ctx: SttKontext): Promise<string> =>
  mitFallback(() => (isFull ? transcribeFullAudioWithGoogle(wavBlob, ctx) : transcribeChunkWithGoogle(wavBlob, ctx)),
    wavBlob, ctx);
