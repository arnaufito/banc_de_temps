import sqlite3
from flask import Flask, session, redirect, url_for, request, render_template

app = Flask(__name__)
app.secret_key = "clau_super_secreta_del_tdr"

# --- FUNCIÓ D'INICIALITZACIÓ ---
def inicialitzar_bd():
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Taula Usuaris
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuaris (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        correu TEXT UNIQUE NOT NULL,
        contrasenya TEXT NOT NULL,
        saldo REAL DEFAULT 5.0
    )
    ''')
    
    # Taula Ofertes (Hem afegit 'hores'!)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ofertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuari INTEGER NOT NULL,
        titol TEXT NOT NULL,
        descripcio TEXT,
        hores REAL NOT NULL,
        FOREIGN KEY (id_usuari) REFERENCES usuaris (id)
    )
    ''')
    
    # Taula Transaccions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transaccions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pagador INTEGER NOT NULL,
        id_cobrador INTEGER NOT NULL,
        hores REAL NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_pagador) REFERENCES usuaris (id),
        FOREIGN KEY (id_cobrador) REFERENCES usuaris (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Executem la funció només en engegar l'app
inicialitzar_bd()
# ==========================================
# 1. ZONA PÚBLICA I ACCÉS
# ==========================================
@app.route("/")
def inici():
    # Ara, l'arrel de la web ensenya directament el teu index.html bonic
    if 'nom' in session:
        # Si ja està connectat, el portem al mercat directament
        return redirect(url_for('mercat'))
    return render_template("index.html")
@app.route("/registre", methods=["GET", "POST"])
def registre():
    if request.method == "POST":
        nom_usuari = request.form["nom"]
        correu_usuari = request.form["correu"]
        contrasenya_usuari = request.form["contrasenya"]
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO usuaris (nom, correu, contrasenya) VALUES (?, ?, ?)", 
                           (nom_usuari, correu_usuari, contrasenya_usuari))
            conn.commit()
        except sqlite3.IntegrityError:
            return "<h3>Aquest correu ja està registrat!</h3><a href='/registre'>Torna a provar-ho</a>"
        finally:
            conn.close()
            
        return redirect(url_for('login'))
    return render_template("registre.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # 1. Si enviem el formulari (POST)
    if request.method == "POST":
        correu_usuari = request.form["correu"]
        contrasenya_usuari = request.form["contrasenya"]

        print(f"Intentant entrar amb: {correu_usuari} i {contrasenya_usuari}")
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nom FROM usuaris WHERE correu = ? AND contrasenya = ?", 
                       (correu_usuari, contrasenya_usuari))
        usuari = cursor.fetchone()
        conn.close()
        
        print(f"Resultat de la base de dades: {usuari}")

        if usuari:
            session["id_usuari"] = usuari[0]
            session["nom"] = usuari[1]
            return redirect(url_for('mercat')) 
        else:
            return "<h3>Correu o contrasenya incorrectes!</h3><a href='/login'>Torna a provar-ho</a>"

    # 2. Si només entrem a la web (GET) - AQUEST RETURN HA D'ESTAR AL MATEIX NIVELL QUE L'IF
    return render_template("login.html")
def logout():
    session.clear()
    return redirect(url_for('inici'))

# ==========================================
# 2. ZONA PRIVADA (MERCAT I OFERTES)
# ==========================================
@app.route("/mercat")
def mercat():
    # 1. Connectem a la base de dades
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # 2. Llegim totes les ofertes
    cursor.execute("SELECT id, titol, descripcio, hores FROM ofertes")
    ofertes = cursor.fetchall()
    
    # 3. LÍNIA DE RADIOGRAFIA (per veure què llegeix realment)
    print("🔴 ATENCIÓ! Les ofertes a la BD són:", ofertes)
    
    # 4. Tanquem i enviem a l'HTML
    conn.close()
    return render_template("mercat.html", ofertes=ofertes)
@app.route("/crear_oferta", methods=["GET", "POST"])
def crear_oferta():
    # Comprovem si l'usuari està loguejat
    if 'id_usuari' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        # Recollim les dades del formulari
        titol = request.form["titol"]
        descripcio = request.form["descripcio"]
        hores = request.form["hores"]
        autor_id = session["id_usuari"] # Agafem l'ID de la sessió
        
        # Guardem a la BD
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        # Inserim les dades a la taula 'ofertes'
        # Assegura't que la taula té aquestes columnes exactes
        cursor.execute("INSERT INTO ofertes (titol, descripcio, hores, id_usuari) VALUES (?, ?, ?, ?)", 
                       (titol, descripcio, hores, autor_id))
        
        conn.commit()
        conn.close()
        
        # Redirigim al mercat un cop guardat
        return redirect(url_for('mercat')) 
        
    # Si és un GET, mostrem el formulari
    return render_template("crear_oferta.html")

@app.route("/detall_oferta")
def detall_oferta():
    return render_template("detall_oferta.html")

# ==========================================
# 3. ZONA PERSONAL I CONFIANÇA
# ==========================================
@app.route("/perfil")
def perfil():
    return render_template("perfil.html")

@app.route("/xat")
def xat():
    return render_template("xat.html")

@app.route("/transferencia")
def transferencia():
    return render_template("transferencia.html")

@app.route("/historial")
def historial():
    return render_template("historial.html")

# ==========================================
# EXECUCIÓ DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)

@app.route("/oferta/<int:id_oferta>")
def detall_oferta(id_oferta):
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, titol, descripcio, hores FROM ofertes WHERE id = ?", (id_oferta,))
    oferta = cursor.fetchone()
    conn.close()
    return render_template("detall_oferta.html", oferta=oferta)