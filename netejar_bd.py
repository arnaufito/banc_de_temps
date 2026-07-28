import sqlite3

def netejar_base_de_dades():
    # Connectem a la base de dades
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    print("Netejant la base de dades...")
    
    # Esborrem les dades de totes les taules (mantenint l'estructura)
    try:
        cursor.execute("DELETE FROM missatges")
        cursor.execute("DELETE FROM ofertes")
        cursor.execute("DELETE FROM usuaris")
        conn.commit()
        print("S'han buidat totes les taules correctament!")
    except sqlite3.OperationalError as e:
        print(f"Avís: No s'ha pogut trobar alguna taula o s'ha produït un error: {e}")
    
    conn.close()

if __name__ == "__main__":
    netejar_base_de_dades()