import sqlite3
import os
from collections import Counter
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "practice_reports.db")
TEMPLATES_PATH = os.path.join(BASE_DIR, "templates.json")

# Mapping von Datenbank-Kategorien auf templates.json Keys
# Wir wählen vernünftige Zuordnungen
TEMPLATE_MAPPING = {
    "Thorax": "thorax_in_2_ebenen",
    "LWS": "lendenwirbelsäule_in_2_ebenen",
    "HWS": "halswirbelsäule_in_2_ebenen",
    "BWS": "brustwirbelsäule_in_2_ebenen",
    "Knie": "kniegelenk_in_2_ebenen",
    "Schulter": "schultergelenk_in_2_ebenen",
    "Hüfte": "hüftgelenk_in_2_ebenen",
    "Sprunggelenk/Fuß": "sprunggelenk_in_2_ebenen",
}

def clean_lr_and_make_template(text):
    """
    Ersetzt 'rechts'/'links' oder 'bds' durch Platzhalter oder macht den Text allgemeingültig,
    um ein sauberes Template zu erstellen.
    """
    # In Templates ist es oft besser, den Text so zu belassen oder leicht zu verallgemeinern
    # Wir entfernen auch patientenspezifische Rückbleibsel
    lines = text.split("\n")
    if not lines:
        return ""
        
    # Wenn die erste Zeile nur "Kniegelenk rechts" o.ä. ist, machen wir sie neutral
    first_line = lines[0].strip()
    if re_match := re.match(r"^(Kniegelenk|Schulter|Hand|Fuß|Hüftgelenk)\s+(rechts|links|beidseits|bds\.?)$", first_line, re.IGNORECASE):
        lines[0] = re_match.group(1) # Z.B. nur "Kniegelenk"
        
    return "\n".join(lines).strip()

import re

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Datenbank nicht gefunden unter: {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # templates.json laden
    if os.path.exists(TEMPLATES_PATH):
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            templates = json.load(f)
    else:
        templates = {}
        
    print("[INFO] Analysiere häufigste Befundtexte je Kategorie...")
    
    updates_proposed = {}
    
    for cat, template_key in TEMPLATE_MAPPING.items():
        cursor.execute("SELECT content FROM reports WHERE category = ?", (cat,))
        rows = cursor.fetchall()
        if not rows:
            continue
            
        texts = [r[0] for r in rows]
        # Häufigkeitsanalyse
        counter = Counter(texts)
        
        print(f"\n--- Top 3 für Kategorie {cat} (Gesamt: {len(texts)} Befunde) ---")
        top_entries = counter.most_common(3)
        for i, (txt, count) in enumerate(top_entries):
            preview = txt.replace('\n', ' | ')[:120]
            print(f"  {i+1}. [Anzahl: {count}] {preview}...")
            
        # Wir nehmen den am häufigsten vorkommenden Text als neuen Template-Kandidaten,
        # WENN er mindestens eine gewisse Häufigkeit hat (z.B. >= 2) oder wir den typischen Stil sehen.
        # Alternativ: Für manche Kategorien wie LWS sind fast alle Befunde pathologisch (daher einzigartig).
        # Bei LWS ist der häufigste Befund vielleicht nur 3x vorhanden. In diesem Fall nehmen wir den häufigsten
        # der wie ein Normalbefund aussieht ("Sonst unauffälliger Befund" oder ähnlich) oder nutzen einen 
        # manuell bereinigten häufigen Befund.
        
        # Für Thorax, Knie, Schulter ist der häufigste Befund oft ein echter Normalbefund.
        best_candidate, best_count = top_entries[0]
        
        # Säubern von rechts/links etc.
        template_body = clean_lr_and_make_template(best_candidate)
        
        updates_proposed[template_key] = template_body

    # Aktualisieren von templates.json
    print("\n[INFO] Aktualisiere templates.json mit den häufigsten Praxis-Normalbefunden...")
    
    for key, new_body in updates_proposed.items():
        if key in templates:
            print(f"  -> Aktualisiere Vorlage '{key}'")
            print(f"     ALT: {templates[key]['body'][:80]}...")
            print(f"     NEU: {new_body[:80]}...")
            templates[key]["body"] = new_body
            
    with open(TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)
        
    print("[SUCCESS] templates.json erfolgreich aktualisiert!")
    conn.close()

if __name__ == "__main__":
    main()
