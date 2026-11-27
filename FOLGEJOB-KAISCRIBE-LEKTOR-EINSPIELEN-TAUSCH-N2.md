# Tausch auf KaiScribe 3.32.0 lösen (Wächter 3.31.0 hält X:\KaiScribe\Programm\KaiScribe.exe)

Vorgeschichte: `BERICHT-KAISCRIBE-LEKTOR-EINBAU-N1-EINSPIELEN.md`. Abnahme L0/L1/LS an 451898 ist bestanden; der Tausch
(`kaiscribe_x_tauschen.ps1 2.1 -Schritt exe -Tag 3.32.0 -Sha a3aeeecea12ea9f4158d3c7272b28fb2fe21ad457f6459a3eb7ecbd14070f206`,
EXE liegt geprüft in `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.32.0\`) scheiterte an „nicht umbenennbar“, Halter nur der
eigene SM-Wächter 3.31.0 (PID 28828/37636). Der Wächter 3.28.2 hatte die EXE nicht blockiert.
Regeln wie immer (Ordi nur außerhalb der Ordi-Zeit, Meldungsruhe, nie in die CAS-DB, nichts hart beenden).
1. Ursache klären (nur lesen): warum blockiert 3.31.0 das Umbenennen (Start des Nachfolgers, Handle/Share-Flags, cwd, andere PCs mit offener EXE per Get-SmbOpenFile).
2. Lösung wählen, kleinste zuerst: (a) Tausch erneut, wenn der Halter weg ist; (b) Wächter bekommt einen sauberen Stopp-Weg (Stopp-Datei) in 3.32.1 – gilt erst ab dem nächsten Tausch, daher (c) Abmeldung/Neuanmeldung der Büro-PC-Sitzung in der Nachtzeit nur wenn kein CAS/Word offen und ohne Peters Sitzung zu stören (sonst Kanban-Karte Peter, `--grund vorort`).
3. Dann Tausch auf 3.32.0 (20 min Ruhe nach der letzten Ablage), Wächter muss danach wieder laufen, .alt-Sicherung melden, RL ohne Fehler.
4. `X:\KaiScribe\Daten\lektor.json` AUSDRÜCKLICH AUS anlegen: `{"befunder": {"kp": false, "rg": false}, "monatsdeckel_usd": 40}` (UTF-8 ohne BOM); Beleg: Inhalt + `[INIT] Lektor:`-Zeile.
Scharf-Entscheid bleibt `kaiscribe-lektor-scharf-n1`.
