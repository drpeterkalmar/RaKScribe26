#!/usr/bin/env python3
"""
Migration: 44 beigebrachte Normalbefunde (Skill radiology-shoulder-dictation)
→ templates.json (EXE + Web, byte-identisch).

Regeln:
- REPLACED: Body-Inhalt wird durch den taught-Block ersetzt; Zeile 1 = display_name
  (kanonische Untersuchungs-Überschrift, v2.10.6-Konvention).
- NEW: neue Keys, Zeile 1 + display_name = taught-Header.
- KEPT bewusst unverändert: beinphlebographie (eigene Pressphlebo-Variante kommt
  als neuer Key dazu), naviculareserie (Skaphoidaufnahme kommt als neuer Key dazu),
  sonografie_halsweichteile (breiter gefasst als taught 'Sonographie Hals').
- sonografie_halsgefaesse: taught-Block (mit Titelzeile, '< 0,9 mm'), da App-Body
  ohne Titelzeile war (Bypass hätte Satz 1 als Überschrift geschrieben).
- sonografie_halsweichteile: Titelzeile ergänzt + taught 'Sonographie Hals'-Terminologie
  ('cervicalen Lymphknoten') gemerged statt eigener Duplikat-Key.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).parent
TAUGHT = json.loads((REPO / "taught_blocks.json").read_text())

# taught-Blockname → (mode, template_key)
PLAN_REPLACE = {
    "Schädel in 2 Ebenen": "schädel_in_2_ebenen",
    "Halswirbelsäule in 2 Ebenen mit Dens-Zielaufnahme": "halswirbelsäule_in_2_ebenen",
    "Brustwirbelsäule in 2 Ebenen": "brustwirbelsäule_in_2_ebenen",
    "Lendenwirbelsäule in 2 Ebenen": "lendenwirbelsäule_in_2_ebenen",
    "Kreuzbein in 2 Ebenen": "kreuzbein_und_steißbein_in_2_ebenen",
    "Beckenübersicht a.-p. stehend": "beckenübersicht_stehend",
    "Hüftgelenk in 2 Ebenen": "hüftgelenk_in_2_ebenen",
    "Kniegelenk in 2 Ebenen": "kniegelenk_in_2_ebenen",
    "Unterschenkel in 2 Ebenen": "unterschenkel_in_2_ebenen",
    "Sprunggelenk in 2 Ebenen": "sprunggelenk_in_2_ebenen",
    "Zehe in 2 Ebenen": "zehe_in_2_ebenen",
    "Fuß in 2 Ebenen": "fuß_in_2_ebenen",
    "Vorfuß in 2 Ebenen": "vorfuß_in_2_ebenen",
    "Thorax p.a. und seitlich": "thorax_in_2_ebenen",
    "Knöcherner Hemithorax": "knöcherner_hemithorax",
    "Abdomen im Stand": "abdomen_im_stand",
    "Abdomen im Liegen": "abdomen_im_liegen",
    "Nasennebenhöhlen in 2 Ebenen": "nasennebenhöhlen",
    "Schädelfernröntgen": "schädelfernröntgen",
    "Magen-Duodenum in Doppelkontrast": "durchleuchtung:_magen-darm-passage_mdp",
    "Oesophagus in Doppelkontrast": "durchleuchtung:_ösophagus-breischluck",
    "Hysterosalpingographie": "hysterosalpingographie",
    "Intravenöse Urographie (IVP)": "intravenöses_urogramm",
    "Schultergelenk in 2 Ebenen": "schultergelenk_in_2_ebenen",
    "Finger in 2 Ebenen": "finger_in_2_ebenen",
    "Sonographie der Schulter": "sonografie_schultergelenk",
    "Farbcodierte Duplex-Sonographie der Halsgefäße": "sonografie_halsgefaesse",
}

# taught-Blockname → neuer Key (display_name = taught-Blockname)
PLAN_NEW = {
    "Orbita p.-a.-Aufnahme": "orbita_pa_aufnahme",
    "Steißbein in 2 Ebenen": "steißbein_in_2_ebenen",
    "Sprunggelenk mit Mortise View in 2 Ebenen": "sprunggelenk_mortise_view",
    "Sprunggelenk in 2 Ebenen mit gehaltenen Aufnahmen": "sprunggelenk_gehaltene_aufnahmen",
    "Sprunggelenk in 2 Ebenen mit Fuß": "sprunggelenk_mit_fuss",
    "Calcaneus in 2 Ebenen": "calcaneus_in_2_ebenen",
    "Calcaneus seitlich": "calcaneus_seitlich",
    "Skaphoidaufnahme": "skaphoidaufnahme",
    "Oesophagus-Magenduodenum in Doppelkontrast": "oesophagus_magenduodenum_doppelkontrast",
    "Videokinematographie des Schluckaktes": "videokinematographie_schluckakt",
    "Aszendierende Pressphlebographie des rechten Beins": "aszendierende_pressphlebographie",
    "Sonographie der Bauchdecke": "sonografie_bauchdecke",
    "Sonographie der dorsalen Oberschenkelmuskulatur": "sonografie_dorsaler_oberschenkel",
    "Sonographie des M. gastrocnemius medialis": "sonografie_gastrocnemius_medialis",
    "Sonographie der dorsalen Unterschenkelmuskulatur": "sonografie_dorsaler_unterschenkel",
    "Sonographie der anterioren Oberschenkelmuskulatur": "sonografie_anteriorer_oberschenkel",
}

KEEP = {
    "beinphlebographie": "bewusste Doppel-Variante: taught Pressphlebographie = neuer Key aszendierende_pressphlebographie",
    "naviculareserie": "bewusste Doppel-Variante: taught Skaphoidaufnahme = neuer Key skaphoidaufnahme",
    "sonografie_halsweichteile": "breiter gefasst als taught 'Sonographie Hals' (Schilddrüse/Jugularis-Anteile) — bleibt",
}

def migrate(templates: dict) -> dict:
    t = json.loads(json.dumps(templates))  # deep copy

    for block_name, key in PLAN_REPLACE.items():
        display = t[key]["display_name"]
        body = TAUGHT[block_name].strip()
        t[key]["body"] = f"{display}\n\n{body}"

    for block_name, key in PLAN_NEW.items():
        if key in t:
            sys.exit(f"FATAL: neuer Key existiert bereits: {key}")
        t[key] = {
            "display_name": block_name,
            "body": f"{block_name}\n\n{TAUGHT[block_name].strip()}",
        }

    # Duplex (sonografie_halsgefaesse) ersetzt durch taught-Block:
    # gleiche Sätze, aber '< 0,9 mm' statt 'unter 0,9 mm' und MIT Titelzeile
    # (v2.10.8-Format) — bisher hätte der Bypass den ersten Satz als Überschrift
    # geschrieben.
    t["sonografie_halsgefaesse"]["body"] = (
        "Farbcodierte Duplex-Sonographie der Halsgefäße\n\n"
        + TAUGHT["Farbcodierte Duplex-Sonographie der Halsgefäße"].strip()
    )

    # Verbrauch prüfen: jeder taught-Block muss verplant sein
    consumed = set(PLAN_REPLACE) | set(PLAN_NEW) | {
        "Aszendierende Pressphlebographie des rechten Beins",
        "Farbcodierte Duplex-Sonographie der Halsgefäße",
        "Sonographie Hals",  # → sonografie_halsweichteile (Merge, siehe unten)
    }
    if missing := set(TAUGHT) - consumed:
        sys.exit(f"FATAL: unbehandelte taught-Blöcke: {missing}")

    # Merge statt Duplikat: taught 'Sonographie Hals' ist Teilmenge des
    # App-Templates sonografie_halsweichteile. App-Details (jugulärer Strang,
    # Fetthilus, Weichteile) bleiben; taught-Absatz wörtlich als erster Absatz.
    # Titelzeile ergänzen (Bypass-Sicherheit, wie überall sonst).
    hw = t["sonografie_halsweichteile"]["body"]
    if not hw.startswith("Sonographie der Halsweichteile"):
        hw = "Sonographie der Halsweichteile\n\n" + hw
    taught_hals = TAUGHT["Sonographie Hals"].strip()
    first_para = hw.split("\n", 1)[1].strip() if "\n" in hw else hw
    if taught_hals not in hw:
        hw = "Sonographie der Halsweichteile\n\n" + taught_hals + "\n" + first_para
    t["sonografie_halsweichteile"]["body"] = hw
    return t


def main():
    exe_path = REPO / "templates.json"
    web_path = REPO / "web_app" / "src" / "templates.json"

    before = json.loads(exe_path.read_text())
    assert before == json.loads(web_path.read_text()), "EXE/Web templates divergiert vor Migration!"

    after = migrate(before)

    payload = json.dumps(after, ensure_ascii=False, indent=2) + "\n"
    exe_path.write_text(payload)
    web_path.write_text(payload)  # byte-identisch

    print(f"Keys: {len(before)} → {len(after)} (+{len(after)-len(before)})")
    print("Ersetzte Bodies:", len(PLAN_REPLACE))
    print("Neue Keys:", len(PLAN_NEW))
    print("Byte-identisch geschrieben:", exe_path, web_path)


if __name__ == "__main__":
    main()