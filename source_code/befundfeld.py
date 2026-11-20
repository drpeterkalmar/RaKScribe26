"""Rechtes Befundfeld nie still überschreiben (kaiscribe-befundfeld-sicher-n1, Peter 20.11.2026).

Peter: „Wenn schon was rechts steht und ich dazudiktieren möchte, wird manchmal alles gelöscht oder der Titel ändert
sich, irgendwie random.“ Ursache: ohne Fokus im Befundfeld (kurzer Klick in Plaza/CAS genügte) baute jedes Diktat einen
ganz neuen Befund. Ab 3.19.16:
- modus(): steht rechts schon Text → das Diktat ist eine ERGÄNZUNG (mit Cursor/Markierung an der Stelle, sonst
  ergaenzen() = ans Ende des Befundteils des passenden Abschnitts, vor „## Ergebnis“). Titel und Text bleiben.
  Neuer Befund nur bei leerem Feld (nach EOL / Clear all / F1 Neu); das unberührte IB-Lab-Gerüst wird zum Befund
  ausgebaut (die IB-Lab-Texte setzt pipeline.ibl_anwenden wie bisher wörtlich in den passenden Befund).
- Restructure: vorrang() = Sätze, die Peter seit dem letzten KaiScribe-Stand ergänzt/geändert hat; umbau_segment()
  macht aus einem Abschnitt den Eingangstext für die normale Befundkette (widersprechende Normalsätze der Vorlage
  vorher heraus, Regel-Katalog widersprueche in vorlagen_vorrang.json), umbau_block() den Vorrang-Hinweis für den
  Prompt, titel_uebernehmen() hält die Überschriften, fehlende() prüft danach, dass nichts verloren ging.
Reine Funktionen auf Text — Sync: web_app/src/befundfeld.ts, gemeinsame Fälle tests/offline/snapshots/befundfeld_faelle.txt.
"""
import re

import befund_regeln as br

_UEBERSCHRIFT = re.compile(r"^\s*##\s+(.*?)\s*$")
_ABSCHNITT = {"befund": "befund", "ergebnis": "ergebnis"}
_ERGEBNIS_ZEILE = re.compile(r"^\s*(?:\*\*)?\s*ergebnis\b", re.I)
_SATZENDE = ".!?:;)"
_STOPP = {"und", "oder", "der", "die", "das", "des", "dem", "den", "ein", "eine", "einer", "eines", "einem", "einen",
          "mit", "ohne", "bei", "von", "vom", "zum", "zur", "ist", "sind", "wird", "werden", "sich", "auch", "nicht",
          "kein", "keine", "keiner", "keinen", "noch", "als", "auf", "aus", "fuer", "nach", "ueber", "unter", "sowie",
          "im", "in", "am", "an", "zu", "es", "eher", "etwas", "bzw", "ca", "re", "li", "zusaetzlich", "ausserdem"}

NEU, ERGAENZUNG, CURSOR, GERUEST, MASKE = "neu", "ergaenzung", "cursor", "geruest", "maske"
STATUS = {NEU: "Neuer Befund", ERGAENZUNG: "Ergänzung", GERUEST: "Neuer Befund (IB-Lab-Gerüst)"}


def modus(rechts, geruest=False, cursor=False, maske=False, abgeschlossen=False):
    """Was macht das nächste Diktat mit dem rechten Feld? maske = Mammo-Maske (eigener Weg, unverändert),
    geruest = unberührtes IB-Lab-Gerüst, cursor = Fokus/Markierung im Befundfeld beim Record, abgeschlossen = der
    Befund rechts ging schon automatisch hinaus (F10 ohne CAS: kopiert + eingefügt) — zählt wie nach EOL."""
    if maske:
        return MASKE
    if geruest:
        return GERUEST
    if not (rechts or "").strip() or (abgeschlossen and not cursor):
        return NEU
    return CURSOR if cursor else ERGAENZUNG


def _art(zeile):
    m = _UEBERSCHRIFT.match(zeile)
    if not m:
        return None
    return _ABSCHNITT.get(m.group(1).strip().rstrip(":").strip().lower(), "titel")


def bloecke(report):
    """Befundtext → Abschnitte je Untersuchung: [{titel, titel_zeile, start, ende, befund, ergebnis}] mit Zeilen-
    nummern (ende exklusiv; befund/ergebnis = (erste Inhaltszeile, Ende) oder None). Text vor der ersten Überschrift
    ist ein Abschnitt ohne Titel; ein zweites „## Befund“ ohne neuen Titel beginnt einen neuen Abschnitt."""
    zeilen = (report or "").split("\n")
    out, st = [], {"akt": None, "sektion": None}

    def schliessen(i):
        akt, sek = st["akt"], st["sektion"]
        if akt is not None:
            akt["ende"] = i
            if sek:
                akt[sek] = (akt[sek][0], i)
        st["sektion"] = None

    def oeffnen(i, titel=None, tz=None):
        st["akt"] = {"titel": titel, "titel_zeile": tz, "start": i, "ende": len(zeilen), "befund": None, "ergebnis": None}
        out.append(st["akt"])

    for i, z in enumerate(zeilen):
        art = _art(z)
        if art == "titel":
            schliessen(i)
            oeffnen(i, _UEBERSCHRIFT.match(z).group(1).strip(), i)
        elif art:
            if st["akt"] is None or st["akt"][art] is not None:
                schliessen(i)
                oeffnen(i)
            elif st["sektion"]:
                akt = st["akt"]
                akt[st["sektion"]] = (akt[st["sektion"]][0], i)
            st["akt"][art] = (i + 1, len(zeilen))
            st["sektion"] = art
        elif st["akt"] is None and z.strip():
            oeffnen(i)
    schliessen(len(zeilen))
    return out


def _regionen(text):
    t = (text or "").lower()
    return {k for k, pat in br.REGIONEN + br.REGIONEN_OHNE_SEITE if re.search(r"(?<!\w)(?:" + pat + r")", t)}


def _zeilen_offset(zeilen, i):
    """Zeichen-Offset des Zeilenanfangs i (i == len → Textende)."""
    return sum(len(z) + 1 for z in zeilen[:i])


def _letzte_inhaltszeile(zeilen, a, e):
    for i in range(min(e, len(zeilen)) - 1, a - 1, -1):
        if zeilen[i].strip():
            return i
    return None


def ergaenzung_stelle(report, neu):
    """Wo kommt eine Ergänzung OHNE Cursor hin? → (offset, art): art "zeile" = als neue Zeile hinter offset (Ende
    einer Zeile), "anhaengen" = an den Fließtext anhängen. Befund mit Abschnitten: ans Ende des Befundteils des
    passenden Abschnitts (Region/Seite der Ergänzung, sonst der letzte), vor „## Ergebnis“. Text ohne Abschnitte (Nur
    Text): vor einer Zeile „Ergebnis …“, sonst ans Ende."""
    text = report or ""
    zeilen = text.split("\n")
    bl = [b for b in bloecke(text) if b["befund"] or b["ergebnis"]]
    if not bl:
        ez = next((i for i, z in enumerate(zeilen) if i and _ERGEBNIS_ZEILE.match(z)), None)
        if ez is not None:
            j = _letzte_inhaltszeile(zeilen, 0, ez)
            if j is not None:
                return _zeilen_offset(zeilen, j) + len(zeilen[j]), "zeile"
        return len(text.rstrip()), "anhaengen"
    wahl = bl[-1]
    reg = _regionen(neu)
    if len(bl) > 1 and reg:
        kand = [b for b in bl if _regionen(b["titel"] or "") & reg]
        seite = br.diktierte_seite(neu)
        if len(kand) > 1 and seite:
            kand = [b for b in kand if br.diktierte_seite(b["titel"] or "") in (seite, "")] or kand
        if kand:
            wahl = kand[0]
    if wahl["befund"]:
        a, e = wahl["befund"]
        j = _letzte_inhaltszeile(zeilen, a, e)
        if j is None:
            j = a - 1                                   # leerer Befundteil: direkt unter „## Befund“
        return _zeilen_offset(zeilen, j) + len(zeilen[j]), "zeile"
    a = wahl["ergebnis"][0] - 1                         # nur „## Ergebnis“: vor diese Überschrift
    j = _letzte_inhaltszeile(zeilen, wahl["start"], a)
    if j is None:
        return _zeilen_offset(zeilen, a), "davor"
    return _zeilen_offset(zeilen, j) + len(zeilen[j]), "zeile"


def _satz(neu, gross):
    s = " ".join((neu or "").split())
    if gross and s[:1].isalpha() and s[:1].islower():
        s = s[0].upper() + s[1:]
    if s and s[-1] not in _SATZENDE:
        s += "."
    return s


def ergaenzen(report, neu, gross=True):
    """Ergänzung ohne Cursor einbauen (ergaenzung_stelle). Titel und übriger Text bleiben Zeichen für Zeichen.
    → (neuer Text, Cursor hinter der Ergänzung)."""
    text = report or ""
    s = _satz(neu, gross)
    if not s:
        return text, len(text)
    if not text.strip():
        return s, len(s)
    pos, art = ergaenzung_stelle(text, s)
    if art == "zeile":
        return text[:pos] + "\n" + s + text[pos:], pos + 1 + len(s)
    if art == "davor":
        return text[:pos] + s + "\n\n" + text[pos:], pos + len(s)
    vor = text[:pos]
    return vor + " " + s + text[pos:], pos + 1 + len(s)


# ── Restructure ────────────────────────────────────────────────────────────────────────────────────────────────
_NUM = re.compile(r"^\s*(?:\*\*)?\s*\d+\s*[.)]\s*(?:\*\*)?\s*")


def saetze(report, mit_ergebnis=True):
    """Inhaltssätze eines Befundtexts (ohne Überschriften, Ergebnis-Nummern weg) → [(satz, abschnitt-art)]."""
    out, sektion = [], None
    for z in (report or "").split("\n"):
        art = _art(z)
        if art:
            sektion = art if art != "titel" else None
            continue
        if sektion == "ergebnis" and not mit_ergebnis:
            continue
        z = _NUM.sub("", z) if sektion == "ergebnis" else z
        for a, b in br.saetze_mit_lage(z):
            s = z[a:b].strip()
            if br.vorlage_normalisieren(s):
                out.append((s, sektion or "text"))
    return out


def vorrang(stand, aktuell):
    """Sätze im aktuellen Feld, die im letzten KaiScribe-Stand nicht (wörtlich, ohne Satzzeichen/Groß-Klein) standen
    = Peters Ergänzungen und Änderungen (gesprochen oder getippt). Reihenfolge wie im Text, ohne Doppelte."""
    alt = {br.vorlage_normalisieren(s) for s, _ in saetze(stand)}
    out, gesehen = [], set()
    for s, _ in saetze(aktuell):
        n = br.vorlage_normalisieren(s)
        if n not in alt and n not in gesehen:
            gesehen.add(n)
            out.append(s)
    return out


def block_text(report, b):
    return "\n".join((report or "").split("\n")[b["start"]:b["ende"]]).strip("\n")


def umbau_segment(text, vor):
    """Ein Abschnitt (Titel/Befund/Ergebnis) → Eingangstext für die Befundkette: „Titel: Befundtext … Ergebnis: …“.
    Normalsätze, die einer Vorrang-Angabe widersprechen (Katalog widersprueche, z. B. „unauffällige Spongiosa“ gegen
    „Enostose“), fallen vorher heraus. → (segment, [gestrichene Sätze])."""
    vor_n = {br.vorlage_normalisieren(s) for s in vor}
    befunde = br.widerspruch_befunde(" . ".join(vor)) if vor else []
    titel, teile, ergebnis, gestrichen, sektion = "", [], [], [], None
    for z in (text or "").split("\n"):
        art = _art(z)
        if art:
            if art == "titel" and not titel:
                titel = _UEBERSCHRIFT.match(z).group(1).strip()
            sektion = art if art != "titel" else sektion
            continue
        if not z.strip():
            continue
        if sektion == "ergebnis":
            ergebnis.append(_NUM.sub("", z).strip())
            continue
        if befunde:
            weg = [(a, e) for a, e, _ in br.widerspruch_saetze(z, befunde)
                   if br.vorlage_normalisieren(z[a:e]) not in vor_n]
            for a, e in reversed(weg):
                gestrichen.insert(0, z[a:e].strip())
                z = (z[:a].rstrip() + " " + z[e:].lstrip()).strip()
            if not z.strip():
                continue
        teile.append(z.strip())
    seg = "\n".join(([titel + ":"] if titel else []) + teile + (["Ergebnis: " + " ".join(ergebnis)] if ergebnis else []))
    return seg, gestrichen


def umbau_block(vor, gestrichen=(), ohne_stand=False):
    """Hinweis für den Gen-Prompt (an der Stelle {examples}, wie <widersprueche>): Umbau eines bestehenden Befunds,
    Peters Ergänzungen haben Vorrang. Leer, wenn es nichts umzubauen gibt (ohne Stand: der ganze Text ist von ihm)."""
    if not vor and not ohne_stand:
        return ""
    zeilen = ["<umbau>",
              "Das Diktat ist KEIN neues Diktat, sondern der aktuelle Text aus dem Befundfeld (Untersuchung, Befund, "
              "bisheriges Ergebnis), den der Arzt ergänzt bzw. geändert hat. Erstelle daraus den Befund nach allen "
              "Regeln dieses Prompts vollständig neu strukturiert."]
    if vor:
        zeilen.append("Vom Arzt ergänzt oder geändert (VORRANG – gilt vor Vorlage und bisherigem Text):")
        zeilen += [f"- „{s}“" for s in vor]
    else:
        zeilen.append("Der ganze Text stammt vom Arzt (alles hat Vorrang).")
    zeilen += [
        "Regeln für den Umbau:",
        "1. Jede Vorrang-Angabe steht im Befund an der fachlich passenden Stelle (Wortlaut möglichst beibehalten); "
        "ist sie ein Befund, steht sie auch im Ergebnis.",
        "2. Normal- und Vorlagensätze, die einer Vorrang-Angabe widersprechen, bleiben so nicht stehen (Regeln wie "
        "bei <widersprueche>).",
        "3. Alle übrigen Angaben des bisherigen Textes (Befunde, Messwerte, Seiten, Grade, Empfehlungen, IB-Lab-Texte) "
        "bleiben inhaltlich vollständig erhalten. Nichts erfinden, nichts weglassen.",
        "4. Das Ergebnis wird an die Vorrang-Angaben angepasst; Nummerierung wie immer.",
        "5. Die Überschrift (Untersuchung) bleibt wie im bisherigen Text."]
    if gestrichen:
        zeilen.append("Schon entfernt, weil sie einer Vorrang-Angabe widersprechen: "
                      + " ".join(f"„{s}“" for s in gestrichen))
    zeilen.append("</umbau>")
    return "\n".join(zeilen)


def titel_uebernehmen(neu, alt_titel):
    """Überschriften (## Untersuchung) des neuen Befunds der Reihe nach durch die bisherigen ersetzen — nur, wenn
    beide gleich viele Abschnitte mit Titel haben (sonst unverändert). alt_titel = Liste von Titeln."""
    alt_titel = [t for t in alt_titel if t]
    zeilen = (neu or "").split("\n")
    pos = [b["titel_zeile"] for b in bloecke(neu) if b["titel_zeile"] is not None]
    if not alt_titel or len(pos) != len(alt_titel):
        return neu
    for i, t in zip(pos, alt_titel):
        zeilen[i] = "## " + t
    return "\n".join(zeilen)


def _woerter(text):
    return [w for w in br.vorlage_normalisieren(text).split() if (len(w) >= 4 or w.isdigit()) and w not in _STOPP]


def inhalt_da(satz, report, anteil=0.7):
    """Steht der Inhalt von satz im report? Alle Zahlen und mindestens anteil der Inhaltswörter (ab 4 Zeichen,
    Wortanfang genügt: „Enostose“ ~ „Enostosen“)."""
    w = _woerter(satz)
    if not w:
        return True
    r = set(br.vorlage_normalisieren(report).split())
    def da(x):
        return x in r if x.isdigit() else any(y.startswith(x[:max(4, len(x) - 2)]) for y in r)
    if not all(da(x) for x in w if x.isdigit()):
        return False
    return sum(da(x) for x in w) >= anteil * len(w)


def fehlende(saetze_liste, report):
    """Sätze, deren Inhalt im report nicht (mehr) steht."""
    return [s for s in saetze_liste if not inhalt_da(s, report)]


_VERNEINUNG = re.compile(r"(?<![a-zäöüß])(?:kein|keine|keinen|keiner|keines|ohne|nicht)(?![a-zäöüß])", re.I)


def verneint_vorrang(satz, vor):
    """Verneint satz etwas, das Peter jetzt als Befund ergänzt hat („Kein Hinweis auf eine Fraktur.“ ↔ „Alte Fraktur
    des Schambeinasts.“)? Dann ist sein Wegfall gewollt – keine Prüfzeile."""
    if not _VERNEINUNG.search(satz or ""):
        return False
    vw = {w for s in vor for w in _woerter(s) if not w.isdigit()}
    return any(any(w[:max(4, len(w) - 2)] in v or v[:max(4, len(v) - 2)] in w for v in vw)   # auch Komposita („Wulstfraktur“)
               for w in _woerter(satz) if not w.isdigit() and w not in ("hinweis", "nachweis"))


def pruefzeile(satz, ergebnis=False):
    s = satz if len(satz) <= 60 else satz[:59] + "…"
    return f"„{s}“ nicht im Ergebnis – bitte prüfen" if ergebnis else f"„{s}“ nicht sicher im neuen Befund – bitte prüfen"


def streichen(report, weg):
    """Sätze (Vergleich ohne Satzzeichen/Groß-Klein), die Restructure vorher als widersprechend entfernt hat, dürfen
    nicht wörtlich zurückkommen (Peter: „unauffällige Spongiosa wird gestrichen“). Nur im Befundteil/Text."""
    weg_n = {br.vorlage_normalisieren(x) for x in weg}
    if not weg_n:
        return report
    out, sektion = [], None
    for z in (report or "").split("\n"):
        art = _art(z)
        if art:
            sektion = art
        elif sektion != "ergebnis":
            vorher = z
            for a, b in reversed(br.saetze_mit_lage(z)):
                if br.vorlage_normalisieren(z[a:b]) in weg_n:
                    links, rechts = z[:a].rstrip(), z[b:].lstrip()
                    z = links + (" " if links and rechts else "") + rechts
            if vorher.strip() and not z.strip():
                continue
        out.append(z)
    return "\n".join(out)


def ergebnis_text(report):
    """Alle Zeilen unter „## Ergebnis“ (alle Abschnitte)."""
    out, sektion = [], None
    for z in (report or "").split("\n"):
        art = _art(z)
        if art:
            sektion = art
        elif sektion == "ergebnis":
            out.append(z)
    return "\n".join(out)


def ergebnis_fehlt(vor, report):
    """Vorrang-Angaben mit Pathologie, die im Ergebnis nicht vorkommen (Ergebnis „angepasst“?)."""
    erg = ergebnis_text(report)
    if not erg.strip():
        return []
    return [s for s in vor if br.has_pathology(s) and not inhalt_da(s, erg, 0.5)]
