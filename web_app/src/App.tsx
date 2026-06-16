import React, { useState, useEffect, useRef } from 'react';
import { 
  Stethoscope, 
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
  "HWS", "LWS", "BWS", "MRT", "CT", "Sonographie", "Röntgen", "Mammographie", "DEXA", "DVT", "OPG",
  "Spondylarthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Bandscheibenprolaps", "Fraktur", "Osteoporose",
  "Rotatorenmanschette", "Karpaltunnel", "Nervus medianus", "Aneurysma", "Stenose", "Pleuraerguss", "Infiltrat"
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

export default function App() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [authError, setAuthError] = useState<string>('');

  // Configuration States
  const [provider, setProvider] = useState<'gemini' | 'openai'>('gemini');
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  const [googleApiKey, setGoogleApiKey] = useState<string>('');
  const [sttEngine, setSttEngine] = useState<'browser' | 'google'>('browser');
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);

  // Application States
  const [status, setStatus] = useState<'ready' | 'recording' | 'processing' | 'copied'>('ready');
  const [statusText, setStatusText] = useState<string>('Bereit');
  const [transcript, setTranscript] = useState<string>('');
  const [structuredReport, setStructuredReport] = useState<string>('');
  const [micLevel, setMicLevel] = useState<number>(0);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // RAG mock dataset
  const ragDatabase: string[] = [
    "Befund: HWS in 2 Ebenen. Harmonischer Achsenverlauf. Keine Spondylolisthesis. Keine Höhenminderung der Intervertebralräume. Beurteilung: Unauffälliger HWS-Befund.",
    "Befund: Thorax in 2 Ebenen. Zwerchfellkuppen glatt begrenzt, Sinus frei. Lungenfelder regelrecht belüftet. Cor normal groß. Beurteilung: Herz-Lungen-Befund ohne pathologischen Befund.",
    "Befund: Kniegelenk rechts in 2 Ebenen. Regelrechter Gelenkspalt, keine arthrotischen Randwülste. Intakter Knorpel. Beurteilung: Altersentsprechender Normalbefund."
  ];

  // Particle background Canvas Ref
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Audio recording refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const recognitionRef = useRef<any>(null); // Browser SpeechRecognition

  // Load configuration from local storage
  useEffect(() => {
    const savedGeminiKey = localStorage.getItem('gemini_api_key');
    const savedGoogleKey = localStorage.getItem('google_api_key');
    const savedProvider = localStorage.getItem('llm_provider');
    const savedEngine = localStorage.getItem('stt_engine');
    const savedPrompt = localStorage.getItem('system_prompt');
    const savedAuth = localStorage.getItem('is_authenticated');

    if (savedGeminiKey) setGeminiApiKey(savedGeminiKey);
    if (savedGoogleKey) setGoogleApiKey(savedGoogleKey);
    if (savedProvider) setProvider(savedProvider as 'gemini' | 'openai');
    if (savedEngine) setSttEngine(savedEngine as 'browser' | 'google');
    if (savedAuth === 'true') setIsAuthenticated(true);
    
    if (savedPrompt) {
      setSystemPrompt(savedPrompt);
    } else {
      setSystemPrompt(
        `<role>Radiologe-Assistent</role>\n` +
        `<instructions>\n` +
        `Du bist ein präziser radiologischer Befundungsassistent. Deine Aufgabe ist es, das diktierte Stichwortprotokoll des Arztes in einen formalen und professionellen radiologischen Befund zu strukturieren.\n` +
        `Befolge diese Regeln strikt:\n` +
        `1. Nutze das bereitgestellte Normalbefund-Template als Basis für den Aufbau unter ## Befund.\n` +
        `2. WICHTIG: Wenn im Diktat pathologische Befunde erwähnt werden (z.B. Arthrose, Fraktur, etc.), MUSST du die entsprechenden Abschnitte im Normalbefund-Template abändern oder ersetzen, damit der Befund die Pathologie korrekt beschreibt. Schreibe dort nicht fälschlicherweise 'normal' oder 'regelrecht'.\n` +
        `3. Behalte Normalbefunde bei, wenn im Diktat nichts Abweichendes erwähnt wird.\n` +
        `4. Schreibstil: Orientiere dich für den Aufbau, die Wortwahl und das Format strikt an den Praxisbeispielen. Schreibe im radiologischen Nominalstil.\n` +
        `5. Bilde immer zwei Hauptbereiche: ## Befund (mit dem angepassten Template) und ## Beurteilung (mit der kurzen Zusammenfassung der Diagnosen).\n` +
        `6. Gib ausschließlich den fertigen Befundtext aus. Keine Kommentare, keine Einleitungen.\n` +
        `</instructions>\n` +
        `<normalbefund_template>\n` +
        `{template_body}\n` +
        `</normalbefund_template>\n\n` +
        `{examples}\n\n` +
        `<diktat>\n` +
        `{roh_text}\n` +
        `</diktat>`
      );
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
    localStorage.setItem('google_api_key', googleApiKey);
    localStorage.setItem('llm_provider', provider);
    localStorage.setItem('stt_engine', sttEngine);
    localStorage.setItem('system_prompt', systemPrompt);
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

  // Browser Native Speech Recognition Setup
  const startBrowserRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Spracherkennung wird von Ihrem Browser nicht nativ unterstützt. Bitte Chrome/Edge nutzen oder Google Cloud Key konfigurieren.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'de-DE';

    rec.onresult = (event: any) => {
      let finalStr = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalStr += event.results[i][0].transcript + ' ';
        }
      }
      if (finalStr.trim()) {
        setTranscript(prev => prev + finalStr);
      }
    };

    rec.onerror = (e: any) => {
      console.error("Speech recognition error:", e);
    };

    rec.onend = () => {
      if (status === 'recording') {
        try {
          rec.start();
        } catch (err) {
          console.error("Recognition restart failed", err);
        }
      }
    };

    recognitionRef.current = rec;
    rec.start();
  };

  // Google Cloud Speech to Text REST API Call
  const transcribeWithGoogle = async (wavBlob: Blob): Promise<string> => {
    if (!googleApiKey) {
      throw new Error("Bitte tragen Sie Ihren Google Cloud API-Key in den Einstellungen ein.");
    }

    setStatusText("Transkribiere mit Google STT...");

    const reader = new FileReader();
    return new Promise((resolve, reject) => {
      reader.onloadend = async () => {
        try {
          const base64Data = (reader.result as string).split(',')[1];
          const response = await fetch(
            `https://speech.googleapis.com/v1/speech:recognize?key=${googleApiKey}`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                config: {
                  encoding: "LINEAR16",
                  sampleRateHertz: 16000,
                  languageCode: "de-DE",
                  enableAutomaticPunctuation: true,
                  speechContexts: [{
                    phrases: MEDICAL_PHRASES,
                    boost: 12.0
                  }]
                },
                audio: {
                  content: base64Data
                }
              })
            }
          );

          const data = await response.json();
          if (data.error) {
            reject(new Error(data.error.message || "Google Cloud STT Fehler."));
            return;
          }

          const results = data.results || [];
          const transcriptResult = results
            .map((r: any) => r.alternatives[0].transcript)
            .join(' ');

          resolve(transcriptResult);
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(new Error("Fehler beim Lesen der Audiodatei."));
      reader.readAsDataURL(wavBlob);
    });
  };

  // Call Gemini API to Structure the Transcript
  // Call Gemini API to Structure the Transcript (Aligned 1:1 with EXE parameters)
  const callGeminiLLM = async (rawText: string, templateBody: string, regionName: string, examples: string): Promise<string> => {
    if (!geminiApiKey) {
      throw new Error("Bitte konfigurieren Sie Ihren Gemini API-Key in den Einstellungen.");
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

    const sysMsg = "Du bist ein präziser Radiologie-Assistent. Strukturiere das Diktat unter Verwendung des bereitgestellten Normalbefund-Templates. Nutze ## Befund und ## Beurteilung als Haupttitel.";

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      }
    );

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error.message || "Gemini API Fehler.");
    }

    const outputText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return outputText;
  };

  // Start Audio Recording
  const startRecording = async () => {
    try {
      setTranscript('');
      setStructuredReport('');
      setStatus('recording');
      setStatusText('Aufnahme läuft...');
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        if (sttEngine === 'google') {
          audioChunksRef.current.push(new Float32Array(inputData));
        }

        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        setMicLevel(Math.min(100, Math.round(rms * 400)));
      };

      if (sttEngine === 'browser') {
        startBrowserRecognition();
      }

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

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
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
      let finalRawText = transcript;

      if (sttEngine === 'google') {
        const totalLength = audioChunksRef.current.reduce((acc, val) => acc + val.length, 0);
        const mergedArray = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of audioChunksRef.current) {
          mergedArray.set(chunk, offset);
          offset += chunk.length;
        }

        const ctxTemp = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        const audioBuf = ctxTemp.createBuffer(1, mergedArray.length, 16000);
        audioBuf.copyToChannel(mergedArray, 0);
        const wavBlob = audioBufferToWav(audioBuf);
        ctxTemp.close();

        finalRawText = await transcribeWithGoogle(wavBlob);
        setTranscript(finalRawText);
      }

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
        body: "Befund der untersuchten Region entsprechend dem Standardvorgehen.\nBeurteilung der radiologischen Pathologien."
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
        
        const report = `## Befund\n${activeTemplate.body}\n\n## Beurteilung\n${formattedRaw}`;
        setStructuredReport(report);
        setStatus('ready');
        setStatusText('Bereit');
        
        try {
          await navigator.clipboard.writeText(report);
          setIsCopied(true);
          setTimeout(() => setIsCopied(false), 3000);
        } catch (clipErr) {
          console.error("Clipboard copy failed:", clipErr);
        }
        return;
      }

      // Normal path: structure with LLM
      const examples = getFewShotExamples(finalRawText);
      let structuredText = "";
      if (geminiApiKey) {
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
        structuredText = `## Befund\n${activeTemplate.body}\n\n## Beurteilung\n${formattedRaw}`;
      }

      setStructuredReport(structuredText);
      setStatus('ready');
      setStatusText('Bereit');

      try {
        await navigator.clipboard.writeText(structuredText);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 3000);
      } catch (clipErr) {
        console.error("Clipboard copy failed:", clipErr);
      }

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
    try {
      await navigator.clipboard.writeText(structuredReport);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 3000);
    } catch (err) {
      alert("Fehler beim Kopieren in die Zwischenablage.");
    }
  };

  // Reset fields
  const handleReset = () => {
    setTranscript('');
    setStructuredReport('');
    setStatus('ready');
    setStatusText('Bereit');
  };

  // Refs to avoid stale closures in global keyboard event listeners
  const statusRef = useRef(status);
  statusRef.current = status;
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

  // Render Login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="login-container">
        {/* Canvas background for login */}
        <canvas ref={canvasRef} id="particle-canvas" />

        <div className="login-card" style={{ zIndex: 1 }}>
          <div className="login-header">
            <div className="login-icon">
              <Stethoscope size={40} />
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
            <Stethoscope size={24} />
          </div>
          <div className="brand-title-group">
            <div className="brand-name">
              <span>RaKScribe26</span>
              <span className="brand-badge">Web Beta</span>
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
              Engine: {sttEngine.toUpperCase()}
            </span>
          </div>

          <div className="card-body">
            <textarea
              value={transcript}
              onChange={e => {
                setTranscript(e.target.value);
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
            <button onClick={handleReset} className="btn btn-secondary">
              Zurücksetzen
            </button>

            {status === 'recording' ? (
              <button onClick={stopRecording} className="btn btn-danger pulse-recording">
                <MicOff size={18} /> Aufnahme Stoppen
              </button>
            ) : (
              <button onClick={startRecording} disabled={status === 'processing'} className="btn btn-primary">
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
              className="btn btn-secondary"
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
              {/* STT Config */}
              <div className="settings-section">
                <h3 className="settings-sec-title">1. Spracherkennung (Speech-to-Text)</h3>
                
                <div className="settings-grid">
                  <div 
                    className={`engine-option-card ${sttEngine === 'browser' ? 'selected' : ''}`}
                    onClick={() => setSttEngine('browser')}
                  >
                    <input 
                      type="radio" 
                      name="stt_engine" 
                      value="browser"
                      checked={sttEngine === 'browser'}
                      readOnly
                      className="engine-radio"
                    />
                    <div>
                      <span className="engine-title">Browser-Erkennung (Free)</span>
                      <span className="engine-desc">Nutzt die eingebaute Spracherkennung von Chrome/Edge. Kein Setup nötig.</span>
                    </div>
                  </div>

                  <div 
                    className={`engine-option-card ${sttEngine === 'google' ? 'selected' : ''}`}
                    onClick={() => setSttEngine('google')}
                  >
                    <input 
                      type="radio" 
                      name="stt_engine" 
                      value="google"
                      checked={sttEngine === 'google'}
                      readOnly
                      className="engine-radio"
                    />
                    <div>
                      <span className="engine-title">Google Cloud STT</span>
                      <span className="engine-desc">Sehr präzises medizinisches Diktat. Benötigt Google API-Key.</span>
                    </div>
                  </div>
                </div>

                {sttEngine === 'google' && (
                  <div style={{ marginTop: '12px' }}>
                    <label className="form-label">Google Cloud API-Key</label>
                    <input 
                      type="password"
                      value={googleApiKey}
                      onChange={e => setGoogleApiKey(e.target.value)}
                      placeholder="AIzaSy..."
                      className="form-input"
                    />
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', display: 'block' }}>
                      Tipp: Erstellen Sie einen API-Schlüssel in der Google Cloud Console mit Zugriff auf Speech-to-Text.
                    </span>
                  </div>
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
                <textarea
                  value={systemPrompt}
                  onChange={e => setSystemPrompt(e.target.value)}
                  rows={6}
                  className="settings-textarea"
                />
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
