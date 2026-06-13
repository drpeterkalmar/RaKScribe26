import os
import sqlite3
import re

# Pfade definieren
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEFUNDE_DIR = os.path.join(BASE_DIR, "Befundvorlagen")
DB_PATH = os.path.join(BASE_DIR, "practice_reports.db")

def clean_edifact_text(text):
    """
    Bereinigt die speziellen EDIFACT-Fluchtzeichen.
    In EDIFACT wird '?' als Escape-Zeichen verwendet.
    """
    text = text.replace("?+", "+")
    text = text.replace("?:", ":")
    text = text.replace("?'", "'")
    text = text.replace("?.", ".")
    text = text.replace("??", "?")
    return text

def parse_bef_file(filepath):
    """
    Liest eine .bef Datei in CP850 Kodierung ein und extrahiert BFD und ERG Segmente.
    """
    try:
        with open(filepath, "r", encoding="cp850", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return None, f"Fehler beim Lesen der Datei: {e}"
    
    # Trennung der Segmente anhand des EDIFACT-Segmenttrenners '\''
    segments = content.split("'")
    
    bfd_lines = []
    erg_lines = []
    
    for seg in segments:
        seg = seg.strip()
        if seg.startswith("FTX+BFD++"):
            line = seg[9:]
            bfd_lines.append(clean_edifact_text(line))
        elif seg.startswith("FTX+ERG++"):
            line = seg[9:]
            erg_lines.append(clean_edifact_text(line))
            
    bfd_text = "\n".join(bfd_lines).strip()
    erg_text = "\n".join(erg_lines).strip()
    
    # Zusammenführen von Befund und Ergebnis (falls vorhanden)
    full_report = bfd_text
    if erg_text:
        full_report += "\n\nErgebnis:\n" + erg_text
        
    return full_report, None

def anonymize_and_clean_report(text):
    """
    Bereinigt den Bericht von Kopfzeilen (Patientendaten, Arzt, Datum) und Fußzeilen (Signaturen),
    um die DSGVO-Konformität zu gewährleisten und Rauschen für das LLM zu minimieren.
    """
    lines = text.split("\n")
    cleaned_lines = []
    
    # Zeilenpräfixe zum Überspringen (Header)
    skip_headers = [
        "arzt:", "befunddatum:", "patient:", "geb.dat.:", "geb.dat?:", 
        "patient?:", "befunddatum?:", "arzt?:", "radiologie og"
    ]
    
    # Schlüsselwörter zum Abbrechen des Einlesens (Footer / Signaturen)
    stop_footers = [
        "mit bestem dank", 
        "herzlichem gruß", 
        "herzlichem gru?",
        "erstbefunder", 
        "zweitbefunder", 
        "ihr befund ist", 
        "your findings are", 
        "vas nalaz je", 
        "raporunuzda",
        "___",
        "dr. med.",
        "dr. gu",
        "dr. gnter"
    ]
    
    in_clinical_part = False
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            if in_clinical_part:
                cleaned_lines.append("")
            continue
            
        # Überprüfen auf Kopfzeilen
        is_header = False
        for h in skip_headers:
            if line_strip.lower().startswith(h):
                is_header = True
                break
        if is_header:
            continue
            
        # Überprüfen auf Fußzeilen (bricht das Lesen ab, da danach nur noch Signaturen kommen)
        is_footer = False
        for f in stop_footers:
            if f in line_strip.lower():
                is_footer = True
                break
        if is_footer:
            break
            
        # Wenn wir hier ankommen, sind wir im klinischen Teil des Befundes
        in_clinical_part = True
        cleaned_lines.append(line_strip)
        
    content = "\n".join(cleaned_lines).strip()
    return content

def classify_report(text):
    """
    Klassifiziert den Befund anhand von Schlüsselwörtern in Untersuchungstypen.
    """
    text_lower = text.lower()
    
    categories = {
        "Mammographie": ["mammographie", "mamma", "screening"],
        "LWS": ["lws", "lendenwirbel", "lumbal", "l4/5", "l5/s1"],
        "HWS": ["hws", "halswirbel", "cervical", "hwk"],
        "BWS": ["bws", "brustwirbel", "thorakal", "bwk"],
        "Thorax": ["thorax", "röntgen thorax", "lunge", "pulmo", "cor", "rö-th"],
        "Knie": ["knie", "gonarthrose", "meniskus", "patella"],
        "Schulter": ["schulter", "rotatorenmanschette", "humerus", "omarthrose"],
        "Sonographie Abdomen": ["sono abd", "sonografie abd", "ultraschall abd"],
        "Sonographie Schilddrüse": ["sono schild", "sonografie schilddrüse"],
        "Hüfte": ["hüft", "coxarthrose", "acetabulum"],
        "Sprunggelenk/Fuß": ["sprunggelenk", "calcaneus", "tarsus", "fuß", "zehe"],
        "Hand/Finger/Handgelenk": ["handgelenk", "karpaltunnel", "finger", "scaphoideum"],
        "CT": ["ct", "computertomographie", "cct"],
        "MRT": ["mrt", "mr des", "mr der", "mr des gehirns", "mr der lws"],
    }
    
    matched = []
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(cat)
                break
                
    if not matched:
        return "Andere"
    elif len(matched) == 1:
        return matched[0]
    else:
        # Priorisierung bei Mehrfachnennung
        if "MRT" in matched: return "MRT"
        if "CT" in matched: return "CT"
        return matched[0]

def main():
    if not os.path.exists(BEFUNDE_DIR):
        print(f"[ERROR] Befundordner nicht gefunden: {BEFUNDE_DIR}")
        return

    files = [f for f in os.listdir(BEFUNDE_DIR) if f.endswith(".bef")]
    print(f"[INFO] Gefunden: {len(files)} .bef-Dateien.")
    
    # SQLite initialisieren
    print(f"[INFO] Initialisiere Datenbank: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            category TEXT,
            content TEXT
        )
    """)
    conn.commit()
    
    batch_data = []
    processed_count = 0
    skipped_count = 0
    
    for f in files:
        filepath = os.path.join(BEFUNDE_DIR, f)
        raw_text, err = parse_bef_file(filepath)
        if err or not raw_text:
            skipped_count += 1
            continue
            
        clean_text = anonymize_and_clean_report(raw_text)
        if not clean_text:
            skipped_count += 1
            continue
            
        category = classify_report(clean_text)
        batch_data.append((f, category, clean_text))
        processed_count += 1
        
        # Batch-Schreiben alle 1000 Einträge
        if len(batch_data) >= 1000:
            cursor.executemany(
                "INSERT OR REPLACE INTO reports (filename, category, content) VALUES (?, ?, ?)",
                batch_data
            )
            conn.commit()
            batch_data.clear()
            print(f"[INFO] {processed_count} Berichte verarbeitet...")
            
    # Restliche Daten schreiben
    if batch_data:
        cursor.executemany(
            "INSERT OR REPLACE INTO reports (filename, category, content) VALUES (?, ?, ?)",
            batch_data
        )
        conn.commit()
        
    print(f"[SUCCESS] Datenbank-Import abgeschlossen!")
    print(f"  - Erfolgreich verarbeitet: {processed_count}")
    print(f"  - Übersprungen (leer/Fehler): {skipped_count}")
    
    # Statistiken anzeigen
    cursor.execute("SELECT category, COUNT(*) FROM reports GROUP BY category ORDER BY COUNT(*) DESC")
    stats = cursor.fetchall()
    print("\n--- STATISTIKEN IN DER DATENBANK ---")
    for cat, count in stats:
        print(f"  {cat}: {count}")
        
    conn.close()

if __name__ == "__main__":
    main()
