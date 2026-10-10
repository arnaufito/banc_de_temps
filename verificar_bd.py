import os
import sqlite3

# Mateixa base de dades que fa servir l'app (variable DATABASE o el banc_temps.db de la carpeta del projecte)
DB_PATH = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banc_temps.db"))

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Només demanem les dades segures, excloent la contrasenya
cursor.execute("SELECT id, nom, correu, saldo, es_admin FROM usuaris")
usuaris = cursor.fetchall()

print("--- Usuaris a la Base de Dades ---")
if not usuaris:
    print("La base de dades està BUIDA!")
else:
    for u in usuaris:
        rol = "ADMIN" if u[4] == 1 else "Usuari"
        print(f"ID: {u[0]} | Nom: {u[1]} | Correu: {u[2]} | Saldo: {u[3]}h | Rol: {rol}")

conn.close()