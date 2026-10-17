"""
fer_admin.py · Converteix un usuari ja registrat en administrador.

Ús:
    1. Registra't a la web amb el correu que vols fer servir d'administrador.
    2. Escriu aquest correu a EL_TEU_CORREU (a sota).
    3. Executa:   py fer_admin.py

Compte: no facis servir l'adreça pública de contacte de normes.html,
perquè qualsevol persona podria registrar-la abans que tu.
"""

import os
import sqlite3

# Posa aquí el correu amb el qual t'has registrat a la teva web
EL_TEU_CORREU = "admin@bancdetemps.cat"

# Mateixa base de dades que fa servir l'app (variable DATABASE o el banc_temps.db de la carpeta del projecte)
DB_PATH = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banc_temps.db"))

if not os.path.exists(DB_PATH):
    raise SystemExit(f"No existeix la base de dades ({DB_PATH}). Arrenca l'app una vegada perquè es creï.")

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
