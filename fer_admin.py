import sqlite3

# Posa aquí el correu amb el qual et registres a la teva web
EL_TEU_CORREU = "elteucorreu@exemple.cat"

conn = sqlite3.connect("banc_temps.db")
cursor = conn.cursor()

# Actualitzem l'usuari i li posem es_admin = 1
cursor.execute("UPDATE usuaris SET es_admin = 1 WHERE correu = ?", (EL_TEU_CORREU,))
conn.commit()
conn.close()

print(f"✅ L'usuari amb correu {EL_TEU_CORREU} ara és ADMINISTRADOR SUPREM.")