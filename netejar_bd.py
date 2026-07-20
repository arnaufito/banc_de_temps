import sqlite3

# 1. Ens connectem al teu arxiu de la base de dades
conn = sqlite3.connect("banc_temps.db")
cursor = conn.cursor()

# 2. Executem l'ordre per esborrar absolutament tot el que hi ha a la taula ofertes
cursor.execute("DELETE FROM ofertes") 

# 3. Guardem els canvis definitivament (el famós commit!)
conn.commit()

# 4. Tanquem la connexió
conn.close()

print("✅ Base de dades completament neta! Totes les ofertes s'han esborrat.")