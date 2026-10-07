"""Befund-Pipeline der EXE ohne Oberfläche (Umbau Schritte 5 + 15) — ohne Windows/Tk importierbar und testbar.

befund_aus_diktat(diktat, ctx): Fehlhör-Liste → Regionen-Trenner → je Region Normalbefund-Bypass ODER LLM
(Gen-Prompt aus radiology_prompt.txt + Vorlage) → Nachbearbeitung (## Befund sichern, Ergebnis nummerieren)
→ Regionen zusammenfügen. Die Oberfläche (RaKScribe.py) und die Test-/Messkette (prod_pipeline.exe_kette)
rufen DIESELBE Funktion; nur der LLM-Aufruf wird übergeben (ctx.llm).
Tests: tests/offline/test_pipeline_exe.py, tests/offline/test_regionen.py.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import bausteine as bs
import befund_regeln as br
import detect
import gemini
import normalbypass as nb
import protokoll

ORDI_BAUSTEINE = bs.laden()  # v3.3 (Peter 06.10.): gebündelt, keine Extradatei

FEHLTEXT = "Befund für Region {region} konnte nicht erstellt werden — bitte erneut diktieren."


def region_name(segment):
    """Kurzname eines Diktat-Segments für Hinweise: erster Satz (z. B. „Ellbogen rechts“), höchstens 40 Zeichen.
    Satzende auch gesprochen („Punkt“, „neue Zeile“, „Absatz“) — so kommt es aus chirp_3."""
    erster = re.split(r"[.:;,\n]|(?<!\w)(?:punkt|neue\s+zeile|neuzeile|absatz)(?!\w)", (segment or "").strip(),
                      maxsplit=1, flags=re.I)[0].strip()
    return erster[:40].strip() or "?"


def assemble_regions(segmente, teile, ist_vollstaendig):
    """Mehr-Regionen-Befund zusammensetzen (Gutachten P2-6). teile[i] = Befundtext oder Exception (bzw. None).
    Gescheiterte/unvollständige Regionen stehen als Hinweistext an ihrer Stelle, fertige Befunde bleiben sichtbar.
    Rückgabe: (report, [Namen der gescheiterten Regionen]) — report wird bei Fehlern NIE eingefügt."""
    bloecke, fehler = [], []
    for seg, teil in zip(segmente, teile):
        if isinstance(teil, str) and ist_vollstaendig(teil):
            bloecke.append(teil)
        else:
            name = region_name(seg)
            fehler.append(name)
            bloecke.append(FEHLTEXT.format(region=name))
    return br.befunde_zusammenfuegen(bloecke), fehler


@dataclass
class Kontext:
    templates: dict                              # templates.json
    display_names: list                          # für den Normalbefund-Bypass
    prompt: str                                  # Gen-Prompt (radiology_prompt.txt, mit Versionsmarker)
    llm: Callable[[str], str]                    # Gen-Prompt → Rohbefund (Gemini/OpenAI); wirft bei Fehler
    misheard: Optional[Callable[[str], str]] = None   # deterministische Fehlhör-Korrektur (mode 'auto')
    hinweise: str = ""                           # <stt_hinweise> (Fehlhör-Liste, mode 'llm')
    beispiele: Optional[Callable[[str], str]] = None  # RAG-Beispiele je Segment (Standard aus)
    log: Callable[..., Any] = print
    ausnahme_log: Optional[Callable[[str], Any]] = None  # wird IM except-Block gerufen (Traceback)
    protokoll: Optional[list] = None             # Mess-Harness: je Segment {segment, template, roh}
    bausteine: Optional[dict] = None             # v3.3: Ordi-Textbausteine (Standard: gebündelte ordi_bausteine.json)
    korrektur: Optional[Callable[[str], str]] = None  # v3.4: Call 0 (korrektur.py) — nur im Nur-Text-Modus


@dataclass
class Ergebnis:
    raw: str = ""                                # Diktat nach Fehlhör-Korrektur
    report: str = ""
    fehler: List[str] = field(default_factory=list)       # gescheiterte Regionen (Mehr-Regionen-Diktat)
    ausnahmen: List[Exception] = field(default_factory=list)
    segmente: List[str] = field(default_factory=list)
    leer: bool = False                           # kein Text diktiert

    @property
    def vollstaendig(self):
        return not self.fehler and gemini.report_complete(self.report)


def ist_normalbefund(raw, template_key, display_names):
    """Bypass ohne LLM nur bei REINEM Normalbefund (nur Untersuchung + Normal-Worte, v3.2 Peter 05.10.)
    UND erkannter Region — jedes weitere Wort ("sonst", Pathologie, Beschreibung) → LLM."""
    return nb.is_pure_normal_finding(raw, display_names) and template_key != "allgemein"


def bypass_befund(raw, template_data):
    """Normalbefund direkt aus der Vorlage. v3.2 (Peter 05.10.): Ergebnis = Normal-Ergebnis der Untersuchung
    (+ Seite) — NIE das Diktat abschreiben; v3.2.2: CSA-Platzhalter raus (nachbearbeiten)."""
    ergebnis = br.ergebnis_mit_seite(template_data.get('ergebnis', ''), raw)
    tpl_lines = template_data['body'].split('\n')
    tpl_title = br.titel_mit_seite(detect.derive_untersuchungs_titel(raw, tpl_lines[0].strip().rstrip(':')), raw)
    tpl_body = '\n'.join(tpl_lines[1:])
    return f"## {tpl_title}\n\n## Befund\n{tpl_body}\n\n## Ergebnis\n{ergebnis}"


def gen_prompt(raw, template_data, prompt, hinweise="", beispiele=""):
    """Gen-Prompt für EIN Segment (wie bisher in RaKScribe.py _befund_fuer_segment)."""
    p_full = br.strip_prompt_marker(prompt)
    p_full = p_full.replace('{roh_text}', raw)
    p_full = p_full.replace('{template_body}', template_data['body'])
    p_full = p_full.replace('{region_name}', template_data['display_name'])
    # v2.10.13 (K3-Review Befund 2/3): Der LLM-Pfad bekommt die KANONISCHE Bezeichnung (display_name, inkl.
    # "(Allgemein)"), damit die "(Allgemein)"-Ausnahme im Gen-Prompt ECHT feuern kann — bei pathologischen
    # (Allgemein)-Diktaten leitet das LLM die Überschrift aus dem Diktat ab. Der Bypass-Pfad bleibt bei derive.
    p_full = p_full + "\n<untersuchung>" + template_data['display_name'] + "</untersuchung>\n"
    # v3.2 (Peter 05.10.): Normal-Ergebnis der Untersuchung — fürs Ergebnis, wenn das Diktat keine Pathologie nennt
    p_full = p_full + "<normal_ergebnis>" + (template_data.get('ergebnis') or "Unauffälliger Befund.") + "</normal_ergebnis>\n"
    if hinweise:  # v3.1: kontextabhängige Verhörer (mode 'llm') als Hinweis für Gemini
        p_full = p_full + hinweise + "\n"
    if "{examples}" in p_full:
        return p_full.replace("{examples}", beispiele)
    return p_full + "\n\n" + beispiele


def befund_fuer_segment(seg, ctx):
    """Ein Befund (## Titel / ## Befund / ## Ergebnis) für EIN Diktat-Segment = eine Region."""
    bausteine = ORDI_BAUSTEINE if ctx.bausteine is None else ctx.bausteine
    b_key, b_rest = bs.befund_baustein(seg, bausteine)
    if b_key:  # v3.3 (Peter 06.10.): „Baustein Mammo 1“ → Ordi-Textbaustein statt Vorlage
        template_key = "baustein:" + b_key
        woertlich = bs.nur_baustein(b_rest)
        if woertlich:
            ctx.log(f"[BAUSTEIN] '{b_key}' wörtlich (ohne KI).")
            roh = bs.bericht(b_key, bausteine, seg)
        else:
            template_data = bs.vorlage(b_key, bausteine, seg)
            beispiele = ctx.beispiele(seg) if ctx.beispiele else ""
            hinweise = (ctx.hinweise + "\n" if ctx.hinweise else "") + bs.KI_HINWEIS.format(key=b_key)
            roh = ctx.llm(gen_prompt(seg, template_data, ctx.prompt, hinweise, beispiele))
        if ctx.protokoll is not None:
            ctx.protokoll.append({"segment": seg, "template": template_key, "roh": roh})
        return br.nachbearbeiten(roh, nummerieren=not woertlich)  # v3.7.2: wörtlich = Layout der Ordi unverändert
    template_key = detect.detect_template(seg, ctx.templates)
    template_data = ctx.templates.get(template_key) or ctx.templates["allgemein"]  # templates.json enthält „allgemein“
    if ist_normalbefund(seg, template_key, ctx.display_names):
        ctx.log(f"[BYPASS] Normalbefund erkannt: {protokoll.diktat(seg)}. Generiere direkt aus Template '{template_key}'.")
        roh = bypass_befund(seg, template_data)
    else:
        beispiele = ctx.beispiele(seg) if ctx.beispiele else ""
        roh = ctx.llm(gen_prompt(seg, template_data, ctx.prompt, ctx.hinweise, beispiele))
    if ctx.protokoll is not None:
        ctx.protokoll.append({"segment": seg, "template": template_key, "roh": roh})
    # v3.2: '## Befund' sichern + Ergebnis deterministisch nummerieren (einzelner Normalbefund-Satz unnummeriert)
    return br.nachbearbeiten(roh)


def befund_aus_diktat(diktat, ctx, beim_start=None):
    """Diktat → Ergebnis. Ein-Regionen-Diktat: Fehler werden geworfen (wie bisher); Mehr-Regionen-Diktat:
    gescheiterte Regionen stehen in Ergebnis.fehler, die übrigen im Report (Gutachten P2-6)."""
    raw = (diktat or "").strip()
    if ctx.misheard:
        raw = ctx.misheard(raw)  # v3.1: Fehlhör-Liste vor Bypass/LLM
    if not raw:
        return Ergebnis(leer=True)
    # v3.3: Satz-Bausteine („Baustein A1“, „Baustein Fraktur“) wörtlich an derselben Stelle einsetzen
    raw = bs.saetze_einsetzen(raw, ORDI_BAUSTEINE if ctx.bausteine is None else ctx.bausteine)
    if beim_start:
        beim_start()
    # v3.2: Diktat mit mehreren Regionen ("Schulter rechts … Ellbogen rechts …") → je Region ein eigener Befund
    # (eigenes Template, eigenes Ergebnis), parallel erzeugt und untereinander ausgegeben.
    segmente = br.split_regionen(raw)
    if len(segmente) <= 1:
        return Ergebnis(raw=raw, report=befund_fuer_segment(raw, ctx), segmente=segmente)
    ctx.log(f"[MULTI] {len(segmente)} Regionen")
    with ThreadPoolExecutor(max_workers=len(segmente)) as ex:
        futures = [ex.submit(befund_fuer_segment, seg, ctx) for seg in segmente]
    teile, ausnahmen = [], []
    for fut in futures:
        try:
            teile.append(fut.result())
        except Exception as e:  # eine Region scheitert → die anderen trotzdem zeigen
            if ctx.ausnahme_log:
                ctx.ausnahme_log("Befund-Generierung (Region)")
            ausnahmen.append(e)
            teile.append(e)
    report, fehler = assemble_regions(segmente, teile, gemini.report_complete)
    return Ergebnis(raw=raw, report=report, fehler=fehler, ausnahmen=ausnahmen, segmente=segmente)


def nur_text_aus_diktat(diktat, ctx):
    """v3.4.0 (Peter 07.10., „manchmal ist weniger mehr“): nur die korrigierte Spracherkennung, kein Befund.
    Fehlhör-Liste → Call-0-Korrektur (wie Web) → Satz-Bausteine. Sync: pipeline.ts nurTextAusDiktat."""
    raw = (diktat or "").strip()
    if ctx.misheard:
        raw = ctx.misheard(raw)
    if not raw:
        return Ergebnis(leer=True)
    if ctx.korrektur:
        raw = (ctx.korrektur(raw) or raw).strip()
    raw = bs.saetze_einsetzen(raw, ORDI_BAUSTEINE if ctx.bausteine is None else ctx.bausteine)
    return Ergebnis(raw=raw, report=raw, segmente=[raw])
