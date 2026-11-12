# KaiScribe 3.18.3 bauen/freigeben – Bericht kaiscribe-v3183-release (12.11.2026)

**Kurz:** Ein eigenes 3.18.3 wurde **nicht gebaut**, denn das wäre ein Rückschritt gewesen. Beide 3.18.3-Commits liegen auf main schon
unter den späteren Releases: 83a0f5d (ein einzelner Ergebnispunkt wird nicht nummeriert) und 62aa266 (Doppelpunkt nach Kortikalis/Kompakta).
Diese Releases haben die Jobs kaiscribe-konfabulation-n1/-n2 gebaut: **3.18.4** (10:08 UTC) und **3.18.5** (11:21 UTC, Latest,
Windows-UI-Test grün). Einen GitHub-Release 3.18.3 gibt es nicht.

## Geprüft
- main = 3.18.5 (0408266): Einzelpunkt-Regel (`_nummeriere_block`, Marker `2026-11-12-v3183-einzelpunkt`) und
  „Kortikalis: glatte und scharfe Kontur …“ in templates.json (13 Stellen) sind enthalten.
- Volle Offline-Gates `tests/offline/test_*.py` + `*_test.py` mit venv (tkinter, numpy, pyyaml): **alle grün**, auch
  test_deploy_guard.py und befund_regeln_test (185/185 TS + PY).
- GitHub API releases/latest: 3.18.5, Asset rakscribe26.exe.

## Einspielen + Echttest
Das Einspielen an die Befund-PCs übernimmt der wartende Job `kaiscribe-nachvollzug-paket-n1` (Ressource ordi, Ordi-Zeit-Regeln),
und zwar mit 3.18.5. Er hat einen Nachtrag mit den Echttests (a)–(d) dieses Auftrags bekommen: ein Punkt ohne „1.“, zwei
Pathologien als 1./2., Normalbefund unnummeriert, Hand rechts mit dem Kortikalis/Kompakta-Wortlaut. Ergebnis wörtlich in
seinem Bericht. Für 3.18.3 selbst wurde **nichts** an den Befund-PCs belegt und kein Echttest gemacht.

## Offen
- Belegt laufende Version an jedem Befund-PC und Echttest (a)–(d): kommen mit kaiscribe-nachvollzug-paket-n1.
- Arbeitsdatei: `~/cj/work/kaiscribe-v3183-release/nachtrag.py` (Nachtrag am Queue-Job).
