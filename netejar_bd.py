import os
import sqlite3

# Mateixa base de dades que fa servir l'app (variable DATABASE o el banc_temps.db de la carpeta del projecte)
DB_PATH = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banc_temps.db"))

def netejar_base_de_dades():
    # Operació destructiva: demanem confirmació
    resposta = input(f"Això ESBORRARÀ TOTES LES DADES de {DB_PATH}. Escriu SI per continuar: ")
    if resposta.strip().upper() != "SI":
        print("Cancel·lat. No s'ha esborrat res.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Netejant la base de dades...")

    # Esborrem les dades de totes les taules (mantenint l'estructura)
    try:
        cursor.execute("DELETE FROM missatges")
        cursor.execute("DELETE FROM transaccions")
        cursor.execute("DELETE FROM ofertes")
        cursor.execute("DELETE FROM usuaris")
        conn.commit()
        print("S'han buidat totes les taules correctament!")
        print("Recorda: l'administrador es torna a crear en arrencar l'app si tens ADMIN_CORREU i ADMIN_CONTRASENYA definits.")
    except sqlite3.OperationalError as e:
        print(f"Avís: No s'ha pogut trobar alguna taula o s'ha produït un error: {e}")

    conn.close()

if __name__ == "__main__":
    netejar_base_de_dades()