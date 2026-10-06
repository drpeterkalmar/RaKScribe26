#!/usr/bin/env python3
"""tools/add_normal_ergebnis.py — v3.2: Normalbefund-ERGEBNIS je Template (Feld "ergebnis") in templates.json.

Peter 05.10.: Bei unauffälligem Diktat stand das Diktat 1:1 im Ergebnis. Jetzt hat jedes Template
einen zur Untersuchung passenden Ergebnis-Satz (Quelle: beigebrachte Normalbefunde im Skill
radiology-shoulder-dictation, Rest nach Praxis-Konvention 'Regelrechte Darstellung des/der …'
bzw. 'Unauffälliger Befund.'). Schreibt EXE- und Web-Kopie byte-identisch. Idempotent.
"""
import json, pathlib
REPO = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)

# Beigebracht (Skill) → Template-Key
TAUGHT = {
    "schädel_in_2_ebenen": "Unauffälliger Befund des Schädels.",
    "orbita_pa_aufnahme": "Regelrechte Darstellung beider Orbitae.",
    "halswirbelsäule_in_2_ebenen": "Regelrechte Darstellung der HWS.",
    "brustwirbelsäule_in_2_ebenen": "Regelrechte Darstellung der BWS.",
    "lendenwirbelsäule_in_2_ebenen": "Regelrechte Darstellung der LWS.",
    "steißbein_in_2_ebenen": "Regelrechte Darstellung des Steißbeins.",
    "kreuzbein_und_steißbein_in_2_ebenen": "Regelrechte Darstellung des Kreuzbeins und Steißbeins.",
    "beckenübersicht_stehend": "Regelrechte Darstellung des Beckens.",
    "hüftgelenk_in_2_ebenen": "Regelrechte Darstellung des Hüftgelenkes.",
    "kniegelenk_in_2_ebenen": "Regelrechte Darstellung des Kniegelenkes.",
    "unterschenkel_in_2_ebenen": "Regelrechte Darstellung des Unterschenkels.",
    "sprunggelenk_in_2_ebenen": "Regelrechte Darstellung des oberen Sprunggelenkes.",
    "sprunggelenk_mortise_view": "Regelrechte Darstellung des oberen Sprunggelenkes.",
    "sprunggelenk_gehaltene_aufnahmen": "Regelrechte Darstellung des oberen Sprunggelenkes. Keine vermehrte Aufklappbarkeit des lateralen bzw. medialen Gelenkspaltes. Normaler Talusvorschub. Somit radiologisch kein Hinweis auf eine Läsion des Bandapparates des OSG.",
    "calcaneus_in_2_ebenen": "Regelrechte Darstellung des Calcaneus.",
    "calcaneus_seitlich": "Regelrechte Darstellung des Calcaneus.",
    "zehe_in_2_ebenen": "Regelrechte Darstellung der Zehe.",
    "fuß_in_2_ebenen": "Regelrechte Darstellung des Fußskeletts.",
    "vorfuß_in_2_ebenen": "Regelrechte Darstellung der knöchernen Anteile und Weichteile des Vorfußes.",
    "sprunggelenk_mit_fuss": "Regelrechte Darstellung des oberen Sprunggelenkes und des Fußskeletts.",
    "thorax_in_2_ebenen": "Unauffälliger Befund.",
    "knöcherner_hemithorax": "Unauffälliger Befund des knöchernen Hemithorax.",
    "abdomen_im_stand": "Regelrechte Darstellung des Abdomens.",
    "abdomen_im_liegen": "Regelrechte Darstellung des Abdomens.",
    "nasennebenhöhlen": "Unauffälliger Befund.",
    "schädelfernröntgen": "Unauffälliger Befund.",
    "durchleuchtung:_magen-darm-passage_mdp": "Unauffälliger Befund.",
    "durchleuchtung:_ösophagus-breischluck": "Unauffälliger Befund.",
    "oesophagus_magenduodenum_doppelkontrast": "Unauffälliger Befund.",
    "sonografie_halsgefaesse": "Unauffälliger Befund.",
    "hysterosalpingographie": "Unauffälliger Befund.",
    "aszendierende_pressphlebographie": "Unauffälliger Befund.",
    "intravenöses_urogramm": "Unauffällige Darstellung beider Nieren, der ableitenden Harnwege und der Blase in der intravenösen Urographie.",
    "videokinematographie_schluckakt": "Unauffälliger Befund.",
    "schultergelenk_in_2_ebenen": "Regelrechte Darstellung des Schultergelenkes.",
    "finger_in_2_ebenen": "Regelrechte Darstellung des Fingers.",
    "skaphoidaufnahme": "Regelrechte Darstellung des Os scaphoideum.",
    "sonografie_schultergelenk": "Regelrechte Darstellung der Schulter.",
    "sonografie_halsweichteile": "Regelrechte Darstellung der Halsweichteile.",
    "sonografie_bauchdecke": "Regelrechte Darstellung der Bauchdecke.",
    "sonografie_dorsaler_oberschenkel": "Regelrechte Darstellung der dorsalen Oberschenkelmuskulatur.",
    "sonografie_gastrocnemius_medialis": "Regelrechte Darstellung des M. gastrocnemius medialis.",
    "sonografie_dorsaler_unterschenkel": "Regelrechte Darstellung der dorsalen Unterschenkelmuskulatur.",
    "sonografie_anteriorer_oberschenkel": "Regelrechte Darstellung der anterioren Oberschenkelmuskulatur.",
}

# Praxis-Konvention für die übrigen Röntgen-/Sono-Regionen (gleiche Bauart wie die beigebrachten)
KONVENTION = {
    "nasenbein": "Regelrechte Darstellung des Nasenbeins.",
    "jochbogen": "Regelrechte Darstellung des Jochbogens.",
    "orthopantomogramm_des_kiefer-_und_gesichtsschädels": "Unauffälliger Befund.",
    "ganzaufnahme_der_wirbelsäule_a-p": "Regelrechte Darstellung der Wirbelsäule.",
    "schrägaufnahme_der_halswirbelsäule": "Regelrechte Darstellung der HWS.",
    "funktionsaufnahmen_der_halswirbelsäule": "Regelrechte Darstellung der HWS. Kein Hinweis auf eine segmentale Instabilität.",
    "funktionsaufnahmen_der_lendenwirbelsäule": "Regelrechte Darstellung der LWS. Kein Hinweis auf eine segmentale Instabilität.",
    "iliosakralgelenke_a-p": "Regelrechte Darstellung der Iliosakralgelenke.",
    "sternum_in_2_ebenen": "Regelrechte Darstellung des Sternums.",
    "schultergelenke_a-p_unter_belastung": "Regelrechte Darstellung beider Schultergelenke.",
    "clavicula": "Regelrechte Darstellung der Clavicula.",
    "akromioklavikulargelenk": "Regelrechte Darstellung des Akromioklavikulargelenkes.",
    "scapula_in_2_ebenen": "Regelrechte Darstellung der Scapula.",
    "schultergelenk_tangential_bizepssehnenkanal": "Regelrechte Darstellung des Bizepssehnenkanals.",
    "oberarm_in_2_ebenen": "Regelrechte Darstellung des Oberarms.",
    "ellbogengelenk_in_2_ebenen": "Regelrechte Darstellung des Ellbogengelenkes.",
    "axialaufnahme_des_ellbogens": "Regelrechte Darstellung des Ellbogengelenkes.",
    "unterarm_in_2_ebenen": "Regelrechte Darstellung des Unterarms.",
    "hand_in_2_ebenen": "Regelrechte Darstellung der Hand.",
    "handgelenk_in_2_ebenen": "Regelrechte Darstellung des Handgelenkes.",
    "karpaltunnelaufnahme": "Regelrechte Darstellung des Karpaltunnels.",
    "naviculareserie": "Regelrechte Darstellung des Os scaphoideum.",
    "ganzbeinaufnahme_im_stand": "Regelrechte Darstellung der Beinachsen.",
    "konturaufnahmen_des_femurkopfes": "Regelrechte Darstellung des Femurkopfes.",
    "oberschenkel_in_2_ebenen": "Regelrechte Darstellung des Oberschenkels.",
    "defileeaufnahmen_der_patella_in_30°_60°_und_90°": "Regelrechte Darstellung der Patella.",
    "mittelfuß_in_2_ebenen": "Regelrechte Darstellung des Mittelfußes.",
    "beinphlebographie": "Unauffälliger Befund.",
    "schulterprothese": "Regelrechte Lage der Schulterprothese ohne Lockerungszeichen.",
    "daumensattelprothese": "Regelrechte Lage der Daumensattelgelenksprothese ohne Lockerungszeichen.",
    "knieprothese": "Regelrechte Lage der Knieprothese ohne Lockerungszeichen.",
    "hüftprothese": "Regelrechte Lage der Hüftprothese ohne Lockerungszeichen.",
    "beckenübersicht_und_hüfte": "Regelrechte Darstellung des Beckens und des Hüftgelenkes.",
    "beckenübersicht_mit_einseitiger_hüftprothese": "Regelrechte Lage der Hüftprothese ohne Lockerungszeichen.",
    "beckenübersicht_mit_beidseitiger_hüftprothese": "Regelrechte Lage beider Hüftprothesen ohne Lockerungszeichen.",
    "wirbelsäule_gesamt": "Regelrechte Darstellung der Wirbelsäule.",
    "hws_und_lws": "Regelrechte Darstellung der HWS und LWS.",
    "mammographie_beidseits": "Unauffälliger Befund. BI-RADS 1 beidseits.",
    "mammasonographie_beidseits": "Unauffälliger Befund. BI-RADS 1 beidseits.",
    "sonografie_weichteile": "Regelrechte Darstellung der Weichteile.",
    "sonografie_unterschenkel": "Regelrechte Darstellung des Unterschenkels.",
    "sonografie_schilddrüse": "Unauffälliger Befund der Schilddrüse.",
    "sonografie_beinvenen": "Kein Hinweis auf eine Thrombose.",
    "varizensonografie": "Unauffälliger Befund.",
}
# Alles andere (MR/CT/Abdomen-Sono/Nerven/(Allgemein)/DEXA/Blockade …): 'Unauffälliger Befund.'
# Ausnahme: DEXA und Blockade sind keine Normal/Pathologie-Untersuchungen → kein Standard-Ergebnis.
OHNE = {"knochendichtemessung_dexa", "ultraschall_gezielte_blockade"}


def main():
    exe_p = REPO / "templates.json"  # seit Umbau Schritt 20 die einzige Vorlagen-Datei (EXE + Web)
    t = json.loads(exe_p.read_text())
    for k in list(TAUGHT) + list(KONVENTION):
        assert k in t, f"unbekannter Key {k}"
    for k, v in t.items():
        if k in OHNE:
            v.pop("ergebnis", None)
            continue
        v["ergebnis"] = TAUGHT.get(k) or KONVENTION.get(k) or "Unauffälliger Befund."
    payload = json.dumps(t, ensure_ascii=False, indent=2) + "\n"
    exe_p.write_text(payload)
    print(f"{sum('ergebnis' in v for v in t.values())}/{len(t)} Templates mit Normal-Ergebnis")


if __name__ == "__main__":
    main()
