"""Gate v3.18.8 (Peter 12.11.2026, Foto „Fuß beidseits in 2 Ebenen“: „Das ist viel zu viel für den Befund. Bitte nur die
pathologischen Maße in den Befund eintragen. Die Schlussfolgerungen im FROG-Ergebnis gefallen mir schon sehr gut.“ –
Nachtrag: HIPPO und KOALA ebenso). ibl_bausteine.BEFUND_NUR_AUFFAELLIG = {frog, hippo, koala}: in den Befund (Gerüst vor
dem Diktat und Einsetzen nach der KI) kommen nur Messzeilen, aus denen eine aktive Regel des Abholers (ris-mods
ibl/regeln/<modul>.toml) einen Ergebnispunkt gemacht hat; Ergebnispunkte unverändert und vollständig.
Fälle: Peters Foto (Werte ohne Patientendaten, Texte wie ris-mods ibl/vorbefund.py sie bildet), ris-mods ibl/beispiele
frog_beidseits/frog_pes_planus, Hersteller-Fixtures FROG d.p./seitlich, HIPPO und KOALA je mit und ohne Regeltreffer,
Diktat-Abgleich weggefilterter Werte, Gen-Prompt, Modul ohne Filter (SQUIRREL/Rho/LAMA/PANDA) bit-gleich zu 3.18.7
(Schnappschuss tests/offline/snapshots/ibl_ohne_filter.json, erzeugt mit dem Code von 3.18.7).
Aufruf: python3 tests/offline/test_ibl_nur_auffaellig.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import ibl_bausteine as I  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def bericht(titel, befund, ergebnis):
    return f"## {titel}\n\n## Befund\n{befund}\n\n## Ergebnis\n{ergebnis}"


def baustein(modul, befundteil, ergebnis, seiten=("rechts", "links"), **kw):
    d = {"accno": "T-0091", "ziffer": 1, "modul": modul, "name": modul.upper(), "modul_name": f"IB Lab {modul.upper()}",
         "version": 1, "seiten": list(seiten), "befundteil": list(befundteil), "ergebnis": list(ergebnis),
         "hinweise": [], "nicht_zugeordnet": []}
    d.update(kw)
    return I.aus_liste([d])


check("Schalter: FROG, HIPPO und KOALA (Nachtrag Peter 12.11.2026)", I.BEFUND_NUR_AUFFAELLIG == {"frog", "hippo", "koala"})

# ───────────────────────────── Peters Foto: Fuß beidseits d.p. + seitlich ─────────────────────────────
FOTO_BT = [
    "Fuß d.p.:",
    "Hallux-valgus-Winkel rechts 19° (IB Lab FROG).",
    "Intermetatarsalwinkel I/II rechts 10° (IB Lab FROG).",
    "Distaler metatarsaler Gelenkflächenwinkel rechts 6° (IB Lab FROG).",
    "Talocalcanealwinkel d.p. rechts 31° (IB Lab FROG).",
    "Vorfußadduktionswinkel rechts 16° (IB Lab FROG).",
    "Intermetatarsalwinkel I/V rechts 29° (IB Lab FROG).",
    "Intermetatarsalwinkel IV/V rechts 8° (IB Lab FROG).",
    "Metatarsophalangealwinkel V rechts 16° (IB Lab FROG).",
    "Knöcherne Fußbreite rechts 100,4 mm (IB Lab FROG).",
    "Hallux-valgus-Winkel links 24° (IB Lab FROG).",
    "Intermetatarsalwinkel I/II links 10° (IB Lab FROG).",
    "Distaler metatarsaler Gelenkflächenwinkel links 11° (IB Lab FROG).",
    "Talocalcanealwinkel d.p. links 22° (IB Lab FROG).",
    "Vorfußadduktionswinkel links 13° (IB Lab FROG).",
    "Intermetatarsalwinkel I/V links 29° (IB Lab FROG).",
    "Intermetatarsalwinkel IV/V links 9° (IB Lab FROG).",
    "Metatarsophalangealwinkel V links 13° (IB Lab FROG).",
    "Knöcherne Fußbreite links 98,2 mm (IB Lab FROG).",
    "Fuß seitlich rechts:",
    "Calcaneusneigungswinkel rechts 27° (IB Lab FROG).",
    "Längsgewölbewinkel nach Djian-Annonier rechts 113° (IB Lab FROG).",
    "Meary-Winkel rechts 12° (IB Lab FROG).",
    "Talocalcanealwinkel seitlich rechts 45° (IB Lab FROG).",
    "Cuboidhöhe rechts 17,6 mm (IB Lab FROG).",
    "Länge des 1. Strahls (sagittal) rechts 103,4 mm (IB Lab FROG).",
]
FOTO_ERG = [
    "Fuß d.p.: Geringgradiger Hallux valgus rechts (Hallux-valgus-Winkel 19°).",
    "Fuß d.p.: Mittelgradiger Hallux valgus links (Hallux-valgus-Winkel 24°).",
    "Fuß d.p.: Vergrößerter Intermetatarsalwinkel I/II (Metatarsus primus varus) beidseits (Intermetatarsalwinkel I/II "
    "rechts 10°, links 10°).",
]
FOTO_SOLL = ["Fuß d.p.:", "Hallux-valgus-Winkel rechts 19° (IB Lab FROG).", "Intermetatarsalwinkel I/II rechts 10° (IB Lab FROG).",
             "Hallux-valgus-Winkel links 24° (IB Lab FROG).", "Intermetatarsalwinkel I/II links 10° (IB Lab FROG)."]
foto = baustein("frog", FOTO_BT, FOTO_ERG)
check("Foto: in den Befund nur HVA + IMA I/II je Seite (Beschriftung „Fuß d.p.:“ bleibt, „Fuß seitlich rechts:“ ohne "
      "Zeile darunter entfällt)", I.befund_zeilen(foto[0]) == FOTO_SOLL, I.befund_zeilen(foto[0]))
g = I.geruest(foto, None, T)
befund_teil = g.report.split("## Befund\n", 1)[1].split("\n\n## Ergebnis", 1)[0]
check("Foto, Gerüst: Befund = genau diese Zeilen, Ergebnis = alle drei Punkte unverändert (nummeriert)",
      befund_teil.split("\n") == FOTO_SOLL and g.report.endswith(
          "## Ergebnis\n1. " + FOTO_ERG[0] + "\n2. " + FOTO_ERG[1] + "\n3. " + FOTO_ERG[2]), g.report)
check("Foto, Gerüst: keine unauffälligen Werte (Fußbreite, Meary, Cuboid, DMAA …), Gate ok",
      not any(w in g.report for w in ("Fußbreite", "Meary", "Cuboid", "Gelenkflächenwinkel", "Calcaneus", "seitlich"))
      and I.gate(g.report, g.zeilen) == [] and g.zeilen == FOTO_SOLL + FOTO_ERG, g.zeilen)
check("Foto: hervorgehoben werden die vier Messzeilen und die Punkte",
      I.auffaellige_zeilen(foto) == FOTO_SOLL[1:] + FOTO_ERG, I.auffaellige_zeilen(foto))
FUSS = bericht("Fuß beidseits in 2 Ebenen", "Keine Fraktur. Os tibiale externum rechts.",
               "Os tibiale externum rechts.")
e = I.einsetzen(FUSS, foto, diktat="Fuß beidseits: keine Fraktur.", templates=T)
check("Foto, nach der KI: nur die auffälligen Zeilen eingesetzt, Ergebnispunkte vollständig, Gate ok",
      all(z in e.report for z in FOTO_SOLL) and all(p in e.report for p in FOTO_ERG)
      and not any(w in e.report for w in ("Fußbreite", "Meary", "Cuboid", "Talocalcanealwinkel", "seitlich rechts:"))
      and I.gate(e.report, e.zeilen) == [] and not e.hinweise, e.report + str(e.hinweise))
e = I.einsetzen(FUSS, foto, diktat="Fuß beidseits: Hallux-valgus-Winkel rechts 19 Grad. Hallux-valgus-Winkel links "
                "24 Grad. Intermetatarsalwinkel I/II beidseits 10 Grad.", templates=T)
check("Foto: alle auffälligen Werte schon diktiert → nichts doppelt, Beschriftung „Fuß d.p.:“ allein entfällt",
      "Fuß d.p.:" not in e.report.split("## Ergebnis")[0] and "(IB Lab FROG)" not in e.report
      and sum("schon im Befund" in h for h in e.hinweise) == 3, e.report + str(e.hinweise))
e = I.einsetzen(FUSS, foto, diktat="Fuß beidseits: Meary-Winkel 20 Grad. Cuboidhöhe 17,6 mm.", templates=T)
check("Foto: abweichender diktierter Wert einer weggefilterten Messgröße → Prüf-Hinweis; gleicher Wert → kein Hinweis",
      "Meary" not in e.report.split("## Ergebnis")[0].replace("## Befund\nKeine", "")
      and any("Meary-Winkel im Befund 20 grad, laut IB Lab 12°" in h for h in e.hinweise)
      and not any("Cuboid" in h for h in e.hinweise), str(e.hinweise))
blk = I.prompt_block(foto, T["fuß_in_2_ebenen"]["body"])
check("Foto, Gen-Prompt: nur HVA + IMA I/II als „wird eingefügt“, kein weggefilterter Wert, kein Themen-Ersatz",
      "- FROG: Hallux-valgus-Winkel, Intermetatarsalwinkel I/II\n" in blk
      and not any(w in blk for w in ("Fußbreite", "Meary", "Cuboid", "Fuß d.p.", "ersetzt Vorlagen-Sätze")), blk)

# ───────────────────────────── ris-mods-Beispiele und Hersteller-Fixtures ─────────────────────────────
bds = baustein("frog", ["Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG).",
                        "Intermetatarsalwinkel I/II rechts 8,5° (IB Lab FROG).",
                        "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).",
                        "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."],
               ["Pes planus beidseits (Calcaneusneigungswinkel rechts 10,0°, links 12,4°).",
                "Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24,3°)."])
check("ris-mods frog_beidseits: IMA 8,5° (< 9°) raus, Pes planus beidseits hält beide Calcaneus-Zeilen",
      I.befund_zeilen(bds[0]) == ["Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG).",
                                  "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).",
                                  "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."], I.befund_zeilen(bds[0]))
planus = baustein("frog", ["Calcaneusneigungswinkel 10° (IB Lab FROG)."], ["Pes planus (Calcaneusneigungswinkel 10°)."],
                  seiten=())
check("ris-mods frog_pes_planus: die eine Zeile bleibt", I.befund_zeilen(planus[0]) == ["Calcaneusneigungswinkel 10° (IB Lab FROG)."])
dp = baustein("frog", ["Hallux-valgus-Winkel rechts 27,0° (IB Lab FROG).", "Intermetatarsalwinkel I/II rechts 17,0° (IB Lab FROG).",
                       "Distaler metatarsaler Gelenkflächenwinkel rechts 20,0° (IB Lab FROG).",
                       "Hallux-valgus-Winkel links 42,0° (IB Lab FROG).", "Intermetatarsalwinkel I/II links 19,0° (IB Lab FROG).",
                       "Knöcherne Fußbreite links 99,6 mm (IB Lab FROG)."],
              ["Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 27,0°).",
               "Hochgradiger Hallux valgus links (Hallux-valgus-Winkel 42,0°).",
               "Vergrößerter Intermetatarsalwinkel I/II (Metatarsus primus varus) beidseits (Intermetatarsalwinkel I/II "
               "rechts 17,0°, links 19,0°)."])
check("FROG d.p. (Hersteller-Fixture): HVA/IMA je Seite, DMAA und Fußbreite raus",
      [z.split(" (")[0] for z in I.befund_zeilen(dp[0])] == ["Hallux-valgus-Winkel rechts 27,0°", "Intermetatarsalwinkel I/II rechts 17,0°",
                                                         "Hallux-valgus-Winkel links 42,0°", "Intermetatarsalwinkel I/II links 19,0°"])
seite = baustein("frog", ["Hallux-valgus-Winkel rechts 24° (IB Lab FROG).", "Hallux-valgus-Winkel links 24° (IB Lab FROG)."],
                 ["Mittelgradiger Hallux valgus links (Hallux-valgus-Winkel 24°)."])
check("Seite zählt: gleicher Wert, Punkt nur links → nur die linke Zeile",
      I.befund_zeilen(seite[0]) == ["Hallux-valgus-Winkel links 24° (IB Lab FROG)."], I.befund_zeilen(seite[0]))
zwei = baustein("frog", ["Fuß d.p.:", "Hallux-valgus-Winkel rechts 24° (IB Lab FROG).", "Fuß schräg:",
                         "Hallux-valgus-Winkel rechts 24° (IB Lab FROG)."],
                ["Fuß d.p.: Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24°)."], seiten=("rechts",))
check("Aufnahme zählt: Punkt „Fuß d.p.: …“ hält nur die Zeile unter „Fuß d.p.:“",
      I.befund_zeilen(zwei[0]) == ["Fuß d.p.:", "Hallux-valgus-Winkel rechts 24° (IB Lab FROG)."], I.befund_zeilen(zwei[0]))

ohne = baustein("frog", ["Calcaneusneigungswinkel rechts 24° (IB Lab FROG).", "Hallux-valgus-Winkel rechts 12° (IB Lab FROG)."],
                [], seiten=("rechts",))
check("FROG ohne Regeltreffer: 0 Befundzeilen, kein Gerüst, nichts hervorgehoben",
      I.befund_zeilen(ohne[0]) == [] and I.geruest(ohne, None, T) is None and I.auffaellige_zeilen(ohne) == []
      and not I.hat_inhalt(ohne[0]))
rep = bericht("Fuß rechts in 2 Ebenen", "Regelrechte Stellung.", "Regelrechte Darstellung des Fußskeletts rechts.")
e = I.einsetzen(rep, ohne, diktat="Fuß rechts unauffällig.", templates=T)
check("FROG ohne Regeltreffer, nach der KI: Befund unverändert (kein erfundener Normalsatz), keine Hinweise",
      e.report == rep and e.zeilen == [] and not e.hinweise and e.behandelt == {("T-0091", "frog"): 1}, e.report + str(e.hinweise))
check("FROG ohne Regeltreffer: kein <ibl_messwerte> im Gen-Prompt", I.prompt_block(ohne, T["fuß_in_2_ebenen"]["body"]) == "")

# ───────────────────────────── HIPPO mit und ohne Regeltreffer ─────────────────────────────
HIPPO_BT = ["LCE-Winkel nach Wiberg rechts 32,3° (IB Lab HIPPO).", "CCD-Winkel rechts 132,6° (IB Lab HIPPO).",
            "Pfannendachwinkel nach Tönnis (Acetabulumindex) rechts 10,1° (IB Lab HIPPO).",
            "Sharp-Winkel rechts 34,7° (IB Lab HIPPO).", "Femorales Offset rechts 46,9 mm (IB Lab HIPPO).",
            "LCE-Winkel nach Wiberg links 38,3° (IB Lab HIPPO).", "CCD-Winkel links 132,1° (IB Lab HIPPO).",
            "Pfannendachwinkel nach Tönnis (Acetabulumindex) links 5,9° (IB Lab HIPPO).",
            "Beckenschiefstand 0,0° (IB Lab HIPPO).", "Beinlängendifferenz 7,0 mm (IB Lab HIPPO)."]
HIPPO_ERG = ["Steiles Pfannendach rechts (Pfannendachwinkel nach Tönnis (Acetabulumindex) 10,1°)."]
hip = baustein("hippo", HIPPO_BT, HIPPO_ERG)
check("HIPPO mit Treffer: nur der Pfannendachwinkel rechts (Klammer im Namen)",
      I.befund_zeilen(hip[0]) == ["Pfannendachwinkel nach Tönnis (Acetabulumindex) rechts 10,1° (IB Lab HIPPO)."],
      I.befund_zeilen(hip[0]))
BECKEN = bericht("Becken und Hüfte beidseits", "Keine Fraktur. Os acetabuli rechts.", "Os acetabuli rechts.")
e = I.einsetzen(BECKEN, hip, diktat="Becken: keine Fraktur.", templates=T)
check("HIPPO mit Treffer, nach der KI: eine Messzeile + der Punkt, sonst kein HIPPO-Wert, Gate ok",
      e.zeilen == I.befund_zeilen(hip[0]) + HIPPO_ERG and "LCE" not in e.report and "Offset" not in e.report
      and I.gate(e.report, e.zeilen) == [], e.report)
hip0 = baustein("hippo", ["LCE-Winkel nach Wiberg rechts 32° (IB Lab HIPPO).", "CCD-Winkel rechts 132° (IB Lab HIPPO).",
                          "Pfannendachwinkel nach Tönnis (Acetabulumindex) rechts 6° (IB Lab HIPPO).",
                          "LCE-Winkel nach Wiberg links 30° (IB Lab HIPPO).", "CCD-Winkel links 130° (IB Lab HIPPO)."], [])
e = I.einsetzen(BECKEN, hip0, diktat="Becken: keine Fraktur.", templates=T)
check("HIPPO ohne Treffer: 0 Zeilen, Befund unverändert, kein Gerüst",
      I.befund_zeilen(hip0[0]) == [] and e.report == BECKEN and I.geruest(hip0, None, T) is None, e.report)
e = I.einsetzen(BECKEN, hip0, diktat="Becken: CCD-Winkel rechts 140 Grad.", templates=T)
check("HIPPO ohne Treffer: diktierter abweichender CCD-Winkel → Prüf-Hinweis, nichts angefügt",
      e.report == BECKEN and any("CCD-Winkel im Befund 140 grad, laut IB Lab 132°" in h for h in e.hinweise), str(e.hinweise))

# ───────────────────────────── KOALA mit und ohne Regeltreffer ─────────────────────────────
KOALA_BT = ["Kellgren-Lawrence-Grad rechts 3 (IB Lab KOALA).", "Minimale Gelenkspaltweite medial rechts 2,1 mm (IB Lab KOALA).",
            "Minimale Gelenkspaltweite lateral rechts 5,0 mm (IB Lab KOALA).",
            "Gelenkspaltverschmälerung (OARSI-Grad) rechts 2 (IB Lab KOALA).", "Kellgren-Lawrence-Grad links 1 (IB Lab KOALA).",
            "Minimale Gelenkspaltweite medial links 4,4 mm (IB Lab KOALA).",
            "Gelenkspaltverschmälerung (OARSI-Grad) links 0 (IB Lab KOALA)."]
KOALA_ERG = ["Mittelgradige Gonarthrose rechts (Kellgren-Lawrence-Grad 3)."]
ko = baustein("koala", KOALA_BT, KOALA_ERG)
check("KOALA mit Treffer: nur K&L rechts 3 (links 1 und Gelenkspalt/OARSI raus)",
      I.befund_zeilen(ko[0]) == ["Kellgren-Lawrence-Grad rechts 3 (IB Lab KOALA)."], I.befund_zeilen(ko[0]))
g = I.geruest(ko, None, T)
check("KOALA mit Treffer, Gerüst: eine Messzeile + Punkt", g.zeilen == ["Kellgren-Lawrence-Grad rechts 3 (IB Lab KOALA)."]
      + KOALA_ERG and "Gelenkspaltweite" not in g.report, g.report)
check("KOALA: K&L-Grade fürs Diktat/den Wächter bleiben vollständig (links 1, rechts 3)",
      I.kl_grade(ko, "links") == ["1"] and I.kl_grade(ko, "rechts") == ["3"])
ko0 = baustein("koala", ["Kellgren-Lawrence-Grad 1 (IB Lab KOALA).", "Minimale Gelenkspaltweite medial 4,5 mm (IB Lab KOALA).",
                         "Osteophyten (OARSI-Grad) 0 (IB Lab KOALA)."], [], seiten=("links",))
KNIE = bericht("Kniegelenk links in 2 Ebenen", "Regelrechte Gelenkstellung.", "Unauffälliges Kniegelenk links.")
e = I.einsetzen(KNIE, ko0, diktat="Knie links unauffällig.", templates=T)
check("KOALA ohne Treffer: 0 Zeilen, Befund unverändert, kein Gerüst",
      I.befund_zeilen(ko0[0]) == [] and e.report == KNIE and not e.hinweise and I.geruest(ko0, None, T) is None,
      e.report + str(e.hinweise))
blk = I.prompt_block(ko0, T["kniegelenk_in_2_ebenen"]["body"])
check("KOALA ohne Treffer, Gen-Prompt: K&L-Grad bekannt (für eine diktierte Arthrose), aber nichts „wird eingefügt“",
      "Kellgren-&-Lawrence-Grad laut IB Lab: Kellgren-Lawrence-Grad 1." in blk and "fügt sie nach dem Befund" not in blk
      and "Gelenkspaltweite" not in blk, blk)

# ───────────────────────────── Module ohne Filter: bit-gleich zu 3.18.7 ─────────────────────────────
snap = json.loads((ROOT / "tests" / "offline" / "snapshots" / "ibl_ohne_filter.json").read_text(encoding="utf-8"))
for f in snap:
    b = I.aus_liste(f["bausteine"])
    e = I.einsetzen(f["bericht"], b, diktat=f["diktat"], templates=T)
    g = I.geruest(b, None, T)
    ist = {"einsetzen": {"report": e.report, "hinweise": e.hinweise, "zeilen": e.zeilen, "zuordnung": e.zuordnung},
           "geruest": None if g is None else {"report": g.report, "zeilen": g.zeilen, "zuordnung": g.zuordnung},
           "prompt": I.prompt_block(b, (T.get(f["vorlage"]) or {}).get("body") if f["vorlage"] else None),
           "auffaellig": I.auffaellige_zeilen(b)}
    soll = {k: f[k] for k in ist}
    check(f"bit-gleich zu 3.18.7: {f['name']} (Einsetzen, Gerüst, Gen-Prompt, Hervorhebung)", ist == soll,
          json.dumps({k: (ist[k], soll[k]) for k in ist if ist[k] != soll[k]}, ensure_ascii=False)[:600])
check("Schnappschuss enthält SQUIRREL und Rho", {"squirrel", "rho"} <= {f["name"] for f in snap})

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
