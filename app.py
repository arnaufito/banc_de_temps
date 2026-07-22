import sqlite3
import os
from flask import Flask, session, redirect, url_for, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash


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
        ciutat TEXT NOT NULL,  -- AFEGIM AQUESTA LÍNIA
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

    # Taula Missatges
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS missatges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_oferta INTEGER NOT NULL,
        id_remitent INTEGER NOT NULL,
        missatge TEXT NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_oferta) REFERENCES ofertes (id),
        FOREIGN KEY (id_remitent) REFERENCES usuaris (id)
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
        ciutat_usuari = request.form["ciutat"]
        
        # --- LA MÀGIA DE L'ENCRIPTACIÓ ---
        contrasenya_encriptada = generate_password_hash(contrasenya_usuari)
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        try:
            # Fixa't que ara desem 'contrasenya_encriptada', no la normal!
            cursor.execute("INSERT INTO usuaris (nom, correu, contrasenya, ciutat) VALUES (?, ?, ?, ?)", 
                           (nom_usuari, correu_usuari, contrasenya_encriptada, ciutat_usuari))
            conn.commit()
        except sqlite3.IntegrityError:
            return "<h3>Aquest correu ja està registrat!</h3><a href='/registre'>Torna a provar-ho</a>"
        finally:
            conn.close()
            
        return redirect(url_for('login'))
    return render_template("registre.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('inici'))
@app.route("/login", methods=["GET", "POST"])
def login():
    # 1. Si enviem el formulari (POST)
    if request.method == "POST":
        correu_usuari = request.form["correu"]
        contrasenya_usuari = request.form["contrasenya"]

        print(f"Intentant entrar amb: {correu_usuari}")
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        # Busquem l'usuari NOMÉS pel correu per obtenir la seva contrasenya encriptada
        cursor.execute("SELECT id, nom, contrasenya FROM usuaris WHERE correu = ?", (correu_usuari,))
        usuari = cursor.fetchone()
        conn.close()
        
        # Comprovem si l'usuari existeix I si la contrasenya coincideix amb el hash
        if usuari and check_password_hash(usuari[2], contrasenya_usuari):
            session["id_usuari"] = usuari[0]
            session["nom"] = usuari[1]
            print(f"Login correcte per a l'usuari: {usuari[1]}")
            return redirect(url_for('mercat')) 
        else:
            print("Login fallit: Correu o contrasenya incorrectes")
            return "<h3>Correu o contrasenya incorrectes!</h3><a href='/login'>Torna a provar-ho</a>"

    # 2. Si només entrem a la web (GET)
    return render_template("login.html")
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

# ==========================================
# 3. ZONA PERSONAL I CONFIANÇA
# ==========================================
@app.route("/perfil")
def perfil():
    return render_template("perfil.html")

# 1. Vista general de xats (Quan cliques "Xats" a la barra superior)
@app.route("/xat")
def xat():
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, titol FROM ofertes")
    chats = cursor.fetchall()
    conn.close()
    
    # S'han d'enviar exactament aquestes 5 variables:
    return render_template("xat.html", chats=chats, missatges=None, id_oferta=None, titol=None, el_meu_id=session['id_usuari'])
# 2. Xat seleccionat d'una oferta específica (Quan cliques un xat concret de la llista)
@app.route("/xat/<int:id_oferta>", methods=["GET", "POST"])
def xat_concret(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    el_meu_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Llista de xats per a la barra esquerra
    cursor.execute("SELECT id, titol FROM ofertes")
    chats = cursor.fetchall()
    
    # Títol de l'oferta actual
    cursor.execute("SELECT titol FROM ofertes WHERE id = ?", (id_oferta,))
    oferta = cursor.fetchone()
    titol_oferta = oferta[0] if oferta else "Oferta"
    
    if request.method == "POST":
        text_missatge = request.form["missatge"]
        cursor.execute("INSERT INTO missatges (id_oferta, id_remitent, missatge) VALUES (?, ?, ?)",
                       (id_oferta, el_meu_id, text_missatge))
        conn.commit()
        return redirect(url_for('xat_concret', id_oferta=id_oferta))
        
    cursor.execute('''
        SELECT u.nom, m.missatge, m.id_remitent 
        FROM missatges m
        JOIN usuaris u ON m.id_remitent = u.id
        WHERE m.id_oferta = ?
        ORDER BY m.id ASC
    ''', (id_oferta,))
    missatges = cursor.fetchall()
    conn.close()
    
    return render_template("xat.html", chats=chats, missatges=missatges, id_oferta=id_oferta, titol=titol_oferta, el_meu_id=el_meu_id)

@app.route("/transferencia")
def transferencia():
    return render_template("transferencia.html")

@app.route("/historial")
def historial():
    return render_template("historial.html")
@app.route("/oferta/<int:id_oferta>")
def detall_oferta(id_oferta):
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Ara fem un JOIN per llegir també el nom de l'usuari (u.nom)
    cursor.execute('''
        SELECT o.id, o.titol, o.descripcio, o.hores, u.nom 
        FROM ofertes o
        JOIN usuaris u ON o.id_usuari = u.id
        WHERE o.id = ?
    ''', (id_oferta,))
    
    oferta = cursor.fetchone()
    conn.close()
    
    return render_template("detall_oferta.html", oferta=oferta)
# ==========================================
# EXECUCIÓ DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)
#prova
