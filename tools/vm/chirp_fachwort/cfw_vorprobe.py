"""chirp-fachwortliste-n1: Vorprobe CAS (nur SELECT, READ ONLY) – NUR Spaltennamen der Tabellen mit Namen/Orten/Straßen
und Zeilenzahlen. Keine Inhalte."""
import sys

for p in (r"C:\RaK\kaiscribe_lernen\prog\bruecke", r"C:\RaKScribe-Py\ris-mods\bruecke"):
    sys.path.insert(0, p)
import casdb  # noqa: E402

SQL = casdb._KOPF + casdb._abschnitt("spalten", """
SELECT 'C|' || table_name || '|' || column_name || '|' || data_type FROM all_tab_columns
 WHERE owner = 'SYSADM' AND (REGEXP_LIKE(column_name, '(NAME|ORT|STRASSE|STRASE|ADRESS|ADR|STADT|GEMEINDE|PLZ|TITEL)'))
   AND column_name NOT LIKE '%PASS%' AND column_name NOT LIKE '%USERNAME%'
 ORDER BY table_name, column_name;""") + casdb._abschnitt("zahlen", """
SELECT 'N|' || table_name || '|' || num_rows FROM all_tables WHERE owner = 'SYSADM'
 AND table_name IN ('WARTEROW','ALLARZTE','ARZTE','PRIVADRESS','PATIENT','PATIENTS','PATIENTEN','PERSON','PERSONS');""") + \
    "SELECT '###ENDE###' FROM dual;\nROLLBACK;\nEXIT\n"

anm = casdb.anmeldung_lesen()
sp = casdb.sqlplus_finden()
if not anm or not sp:
    print("VP FEHLER anm=%s sqlplus=%s" % ("ja" if anm else "nein", sp))
    sys.exit(1)
rc, out = casdb.sqlplus_ausfuehren([sp], "CASMED", anm[0], anm[1], SQL, frist_s=280)
print("VP rc=%s" % rc)
for z in out.splitlines():
    if z.startswith(("C|", "N|")) or "ORA-" in z:
        print("VP " + z.strip())
