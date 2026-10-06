"""Vorlagen-Erkennung und Befundtitel der EXE (Umbau Schritt 12) — reine Funktionen, ohne Tk/Windows importierbar.

Sync: web_app/src/App.tsx detectTemplate / deriveUntersuchungsTitel (Parität: detect_fixtures.json,
test_normalbefunde.py TEIL 2c; Titel: titel_fixtures.py). Die Tests und prod_pipeline.py importieren diese Datei
direkt (vorher: AST-Extrakt aus RaKScribe.py).
"""
import re

import befund_regeln as br


def derive_untersuchungs_titel(raw: str, display_name: str) -> str:
    """Befundtitel fuer Bypass & <untersuchung>-Embed (v2.10.12/13, Peter 09.09.).

    Generische Sammel-Templates (display_name mit '(Allgemein)') duerfen ihren
    internen Namen NICHT als Befundtitel ausgeben — dann wird die
    Untersuchungsbezeichnung aus dem DIKTAT gebildet: 'Unterschenkel-
    Sonographie rechts unauffaellig' → 'Unterschenkel-Sonographie rechts'.
    Konkrete Templates (HWS, Orbita, ...) behalten den kanonischen Namen.
    """
    if not re.search(r"\(allgemein\)", display_name or "", re.I):
        return display_name
    # v2.10.13 (K3-Review): Negations-Guard ("nicht unauffällig" kappselt das
    # NICHT), Loop über alle Findings statt break, ':'-Strip,
    # (Allgemein)-Leak aus dem Diktat entfernen, Newline-Falt, Cap 80.
    t = re.sub(r"\bHW\b", "HWS", (raw or "").strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.?!]\s*$", "", t).strip()
    for _ in range(3):
        stripped = False
        for f in (r"unauff(?:ae|ä)?llig", r"o\.?\s?B\.?", r"ohne pathologischen Befund",
                  r"ohne pathologischem Befund", r"kein pathologischer Befund",
                  r"regelrecht", r"normal"):
            m = re.search(r"(?:^|[\s,])" + f + r"\s*$", t, re.I)
            if m:
                pre = t[:m.start()].strip()
                if re.search(r"\bnicht\s*$", pre, re.I):
                    continue  # Negation: "nicht unauffällig" nicht kappseln
                t = pre.strip()
                stripped = True
        if not stripped:
            break
    t = re.sub(r"[.,?!:]+$", "", t).strip()
    t = re.sub(r"\(\s*allgemein\s*\)", "", t, flags=re.I).strip()
    if len(t) > 80:
        t = t[:80].strip()
    return t or re.sub(r"\s*\(Allgemein\)", "", display_name, flags=re.I).strip()


def detect_template(text, templates):
    """Bessere Erkennungslogik für den Untersuchungstyp. templates = Vorlagen (templates.json) — für die
    Vorrang-Regeln und den Fallback „Key steht im Diktat“."""
    # v3.2.3 (Peter 06.10.: alle Vorlagen erreichbar + korrekt priorisiert): zuerst Vorrang-Regeln und diktierter
    # Vorlagenname aus vorlagen_vorrang.json (EINE Datei für EXE + Web), danach die bisherige Erkennung.
    _vorrang = br.vorrang_vorlage(text, templates)
    if _vorrang:
        return _vorrang
    text_lower = text.lower()

    # v3.2.2 (Georg 05.10.): Nerven-Diktate OHNE "Sono"-Wort ("N. medianus rechts unauffällig",
    # "Nervus ulnaris links …") fielen in allgemein/Unterarm/HWS → Standardbefund fehlte. Nerven-Kontext
    # (Nervus/N./Plexus/Nervensono) + Nervenname → Nerven-Template, VOR allen Röntgen-Regeln.
    # Sync: web_app/src/App.tsx detectTemplate (gleiche Liste, gleiche Reihenfolge).
    if (re.search(r"\bnerv(?:us|i|en)?\b|\bn\.\s*[a-zäöü]|\bplexus\b|nervenson|nervenschall|nervenultraschall|tarsaltunnel", text_lower)
            and not any(x in text_lower for x in ["injektion", "infiltration"])):
        if "blockade" in text_lower:  # Skill 3ae: ultraschallgezielte Blockade hat eigenes Template
            return "ultraschall_gezielte_blockade"
        for keys, tkey in [
            (["cutaneus femoris", "femoris cutaneus", "cutaneus lateralis", "femoralis cutaneus", "meralgi"], "sonografie_nerv_femoralis_cutaneus_lateralis"),
            (["medianus", "karpaltunnelsyndrom"], "sonografie_nerv_medianus"),
            (["ulnaris", "guyon"], "sonografie_nerv_ulnaris"),
            (["radialis", "frohse", "wartenberg"], "sonografie_nerv_radialis"),
            (["plexus cervicalis"], "sonografie_plexus_cervicalis"),
            (["plexus"], "sonografie_plexus_brachialis"),
            (["ischiadicus"], "sonografie_nerv_ischiadicus"),
            (["peroneus", "fibularis"], "sonografie_nerv_peroneus"),
            (["tibialis", "tarsaltunnel"], "sonografie_nerv_tibialis"),
            (["femoralis"], "sonografie_nerv_femoralis"),
            (["pudendus"], "sonografie_nervus_pudendus"),
            (["iliohypogastricus", "ilioinguinalis"], "sonografie_nervus_iliohypogastricus_ilioinguinalis"),
        ]:
            if any(k in text_lower for k in keys):
                return tkey

    # 0.0. Kombinierte Untersuchungen vorab prüfen
    if any(x in text_lower for x in ["becken", "wecken", "pelvis"]):
        if any(x in text_lower for x in ["tep", "prothese", "endoprothese", "h-tep"]):
            if any(x in text_lower for x in ["beidseits", "bds", "beide"]):
                return "beckenübersicht_mit_beidseitiger_hüftprothese"
            else:
                return "beckenübersicht_mit_einseitiger_hüftprothese"
        elif any(x in text_lower for x in ["hüfte", "hüftgelenk", "hfte", "hft"]):
            return "beckenübersicht_und_hüfte"

    # ── Gesamtwirbelsäule / Multi-Segment Erkennung (erweiterte Keywords) ──────
    # Deckt ab: "Wirbelsäulen ganz Aufnahme", "zerviko-thorako-lumbal",
    #           "toracco lumbal Skoliose", "Ganzwirbelsäule" etc.
    has_cervical  = any(x in text_lower for x in ["hws", "hwk", "zervik", "zerviko", "cervik", "cervico", "halswirbel"]) or re.search(r'\bhw\b', text_lower)
    has_thoracic  = any(x in text_lower for x in ["bws", "thorakal", "thorako", "thoraco", "toracco", "brustwirbel"])
    has_lumbar    = any(x in text_lower for x in ["lws", "lumbal", "lendenwirbel"])
    is_full_spine = any(x in text_lower for x in ["ganzaufnahme", "gesamtwirbel", "ganzwirbel"]) or \
                   ("ganz" in text_lower and "wirbels" in text_lower) or \
                   ("gesamt" in text_lower and "wirbel" in text_lower) or \
                   ("komplett" in text_lower and "wirbel" in text_lower)

    # Umbau Schritt 7 (Gutachten P1-3): Ganzaufnahme a.-p. hat eigenes Template — vor wirbelsäule_gesamt prüfen
    # (wie web_app/src/App.tsx detectTemplate)
    if "ganzaufnahme" in text_lower and not has_cervical:
        return "ganzaufnahme_der_wirbelsäule_a-p"

    if is_full_spine or (has_cervical and has_thoracic and has_lumbar):
        return "wirbelsäule_gesamt"
    if has_cervical and has_lumbar:
        return "hws_und_lws"
    if has_cervical and has_thoracic:
        return "wirbelsäule_gesamt"
    # ─────────────────────────────────────────────────────────────────────────
    if re.search(r'\bhw\b', text_lower):
        # STT schreibt HWS oft nur als "HW" (z.B. "HW ist unauffällig")
        return "halswirbelsäule_in_2_ebenen"

    if "hws" in text_lower and "lws" in text_lower:
        if "bws" in text_lower:
            return "wirbelsäule_gesamt"
        else:
            return "hws_und_lws"
    
    # 0. Spezialregeln für Sonographie vorab prüfen (da sehr häufig)
    if any(x in text_lower for x in ["sono", "schall", "ultraschall", "duplex"]):
        # v3.2.2: Schulter-Sonographie (Web-Parität — die EXE fiel hier bisher auf sonografie_allgemein)
        if any(x in text_lower for x in ["schulter", "supraspinatus", "infraspinatus", "bizepssehne",
                                          "rotatorenmanschette", "subacromial", "subakromial"]):
            return "sonografie_schultergelenk"
        # Bauchdecke (vor abdomen/bauch, sonst greift das Allgemein-Abdomen)
        if "bauchdeck" in text_lower or "hernie" in text_lower or "rektusdiastase" in text_lower or "rectusdiastase" in text_lower:
            return "sonografie_bauchdecke"
        # Abdomen-Sonographie
        if "abdomen" in text_lower or "bauch" in text_lower or "abd" in text_lower:
            if "weiblich" in text_lower:
                return "sonografie_abdomen_weiblich"
            else:
                return "sonografie_abdomen_maennlich"
        # Halsgefäße / Carotis
        if any(x in text_lower for x in ["carotis", "halsgef", "halsart", "extracran", "commun"]):
            return "sonografie_halsgefaesse"
        # Varizensonographie
        if any(x in text_lower for x in ["varizen", "variko", "variz"]):
            return "varizensonografie"
        # Mamma VOR dem generischen "venen"-Trigger (K3-Befund 2-Familie:
        # "Hautvenen" im Mamma-Diktat matcht "venen" → falsches Beinvenen-Template).
        # Trigger 'mamma' (nicht 'mammo'): 'Mammasonographie' enthält 'mamma',
        # aber NIE 'mammo' (m-a-m-m-a + sono)!
        if "mamma" in text_lower:
            if any(x in text_lower for x in ["sono", "schall", "ultraschall", "mammasono"]):
                return "mammasonographie_beidseits"
            return "mammographie_beidseits"
        # Beinvenen
        if any(x in text_lower for x in ["beinven", "v. femoralis", "poplitea", "fibularis", "venen"]):
            return "sonografie_beinvenen"
        # Muskel-/Weichteil-Sonographie (Pedret/BAMIC-Regionen)
        if any(x in text_lower for x in ["muskel", "muskul", "gastrocnem", "soleus", "quadriceps", "ischio", "faserriss"]):
            if "dorsal" in text_lower and "unterschenkel" in text_lower:
                return "sonografie_dorsaler_unterschenkel"
            if "gastrocnem" in text_lower:
                return "sonografie_gastrocnemius_medialis"
            if "dorsal" in text_lower and "oberschenkel" in text_lower:
                return "sonografie_dorsaler_oberschenkel"
            if "anterior" in text_lower and "oberschenkel" in text_lower:
                return "sonografie_anteriorer_oberschenkel"
            return "sonografie_weichteile"
        # Halsweichteile vs Schilddrüse
        if "halsweichteil" in text_lower or "hals-weichteil" in text_lower:
            return "sonografie_halsweichteile"
        if "schilddr" in text_lower or "sd-" in text_lower:
            return "sonografie_schilddrüse"
        # Weichteilschall allgemein
        if "weichteil" in text_lower:
            return "sonografie_weichteile"
        # Nerven
        if "medianus" in text_lower or "karpal" in text_lower or "cts" in text_lower:
            return "sonografie_nerv_medianus"
        if "ulnaris" in text_lower or "sulcus" in text_lower or "loge" in text_lower or "guyon" in text_lower:
            return "sonografie_nerv_ulnaris"
        if "radialis" in text_lower or "supinator" in text_lower or "frohse" in text_lower or "wartenberg" in text_lower:
            return "sonografie_nerv_radialis"
        if "plexus" in text_lower and "cervicalis" in text_lower:
            return "sonografie_plexus_cervicalis"
        if "plexus" in text_lower:
            return "sonografie_plexus_brachialis"
        if "ischiadicus" in text_lower:
            return "sonografie_nerv_ischiadicus"
        if "peroneus" in text_lower:
            return "sonografie_nerv_peroneus"
        if "tibialis" in text_lower:
            return "sonografie_nerv_tibialis"
        if "femoralis" in text_lower and "cutaneus" in text_lower:
            return "sonografie_nerv_femoralis_cutaneus_lateralis"
        if "femoralis" in text_lower:
            return "sonografie_nerv_femoralis"
        if "pudendus" in text_lower:
            return "sonografie_nervus_pudendus"
        if "iliohypogastricus" in text_lower or "ilioinguinalis" in text_lower:
            return "sonografie_nervus_iliohypogastricus_ilioinguinalis"
        if "blockade" in text_lower or "injektion" in text_lower:
            return "ultraschall_gezielte_blockade"
        if any(x in text_lower for x in ["nerv", "neuro", "suralis"]):
            return "sonografie_nerv_allgemein"
        # Unterschenkel-Weichteil-Sono (v2.10.13-fix2, Peter: eigenes Template)
        if "unterschenkel" in text_lower:
            return "sonografie_unterschenkel"
        # Sonographie Allgemein
        return "sonografie_allgemein"

    # 1. DVT / Digitale Volumentomographie / Zahnröntgen / OPG / Zahnstatus
    if "dvt" in text_lower or "volumentomographie" in text_lower:
        if "oberkiefer" in text_lower or "ok" in text_lower:
            return "dvt_oberkiefer"
        if "unterkiefer" in text_lower or "uk" in text_lower:
            return "dvt_unterkiefer"
        return "dvt_oberkiefer"  # Default
        
    if any(x in text_lower for x in ["opg", "zahnröntgen", "zahnstatus", "orthopantomogramm"]):
        return "orthopantomogramm_des_kiefer-_und_gesichtsschädels"
        
    # 2. DEXA / Knochendichtemessung / Osteodensitometrie
    if any(x in text_lower for x in ["dexa", "knochendichte", "densitometrie", "odm"]):
        return "knochendichtemessung_dexa"
        
    # 3. Mammographie / Fernröntgen
    if "mamma" in text_lower:
        if any(x in text_lower for x in ["sono", "schall", "ultraschall", "mammasono"]):
            return "mammasonographie_beidseits"
        return "mammographie_beidseits"
        
    if "fernröntgen" in text_lower or "fern-röntgen" in text_lower or "frs" in text_lower:
        return "schädelfernröntgen"

    # 2b. Röntgen-Regionen mit eigenen Normalbefund-Templates (v2.10.12/13)
    if "orbita" in text_lower:
        return "orbita_pa_aufnahme"
    if any(x in text_lower for x in ["calcaneus", "kalkaneus", "ferse"]):
        if "seitlich" in text_lower and "2 ebenen" not in text_lower:
            return "calcaneus_seitlich"
        return "calcaneus_in_2_ebenen"
    if "mortise" in text_lower:
        return "sprunggelenk_mortise_view"
    if "gehaltene" in text_lower:
        return "sprunggelenk_gehaltene_aufnahmen"
    if ("sprunggelenk" in text_lower or "osg" in text_lower) and ("fuß" in text_lower or "fuss" in text_lower):
        return "sprunggelenk_mit_fuss"
    if any(x in text_lower for x in ["naviculare", "skaphoid", "scaphoid", "kahnbein"]):
        return "naviculareserie"

    # Peters Diktat-Kürzel: "Visa" = Videokinematographie des Schluckaktes (Konvention 3x)
    if any(x in text_lower for x in ["visa", "wiederschluck", "videokinematographie"]):
        return "videokinematographie_schluckakt"

    # 4. Durchleuchtungen (Fluoroscopy)
    if "breischluck" in text_lower or "ösophagus" in text_lower or "schluckakt" in text_lower:
        if any(x in text_lower for x in ["videokinematographie", "video", "vis-a-vis", "wiederschluck", "visa"]):
            return "videokinematographie_schluckakt"
        if any(x in text_lower for x in ["magen", "duodenum", "magenduodenum"]):
            return "oesophagus_magenduodenum_doppelkontrast"
        return "durchleuchtung:_ösophagus-breischluck"
    if "mdp" in text_lower or "magen-darm" in text_lower or "magen" in text_lower:
        return "durchleuchtung:_magen-darm-passage_mdp"
    if "urogramm" in text_lower or "ivu" in text_lower or "ivp" in text_lower:
        return "intravenöses_urogramm"
    if "phlebographie" in text_lower or "phlebo" in text_lower:
        if any(x in text_lower for x in ["press", "aszendier", "aufsteigend"]):
            return "aszendierende_pressphlebographie"
        return "beinphlebographie"
    if "hsg" in text_lower or "hysterosalpingographie" in text_lower:
        return "hysterosalpingographie"

    # Priorisiertes Mapping: spezifischere Begriffe zuerst prüfen
    mappings = [
        ("beckenübersicht_stehend", ["becken", "wecken", "pelvis"]),
        # Prothesen / TEP / Varizen
        ("varizensonografie", ["varizen", "variko", "variz"]),
        ("schulterprothese", ["schulterprothese", "schulter-tep", "schulter tep", "schulterendoprothese"]),
        ("daumensattelprothese", ["daumensattel", "sattelprothese", "sattelgelenk"]),
        ("knieprothese", ["knieprothese", "knie-tep", "knie tep", "knieendoprothese"]),
        ("hüftprothese", ["hüftprothese", "hüft-tep", "hüft tep", "hüftendoprothese", "h-tep"]),

        # MRT / CT (am spezifischsten)
        ("mr_des_gehirnschädels:", ["mrt schädel", "mr schädel", "mrt kopf", "mr kopf", "mrt gehirn", "mr gehirn"]),
        ("mr_der_lendenwirbelsäule:", ["mrt lws", "mr lws"]),
        ("mr_der_halswirbelsäule:", ["mrt hws", "mr hws"]),
        ("mr_des_kniegelenkes:", ["mrt knie", "mr knie"]),
        ("mr_des_schultergelenkes:", ["mrt schulter", "mr schulter"]),
        ("mr_handgelenk:", ["mrt handgelenk", "mr handgelenk"]),
        ("mr_hüftgelenk:", ["mrt hüfte", "mr hüfte", "mrt hüftgelenk", "mr hüftgelenk"]),
        ("cct:", ["cct", "craniales ct", "ct kopf", "ct schädel", "ct gehirn"]),
        ("ct_thorax:", ["ct thorax", "ct lunge", "ct brustkorb"]),
        ("ct_abdomen:", ["ct abdomen", "ct bauch"]),
        
        # Röntgen (Wirbelsäule)
        ("lendenwirbelsäule_in_2_ebenen", ["lws", "lumbal", "lendenwirbel"]),
        ("halswirbelsäule_in_2_ebenen", ["hws", "cervical", "halswirbel"]),
        ("brustwirbelsäule_in_2_ebenen", ["bws", "thorakal", "brustwirbel"]),
        # v3.2: knöcherner Hemithorax VOR Thorax ("Hemithorax" enthält "thorax")
        ("knöcherner_hemithorax", ["hemithorax", "rippenaufnahme", "rippenserie", "rippen in 2"]),
        ("thorax_in_2_ebenen", ["thorax", "torax", "lunge", "pulmo", "brustkorb", "herz", "rö-th", "rö thor"]),
        
        # Obere Extremitäten Röntgen (Reihenfolge: Finger/Handgelenk vor Hand!)
        ("handgelenk_in_2_ebenen", ["handgelenk"]),
        ("finger_in_2_ebenen", ["finger", "daumen", "kleinfinger", "zeigefinger", "mittelfinger", "ringfinger"]),
        ("hand_in_2_ebenen", ["hand", "mittelhand"]),
        ("ellbogengelenk_in_2_ebenen", ["ellbogen", "ellenbogen"]),
        ("unterarm_in_2_ebenen", ["unterarm", "radius", "ulna"]),
        ("oberarm_in_2_ebenen", ["oberarm", "humerus"]),
        ("schultergelenk_in_2_ebenen", ["schulter", "omarthrose"]),
        
        # Untere Extremitäten Röntgen
        ("sprunggelenk_in_2_ebenen", ["sprunggelenk", "osg", "usg", "malleolar", "malleolus"]),
        ("fuß_in_2_ebenen", ["fuß", "fuss", "mittelfuß", "vorfuß", "rückfuß"]),
        ("zehe_in_2_ebenen", ["zehe", "großzehe"]),
        ("kniegelenk_in_2_ebenen", ["knie", "gonarthrose"]),
        ("hüftgelenk_in_2_ebenen", ["hüfte", "hft", "coxarthrose"]),
    ]
    
    # 1. Prüfe die priorisierten Schlagwort-Mappings
    for key, keywords in mappings:
        for kw in keywords:
            if kw in text_lower:
                return key
                
    # 2. Direkte Treffer auf Keys (als Fallback)
    for key in templates.keys():
        search_key = key.replace('_', ' ')
        if search_key in text_lower:
            return key
            
    return "allgemein"
