import sqlite3

conn = sqlite3.connect("banc_temps.db")
cursor = conn.cursor()

# Demanem tots els usuaris que hi ha a la taula
cursor.execute("SELECT * FROM usuaris")
usuaris = cursor.fetchall()

print("--- Usuaris a la Base de Dades ---")
if not usuaris:
    print("La base de dades està BUIDA!")
else:
    for u in usuaris:
        print(f"ID: {u[0]} | Nom: {u[1]} | Correu: {u[2]} | Contrasenya: {u[3]}")

conn.close()
