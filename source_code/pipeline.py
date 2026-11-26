"""Befund-Pipeline der EXE ohne Oberfläche (Umbau Schritte 5 + 15) — ohne Windows/Tk importierbar und testbar.

befund_aus_diktat(diktat, ctx): Fehlhör-Liste → Regionen-Trenner → je Region Normalbefund-Bypass ODER LLM
(Gen-Prompt aus radiology_prompt.txt + Vorlage) → Nachbearbeitung (## Befund sichern, Ergebnis nummerieren)
→ Regionen zusammenfügen. Die Oberfläche (RaKScribe.py) und die Test-/Messkette (prod_pipeline.exe_kette)
rufen DIESELBE Funktion; nur der LLM-Aufruf wird übergeben (ctx.llm).
Tests: tests/offline/test_pipeline_exe.py, tests/offline/test_regionen.py.
v3.13.0: mit IB-Lab-Bausteinen (ctx.ibl) danach ibl_anwenden() — Messwerte wörtlich, ohne KI (ibl_bausteine.py).
"""
import dataclasses
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import bausteine as bs
import befund_regeln as br
import befundfeld as bf
import cas_vorlagen as cv
import detect
import gemini
import ibl_bausteine as iblb
import llm_anbieter as la
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
    umbau: str = ""                               # 3.19.16 Restructure: <umbau>-Hinweis (befundfeld.umbau_block); "" = wie bisher
    umbau_weg: tuple = ()                         # 3.19.16 Restructure: vorher gestrichene Normalsätze (vor den Wächtern raus)


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
    ohne_ki: str = ""                            # ohne-gemini-n1: KI zweimal nicht verfügbar → Grund-Kategorie (report = Diktat)

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
        if woertlich:
            return out
        out = br.widersprueche_bereinigen(out, seg)[0]                                    # v3.15.5
        out = br.kurzsaetze_sichern(br.abschnitte_bereinigen(out, seg, ctx.templates)[0], seg)[0]   # v3.18.13, v3.16.6
        return _grundregeln(_kl_waechter(out, seg, template_key, ctx), seg, ctx)
    template_key = wahl.vorlage if wahl is not None else detect.detect_template(seg, ctx.templates)
    template_data = ctx.templates.get(template_key) or ctx.templates["allgemein"]  # templates.json enthält „allgemein“
    bds = cv.beidseits(wahl)   # v3.15.4 (Peter 15.10.): CAS-Leistung beidseits → Befund IMMER beidseitig
    normal = ist_normalbefund(seg, template_key, ctx.display_names) and not ctx.umbau   # Restructure: immer KI
    if normal:
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
        if ctx.umbau:   # 3.19.16 Restructure: Vorrang-Hinweis an derselben Stelle wie <widersprueche> (Web gleich)
            beispiele = ctx.umbau + ("\n" + beispiele if beispiele else "")
        roh = ctx.llm(gen_prompt(seg, template_data, ctx.prompt, ctx.hinweise, beispiele, cas_block,
                                 _ibl_block(seg, template_key, ctx)))
    if ctx.protokoll is not None:
        ctx.protokoll.append({"segment": seg, "template": template_key, "roh": roh})
    # v3.2: '## Befund' sichern + Ergebnis deterministisch nummerieren (einzelner Normalbefund-Satz unnummeriert)
    out = br.nachbearbeiten(roh)
    if ctx.umbau_weg:   # 3.19.16: gestrichene Normalsätze nicht wörtlich zurück (sonst machte der Wächter „Im Übrigen …“)
        out = bf.streichen(out, ctx.umbau_weg)
    out, koala = _koala_frueh(out, seg, template_key, ctx)   # 18.11.2026: KOALA-Kniebefund vor den Wächtern
    # v3.15.5: übrig gebliebene widersprechende Normalsätze → „Im Übrigen …“, Befund/Ergebnis nennen den Befund
    out, aend = br.widersprueche_bereinigen(out, seg)
    if aend:
        ctx.log(f"[WIDERSPRUCH] {len(aend)} Korrektur(en) nach der KI: " + " · ".join(a[:50] for a in aend))
    # v3.18.13 (Peter 14.11.2026, #314): Abschnitt nennt selbst einen Befund ↔ Normalsatz daneben, fremder Vorlagensatz weg
    # (nicht beim Bypass: der ist die Vorlage selbst; Web gleich)
    if not normal:
        out, abschn = br.abschnitte_bereinigen(out, seg, ctx.templates)
        if abschn:
            ctx.log(f"[ABSCHNITT] {len(abschn)} Korrektur(en): " + " · ".join(a[:50] for a in abschn))
    # v3.16.6 (Peter 18.10.): diktierte Empfehlungs-/Einschränkungssätze, die der KI verloren gingen, wörtlich zurück
    out, kurz = br.kurzsaetze_sichern(out, seg)
    if kurz:
        ctx.log(f"[KURZSATZ] {len(kurz)} diktierte(r) Satz/Sätze ergänzt: " + " · ".join(k[:60] for k in kurz))
    if bds:
        ctx.log(f"[CAS] beidseits laut CAS ({wahl.leistung.kurz}): Überschrift „beidseits“")
        out = cv.report_beidseits(out)
    elif wahl is not None and wahl.leistung is not None and wahl.leistung.seite in ("rechts", "links") \
            and wahl.leistung.regionen & cv.PAARIG:
        # kaiscribe-ursula-2011-text-n1 (Ursula 20.11.2026, Punkt 6, RH 120): Seite der CAS-Leistung in die Überschrift,
        # wenn die KI sie weggelassen hat (eine diktierte bzw. vorhandene Seite bleibt; fehlt sie auch im CAS → Prüfzeile)
        neu = cv.report_seite(out, wahl.leistung.seite)
        if neu != out:
            ctx.log(f"[CAS] Seite laut CAS ({wahl.leistung.kurz}) in die Überschrift")
            out = neu
    if not normal:   # v3.18.4: Bypass (Vorlage ohne KI) braucht keinen K&L-Wächter
        seite = wahl.leistung.seite if (wahl is not None and wahl.leistung is not None) else ""
        out = _kl_waechter(out, seg, template_key, ctx, seite, behalten=koala)
    if template_key == KOMBI_BECKEN_HUEFTE and wahl is not None and wahl.leistung is not None \
            and wahl.leistung.seite in ("rechts", "links"):   # RH 49: Seite der Hüfte laut CAS in die Überschrift
        out = re.sub(r"(?m)^## Beckenübersicht und Hüfte(?: in 2 Ebenen)?[ \t]*$",
                     f"## Beckenübersicht und Hüfte {wahl.leistung.seite}", out)
    if template_key == KOMBI_PROTHESE and ((wahl is not None and wahl.art == "kombi") or _KOMBI_SIGNAL.search(seg[:140])):
        # Punkt 59: Kombi mit Prothese → „Becken sowie Hüftgelenk in 2 Ebenen <Seite> nach Hüft-TEP“ (Seite aus dem Diktat
        # am TEP-Wort, sonst CAS; nie geraten)
        m = _PROTHESE_DIKTAT.search(seg)
        seite = br.wid_seite(seg[max(0, m.start() - 50):m.end() + 30]) if m else ""
        seite = seite or (wahl.leistung.seite if wahl is not None and wahl.leistung is not None
                          and wahl.leistung.seite in ("rechts", "links") else "")
        out = re.sub(r"(?m)^## Beckenübersicht mit einseitiger Hüftprothese[^\n]*$",
                     "## Becken sowie Hüftgelenk in 2 Ebenen" + (f" {seite}" if seite else "") + " nach Hüft-TEP", out, count=1)
    return _grundregeln(out, seg, ctx)


def _grundregeln(out, diktat, ctx):
    """kaiscribe-georg-2011-n1 (Georg 20.11.2026): Befund nie mit „Im Übrigen/Ansonsten“, widersprechende Normalsätze zu
    diktierter/KI-Pathologie weg, KI-Hinweise nie im Ergebnis, SI-Gelenksarthrose, Wirbelsäule ohne K&L (Sync: pipeline.ts)."""
    out, aend = br.grundregeln(out, diktat, ctx.templates)
    if aend:
        ctx.log(f"[GRUNDREGEL] {len(aend)} Korrektur(en): " + " · ".join(a[:50] for a in aend))
    return out


def _koala_frueh(out, seg, template_key, ctx):
    """18.11.2026 (Georg, kaiscribe-kl-tabelle-zurueck-n1): den KOALA-Kniebefund schon VOR den Wächtern einsetzen – sie
    würden sonst die Vorlagensätze, die KOALA ersetzt („Der Gelenkspalt ist allseits normal weit.“), mit „Im Übrigen …“
    angleichen. ibl_anwenden setzt danach nichts doppelt ein. → (report, eingesetzte Zeilen)."""
    if not ctx.ibl:
        return out, []
    reg = cv.regionen(cv.vorlagen_text(template_key, ctx.templates) + " " + region_name(seg))
    ko = [b for b in iblb.fuer_abschnitt(ctx.ibl.bausteine, reg) if b.modul == "koala"]
    if not ko:
        return out, []
    e = iblb.einsetzen(out, ko, diktat=seg, cas_leistungen=ctx.ibl.cas_leistungen, templates=ctx.templates)
    return e.report, [z for zs in e.eingesetzt.values() for z in zs]


def _kl_waechter(out, seg, template_key, ctx, seite="", behalten=()):
    """v3.18.4 (Peter 12.11.2026, RH 38): K&L-Grad nur aus Diktat oder IB-Lab-Baustein (passende Region + Seite) —
    nicht gedeckte Grade der KI weg bzw. auf den einzigen erlaubten Grad. Sync: pipeline.ts (ohne IB Lab)."""
    erlaubt = []
    if ctx.ibl:
        reg = cv.regionen(cv.vorlagen_text(template_key, ctx.templates) + " " + region_name(seg))
        erlaubt = iblb.kl_grade(iblb.fuer_abschnitt(ctx.ibl.bausteine, reg), seite or br.diktierte_seite(seg))
    out, aend = br.kl_bereinigen(out, seg, erlaubt)
    if aend:
        ctx.log("[K&L] " + " · ".join(aend))
    # v3.18.5 (Nachtrag RH 99): ohne diktierte Arthrose keine Arthrose-Diagnose im Ergebnis (HIPPO-Messwerte ≠ Arthrose)
    out, aend = br.arthrose_bereinigen(out, seg, behalten=behalten)   # behalten: KOALA-Punkte (IB Lab, nicht die KI)
    if aend:
        ctx.log("[ARTHROSE] " + " · ".join(a[:60] for a in aend))
    return out


def _cas_block(ctx):
    return cv.prompt_block(ctx.cas, ctx.templates) if ctx.cas else ""


def _ibl_block(seg, template_key, ctx):
    """v3.13.0: <ibl_messwerte> nur mit Bausteinen, deren Modul zur Region dieses Abschnitts passt."""
    if not ctx.ibl:
        return ""
    reg = cv.regionen(cv.vorlagen_text(template_key, ctx.templates) + " " + region_name(seg))
    return iblb.prompt_block(iblb.fuer_abschnitt(ctx.ibl.bausteine, reg),
                             (ctx.templates.get(template_key) or {}).get("body"), seg)


def ibl_anwenden(erg, ctx):
    """v3.13.0 (Peter 13.10.): IB-Lab-Bausteine NACH der KI deterministisch einsetzen (Messwerte 1:1) — nur mit
    Bausteinen und vollständigem Befund; Hinweise stehen in erg.ibl.hinweise (nur Anzeige)."""
    if not ctx.ibl or erg.fehler or not erg.report:
        return erg
    erg.ibl = iblb.einsetzen(erg.report, ctx.ibl.bausteine, segmente=erg.segmente, diktat=erg.raw,
                            cas_leistungen=ctx.ibl.cas_leistungen, templates=ctx.templates)
    # kaiscribe-georg-2011-n1: IB-Lab-Texte (HIPPO-Beckenschiefstand, SQUIRREL-Cobb) zählen wie diktierte Befunde
    # Punkt 9: „Anmerkung: …“-Block; Punkt 35: kein „Varisierung“ bei regelrechter LAMA-Achse
    erg.report = iblb.anmerkung_absetzen(iblb.lama_achsworte(_grundregeln(erg.ibl.report, "", ctx)))
    ctx.log("[IBL] eingesetzt: " + (", ".join(f"{m} → {t}" for m, t in erg.ibl.zuordnung.items()) or "nichts")
            + f" · {len(erg.ibl.zeilen)} Zeile(n) · {len(erg.ibl.hinweise)} Hinweis(e)")
    return erg


def cas_wahlen(segmente, ctx):
    """v3.12.0 (Peter 13.10.): mit CAS-Leistungen Abschnitte ggf. weiter teilen (gemischte Diktate) und je Abschnitt
    die Vorlage wählen (CAS = Vorrang-Hinweis). → (segmente, wahlen, hinweise). Ordi-Bausteine bleiben, wie sie sind."""
    erkennen = lambda t: detect.detect_template(t, ctx.templates)  # noqa: E731
    segmente = cv.aufteilen(segmente, ctx.cas, ctx.templates, erkennen)
    bausteine = ORDI_BAUSTEINE if ctx.bausteine is None else ctx.bausteine
    # kaiscribe-mehrfach-seitenlos-n1 (Georg 19.11.2026): mehrere CAS-Untersuchungen → Sätze nach Inhalt zuordnen
    # (Coxarthrose/Trochanter → Becken, Osteochondrose L5/S1 → LWS), Prüfzeilen bei unklaren/fremden Sätzen.
    # Ordi-Bausteine („Baustein Mammo 1“) bleiben unberührt.
    if any(bs.befund_baustein(br.rho_erkennen(s)[0], bausteine)[0] for s in segmente):
        leistungen, inhalt_hinweise = [None] * len(segmente), []
    else:
        segmente, leistungen, inhalt_hinweise = cv.inhalt_zuordnen(segmente, ctx.cas, ctx.templates, erkennen)
    wahlen = []
    for seg, ziel in zip(segmente, leistungen):
        ohne_rho = br.rho_erkennen(seg)[0]
        if bs.befund_baustein(ohne_rho, bausteine)[0]:
            wahlen.append(cv.Wahl("baustein", "baustein"))
            continue
        w = cv.wahl(ohne_rho, ctx.cas, ctx.templates, erkennen)
        # nach Inhalt gebildeter Abschnitt: Vorlage der CAS-Leistung – die des Diktats nur, wenn sein Satzanfang sie nennt
        # („Hüftgelenk links: …“), nicht wenn nur ein Befundwort (Coxarthrose) auf die Hüfte zeigt
        ss = cv.saetze(ohne_rho)
        if ziel is not None and (w.leistung is None or (w.leistung.vorlage or w.leistung.kurz) != (ziel.vorlage or ziel.kurz)
                                 or (w.vorlage != ziel.vorlage and not (ss and erkennen(cv.kopf(ss[0][1])) == w.vorlage
                                                                        and not br.has_pathology(cv.kopf(ss[0][1]))))):
            w = cv.Wahl(ziel.vorlage, "inhalt", ziel, w.erkannt)
        wahlen.append(w)
    segmente, wahlen, inhalt_hinweise = _becken_huefte_kombi(segmente, wahlen, inhalt_hinweise, ctx)
    hinweise = cv.hinweise(segmente, wahlen, ctx.cas, ctx.templates) + inhalt_hinweise + _strahl_hinweise(segmente, wahlen) \
        + _seite_hinweise(segmente, wahlen)
    if inhalt_hinweise:   # Protokoll ohne Diktatinhalt (Umbau Schritt 23): nur die Zahl
        ctx.log(f"[CAS] {len(inhalt_hinweise)} Prüfzeile(n) zur Satz-Zuordnung")
    # kaiscribe-funktion-n1 (RH 97): Funktionsaufnahmen laut CAS → eigener Abschnitt nach HWS/LWS in 2 Ebenen
    segmente, wahlen, f_log = cv.funktion_ergaenzen(segmente, wahlen, ctx.cas, ctx.templates)
    # kaiscribe-nicht-diktiert-streichen-n1 (Georg 26.11.2026, ersetzt die Regel vom 20.11.): nicht diktierte
    # CAS-Untersuchung → gestrichen + EINE rote Prüfzeile; nur ein reiner IB-Lab-Teil (Ganzbein/LAMA) behält seinen Befund
    segmente, wahlen, hinweise, n_log = cv.nicht_diktiert_ergaenzen(segmente, wahlen, hinweise, ctx.cas, ctx.templates,
                                                                    ctx.ibl.bausteine if ctx.ibl else None)
    # kaiscribe-ursula-2011-text-n1 (Punkt 6): auch ein nicht diktierter Teil ohne Seite (Ganzbein) → rote Prüfzeile
    hinweise += [h for h in _seite_hinweise(segmente, wahlen) if h not in hinweise]
    for z in f_log + n_log:
        ctx.log("[CAS] " + z)
    for i, w in enumerate(wahlen, 1):
        ctx.log(f"[CAS] Abschnitt {i}/{len(wahlen)}: Vorlage {w.vorlage} ({w.art}"
                + (f", Diktat allein: {w.erkannt}" if w.erkannt and w.erkannt != w.vorlage else "")
                + (f", CAS {w.leistung.kurz}" if w.leistung else "") + ")")
    return segmente, wahlen, hinweise


# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkt 22, RH 93): CAS-Kürzel nur „Zehe“/„Finger“ ohne Nummer – fehlt die
# Nummer auch im Diktat, wird sie nie geraten: rote Prüfzeile
_STRAHL = re.compile(r"(?<![a-zäöüß])(?:dig(?:itus)?\.?\s*)?(?:i{1,3}|iv|v|[1-5])(?![a-zäöüß0-9])|daumen|großzeh|grosszeh|"
                     r"kleinzeh|zeigefinger|mittelfinger|ringfinger|kleinfinger|hallux|digitus", re.I)
STRAHL_FEHLT = "{name}: Nummer (I–V) nicht diktiert – bitte im Befund ergänzen (wird nicht geraten)"


SEITE_FEHLT = "{name}: Seite weder in der CAS-Leistung noch im Diktat – bitte prüfen (wird nicht geraten)"


def _seite_hinweise(segmente, wahlen):
    """kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkt 55, RH 60): seitenlose CAS-Leistung einer paarigen Region
    (z. B. „Hüft-OP“) und keine Seite im Diktat → rote Prüfzeile (Bildkopf/Ausschluss nur mit Beleg, sonst nie raten)."""
    out = []
    for seg, w in zip(segmente, wahlen):
        l = w.leistung if w is not None else None
        if l is None or l.seite or not (l.regionen & cv.PAARIG) or br.diktierte_seite(seg) or w.art == "kombi":
            continue
        h = SEITE_FEHLT.format(name=l.label)
        if h not in out:
            out.append(h)
    return out


def _strahl_hinweise(segmente, wahlen):
    out = []
    for seg, w in zip(segmente, wahlen):
        if w.vorlage in ("zehe_in_2_ebenen", "finger_in_2_ebenen") and not _STRAHL.search(br.rho_erkennen(seg)[0]):
            out.append(STRAHL_FEHLT.format(name="Zehe" if w.vorlage.startswith("zehe") else "Finger"))
    return out


KOMBI_BECKEN_HUEFTE = "beckenübersicht_und_hüfte"
KOMBI_PROTHESE = "beckenübersicht_mit_einseitiger_hüftprothese"
_BECKEN_FAMILIE = {"beckenübersicht_stehend", "hüftgelenk_in_2_ebenen", KOMBI_BECKEN_HUEFTE, "hüftprothese", KOMBI_PROTHESE,
                   "beckenübersicht_mit_beidseitiger_hüftprothese"}
# kaiscribe-schulter-ergebnis-n1 (Georg FINAL 23.11.2026, Punkt 59, RH 30): Kombibefund per DIKTAT – nennt der Arzt die
# Untersuchungen am Anfang in EINEM Titel verbunden („Beckenübersicht und Hüfte rechts“, „Becken und Hüftgelenk … nach
# Hüft-TEP“), wird es EIN Befund (Kombi-Vorlage, mit Prothese die Prothesen-Kombi), beide CAS-Leistungen gedeckt. Ohne das
# Signal bleiben getrennte Teile (nur CAS bü + Hüft-OP ist KEIN Signal). Weitere Kombis (HWS und BWS, Knie und Ganzbein)
# vorbereitet in KOMBI_LISTE, aktiv nur Becken + Hüfte.
KOMBI_LISTE = {"becken_huefte": {"aktiv": True,
                                 "signal": r"becken(?:übersicht)?(?:\s+[a-zäöüß]+){0,2}\s+(?:und|sowie|mit)\s+(?:der\s+|dem\s+|den\s+)?hüft"},
               "hws_bws": {"aktiv": False, "signal": r"(?:hws|halswirbelsäule)\s+(?:und|sowie)\s+(?:bws|brustwirbelsäule)"},
               "knie_ganzbein": {"aktiv": False, "signal": r"knie\w*\s+(?:und|sowie)\s+ganzbein"}}
_KOMBI_SIGNAL = re.compile(KOMBI_LISTE["becken_huefte"]["signal"], re.I)
_PROTHESE_DIKTAT = re.compile(r"(?<![a-zäöüß])tep(?![a-zäöüß])|prothes|endoprothes", re.I)


def _becken_huefte_kombi(segmente, wahlen, inhalt_hinweise, ctx):
    """kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkt 26, RH 49: „Beckenübersicht und Hüftgelenk rechts“ → zwei Befunde,
    Titel/Seite falsch): wählt ein Abschnitt die Kombi-Vorlage Becken + Hüfte (v3.18.7) und gehören alle Abschnitte zu
    Becken/Hüfte, bleibt es EIN Befund mit der Kombi-Vorlage; die Seite kommt von der Hüft-Leistung laut CAS."""
    gesamt = " ".join(s.strip() for s in segmente)
    signal = KOMBI_LISTE["becken_huefte"]["aktiv"] and _KOMBI_SIGNAL.search(gesamt[:140]) is not None
    if not all(w.vorlage in _BECKEN_FAMILIE for w in wahlen) or not (
            (len(segmente) >= 2 and signal) or (len(segmente) < 2 and any(w.vorlage == KOMBI_BECKEN_HUEFTE for w in wahlen))):
        return segmente, wahlen, inhalt_hinweise   # Punkt 59: mehrere Abschnitte nur mit Kombi-Signal im Diktat
    if len(segmente) < 2:            # ein Abschnitt mit der Kombi-Vorlage deckt beide CAS-Leistungen
        return segmente, wahlen, [h for h in inhalt_hinweise if "nicht eindeutig zuzuordnen" not in h]
    huefte = next((w.leistung for w in wahlen if w.leistung is not None and w.leistung.seite), None) or \
        next((l for l in ctx.cas.alle if l.vorlage == "hüftgelenk_in_2_ebenen"), None)
    vorlage = KOMBI_PROTHESE if (signal and _PROTHESE_DIKTAT.search(gesamt) and KOMBI_PROTHESE in ctx.templates
                                 and not re.search(r"beidseit\w*\s+(?:hüft-?)?(?:tep|totalendo|prothes)", gesamt, re.I)) \
        else KOMBI_BECKEN_HUEFTE
    ctx.log(f"[CAS] Becken + Hüfte: {len(segmente)} Abschnitte → ein Befund mit der Kombi-Vorlage {vorlage}"
            + (" (Diktat nennt die Kombi)" if signal else ""))
    return [gesamt], [cv.Wahl(vorlage, "kombi", huefte, vorlage)], \
        [h for h in inhalt_hinweise if "nicht eindeutig zuzuordnen" not in h]


def _pruefen(erg, ctx):
    """kaiscribe-schulter-ergebnis-n1 (Punkte 60/60b): rote Prüfzeilen statt stiller Normalvorlage – leeres Ergebnis,
    „Regelrechte Darstellung“ trotz Pathologie im Befund. Nur Anzeige.
    kaiscribe-dexa-doppelt-rh60-n1: vorher Sätze mit unbefülltem Platzhalter ([Wert_LWS] …) raus + rote Prüfzeile."""
    _platzhalter(erg, ctx)
    if erg.report and not erg.fehler:
        neu = [h for h in br.pruefzeilen_2311(erg.report, erg.raw, ctx.templates) if h not in (erg.cas_hinweise or [])]
        if neu:
            erg.cas_hinweise = list(erg.cas_hinweise or []) + neu
    return erg


def _platzhalter(erg, ctx):
    """kaiscribe-dexa-doppelt-rh60-n1 (Ursula 23.11.2026, RH 60): nie ein unbefüllter Platzhalter im Brief."""
    if erg.report:
        erg.report, zeilen = br.platzhalter_entfernen(erg.report)
        if zeilen:
            ctx.log(f"[PLATZHALTER] {len(zeilen)} unbefüllte(r) Platzhalter → „…“, rote Prüfzeile")
            erg.cas_hinweise = list(erg.cas_hinweise or []) + [h for h in zeilen if h not in (erg.cas_hinweise or [])]
    return erg


def _rho_dexa(ctx):
    """kaiscribe-rho-regel-becken-n1: DEXA-Auskunft für die Rho-Regel. KaiScribe kennt die DEXA der letzten 2 Jahre nicht –
    eine DEXA-Leistung im selben CAS-Auftrag sperrt („gesperrt“), sonst gilt das diktierte „Rho“ als Arzt-Auskunft („frei“)."""
    cas = getattr(ctx, "cas", None)
    # kaiscribe-dexa-doppelt-rh60-n1: DEXA-Leistungen stehen nicht mehr in cas.alle (nie eine Vorlage), sondern in cas.dexa
    return "gesperrt" if cas is not None and (getattr(cas, "dexa", None)
                                              or any("dexa" in (l.regionen or set()) for l in cas.alle)) else "frei"


def _osteopen(erg, ctx, diktat=None):
    """kaiscribe-rho-osteopen-n1 (Georg 22.11.2026): Rho-Schlussbefund (Score ≥ 7) im Befund → Mineralisations-
    Normalsatz aller Untersuchungen durch „Osteopenischer Knochenaspekt.“ ersetzen (ganz am Schluss, nach den Wächtern
    und IB Lab). Diktat nennt die Knochendichte selbst → nichts. Restructure: „Diktat“ = Peters eigene Sätze (vor).
    Sync: pipeline.ts befundAusDiktat/befundUmbauen.
    kaiscribe-rho-regel-becken-n1 (Kanban #533): vorher die EINE Rho-Regel (Score ≥ 7, LWS, keine DEXA laut CAS) – nicht
    erfüllt → Rho-Teil raus, Hinweis in der Anzeige."""
    if erg.report:
        erg.report, grund = br.rho_regel_anwenden(erg.report, _rho_dexa(ctx))
        if grund:
            ctx.log(f"[RHO] kein Rho-Text – {grund} (Rho-Regel)")
            hw = f"Rho: kein Rho-Text – {grund} (Rho-Regel: Score ≥ 7, LWS, keine DEXA in den letzten 2 Jahren)"
            if hw not in (erg.cas_hinweise or []):
                erg.cas_hinweise = list(erg.cas_hinweise or []) + [hw]
        erg.report, teile = br.osteopen_ersetzen(erg.report, erg.raw if diktat is None else diktat)
        if teile:
            ctx.log(f"[RHO] Osteopenischer Knochenaspekt statt Mineralisations-Normalsatz in {len(teile)} Untersuchung(en)")
    return erg


def _schluss(erg, ctx):
    """kaiscribe-ursula-2011-text-n1 (Ursula 20.11.2026, Punkte 5/8): ganz am Ende – keine Leerzeile nach „Ergebnis“, keine
    Überschrift ohne Inhalt, kein loses Regions-Wort (nach IB Lab: reine IB-Lab-Teile haben dann ihren Text).
    Nicht bei gescheiterten Regionen (Hinweistext bleibt). Sync: pipeline.ts befundAusDiktat."""
    if erg.report and not erg.fehler:
        erg.report, aend = br.befund_schluss(erg.report)
        if aend:
            ctx.log("[SCHLUSS] " + " · ".join(a[:50] for a in aend))
    return erg


def _ohne_ki(raw, e, segmente, cas_hinweise, vorlagen, ctx):
    """kaiscribe-ohne-gemini-n1 (Peter 23.11.2026, kein Gemini mehr): Befund-KI auch im zweiten Versuch nicht verfügbar →
    das (fehlhör-korrigierte) Diktat UNVERÄNDERT als Befundtext plus rote Prüfzeile (OHNE_KI_ZEILE). Nie ein Befund
    verloren, nie fremder Text; vollstaendig ist False → die EXE fügt nichts automatisch ins Zielprogramm ein."""
    ctx.log(f"[KI] Befund ohne KI: {e.grund} → Diktat unformatiert im Befundfeld (rote Prüfzeile)")
    return Ergebnis(raw=raw, report=raw, segmente=segmente, vorlagen=vorlagen, ohne_ki=e.grund,
                    cas_hinweise=[la.OHNE_KI_ZEILE] + [h for h in (cas_hinweise or []) if h != la.OHNE_KI_ZEILE])


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
        try:
            teil = befund_fuer_segment(segmente[0] if segmente else raw, ctx, wahlen[0] if wahlen else None)
        except la.OhneKi as e:
            return _ohne_ki(raw, e, segmente, cas_hinweise, vorlagen, ctx)
        return _pruefen(_schluss(_osteopen(ibl_anwenden(Ergebnis(raw=raw, report=br.teile_zusammenlegen(teil, raw)[0],
            segmente=segmente, cas_hinweise=cas_hinweise, vorlagen=vorlagen), ctx), ctx), ctx), ctx)
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
    ohne = next((e for e in ausnahmen if isinstance(e, la.OhneKi)), None)
    if ohne is not None:   # ohne-gemini-n1: eine Region ohne KI → ganzes Diktat unformatiert (nichts geht verloren)
        return _ohne_ki(raw, ohne, segmente, cas_hinweise, vorlagen, ctx)
    report, fehler = assemble_regions(segmente, teile, gemini.report_complete)
    if not fehler:   # kaiscribe-schulter-ergebnis-n1 (Punkte 58a/64): nie doppelte Teile, kein nicht diktierter Unterarm
        report, zus = br.teile_zusammenlegen(report, raw)
        if zus:
            ctx.log("[MULTI] " + " · ".join(zus))
    report = br.rho_ans_ende(report)   # kaiscribe-georg-2011-n1 (Georg 20.11., Punkt 19): Rho-Befund immer am Schluss
    return _pruefen(_schluss(_osteopen(ibl_anwenden(Ergebnis(raw=raw, report=report, fehler=fehler, ausnahmen=ausnahmen,
                                                             segmente=segmente, cas_hinweise=cas_hinweise,
                                                             vorlagen=vorlagen), ctx), ctx), ctx), ctx)


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
    # kaiscribe-schulter-ergebnis-n1 (Punkte 49a/52): Überschriften auch im Nur-Text-Weg als „## …“ (fett)
    return Ergebnis(raw=raw, report=br.nur_text_ueberschriften(raw), segmente=[raw])


def befund_umbauen(aktuell, stand, ctx):
    """3.19.16 Restructure (Peter 20.11.2026): den AKTUELLEN Text im Befundfeld (mit Peters diktierten oder getippten
    Änderungen) über die normale Befundkette neu aufbauen. Peters Änderungen = Sätze, die im letzten KaiScribe-Stand
    (stand) nicht standen, haben Vorrang; widersprechende Normalsätze fallen vorher heraus (befundfeld.umbau_segment),
    das Ergebnis wird angepasst, die Überschriften bleiben. Abschnitte ohne Änderung bleiben bei mehreren Untersuchungen
    Zeichen für Zeichen stehen. Danach: jede Vorrang-Angabe muss inhaltlich im Befund stehen (sonst wörtlich
    nachgetragen + Prüfzeile), jede eigene (nicht aus einer Vorlage stammende) Angabe ebenso (sonst Prüfzeile).
    → Ergebnis (report, cas_hinweise = Prüfzeilen, leer = nichts umzubauen). Sync: pipeline.ts befundUmbauen."""
    text = (aktuell or "").strip()
    if not text:
        return Ergebnis(leer=True)
    ohne_stand = not (stand or "").strip()
    vor = [] if ohne_stand else bf.vorrang(stand, text)
    if not vor and not ohne_stand:
        return Ergebnis(raw=text, report=text, leer=True)
    bloecke = [b for b in bf.bloecke(text) if b["befund"] or b["ergebnis"]] or bf.bloecke(text)
    teile, segmente, titel = [], [], []
    for b in bloecke:
        bt = bf.block_text(text, b)
        eigene = [s for s in vor if br.vorlage_normalisieren(s) in br.vorlage_normalisieren(bt)]
        if len(bloecke) > 1 and not eigene and not ohne_stand:
            teile.append(bt)          # unverändert (KL-/Kinder-/Mehrfachbefund der anderen Untersuchung bleibt)
            titel.append(b["titel"])
            continue
        seg, gestrichen = bf.umbau_segment(bt, eigene)
        if gestrichen:
            ctx.log(f"[UMBAU] {len(gestrichen)} widersprechende(r) Normalsatz/Normalsätze vorher entfernt")
        uctx = dataclasses.replace(ctx, umbau=bf.umbau_block(eigene, gestrichen, ohne_stand), umbau_weg=tuple(gestrichen))
        wahl = None
        if ctx.cas:
            erkennen = lambda t: detect.detect_template(t, ctx.templates)  # noqa: E731
            wahl = cv.wahl(br.rho_erkennen(seg)[0], ctx.cas, ctx.templates, erkennen)
        teile.append(bf.streichen(befund_fuer_segment(seg, uctx, wahl), gestrichen))
        segmente.append(seg)
        titel.append(b["titel"])
    report = br.befunde_zusammenfuegen(teile)
    if len(teile) == len(titel):
        report = bf.titel_uebernehmen(report, titel)
    erg = _osteopen(ibl_anwenden(Ergebnis(raw=text, report=report, segmente=segmente), ctx), ctx, " ".join(vor))
    hinweise = []
    fehlt = bf.fehlende(vor, erg.report)
    for s in fehlt:               # Peters Angabe ging verloren → wörtlich zurück, rot zum Prüfen
        erg.report = bf.ergaenzen(erg.report, s)[0]
        hinweise.append(bf.pruefzeile(s))
    hinweise += [bf.pruefzeile(s, ergebnis=True) for s in bf.ergebnis_fehlt(vor, erg.report)]
    vorlagen = br._vorlagen_saetze(ctx.templates)[0]
    eigene_alt = [s for s, art in bf.saetze(text, mit_ergebnis=False)
                  if br.vorlage_normalisieren(s) not in vorlagen and s not in vor]
    hinweise += [bf.pruefzeile(s) for s in bf.fehlende(eigene_alt, erg.report) if not bf.verneint_vorrang(s, vor)]
    erg.cas_hinweise = hinweise
    _platzhalter(erg, ctx)       # kaiscribe-dexa-doppelt-rh60-n1: nie ein unbefüllter Platzhalter
    ctx.log(f"[UMBAU]{len(vor)} Änderung(en) mit Vorrang, {len(teile)} Abschnitt(e), {len(fehlt)} nachgetragen, "
            f"{len(hinweise)} Prüfzeile(n)")
    return erg
