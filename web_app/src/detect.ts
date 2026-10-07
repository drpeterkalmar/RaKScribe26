// Vorlagen-Erkennung und Befundtitel der Web-App (Umbau Schritt 17) — reine Funktionen, aus App.tsx herausgelöst.
// Sync: source_code/detect.py (Parität: detect_fixtures.json → tests/offline/test_normalbefunde.py TEIL 2c; Titel: tests/offline/titel_fixtures.py).
import { vorrangVorlage, type VorrangDaten } from './befundRegeln.ts';

export type Template = {
  display_name: string;
  body: string;
  ergebnis?: string;  // v3.2: Normal-Ergebnis der Untersuchung (Bypass + <normal_ergebnis> im LLM-Pfad)
};

export type TemplatesMap = {
  [key: string]: Template;
};

// deriveUntersuchungsTitel — Befundtitel für Bypass & <untersuchung>-Embed (Sync mit RaKScribe.py, v2.10.12).
// Generische Sammel-Templates ('(Allgemein)') dürfen ihren internen Namen NICHT als
// Befundtitel ausgeben (Peter 09.09.) → Titel aus dem Diktat, Befund-Worte gestrippt.
export function deriveUntersuchungsTitel(raw: string, displayName: string): string {
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

// Detect modality template based on text keywords (1:1 from EXE Version)
// v3.3.3: Mammographie in jeder Schreibweise, nicht „Mammasonographie“. Sync: detect.py MAMMOGRAPHIE_RE
export const MAMMOGRAPHIE_RE = /(?<![a-zäöüß])mammo(?:gra(?:ph|f|mm)|(?![a-zäöüß]))/;

export function detectTemplate(text: string, templates: TemplatesMap, vorrangDaten: VorrangDaten): string {
  // v3.2.3 (Peter 06.10.): Vorrang-Regeln + diktierter Vorlagenname aus vorlagen_vorrang.json zuerst (Sync: RaKScribe.py)
  const vorrang = vorrangVorlage(text, templates, vorrangDaten);
  if (vorrang) return vorrang;
  const textLower = text.toLowerCase();

  // v3.2.2 (Georg 05.10.): Nerven-Diktate OHNE "Sono"-Wort fielen in allgemein/Unterarm/HWS → Standardbefund
  // fehlte. Nerven-Kontext + Nervenname → Nerven-Template, VOR allen Röntgen-Regeln. Sync: RaKScribe.py detect_template.
  if (/\bnerv(?:us|i|en)?\b|\bn\.\s*[a-zäöü]|\bplexus\b|nervenson|nervenschall|nervenultraschall|tarsaltunnel/.test(textLower)
      && !["injektion", "infiltration"].some(x => textLower.includes(x))) {
    if (textLower.includes("blockade")) return "ultraschall_gezielte_blockade";  // Skill 3ae
    const nervRules: [string[], string][] = [
      [["cutaneus femoris", "femoris cutaneus", "cutaneus lateralis", "femoralis cutaneus", "meralgi"], "sonografie_nerv_femoralis_cutaneus_lateralis"],
      [["medianus", "karpaltunnelsyndrom"], "sonografie_nerv_medianus"],
      [["ulnaris", "guyon"], "sonografie_nerv_ulnaris"],
      [["radialis", "frohse", "wartenberg"], "sonografie_nerv_radialis"],
      [["plexus cervicalis"], "sonografie_plexus_cervicalis"],
      [["plexus"], "sonografie_plexus_brachialis"],
      [["ischiadicus"], "sonografie_nerv_ischiadicus"],
      [["peroneus", "fibularis"], "sonografie_nerv_peroneus"],
      [["tibialis", "tarsaltunnel"], "sonografie_nerv_tibialis"],
      [["femoralis"], "sonografie_nerv_femoralis"],
      [["pudendus"], "sonografie_nervus_pudendus"],
      [["iliohypogastricus", "ilioinguinalis"], "sonografie_nervus_iliohypogastricus_ilioinguinalis"],
    ];
    for (const [keys, tkey] of nervRules) {
      if (keys.some(k => textLower.includes(k))) return tkey;
    }
  }

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
  
  // v3.3.3 (Peter 07.10.): „Mammographie …, in der Sonographie …“ ist IMMER die Mammographie-Vorlage (Sync: detect.py)
  if (MAMMOGRAPHIE_RE.test(textLower)) return "mammographie_beidseits";

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
    // Umbau Schritt 7 (Gutachten P1-3): Blockade/Injektion wie in der EXE (RaKScribe.py detect_template, Sono-Zweig)
    if (textLower.includes("blockade") || textLower.includes("injektion")) {
      return "ultraschall_gezielte_blockade";
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

  if (textLower.includes("mamma") || /(?<![a-zäöüß])mammo(?![a-zäöüß])/.test(textLower)) {  // v3.3: auch „Mammo“
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
}
