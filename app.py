import sqlite3
import os
from flask import Flask, session, redirect, url_for, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "clau_super_secreta_del_tdr"

@app.context_processor
def injectar_saldo():
    if 'id_usuari' in session:
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        try:
            # Busquem el saldo real a la base de dades
            cursor.execute("SELECT saldo FROM usuaris WHERE id = ?", (session['id_usuari'],))
            resultat = cursor.fetchone()
            saldo_real = resultat[0] if (resultat and resultat[0] is not None) else 5.0
        except:
            saldo_real = 5.0
        conn.close()
        return dict(saldo=saldo_real) # Això envia {{ saldo }} a tots els HTMLs
    return dict(saldo=0.0)
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
# 3. ZONA PERSONAL
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
        
        try:
            cursor.execute("UPDATE usuaris SET nom = ?, ciutat = ?, descripcio = ? WHERE id = ?", 
                           (nou_nom, nova_ciutat, nova_descripcio, user_id))
        except sqlite3.OperationalError:
            cursor.execute("UPDATE usuaris SET nom = ?, ciutat = ? WHERE id = ?", 
                           (nou_nom, nova_ciutat, user_id))
                           
        conn.commit()
        session['nom'] = nou_nom
        
    # 1. Busquem les dades bàsiques i el SALDO REAL sempre a part
    cursor.execute("SELECT nom, correu, ciutat, saldo FROM usuaris WHERE id = ?", (user_id,))
    usuari_bd = cursor.fetchone()
    
    saldo_usuari = usuari_bd[3] if usuari_bd else 0.0
    
    # 2. Intentem buscar la descripció per separat perquè no trenqui el saldo
    try:
        cursor.execute("SELECT descripcio FROM usuaris WHERE id = ?", (user_id,))
        extres = cursor.fetchone()
        descripcio = extres[0] if extres else ""
    except sqlite3.OperationalError:
        descripcio = ""
        
    conn.close()
    
    usuari_complet = [
        usuari_bd[0] if usuari_bd else "Usuari",
        usuari_bd[1] if usuari_bd else "",
        usuari_bd[2] if usuari_bd else "No especificada",
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

@app.route("/transferencia", methods=["GET", "POST"])
def transferencia():
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # 1. AUTO-REPARACIÓ: Si algun usuari té el saldo trencat (NULL), li assignem 5.0h
    cursor.execute("UPDATE usuaris SET saldo = 5.0 WHERE saldo IS NULL")
    conn.commit()
    
    id_pagador = session['id_usuari']
    
    # Obtenim el saldo assegurant-nos que llegeix un número real
    cursor.execute("SELECT saldo FROM usuaris WHERE id = ?", (id_pagador,))
    resultat = cursor.fetchone()
    saldo_actual = resultat[0] if (resultat and resultat[0] is not None) else 5.0

    if request.method == "POST":
        # 2. NETEJA: Agafem el correu i li traiem els espais invisibles amb .strip()
        correu_destinatari = request.form.get("correu_destinatari", "").strip()
        
        try:
            hores = float(request.form.get("hores"))
        except ValueError:
            conn.close()
            return "<h3>Error: Les hores han de ser un número.</h3><br><a href='/transferencia'>Tornar</a>"
            
        if hores <= 0:
            conn.close()
            return "<h3>Error: Has d'enviar més de 0 hores.</h3><br><a href='/transferencia'>Tornar</a>"

        cursor.execute("SELECT id FROM usuaris WHERE correu = ?", (correu_destinatari,))
        destinatari = cursor.fetchone()
        
        if not destinatari:
            conn.close()
            # Ara et mostrarà exactament què ha buscat perquè vegis si hi havia alguna lletra malament
            return f"<h3>Error: No existeix el correu '{correu_destinatari}'. Comprova si està ben escrit.</h3><br><a href='/transferencia'>Tornar</a>"
            
        id_cobrador = destinatari[0]
        
        if id_pagador == id_cobrador:
            conn.close()
            return "<h3>Error: No pots pagar-te a tu mateix.</h3><br><a href='/transferencia'>Tornar</a>"
            
        if saldo_actual < hores:
            conn.close()
            return f"<h3>Error: No tens prou saldo (tens {saldo_actual}h).</h3><br><a href='/transferencia'>Tornar</a>"
            
        # 3. PAGAMENT: Executem el pagament matemàticament i guardem l'historial
        cursor.execute("UPDATE usuaris SET saldo = saldo - ? WHERE id = ?", (hores, id_pagador))
        cursor.execute("UPDATE usuaris SET saldo = saldo + ? WHERE id = ?", (hores, id_cobrador))
        cursor.execute("INSERT INTO transaccions (id_pagador, id_cobrador, hores) VALUES (?, ?, ?)", (id_pagador, id_cobrador, hores))
                       
        conn.commit()
        conn.close()
        
        return f"""
        <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
            <h2 style='color:green;'>✅ Pagament de {hores}h realitzat amb èxit!</h2>
            <br>
            <a href='/mercat' style='padding:10px 20px; background:blue; color:white; text-decoration:none; border-radius:5px;'>Tornar al mercat</a>
        </div>
        """
        
    conn.close()
    return render_template("transferencia.html", saldo=saldo_actual)
@app.route("/oferta/<int:id_oferta>")
def detall_oferta(id_oferta):
    if 'id_usuari' not in session:
        return redirect(url_for('login'))
        
    user_id = session['id_usuari']
    conn = sqlite3.connect("banc_temps.db")
    cursor = conn.cursor()
    
    # Fem servir LEFT JOIN. Així, si l'usuari creador va ser eliminat, l'oferta es continua veient.
    try:
        cursor.execute('''
            SELECT o.id, o.titol, o.descripcio, o.id_usuari, u.nom, u.ciutat, o.hores
            FROM ofertes o 
            LEFT JOIN usuaris u ON o.id_usuari = u.id 
            WHERE o.id = ?
        ''', (id_oferta,))
    except sqlite3.OperationalError:
        cursor.execute('''
            SELECT o.id, o.titol, o.descripcio, o.id_usuari, u.nom, u.ciutat, 1 as hores
            FROM ofertes o 
            LEFT JOIN usuaris u ON o.id_usuari = u.id 
            WHERE o.id = ?
        ''', (id_oferta,))
        
    oferta = cursor.fetchone()
    
    # Si per algun motiu l'usuari estava esborrat, posem noms per defecte perquè no falli l'HTML
    if oferta and oferta[4] is None:
        oferta = list(oferta)
        oferta[4] = "Usuari eliminat"
        oferta[5] = "Desconeguda"
        
    try:
        cursor.execute("SELECT saldo FROM usuaris WHERE id = ?", (user_id,))
        resultat = cursor.fetchone()
        saldo_usuari = resultat[0] if resultat and resultat[0] is not None else 5.0
    except sqlite3.OperationalError:
        saldo_usuari = 5.0
        
    conn.close()
    
    if not oferta:
        return "<h3>Aquesta oferta no existeix o ha estat eliminada.</h3><a href='/mercat'>Tornar al mercat</a>"
        
    return render_template("detall_oferta.html", oferta=oferta, saldo=saldo_usuari)
# ==========================================
# EXECUCIÓ DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)
