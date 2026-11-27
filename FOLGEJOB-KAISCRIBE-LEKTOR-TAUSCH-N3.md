# Tausch auf KaiScribe 3.32.0 nach Abmeldung der Büro-Sitzung

Vorgeschichte: `BERICHT-KAISCRIBE-LEKTOR-EINSPIELEN-TAUSCH-N2.md`. Voraussetzung: Peter hat die Sitzung `cas` am Büro-PC abgemeldet (Kanban #531, Karte Peter vorort); prüfen per query user / keine KaiScribe-Prozesse.
1. Außerhalb der Ordi-Zeit: `kaiscribe_x_tauschen.ps1 2.1 -Schritt exe -Tag 3.32.0 -Sha a3aeeecea12ea9f4158d3c7272b28fb2fe21ad457f6459a3eb7ecbd14070f206` (EXE liegt geprüft in W\v3.32.0). 20 min Ruhe, nichts hart beenden.
2. Wächter wieder da (nach Neuanmeldung/Autostart), .alt melden, RL ohne Fehler.
3. `X:\KaiScribe\Daten\lektor.json` AUS anlegen (`{"befunder": {"kp": false, "rg": false}, "monatsdeckel_usd": 40}`, UTF-8 ohne BOM), Beleg + `[INIT] Lektor:`-Zeile.
4. Optional: Wächter-Stopp-Datei in 3.32.1 vorschlagen (Tausch-Skript legt Datei, Wächter endet sauber).
