"""
verificar_bd.py · Llista els usuaris registrats a la base de dades (mai en mostra les contrasenyes).
Només llegeix: no canvia res.

Ús:   py verificar_bd.py
"""

import os
import sqlite3

# Mateixa base de dades que fa servir l'app (variable DATABASE o el banc_temps.db de la carpeta del projecte)
DB_PATH = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banc_temps.db"))

# Si el fitxer no existeix, sqlite3 en crearia un de buit; ho evitem avisant abans
if not os.path.exists(DB_PATH):
    raise SystemExit(f"No existeix la base de dades ({DB_PATH}). Arrenca l'app una vegada perquè es creï.")

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
        # u = (id, nom, correu, saldo, es_admin); es_admin val 1 per als administradors
        rol = "ADMIN" if u[4] == 1 else "Usuari"
        print(f"ID: {u[0]} | Nom: {u[1]} | Correu: {u[2]} | Saldo: {u[3]}h | Rol: {rol}")

conn.close()