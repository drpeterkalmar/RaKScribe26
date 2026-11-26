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


# kaiscribe-ergaenzung-ohne-ins-n1 (Peter 26.11.2026, Diktat 20261126060: „ich kann noch immer nicht rechts spontan
# dazu diktieren“ / „lässt mich den Befund nicht mit EOL abschließen“): Cursor bzw. Markierung rechts → Record → sprechen
# → Pause ⇒ der Abschnitt steht SOFORT wörtlich an der Stelle (kein INS nötig), links wird nichts angehängt. EOL während
# einer Ergänzung ist nie die Sackgasse „Erst INS“: offene Ergänzung erst einfügen, dann schließt EOL ab. Die Sperre
# „Erst INS“ gilt nur, solange rechts noch gar kein Befund steht (Neuer Befund / IB-Lab-Gerüst / Mammo-Maske).
EOL_SENDEN, EOL_ABSCHLIESSEN, EOL_EINFUEGEN, EOL_WARTEN, EOL_SPERRE = (
    "senden", "abschliessen", "einfuegen", "warten", "sperre")


def ergaenzung_laeuft(einbau, ziel=False):
    """Ist die laufende Aufnahme eine Ergänzung eines schon stehenden Befunds? (Cursor/Markierung oder Text rechts)"""
    return bool(ziel) or einbau in (CURSOR, ERGAENZUNG)


def pause_fuegt_ein(ziel, maske=False):
    """Pause (Record/Stop) fügt den eben diktierten Abschnitt sofort ein: nur mit Cursor/Markierung im Befund."""
    return bool(ziel) and not maske


def eol_aktion(zustand, einbau, ziel=False, offen=0):
    """Was tut EOL? zustand = jobstate-Zustand, einbau = modus() dieser Aufnahme, ziel = Cursor/Markierung gilt,
    offen = Abschnitte, die gerade erkannt/eingefügt werden. → senden (Ruhe: sichtbaren Befund weiterschicken),
    abschliessen (Pause, alles steht rechts: Aufnahme beenden, dann senden), einfuegen (offenes Diktat erst einfügen,
    EOL nochmals), warten (wird gerade eingefügt), sperre („Erst INS“: rechts steht noch kein Befund)."""
    if zustand in ("READY", "ERROR"):
        return EOL_SENDEN
    if zustand not in ("RECORDING", "PAUSED", "PROCESSING") or not ergaenzung_laeuft(einbau, ziel):
        return EOL_SPERRE
    if zustand == "PROCESSING" or offen:
        return EOL_WARTEN
    if zustand == "PAUSED" and ziel:
        return EOL_ABSCHLIESSEN
    return EOL_EINFUEGEN


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


# ── kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkt 62): „zweitens …“ / „Punkt 2 …“ / „neuer Punkt 2 …“ /
# „an zweiter Stelle …“ ins bestehende Ergebnis → wird Punkt 2, alle folgenden rücken nach (nie doppelte Nummern, nie
# überschreiben). Ohne Ordnungswort bleibt alles wie bisher (Ergänzung ans Ende des Befundteils).
_ORDNUNG = ["erst", "zweit", "dritt", "viert", "fünft", "sechst", "siebt", "acht", "neunt", "zehnt"]
_ZAHLWORT = ["eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"]
_ORDINAL_RE = re.compile(
    r"^\s*(?:(?:(?:als\s+)?neue[rn]?\s+)?punkt\s+(\d{1,2}|" + "|".join(_ZAHLWORT) + r")(?![\wäöüß])"
    r"|an\s+(" + "|".join(_ORDNUNG) + r")er\s+stelle"
    r"|(" + "|".join(_ORDNUNG) + r")ens(?![\wäöüß]))\s*[:,.\-]?\s*", re.I)


def ergebnis_ordinal(neu):
    """„zweitens Erguss“ → (2, „Erguss“); ohne Ordnungswort (None, neu)."""
    m = _ORDINAL_RE.match(neu or "")
    if not m or not (neu or "")[m.end():].strip():
        return None, neu
    if m.group(1):
        g = m.group(1).lower()
        n = int(g) if g.isdigit() else _ZAHLWORT.index(g) + 1
    else:
        n = _ORDNUNG.index((m.group(2) or m.group(3)).lower()) + 1
    return (n if n >= 1 else None), neu[m.end():]


def ergebnis_einfuegen(report, neu, gross=True, cursor=None):
    """Punkt 62: Satz mit Ordnungswort als Punkt n ins Ergebnis (Abschnitt am Cursor, sonst der passende bzw. letzte mit
    Ergebnis), folgende Punkte rücken nach, dann neu nummeriert. → (Text, Cursor) oder None (kein Ordnungswort/Ergebnis)."""
    n, rest = ergebnis_ordinal(neu)
    if n is None:
        return None
    text = report or ""
    zeilen = text.split("\n")
    bl = [b for b in bloecke(text) if b["ergebnis"]]
    if not bl:
        return None
    wahl = bl[-1]
    if cursor is not None:                      # Cursor-Diktat: nur wenn der Cursor im Ergebnis steht
        zeile = text[:cursor].count("\n")
        wahl = next((b for b in bl if b["ergebnis"][0] - 1 <= zeile < b["ergebnis"][1]), None)
        if wahl is None:
            return None
    else:
        reg = _regionen(rest)
        kand = [b for b in bl if reg and _regionen(b["titel"] or "") & reg]
        if kand:
            wahl = kand[0]
    a, e = wahl["ergebnis"]
    punkte = [i for i in range(a, e) if zeilen[i].strip() and zeilen[i][:1] not in (" ", "\t")
              and not br._UNNUM_RE.match(_NUM.sub("", zeilen[i]).strip())]
    s = _satz(rest, True if gross is None else gross)
    if not s:
        return None
    if n - 1 < len(punkte):
        ziel = punkte[n - 1]
    else:
        ziel = (punkte[-1] + 1) if punkte else (_letzte_inhaltszeile(zeilen, a, e) or (a - 1)) + 1
    zeilen.insert(ziel, s)
    neu_text = br.ergebnis_nummerieren("\n".join(zeilen))
    nz = neu_text.split("\n")
    return neu_text, _zeilen_offset(nz, ziel) + len(nz[ziel])


def ergaenzen(report, neu, gross=True):
    """Ergänzung ohne Cursor einbauen (ergaenzung_stelle). Titel und übriger Text bleiben Zeichen für Zeichen.
    → (neuer Text, Cursor hinter der Ergänzung)."""
    text = report or ""
    s = _satz(neu, gross)
    if not s:
        return text, len(text)
    if not text.strip():
        return s, len(s)
    e = ergebnis_einfuegen(text, neu, gross)   # Punkt 62: „zweitens …“ → Ergebnispunkt 2
    if e is not None:
        return e
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


# ── kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkte 63 + 67, RH 120 Ganzbein, RH 130 GWS + Funktion) ─────────
# Das IB-Lab-Gerüst stand richtig da (Ganzbein mit LAMA-Sätzen; GWS korrekt in HWS/BWS/LWS geteilt). Das Diktat betraf
# nur EINE Region – der neue Befund aus dem Diktat ersetzte trotzdem alles: die LAMA-Sätze waren weg (KI schrieb
# „irgendetwas“ zum Ganzbein), bzw. aus vier Teilen wurde ein Teil „Funktionsaufnahmen“ mit dem SQUIRREL-Satz.
# Regel: KaiScribe ergänzt das Diktat, löscht nie ohne Rückfrage.
#  - Gerüst-Teil ohne Gegenstück im neuen Befund → bleibt wörtlich (an seiner Stelle).
#  - Gerüst-Teil, dessen Region NICHT diktiert ist → bleibt wörtlich (statt des neu geschriebenen Teils).
#  - diktierter Teil: der neue Teil gilt; IB-Lab-Messsätze des Gerüsts (Werte mit mm/°, HKA/LCE/Cobb …), die dort fehlen,
#    kommen zurück + Prüfzeile („Diff-Wächter“).
#  - neue Teile ohne Gerüst-Gegenstück (z. B. „Funktionsaufnahmen der LWS“) kommen ZUSÄTZLICH hinter den Teil derselben
#    Region; IB-Lab-Sätze, die schon in einem behaltenen Gerüst-Teil stehen (SQUIRREL), fallen dort heraus.
_MESS = re.compile(r"\d+(?:[.,]\d+)?\s*(?:mm|cm|°|%)|(?<![a-zäöüß])(?:hka|lce|ccd|cobb|mikulicz|traglinie)", re.I)


def _teil_text(text, b):
    return "\n".join(text.split("\n")[b["start"]:b["ende"]]).strip("\n")


def _teil_schluessel(titel):
    t = (titel or "").lower()
    return frozenset(_regionen(t)), "funktion" in t, "ganzbein" in t


def _passt(g, n):
    if (g["titel"] or "").strip().lower() == (n["titel"] or "").strip().lower():
        return True
    kg, kn = _teil_schluessel(g["titel"]), _teil_schluessel(n["titel"])
    return bool(kg[0]) and kg == kn


def _mess_saetze(teil):
    return [s for s, art in saetze(teil, mit_ergebnis=True) if _MESS.search(s)]


def geruest_erhalten(geruest, neu, diktat=""):
    """→ (Befund, Prüfzeilen). Ohne Gerüst bzw. ohne mehrere Teile unverändert."""
    g_text, n_text = (geruest or "").strip(), (neu or "").strip()
    if not g_text or not n_text:
        return neu, []
    gb = [b for b in bloecke(g_text) if b["titel"] and (b["befund"] or b["ergebnis"])]
    nb = [b for b in bloecke(n_text) if b["titel"] and (b["befund"] or b["ergebnis"])]
    if not gb or not nb:
        return neu, []
    dk = (diktat or "").lower()
    dreg = _regionen(dk)
    benutzt, out, hinweise = set(), [], []
    for g in gb:
        k = next((j for j, n in enumerate(nb) if j not in benutzt and _passt(g, n)), None)
        gt = _teil_text(g_text, g)
        if k is None:
            out.append(("g", gt, g))
            continue
        benutzt.add(k)
        nt = _teil_text(n_text, nb[k])
        diktiert = bool(_teil_schluessel(g["titel"])[0] & dreg) or ("ganzbein" in dk and "ganzbein" in (g["titel"] or "").lower())
        if not diktiert:
            out.append(("g", gt, g))
            if nt.strip() != gt.strip():
                hinweise.append(f"{g['titel']}: nicht diktiert – Teil aus dem Gerüst unverändert behalten")
            continue
        for s in _mess_saetze(gt):
            if not inhalt_da(s, nt, 0.9):
                nt = ergaenzen(nt, s)[0]
                hinweise.append(pruefzeile(s) + " (aus dem Gerüst wiederhergestellt)")
        out.append(("n", nt, nb[k]))
    behalten = " ".join(t for art, t, _b in out if art == "g")
    for j, n in enumerate(nb):
        if j in benutzt:
            continue
        nt = _teil_text(n_text, n)
        for s in _mess_saetze(nt):
            if s in behalten:
                nt = streichen_wort(nt, s)
        nt = _doppelte_punkte_weg(nt, [t for art, t, _b in out if art == "g"])
        reg = _teil_schluessel(n["titel"])[0]
        stelle = max((i for i, (_a, _t, b) in enumerate(out) if reg & _teil_schluessel(b["titel"])[0]), default=len(out) - 1)
        out.insert(stelle + 1, ("n", nt, n))
    ergebnis = "\n\n\n".join(t.strip() for _a, t, _b in out)
    if ergebnis.strip() == n_text:
        return neu, []
    return br.ergebnis_nummerieren(ergebnis), hinweise


def streichen_wort(text, satz):
    """Einen Satz (wörtlich) samt Leerzeichen aus dem Text nehmen; leer gewordene Zeilen fallen weg."""
    i = text.find(satz)
    if i < 0:
        return text
    vor, nach = text[:i], text[i + len(satz):]
    if nach[:1] == " ":
        nach = nach[1:]
    elif vor[-1:] == " ":
        vor = vor[:-1]
    return vor + nach


def _doppelte_punkte_weg(teil, andere):
    """Ergebnispunkte eines Teils, die wörtlich (ohne Nummer) schon in einem anderen Teil stehen, fallen heraus."""
    schon = {_NUM.sub("", z).strip() for t in andere for z in t.split("\n") if z.strip()}
    zeilen, im_erg, aus = teil.split("\n"), False, []
    for z in zeilen:
        if _UEBERSCHRIFT.match(z):
            im_erg = _art(z) == "ergebnis"
        elif im_erg and z.strip() and _NUM.sub("", z).strip() in schon:
            continue
        aus.append(z)
    return "\n".join(aus)
