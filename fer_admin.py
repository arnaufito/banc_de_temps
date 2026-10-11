import os
import sqlite3

# Posa aquí el correu amb el qual et registres a la teva web
EL_TEU_CORREU = "admin@bancdetemps.cat"

# Mateixa base de dades que fa servir l'app (variable DATABASE o el banc_temps.db de la carpeta del projecte)
DB_PATH = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banc_temps.db"))

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Actualitzem l'usuari i li posem es_admin = 1 (els correus es guarden sempre en minúscules)
cursor.execute("UPDATE usuaris SET es_admin = 1 WHERE correu = ?", (EL_TEU_CORREU.strip().lower(),))
conn.commit()
modificats = cursor.rowcount
conn.close()

if modificats:
    print(f"✅ L'usuari amb correu {EL_TEU_CORREU} ara és ADMINISTRADOR SUPREM.")
else:
    print(f"❌ No existeix cap usuari amb el correu {EL_TEU_CORREU}. Registra't primer a la web i torna-ho a provar.")