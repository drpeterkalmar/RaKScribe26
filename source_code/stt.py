"""Spracherkennung der EXE (Umbau Schritt 13) — ohne Tk/Windows/Google-Bibliotheken importierbar.

- MEDICAL_PHRASES: Phrasen für das Streaming (Live-Anzeige, latest_long).
- CHIRP_PHRASES: kuratiertes chirp_3-PhraseSet (identisch zur Web-App, web_app/src/stt.ts).
- chirp3_request / chirp3_worker: komplettes Diktat an chirp_3 (STT v2, Location eu); > 50 s in Segmenten
  50 s + 4 s Rückhören, Überlappung per Wortvergleich zusammengefügt (stitch_overlaps).
Der Streaming-Teil (Mikrofon → Live-Anzeige) liegt in aufnahme.py (Umbau Schritt 6).
Tests: tests/offline/test_stt.py, sync_fixtures.json (gleiche Fälle für die Web-App).
"""
import base64
import io
import json
import urllib.request
import wave

# Streaming-Live-Anzeige (latest_long, Boost 10): medizinische Fachbegriffe
MEDICAL_PHRASES = [
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
    "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung", "Fibroostose", "Fibroostosen", "Thorax p.a.", "Thorax p.a./seitlich",
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
    "Flachbogig", "S-förmige", "HWS", "HWK",
    "Flachbogige Skoliose", "flachbogige Skoliose", "Kyphose", "kyphotische Fehlhaltung", "Fehlhaltung",
    "Kellgren", "Lawrence", "Kellgren & Lawrence", "Kellgren-Lawrence",
    "Discopathiezeichen", "Diskopathiezeichen",
    "Neoarthrosis interspinosa", "Neoarthrosen interspinosa", "Neoarthrose interspinosa"
]


# v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation), identisch zur Web-App (CHIRP_PHRASES).
CHIRP_PHRASES = [
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
]


def chirp3_request(token, loc, wav_b64, timeout=60, urlopen=None):
    """Ein chirp_3-Request (≤ 60 s Audio). urlopen ist für Tests austauschbar."""
    urlopen = urlopen or urllib.request.urlopen
    host = 'speech' if loc == 'global' else loc + '-speech'
    url = (f"https://{host}.googleapis.com/v2/projects/rakscribe/"
           f"locations/{loc}/recognizers/_:recognize")
    cfg = {"languageCodes": ["de-DE"], "model": "chirp_3",
           "autoDecodingConfig": {},
           "features": {"enableAutomaticPunctuation": True},
           "adaptation": {"phraseSets": [{"inlinePhraseSet": {"phrases": [
               {"value": p, "boost": 10} for p in CHIRP_PHRASES]}}]}}
    body = json.dumps({"config": cfg, "content": wav_b64}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read())
    return " ".join(res["alternatives"][0]["transcript"]
                    for res in j.get("results", []))


def stitch_overlaps(a, b, window=14):
    """Segment-Texte zusammenfügen: gleiche Wörter am Ende von a / Anfang von b (≥ 80 %) nur einmal."""
    aw, bw = a.split(), b.split()
    best = 0
    for L in range(min(window, len(aw), len(bw)), 0, -1):
        tail = [w.lower().strip('.,:;') for w in aw[-L:]]
        head = [w.lower().strip('.,:;') for w in bw[:L]]
        if sum(1 for x, y in zip(tail, head) if x == y) >= int(L * 0.8):
            best = L
            break
    return (a + " " + " ".join(bw[best:])) if best else (a + " " + b)


def wav_b64(pcm_int16, samplerate):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(samplerate)
        wf.writeframes(pcm_int16.tobytes())
    return base64.b64encode(buf.getvalue()).decode()


def chirp3_worker(pcm_int16, samplerate, loc, token, request=None):
    """Komplettes Diktat (int16-Array) → Text. 50-s-Segmente mit 4 s Rückhören (chirp_3: max. 60 s je Request)."""
    request = request or chirp3_request
    SEG = 50 * samplerate      # 50s Segmente
    OV = 4 * samplerate        # 4s Rueckhoeren
    texts = []
    start = 0
    while start < len(pcm_int16):
        end = min(start + SEG, len(pcm_int16))
        txt = request(token, loc, wav_b64(pcm_int16[start:end], samplerate))
        if txt is None:
            return None
        texts.append(txt)
        if end >= len(pcm_int16):
            break
        start = end - OV
    full = texts[0]
    for nxt in texts[1:]:
        full = stitch_overlaps(full, nxt)
    return full
