"""Befund-Pipeline der EXE ohne Oberfläche (Umbau Schritte 5 + 15) — ohne Windows/Tk importierbar und testbar.

befund_aus_diktat(diktat, ctx): Fehlhör-Liste → Regionen-Trenner → je Region Normalbefund-Bypass ODER LLM
(Gen-Prompt aus radiology_prompt.txt + Vorlage) → Nachbearbeitung (## Befund sichern, Ergebnis nummerieren)
→ Regionen zusammenfügen. Die Oberfläche (RaKScribe.py) und die Test-/Messkette (prod_pipeline.exe_kette)
rufen DIESELBE Funktion; nur der LLM-Aufruf wird übergeben (ctx.llm).
Tests: tests/offline/test_pipeline_exe.py, tests/offline/test_regionen.py.
v3.13.0: mit IB-Lab-Bausteinen (ctx.ibl) danach ibl_anwenden() — Messwerte wörtlich, ohne KI (ibl_bausteine.py).
"""
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import bausteine as bs
import befund_regeln as br
import cas_vorlagen as cv
import detect
import gemini
import ibl_bausteine as iblb
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
    cas: Optional[cv.CasHinweis] = None          # v3.12.0: CAS-Leistungen des Auftrags (Vorrang-Hinweis); None = wie bisher
    ibl: Optional[iblb.IblKontext] = None         # v3.13.0: IB-Lab-Bausteine des Auftrags (nach der KI einsetzen); None = wie bisher


@dataclass
class Ergebnis:
    raw: str = ""                                # Diktat nach Fehlhör-Korrektur
    report: str = ""
    fehler: List[str] = field(default_factory=list)       # gescheiterte Regionen (Mehr-Regionen-Diktat)
    ausnahmen: List[Exception] = field(default_factory=list)
    segmente: List[str] = field(default_factory=list)
    leer: bool = False                           # kein Text diktiert
    cas_hinweise: List[str] = field(default_factory=list)  # v3.12.0: „LWS laut CAS, nicht diktiert“ usw. (nur Anzeige)
    vorlagen: List[str] = field(default_factory=list)      # v3.12.0: gewählte Vorlage je Abschnitt (nur mit CAS)
    ibl: Optional[iblb.Einsatz] = None            # v3.13.0: eingesetzte IB-Lab-Zeilen + Hinweise (nur mit Bausteinen)

    @property
    def vollstaendig(self):
        return not self.fehler and gemini.report_complete(self.report)


def ist_normalbefund(raw, template_key, display_names):
    """Bypass ohne LLM nur bei REINEM Normalbefund (nur Untersuchung + Normal-Worte, v3.2 Peter 05.10.)
    UND erkannter Region — jedes weitere Wort ("sonst", Pathologie, Beschreibung) → LLM."""
    return nb.is_pure_normal_finding(raw, display_names) and template_key != "allgemein"


def bypass_befund(raw, template_data, seite=None, erzwingen=False):
    """Normalbefund direkt aus der Vorlage. v3.2 (Peter 05.10.): Ergebnis = Normal-Ergebnis der Untersuchung
    (+ Seite) — NIE das Diktat abschreiben; v3.2.2: CSA-Platzhalter raus (nachbearbeiten).
    v3.12.0: seite = Seite der passenden CAS-Leistung — nur, wenn das Diktat selbst keine nennt.
    v3.15.4: erzwingen = CAS-Leistung beidseits → „beidseits“, auch wenn das Diktat eine Seite nennt."""
    if erzwingen and seite:
        raw_ohne = " ".join(re.sub(r"(?<!\w)(?:rechts|links|re\.|li\.)(?!\w)", " ", raw, flags=re.I).split())
        mit_seite = f"{raw_ohne} {seite}"
    else:
        mit_seite = raw if (not seite or br.diktierte_seite(raw)) else f"{raw} {seite}"
    ergebnis = br.ergebnis_mit_seite(template_data.get('ergebnis', ''), mit_seite)
    tpl_lines = template_data['body'].split('\n')
    tpl_title = br.titel_mit_seite(detect.derive_untersuchungs_titel(raw, tpl_lines[0].strip().rstrip(':')), mit_seite)
    tpl_body = '\n'.join(tpl_lines[1:])
    return f"## {tpl_title}\n\n## Befund\n{tpl_body}\n\n## Ergebnis\n{ergebnis}"


def gen_prompt(raw, template_data, prompt, hinweise="", beispiele="", cas_block="", ibl_block=""):
    """Gen-Prompt für EIN Segment (wie bisher in RaKScribe.py _befund_fuer_segment). v3.12.0: cas_block =
    <cas_untersuchungen> (nur mit CAS-Leistungen; leer = Prompt bit-gleich wie bisher). v3.13.0: ibl_block =
    <ibl_messwerte> (nur mit IB-Lab-Bausteinen zur Region des Abschnitts; leer = bit-gleich)."""
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
    if cas_block:
        p_full = p_full + cas_block + "\n"
    if ibl_block:
        p_full = p_full + ibl_block + "\n"
    if hinweise:  # v3.1: kontextabhängige Verhörer (mode 'llm') als Hinweis für Gemini
        p_full = p_full + hinweise + "\n"
    if "{examples}" in p_full:
        return p_full.replace("{examples}", beispiele)
    return p_full + "\n\n" + beispiele


def befund_fuer_segment(seg, ctx, wahl=None):
    """Ein Befund für EIN Segment; v3.9.0 (Georg 13.10.): Rho-Auslöser raus aus dem Diktat, Rho-Baustein danach rein.
    v3.12.0: wahl = Vorlagenwahl mit CAS-Hinweis (cas_vorlagen.Wahl) oder None (= Erkennung wie bisher)."""
    seg_ohne, score, rho = br.rho_erkennen(seg)
    if not rho:
        return _befund_fuer_segment(seg, ctx, wahl)
    ctx.log(f"[RHO] Textbaustein (Score {score or '–'})")
    return br.rho_einfuegen(_befund_fuer_segment(seg_ohne, ctx, wahl), score)


def _befund_fuer_segment(seg, ctx, wahl=None):
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
            wid_block = br.widerspruch_prompt(br.widerspruch_befunde(seg), template_data["body"])   # v3.15.5
            if wid_block:
                beispiele = wid_block + ("\n" + beispiele if beispiele else "")
            roh = ctx.llm(gen_prompt(seg, template_data, ctx.prompt, hinweise, beispiele, _cas_block(ctx)))
        if ctx.protokoll is not None:
            ctx.protokoll.append({"segment": seg, "template": template_key, "roh": roh})
        out = br.nachbearbeiten(roh, nummerieren=not woertlich)  # v3.7.2: wörtlich = Layout der Ordi unverändert
        return out if woertlich else br.kurzsaetze_sichern(br.widersprueche_bereinigen(out, seg)[0], seg)[0]   # v3.15.5, v3.16.6
    template_key = wahl.vorlage if wahl is not None else detect.detect_template(seg, ctx.templates)
    template_data = ctx.templates.get(template_key) or ctx.templates["allgemein"]  # templates.json enthält „allgemein“
    bds = cv.beidseits(wahl)   # v3.15.4 (Peter 15.10.): CAS-Leistung beidseits → Befund IMMER beidseitig
    if ist_normalbefund(seg, template_key, ctx.display_names):
        ctx.log(f"[BYPASS] Normalbefund erkannt: {protokoll.diktat(seg)}. Generiere direkt aus Template '{template_key}'.")
        # v3.15.4: Seite aus CAS nur für paarige Regionen (Wirbelsäule/Becken/Thorax/Schädel nie „beidseits“)
        seite = (wahl.leistung.seite if (wahl is not None and wahl.leistung is not None
                                         and wahl.leistung.regionen & cv.PAARIG) else None)
        roh = bypass_befund(seg, template_data, seite, erzwingen=bds)
    else:
        beispiele = ctx.beispiele(seg) if ctx.beispiele else ""
        cas_block = _cas_block(ctx) + ("\n" + cv.beidseits_block(wahl) if bds else "")
        # v3.15.5 (Peter 15.10.): diktierte umschriebene Befunde + die widersprechenden Normalsätze der Vorlage — an der
        # Stelle {examples} wie in der Web-App (pipeline.ts)
        wid_block = br.widerspruch_prompt(br.widerspruch_befunde(seg), template_data["body"])
        if wid_block:
            beispiele = wid_block + ("\n" + beispiele if beispiele else "")
        roh = ctx.llm(gen_prompt(seg, template_data, ctx.prompt, ctx.hinweise, beispiele, cas_block,
                                 _ibl_block(seg, template_key, ctx)))
    if ctx.protokoll is not None:
        ctx.protokoll.append({"segment": seg, "template": template_key, "roh": roh})
    # v3.2: '## Befund' sichern + Ergebnis deterministisch nummerieren (einzelner Normalbefund-Satz unnummeriert)
    out = br.nachbearbeiten(roh)
    # v3.15.5: übrig gebliebene widersprechende Normalsätze → „Im Übrigen …“, Befund/Ergebnis nennen den Befund
    out, aend = br.widersprueche_bereinigen(out, seg)
    if aend:
        ctx.log(f"[WIDERSPRUCH] {len(aend)} Korrektur(en) nach der KI: " + " · ".join(a[:50] for a in aend))
    # v3.16.6 (Peter 18.10.): diktierte Empfehlungs-/Einschränkungssätze, die der KI verloren gingen, wörtlich zurück
    out, kurz = br.kurzsaetze_sichern(out, seg)
    if kurz:
        ctx.log(f"[KURZSATZ] {len(kurz)} diktierte(r) Satz/Sätze ergänzt: " + " · ".join(k[:60] for k in kurz))
    if bds:
        ctx.log(f"[CAS] beidseits laut CAS ({wahl.leistung.kurz}): Überschrift „beidseits“")
        out = cv.report_beidseits(out)
    return out


def _cas_block(ctx):
    return cv.prompt_block(ctx.cas, ctx.templates) if ctx.cas else ""


def _ibl_block(seg, template_key, ctx):
    """v3.13.0: <ibl_messwerte> nur mit Bausteinen, deren Modul zur Region dieses Abschnitts passt."""
    if not ctx.ibl:
        return ""
    reg = cv.regionen(cv.vorlagen_text(template_key, ctx.templates) + " " + region_name(seg))
    return iblb.prompt_block(iblb.fuer_abschnitt(ctx.ibl.bausteine, reg),
                             (ctx.templates.get(template_key) or {}).get("body"))


def ibl_anwenden(erg, ctx):
    """v3.13.0 (Peter 13.10.): IB-Lab-Bausteine NACH der KI deterministisch einsetzen (Messwerte 1:1) — nur mit
    Bausteinen und vollständigem Befund; Hinweise stehen in erg.ibl.hinweise (nur Anzeige)."""
    if not ctx.ibl or erg.fehler or not erg.report:
        return erg
    erg.ibl = iblb.einsetzen(erg.report, ctx.ibl.bausteine, segmente=erg.segmente, diktat=erg.raw,
                            cas_leistungen=ctx.ibl.cas_leistungen, templates=ctx.templates)
    erg.report = erg.ibl.report
    ctx.log("[IBL] eingesetzt: " + (", ".join(f"{m} → {t}" for m, t in erg.ibl.zuordnung.items()) or "nichts")
            + f" · {len(erg.ibl.zeilen)} Zeile(n) · {len(erg.ibl.hinweise)} Hinweis(e)")
    return erg


def cas_wahlen(segmente, ctx):
    """v3.12.0 (Peter 13.10.): mit CAS-Leistungen Abschnitte ggf. weiter teilen (gemischte Diktate) und je Abschnitt
    die Vorlage wählen (CAS = Vorrang-Hinweis). → (segmente, wahlen, hinweise). Ordi-Bausteine bleiben, wie sie sind."""
    erkennen = lambda t: detect.detect_template(t, ctx.templates)  # noqa: E731
    segmente = cv.aufteilen(segmente, ctx.cas, ctx.templates, erkennen)
    bausteine = ORDI_BAUSTEINE if ctx.bausteine is None else ctx.bausteine
    wahlen = []
    for seg in segmente:
        ohne_rho = br.rho_erkennen(seg)[0]
        if bs.befund_baustein(ohne_rho, bausteine)[0]:
            wahlen.append(cv.Wahl("baustein", "baustein"))
        else:
            wahlen.append(cv.wahl(ohne_rho, ctx.cas, ctx.templates, erkennen))
    for i, w in enumerate(wahlen, 1):
        ctx.log(f"[CAS] Abschnitt {i}/{len(wahlen)}: Vorlage {w.vorlage} ({w.art}"
                + (f", Diktat allein: {w.erkannt}" if w.erkannt and w.erkannt != w.vorlage else "")
                + (f", CAS {w.leistung.kurz}" if w.leistung else "") + ")")
    return segmente, wahlen, cv.hinweise(segmente, wahlen, ctx.cas, ctx.templates)


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
    wahlen, cas_hinweise = [None] * len(segmente), []
    if ctx.cas:  # v3.12.0: nur mit CAS-Leistungen — ohne bleibt alles wie bisher
        segmente, wahlen, cas_hinweise = cas_wahlen(segmente, ctx)
        wahlen = [None if w.art == "baustein" else w for w in wahlen]
    vorlagen = [w.vorlage for w in wahlen if w is not None]
    if len(segmente) <= 1:
        return ibl_anwenden(Ergebnis(raw=raw, report=befund_fuer_segment(segmente[0] if segmente else raw, ctx,
                                                                         wahlen[0] if wahlen else None),
                                     segmente=segmente, cas_hinweise=cas_hinweise, vorlagen=vorlagen), ctx)
    ctx.log(f"[MULTI] {len(segmente)} Regionen")
    with ThreadPoolExecutor(max_workers=len(segmente)) as ex:
        futures = [ex.submit(befund_fuer_segment, seg, ctx, w) for seg, w in zip(segmente, wahlen)]
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
    return ibl_anwenden(Ergebnis(raw=raw, report=report, fehler=fehler, ausnahmen=ausnahmen, segmente=segmente,
                                 cas_hinweise=cas_hinweise, vorlagen=vorlagen), ctx)


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
