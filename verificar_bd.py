import sqlite3

conn = sqlite3.connect("banc_temps.db")
cursor = conn.cursor()

# Nomes demanem les dades segures, excloent la contrasenya
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