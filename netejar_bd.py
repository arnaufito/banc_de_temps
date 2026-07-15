import sqlite3

conn = sqlite3.connect("banc_temps.db")
cursor = conn.cursor()

# Això esborra totes les files de la taula ofertes
cursor.execute("DELETE FROM ofertes") 

conn.commit()
conn.close()

print("Base de dades neta! Ja no queden ofertes.")
