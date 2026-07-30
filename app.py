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

# Taula Missatges per al xat
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS missatges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_oferta INTEGER NOT NULL,
        id_remitent INTEGER NOT NULL,
        missatge TEXT NOT NULL
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
        # AIXÒ ÉS NOU: Imprimirà a la terminal què envia l'HTML exactament
        print("DADES REBUDES DEL NAVEGADOR:", request.form)
        
        # Canviem la manera de llegir-ho utilitzant .get() perquè no doni Error 400
        nom_usuari = request.form.get("nom")
        correu_usuari = request.form.get("correu")
        ciutat_usuari = request.form.get("ciutat") 
        contrasenya_usuari = request.form.get("contrasenya")
        
        # Si per algun motiu la ciutat segueix sense arribar, li posem un valor per defecte
        if not ciutat_usuari:
            ciutat_usuari = "No especificada"
            
        contrasenya_encriptada = generate_password_hash(contrasenya_usuari)
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO usuaris (nom, correu, contrasenya, ciutat) VALUES (?, ?, ?, ?)", 
                           (nom_usuari, correu_usuari, contrasenya_encriptada, ciutat_usuari))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "<h3>Aquest correu ja està registrat!</h3><a href='/registre'>Torna-ho a provar</a>"
            
        conn.close()
        return redirect(url_for('login'))
        
    return render_template("registre.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('inici'))
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correu_usuari = request.form.get("correu")
        contrasenya_usuari = request.form.get("contrasenya")
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        # Demanem la ID, el nom i la contrasenya encriptada de l'usuari
        cursor.execute("SELECT id, nom, contrasenya FROM usuaris WHERE correu = ?", (correu_usuari,))
        usuari = cursor.fetchone()
        conn.close()
        
        # usuari[0] és la ID, usuari[1] és el nom, usuari[2] és la contrasenya encriptada
        # Utilitzem check_password_hash per traduir i comparar
        if usuari and check_password_hash(usuari[2], contrasenya_usuari):
            # Si la contrasenya és correcta, creem la sessió
            session['id_usuari'] = usuari[0]
            session['nom'] = usuari[1]
            return redirect(url_for('mercat'))
        else:
            # Si falla, mostrem un error
            return "<h3>Correu o contrasenya incorrectes.</h3><br><a href='/login'>Torna-ho a provar</a>"
            
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
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    user_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    if request.method == "POST":
        nou_nom = request.form.get("nom")
        nova_ciutat = request.form.get("ciutat")
        nova_descripcio = request.form.get("descripcio", "")
        
        # Intentem actualitzar incloent la descripció
        try:
            cursor.execute("UPDATE usuaris SET nom = ?, ciutat = ?, descripcio = ? WHERE id = ?", 
                           (nou_nom, nova_ciutat, nova_descripcio, user_id))
        except sqlite3.OperationalError:
            # Si la columna descripcio encara no existeix a la BD vella, actualitzem només nom i ciutat
            cursor.execute("UPDATE usuaris SET nom = ?, ciutat = ? WHERE id = ?", 
                           (nou_nom, nova_ciutat, user_id))
                           
        conn.commit()
        session['nom'] = nou_nom
        
    # Busquem les dades de l'usuari de manera segura
    cursor.execute("SELECT nom, correu, ciutat FROM usuaris WHERE id = ?", (user_id,))
    usuari_basic = cursor.fetchone()
    
    # Intentem buscar si té descripció i saldo
    try:
        cursor.execute("SELECT descripcio, saldo FROM usuaris WHERE id = ?", (user_id,))
        extres = cursor.fetchone()
        descripcio = extres[0] if extres and extres[0] else ""
        saldo_usuari = extres[1] if extres and len(extres) > 1 and extres[1] is not None else 5.0
    except sqlite3.OperationalError:
        descripcio = ""
        saldo_usuari = 5.0
        
    conn.close()
    
    # Creem una estructura de dades neta per enviar a l'HTML
    # usuari[0] = nom, usuari[1] = correu, usuari[2] = ciutat, usuari[3] = descripcio
    usuari_complet = [
        usuari_basic[0] if usuari_basic else "Usuari",
        usuari_basic[1] if usuari_basic else "",
        usuari_basic[2] if usuari_basic else "No especificada",
        descripcio
    ]
    
    return render_template("perfil.html", usuari=usuari_complet, saldo=saldo_usuari)
# 1. Vista general de xats (Manté el teu nom original def xat())
@app.route("/xat")
def xat():
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, titol FROM ofertes")
    chats = cursor.fetchall()
    conn.close()
    
    return render_template("xat.html", chats=chats, missatges=None, id_oferta=None, titol=None, el_meu_id=session['id_usuari'])


# 2. Xat seleccionat d'una oferta específica (Utilitza def xat_concret() per no xocar amb de /xat)
@app.route("/xat/<int:id_oferta>", methods=["GET", "POST"])
def xat_concret(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    el_meu_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Si l'usuari envia un missatge nou, fem servir .get() per evitar cap tipus d'error 400
    if request.method == "POST":
        text_missatge = request.form.get("missatge")
        if text_missatge:
            cursor.execute("INSERT INTO missatges (id_oferta, id_remitent, missatge) VALUES (?, ?, ?)",
                           (id_oferta, el_meu_id, text_missatge))
            conn.commit()
        return redirect(url_for('xat_concret', id_oferta=id_oferta))
        
    # Llista de xats per a la barra esquerra
    cursor.execute("SELECT id, titol FROM ofertes")
    chats = cursor.fetchall()
    
    # Títol de l'oferta actual
    cursor.execute("SELECT titol FROM ofertes WHERE id = ?", (id_oferta,))
    oferta = cursor.fetchone()
    titol_oferta = oferta[0] if oferta else "Oferta"
    
    # Missatges del xat
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


# 3. Ruta de la paperera per esborrar un xat sencer
@app.route("/eliminar_xat/<int:id_oferta>")
def eliminar_xat(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM missatges WHERE id_oferta = ?", (id_oferta,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('xat'))

@app.route("/transferencia")
def transferencia():
    return render_template("transferencia.html")

# 1. Mostrar l'historial amb les meves ofertes
@app.route("/historial")
def historial():
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    user_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Busquem només les ofertes creades per l'usuari actual
    # (Suposant que a la teva taula "ofertes" tens una columna "id_usuari" o "id_creador". 
    # Si la teva columna es diu diferent, només has de canviar "id_usuari = ?" pel teu nom).
    cursor.execute("SELECT id, titol, descripcio FROM ofertes WHERE id_usuari = ?", (user_id,))
    les_meves_ofertes = cursor.fetchall()
    
    # Obtenim el saldo per a la barra de navegació
    try:
        cursor.execute("SELECT saldo FROM usuaris WHERE id = ?", (user_id,))
        resultat = cursor.fetchone()
        saldo_usuari = resultat[0] if resultat and resultat[0] is not None else 5.0
    except sqlite3.OperationalError:
        saldo_usuari = 5.0
        
    conn.close()
    
    return render_template("historial.html", ofertes=les_meves_ofertes, saldo=saldo_usuari)

# 2. La ruta per eliminar una oferta pròpia (Botó paperera)
@app.route("/eliminar_oferta/<int:id_oferta>")
def eliminar_oferta(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Esborrem l'oferta
    cursor.execute("DELETE FROM ofertes WHERE id = ?", (id_oferta,))
    # Esborrem també els missatges d'aquella oferta perquè no quedin penjats a la BD
    cursor.execute("DELETE FROM missatges WHERE id_oferta = ?", (id_oferta,))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('historial'))
@app.route("/oferta/<int:id_oferta>")
def detall_oferta(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    user_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Busquem l'oferta i les dades de l'usuari que la va crear
    try:
        cursor.execute('''
            SELECT o.id, o.titol, o.descripcio, o.id_usuari, u.nom, u.ciutat, o.hores
            FROM ofertes o 
            JOIN usuaris u ON o.id_usuari = u.id 
            WHERE o.id = ?
        ''', (id_oferta,))
    except sqlite3.OperationalError:
        cursor.execute('''
            SELECT o.id, o.titol, o.descripcio, o.id_usuari, u.nom, u.ciutat, 1 as hores
            FROM ofertes o 
            JOIN usuaris u ON o.id_usuari = u.id 
            WHERE o.id = ?
        ''', (id_oferta,))
        
    oferta = cursor.fetchone()
    
    # Obtenim el saldo actual de qui està navegant per la barra superior
    try:
        cursor.execute("SELECT saldo FROM usuaris WHERE id = ?", (user_id,))
        resultat = cursor.fetchone()
        saldo_usuari = resultat[0] if resultat and resultat[0] is not None else 5.0
    except sqlite3.OperationalError:
        saldo_usuari = 5.0
        
    conn.close()
    
    if not oferta:
        return "<h3>Aquesta oferta no existeix o ha estat eliminada.</h3><a href='/mercat'>Tornar al mercat</a>"
        
    # Carreguem directament la teva plantilla detall_oferta.html
    return render_template("detall_oferta.html", oferta=oferta, saldo=saldo_usuari)
# ==========================================
# EXECUCIÓ DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)
