import React, { useState, useEffect, useRef } from 'react';
import { 
  Aperture, 
  Mic, 
  MicOff, 
  Copy, 
  Check, 
  Settings, 
  LogOut, 
  Save, 
  Lock, 
  ArrowRight,
  Sparkles,
  Info
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
  "Flachbogig", "S-förmige"
];


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
  const [provider, setProvider] = useState<'gemini' | 'openai'>('gemini');
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  // Google Cloud STT – service account JSON or simple API-key JSON
  const [googleKeyJson, setGoogleKeyJson] = useState<any>(null);
  const [googleKeyFileName, setGoogleKeyFileName] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Cached access token for service-account auth
  const googleTokenRef = useRef<string>('');
  const googleTokenExpiryRef = useRef<number>(0);

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
    const savedGeminiKey = localStorage.getItem('gemini_api_key');
    const savedProvider = localStorage.getItem('llm_provider');
    const savedPrompt = localStorage.getItem('system_prompt');
    const savedAuth = localStorage.getItem('is_authenticated');
    const savedKeyJson = localStorage.getItem('google_key_json');
    const savedKeyName = localStorage.getItem('google_key_filename');

    if (savedGeminiKey) setGeminiApiKey(savedGeminiKey);
    if (savedProvider) setProvider(savedProvider as 'gemini' | 'openai');
    if (savedKeyJson) { try { setGoogleKeyJson(JSON.parse(savedKeyJson)); } catch {} }
    if (savedKeyName) setGoogleKeyFileName(savedKeyName);
    if (savedAuth === 'true') setIsAuthenticated(true);
    
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
      `- Bei Normalbefund: 'Unauffälliger Befund.' oder der entsprechende Kurztext.\n\n` +
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
  const saveConfig = () => {
    localStorage.setItem('gemini_api_key', geminiApiKey);
    localStorage.setItem('llm_provider', provider);
    localStorage.setItem('system_prompt', systemPrompt);
    if (googleKeyJson) localStorage.setItem('google_key_json', JSON.stringify(googleKeyJson));
    if (googleKeyFileName) localStorage.setItem('google_key_filename', googleKeyFileName);
    alert('Einstellungen erfolgreich gespeichert!');
    setShowSettings(false);
  };

  // Login Handler
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim() !== '' && password === 'rakscribe') {
      setIsAuthenticated(true);
      localStorage.setItem('is_authenticated', 'true');
      setAuthError('');
    } else {
      setAuthError('Ungültige Anmeldedaten. (Tipp: Passwort ist "rakscribe")');
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

  // ── Google Cloud STT – JSON Key File handling ──────────────────────────────

  const loadGoogleKeyFile = (file: File) => {
    if (!file.name.endsWith('.json')) {
      alert('Bitte eine Google Cloud JSON-Schlüsseldatei hochladen.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target?.result as string);
        setGoogleKeyJson(parsed);
        setGoogleKeyFileName(file.name);
        localStorage.setItem('google_key_json', JSON.stringify(parsed));
        localStorage.setItem('google_key_filename', file.name);
        // Invalidate cached token
        googleTokenRef.current = '';
        googleTokenExpiryRef.current = 0;
      } catch {
        alert('Ungültige JSON-Datei.');
      }
    };
    reader.readAsText(file);
  };

  // Base64url encode a Uint8Array
  const toBase64Url = (buffer: ArrayBuffer): string =>
    btoa(String.fromCharCode(...new Uint8Array(buffer)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

  // Sign a JWT with RS256 using a PKCS8 PEM private key (service account)
  const signJwt = async (payload: object, privateKeyPem: string): Promise<string> => {
    const header = { alg: 'RS256', typ: 'JWT' };
    const pemBody = privateKeyPem
      .replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\n|\r/g, '');
    const derBinary = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
    const cryptoKey = await crypto.subtle.importKey(
      'pkcs8', derBinary.buffer,
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

  // Get a valid Bearer token for service accounts (cached, auto-refresh)
  const getGoogleBearerToken = async (keyJson: any): Promise<string> => {
    const now = Math.floor(Date.now() / 1000);
    if (googleTokenRef.current && googleTokenExpiryRef.current > now + 60) {
      return googleTokenRef.current;
    }
    const jwt = await signJwt({
      iss: keyJson.client_email,
      scope: 'https://www.googleapis.com/auth/cloud-platform',
      aud: 'https://oauth2.googleapis.com/token',
      iat: now,
      exp: now + 3600,
    }, keyJson.private_key);
    const resp = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
    });
    const data = await resp.json();
    if (!data.access_token) throw new Error('Google OAuth Fehler: ' + JSON.stringify(data));
    googleTokenRef.current = data.access_token;
    googleTokenExpiryRef.current = now + (data.expires_in || 3600);
    return data.access_token;
  };

  // Google Cloud Speech-to-Text REST API Call (supports API key or service account JSON)
  const transcribeWithGoogle = async (wavBlob: Blob): Promise<string> => {
    if (!googleKeyJson) {
      throw new Error('Bitte laden Sie Ihre Google Cloud JSON-Schlüsseldatei in den Einstellungen hoch.');
    }
    setStatusText('Transkribiere mit Google Cloud STT...');

    // Determine auth method from JSON structure
    let url: string;
    let authHeaders: Record<string, string> = { 'Content-Type': 'application/json' };

    if (googleKeyJson.type === 'service_account' && googleKeyJson.private_key) {
      // Service Account: generate Bearer token via JWT
      const token = await getGoogleBearerToken(googleKeyJson);
      url = 'https://speech.googleapis.com/v1/speech:recognize';
      authHeaders['Authorization'] = `Bearer ${token}`;
    } else {
      // Simple API key (stored in json as "api_key" or "key")
      const apiKey = googleKeyJson.api_key || googleKeyJson.key || googleKeyJson.apiKey;
      if (!apiKey) throw new Error('JSON-Datei enthält weder "type":"service_account" noch "api_key".');
      url = `https://speech.googleapis.com/v1/speech:recognize?key=${apiKey}`;
    }

    const reader = new FileReader();
    return new Promise((resolve, reject) => {
      reader.onloadend = async () => {
        try {
          const base64Data = (reader.result as string).split(',')[1];
          const response = await fetch(url, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({
              config: {
                encoding: 'LINEAR16',
                sampleRateHertz: 16000,
                languageCode: 'de-DE',
                enableAutomaticPunctuation: true,
                model: 'latest_long',
                useEnhanced: true,
                speechContexts: [{ phrases: MEDICAL_PHRASES, boost: 15.0 }],
              },
              audio: { content: base64Data },
            }),
          });
          const data = await response.json();
          if (data.error) { reject(new Error(data.error.message || 'Google STT Fehler.')); return; }
          const results = data.results || [];
          resolve(results.map((r: any) => r.alternatives[0].transcript).join(' '));
        } catch (err) { reject(err); }
      };
      reader.onerror = () => reject(new Error('Fehler beim Lesen der Audiodatei.'));
      reader.readAsDataURL(wavBlob);
    });
  };
  // ─────────────────────────────────────────────────────────────────────────

  // Call Gemini API to Structure the Transcript
  // Call Gemini API to Structure the Transcript (Aligned 1:1 with EXE parameters)
  const callGeminiLLM = async (rawText: string, templateBody: string, regionName: string, examples: string): Promise<string> => {
    let url: string;
    let authHeaders: Record<string, string> = { 'Content-Type': 'application/json' };

    if (googleKeyJson && googleKeyJson.type === 'service_account' && googleKeyJson.private_key) {
      // Service Account: generate Bearer token via JWT
      const token = await getGoogleBearerToken(googleKeyJson);
      url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';
      authHeaders['Authorization'] = `Bearer ${token}`;
    } else if (geminiApiKey) {
      // Simple API key
      url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`;
    } else {
      throw new Error("Weder ein Gemini API-Key noch eine Google Cloud Service-Account JSON-Datei ist konfiguriert.");
    }

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

    const response = await fetch(url, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        contents: [{
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
    });

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error.message || "Gemini API Fehler.");
    }

    const outputText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return outputText;
  };

  // Start Audio Recording
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
      
      const p = transcribeWithGoogle(wavBlob).then(text => {
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
        
        const p = transcribeWithGoogle(wavBlob).then(text => {
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
      // Wait for any active/pending requests to finish
      if (pendingPromisesRef.current.length > 0) {
        setStatusText('Warte auf ausstehende Transkriptionen...');
        await Promise.all(pendingPromisesRef.current);
      }

      const finalRawText = chunkTranscriptsRef.current.filter(t => t.trim()).join(' ');
      setTranscript(finalRawText);

      if (!finalRawText.trim()) {
        throw new Error("Es wurde kein gesprochener Text erkannt.");
      }

      // 1:1 Matching logic from EXE version
      const isNormalFinding = (text: string): boolean => {
        const textLower = text.toLowerCase();
        const normalKeywords = ["unauffällig", "normal", "regelrecht", "ohne befund", "kein nachweis", "unauffaellig"];
        const hasNormal = normalKeywords.some(kw => textLower.includes(kw));
        const isShort = textLower.split(/\s+/).filter(Boolean).length < 12;
        return hasNormal && isShort;
      };

      const detectedKey = detectTemplate(finalRawText);
      const activeTemplate = templates[detectedKey] || templates['allgemein'] || { 
        display_name: "Allgemeine Untersuchung",
        body: "Befund der untersuchten Region entsprechend dem Standardvorgehen.\nErgebnis der radiologischen Pathologien."
      };

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
      const isLlmAvailable = !!geminiApiKey || (googleKeyJson && googleKeyJson.type === 'service_account' && googleKeyJson.private_key);
      let structuredText = "";
      if (isLlmAvailable) {
        structuredText = await callGeminiLLM(
          finalRawText, 
          activeTemplate.body, 
          activeTemplate.display_name, 
          examples
        );
      } else {
        setStatusText("Lokal simulierte KI-Strukturierung...");
        await new Promise(r => setTimeout(r, 1200));
        let formattedRaw = finalRawText.trim();
        if (formattedRaw) {
          formattedRaw = formattedRaw[0].toUpperCase() + formattedRaw.slice(1);
          if (!formattedRaw.endsWith('.')) {
            formattedRaw += '.';
          }
        }
        structuredText = `## Befund\n${activeTemplate.body}\n\n## Ergebnis\n${formattedRaw}`;
      }

      setStructuredReport(structuredText);
      setStatus('ready');
      setStatusText('Bereit');

      await copyTextToClipboard(structuredText);

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
                  placeholder="Passwort eingeben"
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
            <span style={{ fontStyle: 'italic', display: 'block', marginTop: '4px' }}>(Passwort für Testzwecke: "rakscribe")</span>
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
              <span className="brand-badge">Web Beta v2.7.0</span>
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

          {/* Settings button */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="icon-btn"
            title="Einstellungen"
          >
            <Settings size={20} />
          </button>

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
              Engine: GOOGLE CLOUD STT
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
              <button onClick={startRecording} disabled={status === 'processing'} className="btn btn-primary btn-large-action">
                <Mic size={18} /> Aufnahme Starten
              </button>
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

      {/* Settings Dialog (Modal) */}
      {showSettings && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ zIndex: 110 }}>
            <div className="modal-header">
              <h2 className="modal-title"><Settings size={22} className="card-icon" /> Konfiguration & Schlüssel</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="modal-close"
              >
                &times;
              </button>
            </div>

            <div className="modal-body">
              {/* STT Config – Google Cloud only */}
              <div className="settings-section">
                <h3 className="settings-sec-title">1. Google Cloud Speech-to-Text – JSON-Schlüssel</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '10px' }}>
                  Laden Sie Ihre <strong style={{color:'#fff'}}>Service Account JSON</strong>-Datei hoch (aus Google Cloud Console → IAM → Dienstkontoschlüssel), oder eine JSON mit <code style={{color:'#C4A4FF'}}>"api_key"</code>-Feld.
                </p>

                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  style={{ display: 'none' }}
                  onChange={e => { if (e.target.files?.[0]) loadGoogleKeyFile(e.target.files[0]); }}
                />

                {/* Drag & Drop Zone */}
                <div
                  className={`key-dropzone ${isDragOver ? 'drag-over' : ''} ${googleKeyJson ? 'has-key' : ''}`}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={e => {
                    e.preventDefault();
                    setIsDragOver(false);
                    const file = e.dataTransfer.files[0];
                    if (file) loadGoogleKeyFile(file);
                  }}
                >
                  {googleKeyJson ? (
                    <>
                      <span className="dropzone-icon">✓</span>
                      <div>
                        <span className="dropzone-filename">{googleKeyFileName}</span>
                        <span className="dropzone-hint">
                          {googleKeyJson.type === 'service_account'
                            ? `Service Account: ${googleKeyJson.client_email}`
                            : 'API Key geladen'}
                        </span>
                      </div>
                    </>
                  ) : (
                    <>
                      <span className="dropzone-icon">↑</span>
                      <div>
                        <span className="dropzone-filename">JSON-Schlüssel hier droppen</span>
                        <span className="dropzone-hint">oder klicken zum Auswählen</span>
                      </div>
                    </>
                  )}
                </div>

                {googleKeyJson && (
                  <button
                    className="btn btn-secondary"
                    style={{ marginTop: '8px', fontSize: '12px', padding: '6px 14px', height: 'auto', minWidth: 'unset', color: '#FDA29B' }}
                    onClick={() => {
                      setGoogleKeyJson(null);
                      setGoogleKeyFileName('');
                      localStorage.removeItem('google_key_json');
                      localStorage.removeItem('google_key_filename');
                      googleTokenRef.current = '';
                    }}
                  >
                    🗑 Schlüssel entfernen
                  </button>
                )}
              </div>

              {/* LLM Config */}
              <div className="settings-section" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <h3 className="settings-sec-title">2. KI-Strukturierung (LLM)</h3>
                
                <div>
                  <label className="form-label">Gemini API-Key</label>
                  <input 
                    type="password"
                    value={geminiApiKey}
                    onChange={e => setGeminiApiKey(e.target.value)}
                    placeholder="Hinterlegen Sie Ihren Gemini API-Key"
                    className="form-input"
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', display: 'block' }}>
                    Für kostenlose Testzwecke können Sie einen Key im Google AI Studio erstellen. Bleibt das Feld leer, läuft ein lokaler Demo-Mock.
                  </span>
                </div>
              </div>

              {/* Prompt Config */}
              <div className="settings-section" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <h3 className="settings-sec-title">3. System-Prompt konfigurieren</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '10px' }}>
                  Der Prompt steuert, wie die KI Ihr Diktat strukturiert. Er orientiert sich an den Befundvorlagen der Praxis
                  (Nominalstil, zwei Abschnitte <code style={{color:'#C4A4FF'}}>## Befund</code> und <code style={{color:'#C4A4FF'}}>## Ergebnis</code>).
                  Platzhalter: <code style={{color:'#C4A4FF'}}>{'{roh_text}'}</code> = Diktat, <code style={{color:'#C4A4FF'}}>{'{template_body}'}</code> = Normalbefund-Vorlage, <code style={{color:'#C4A4FF'}}>{'{examples}'}</code> = Praxis-Beispiele.
                </p>
                <textarea
                  value={systemPrompt}
                  onChange={e => setSystemPrompt(e.target.value)}
                  rows={10}
                  className="settings-textarea"
                />
                <button
                  onClick={() => {
                    const confirmReset = window.confirm('Prompt auf Praxis-Standard zurücksetzen? Alle eigenen Änderungen gehen verloren.');
                    if (confirmReset) {
                      const resetPrompt = 
                        `<role>Radiologie-Assistent der Praxis "Röntgen am Kai" – Dr. P. Kalmar / Dr. G. Riegler</role>\n` +
                        `<instructions>\n` +
                        `Du bist ein präziser radiologischer Befundungsassistent für die Praxis "Röntgen am Kai" in Graz. Deine Aufgabe ist es, das diktierte Stichwortprotokoll des Arztes in einen formalen, professionellen radiologischen Befund zu strukturieren, der sich EXAKT an den historischen Befundvorlagen der Praxis orientiert.\n\n` +
                        `## STRIKTE FORMATREGELN:\n` +
                        `1. Erstelle IMMER exakt zwei Hauptabschnitte: '## Befund' und '## Ergebnis'. Kein weiterer Text, keine Kommentare, keine Erklärungen außerhalb dieser Abschnitte.\n` +
                        `2. Gib NUR den fertigen Befundtext aus – keine Einleitung, kein Schlusswort.\n\n` +
                        `## ABSCHNITT "## Befund":\n` +
                        `- Nutze das bereitgestellte Normalbefund-Template als genaue strukturelle Basis.\n` +
                        `- Passe gezielt die Sätze an, bei denen das Diktat pathologische Befunde nennt.\n` +
                        `- Behalte ALLE nicht genannten Regionen und Sätze des Templates UNVERÄNDERT.\n` +
                        `- Übernimm Messwerte exakt aus dem Diktat.\n` +
                        `- Schreibe im radiologischen Nominalstil.\n\n` +
                        `## ABSCHNITT "## Ergebnis":\n` +
                        `- Fasse alle diagnosewesentlichen Pathologien kurz und stichpunktartig zusammen.\n` +
                        `- Beispiele: 'Intakte Hüft-TEP rechts.', 'Coxarthrose links.', 'STT-Arthrose beidseits.', 'Osteochondrosis pubis.', 'Beckenschiefstand nach links um 4 mm.'\n` +
                        `</instructions>\n` +
                        `<normalbefund_template>\n` +
                        `{template_body}\n` +
                        `</normalbefund_template>\n\n` +
                        `{examples}\n\n` +
                        `<diktat>\n` +
                        `{roh_text}\n` +
                        `</diktat>`;
                      setSystemPrompt(resetPrompt);
                      localStorage.setItem('system_prompt', resetPrompt);
                    }
                  }}
                  className="btn btn-secondary"
                  style={{ marginTop: '8px', fontSize: '12px', padding: '8px 16px', height: 'auto', minWidth: 'unset' }}
                >
                  ↺ Auf Praxis-Standard zurücksetzen
                </button>
              </div>
            </div>

            <div className="modal-footer">
              <span className="footer-warning">
                <Info size={14} /> Schlüssel werden lokal im Browser gesichert.
              </span>
              <div className="modal-footer-actions">
                <button
                  onClick={() => setShowSettings(false)}
                  className="btn btn-secondary"
                >
                  Abbrechen
                </button>
                <button
                  onClick={saveConfig}
                  className="btn btn-primary"
                >
                  <Save size={16} /> Speichern
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
