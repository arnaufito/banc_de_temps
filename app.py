from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "clau_super_secreta_del_tdr"

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
        
        conn = sqlite3.connect("banc_temps.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nom FROM usuaris WHERE correu = ? AND contrasenya = ?", 
                       (correu_usuari, contrasenya_usuari))
        usuari = cursor.fetchone()
        conn.close()
        
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
    return render_template("mercat.html")

@app.route("/crear_oferta")
def crear_oferta():
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