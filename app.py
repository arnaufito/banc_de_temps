"""
Banc de Temps · aplicació web feta amb Flask i SQLite
=====================================================

Aquest fitxer conté tot el servidor: rutes, base de dades i validacions.
Les plantilles HTML són a templates/ i els estils a static/style.css.

ÍNDEX
-----
  1. Configuració ............ constants, clau secreta, Flask i proxy
  2. Base de dades ........... connexió, transaccions i creació de taules
  3. Sessió i seguretat ...... límit d'intents, capçaleres i decoradors d'accés
  4. Ajudants de validació ... lectura i comprovació dels formularis
  5. Zona pública i accés .... inici, normes, registre, login i logout
  6. Mercat i ofertes ........ llistat, crear, detall i eliminar ofertes
  7. Zona personal ........... perfil, historial i pagaments
  8. Xat ..................... converses entre comprador i venedor
  9. Administració ........... panell d'admin i expulsió d'usuaris
 10. Gestió d'errors ......... pàgines d'error 400, 403, 404, 405, 413 i 500

Variables d'entorn (totes opcionals; vegeu README.md):
  SECRET_KEY, DATABASE, ADMIN_CORREU, ADMIN_CONTRASENYA,
  PROXY, COOKIES_SEGURES, FLASK_DEBUG
"""

import math
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import generate_password_hash, check_password_hash


# =============================================================================
# 1. CONFIGURACIÓ
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ruta absoluta: no depèn de la carpeta des d'on s'executa el servidor
DB_PATH = os.environ.get("DATABASE", os.path.join(BASE_DIR, "banc_temps.db"))

# Poblacions que es poden triar al registre i al perfil
CIUTATS = [
    "Calaf", "Calonge de Segarra", "Els Prats de Rei", "Sant Martí Sesgueioles", "Sant Pere Sallavinera",
    "Castellfollit de Riubregós", "Pujalt", "Argençola", "Copons", "Jorba",
    "Òdena", "Rubió", "Igualada", "Santa Maria de Miralles", "Vilanova del Camí",
    "Santa Margarida de Montbui", "Cervera", "Sant Guim de Freixenet", "Sant Ramon", "Les Oluges",
    "Estaràs", "Ribera d'Ondara", "Torà", "Ivorra", "Massoteres",
    "Guissona", "La Molsosa", "Pinós", "Riner", "Sanahuja",
    "Olius", "Solsona", "Castellfollit del Boix", "Fonollosa", "Rajadell",
    "Sant Salvador de Guardiola", "Manresa", "El Pont de Vilomara i Rocafort", "Navarcles", "Sant Fruitós de Bages",
    "Altres"
]

# Categories de les ofertes: (valor que es desa a la BD, text que es mostra)
CATEGORIES = [
    ("Classes i Formació", "📚 Classes i Formació (Idiomes, repàs escolar, música...)"),
    ("Cures i Acompanyament", "🤝 Cures i Acompanyament (Cangur, passejar mascotes, gent gran...)"),
    ("Llar i Bricolatge", "🛠️ Llar i Bricolatge (Petites reparacions, neteja, muntar mobles...)"),
    ("Informàtica i Tecnologia", "💻 Informàtica i Tecnologia (Reparació d'ordinadors, ajuda amb el mòbil...)"),
    ("Assessorament i Gestions", "📝 Assessorament i Gestions (Tràmits, traduccions, disseny...)"),
    ("Oci i Esports", "⚽ Oci i Esports (Entrenament personal, rutes, jocs de taula...)"),
    ("Bellesa i Benestar", "💆 Bellesa i Benestar (Tallar els cabells, massatges, estètica...)"),
    ("Art i Creativitat", "🎨 Art i Creativitat (Dibuix, fotografia, manualitats...)"),
    ("Altres", "✨ Altres")
]
CATEGORIES_VALIDES = {c[0] for c in CATEGORIES}

# Límits d'hores per oferta i per pagament
MAX_HORES_OFERTA = 50
MAX_HORES_TRANSFERENCIA = 1000

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def carregar_clau_secreta():
    """SECRET_KEY de l'entorn; si no hi és, se'n genera una d'aleatòria i es guarda
    a .secret_key (així no hi ha cap clau escrita al codi i les sessions sobreviuen)."""
    clau = os.environ.get("SECRET_KEY")
    if clau:
        return clau
    cami = os.path.join(BASE_DIR, ".secret_key")
    try:
        # O_EXCL: només un procés pot crear el fitxer (evita que dos workers de Gunicorn
        # generin claus diferents a la primera arrencada)
        fd = os.open(cami, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        for _ in range(50):  # pot ser que un altre worker l'estigui escrivint ara mateix
            with open(cami) as f:
                clau = f.read().strip()
            if clau:
                return clau
            time.sleep(0.1)
        raise RuntimeError("El fitxer .secret_key és buit. Esborra'l i torna a arrencar l'app.")
    clau = secrets.token_hex(32)
    with os.fdopen(fd, "w") as f:
        f.write(clau)
    return clau


app = Flask(__name__)
app.secret_key = carregar_clau_secreta()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Posa COOKIES_SEGURES=1 quan la web estigui servida per HTTPS
    SESSION_COOKIE_SECURE=os.environ.get("COOKIES_SEGURES") == "1",
    MAX_CONTENT_LENGTH=64 * 1024
)

if os.environ.get("PROXY") == "1":  # darrere d'un proxy (Render, Railway...)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


# =============================================================================
# 2. BASE DE DADES
# =============================================================================
def get_db():
    """Retorna la connexió SQLite d'aquesta petició (se'n crea una la primera vegada)."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def tancar_db(_exc):
    """Tanca la connexió a la BD quan acaba la petició."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaccio(db):
    """Transacció atòmica: o es fa tot o no es fa res."""
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise


def afegir_columna(cur, taula, columna, definicio):
    """Afegeix una columna a una taula només si encara no existeix (migració suau)."""
    columnes = [f[1] for f in cur.execute(f"PRAGMA table_info({taula})")]
    if columna not in columnes:
        cur.execute(f"ALTER TABLE {taula} ADD COLUMN {columna} {definicio}")


def inicialitzar_bd():
    """Crea les taules i índexs si no existeixen i, si hi ha ADMIN_CORREU i
    ADMIN_CONTRASENYA, crea l'usuari administrador."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cur = conn.cursor()

    # Si la BD és d'una versió molt antiga (columna cost_hores), no té sentit continuar: avisem clarament
    if "cost_hores" in [f[1] for f in cur.execute("PRAGMA table_info(ofertes)")]:
        conn.close()
        raise RuntimeError("El fitxer banc_temps.db és d'una versió antiga i és incompatible. "
                           "Esborra'l i torna a arrencar l'app: es crearà de nou amb l'estructura correcta.")

    # Taules
    cur.execute('''CREATE TABLE IF NOT EXISTS usuaris (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        correu TEXT UNIQUE NOT NULL,
        contrasenya TEXT NOT NULL,
        ciutat TEXT NOT NULL DEFAULT 'No especificada',
        saldo REAL NOT NULL DEFAULT 5.0,
        es_admin INTEGER NOT NULL DEFAULT 0,
        descripcio TEXT DEFAULT '')''')
    cur.execute('''CREATE TABLE IF NOT EXISTS ofertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuari INTEGER NOT NULL,
        titol TEXT NOT NULL,
        descripcio TEXT,
        hores REAL NOT NULL,
        categoria TEXT NOT NULL DEFAULT 'Altres')''')
    cur.execute('''CREATE TABLE IF NOT EXISTS transaccions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pagador INTEGER NOT NULL,
        id_cobrador INTEGER NOT NULL,
        hores REAL NOT NULL,
        concepte TEXT DEFAULT '',
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS missatges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_oferta INTEGER NOT NULL,
        id_remitent INTEGER NOT NULL,
        id_client INTEGER,
        missatge TEXT NOT NULL)''')

    # Columnes afegides en versions posteriors (per a bases de dades ja existents)
    afegir_columna(cur, "usuaris", "ciutat", "TEXT NOT NULL DEFAULT 'No especificada'")
    afegir_columna(cur, "usuaris", "es_admin", "INTEGER NOT NULL DEFAULT 0")
    afegir_columna(cur, "usuaris", "descripcio", "TEXT DEFAULT ''")
    afegir_columna(cur, "ofertes", "categoria", "TEXT NOT NULL DEFAULT 'Altres'")
    afegir_columna(cur, "transaccions", "concepte", "TEXT DEFAULT ''")
    afegir_columna(cur, "missatges", "id_client", "INTEGER")

    # Índexs per accelerar les consultes més habituals
    cur.execute("CREATE INDEX IF NOT EXISTS idx_missatges_xat ON missatges (id_oferta, id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ofertes_usuari ON ofertes (id_usuari)")

    # Administrador inicial (només si es defineixen les dues variables d'entorn)
    adm_correu = (os.environ.get("ADMIN_CORREU") or "").strip().lower()
    adm_pass = os.environ.get("ADMIN_CONTRASENYA") or ""
    if adm_correu and len(adm_pass) >= 8:
        existeix = cur.execute("SELECT 1 FROM usuaris WHERE correu = ?", (adm_correu,)).fetchone()
        if not existeix:
            try:
                cur.execute(
                    "INSERT INTO usuaris (nom, correu, contrasenya, ciutat, es_admin) VALUES (?, ?, ?, ?, 1)",
                    ("Administrador", adm_correu, generate_password_hash(adm_pass), "Altres")
                )
            except sqlite3.IntegrityError:
                pass  # un altre worker de gunicorn l'ha creat just ara

    conn.commit()
    conn.close()


inicialitzar_bd()


# =============================================================================
# 3. SESSIÓ I SEGURETAT
# =============================================================================

# --- Límit d'intents (en memòria: clau -> cua de moments en què s'ha intentat) ---
_intents = defaultdict(deque)


def massa_intents(clau, maxim, finestra):
    """True si per a aquesta clau ja hi ha 'maxim' intents dins els últims 'finestra' segons."""
    ara = time.time()
    cua = _intents.get(clau, ())  # .get(): consultar no crea entrades noves
    while cua and ara - cua[0] > finestra:
        cua.popleft()
    return len(cua) >= maxim


def registrar_intent(clau):
    """Anota un intent (fallit) per a aquesta clau."""
    ara = time.time()
    if len(_intents) > 1000:  # neteja les entrades caducades (la finestra més llarga és 1 h)
        for k, q in list(_intents.items()):
            if not q or ara - q[-1] > 3600:
                _intents.pop(k, None)
    _intents[clau].append(ara)


# --- Abans i després de cada petició ---
@app.before_request
def abans_de_cada_peticio():
    """Carrega l'usuari de la sessió a g.usuari (o None si no ha iniciat sessió)."""
    if request.endpoint == "static":
        return
    g.usuari = None

    id_usuari = session.get("id_usuari")
    if id_usuari is not None:
        fila = get_db().execute(
            "SELECT id, nom, es_admin, saldo FROM usuaris WHERE id = ?", (id_usuari,)).fetchone()
        if fila is None:  # l'usuari ha estat eliminat: tanquem la sessió
            session.clear()
            return redirect(url_for("login"))
        g.usuari = {"id": fila["id"], "nom": fila["nom"],
                    "es_admin": bool(fila["es_admin"]), "saldo": round(fila["saldo"], 2)}


@app.after_request
def capcaleres_seguretat(resp):
    """Afegeix capçaleres de seguretat a totes les respostes (i evita que es guardin a la memòria cau)."""
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
    if request.endpoint != "static":
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.context_processor
def injectar_comu():
    """Variables disponibles a totes les plantilles: jo, saldo, CIUTATS i CATEGORIES."""
    usuari = getattr(g, "usuari", None)
    return dict(jo=usuari, saldo=usuari["saldo"] if usuari else 0.0,
                CIUTATS=CIUTATS, CATEGORIES=CATEGORIES)


# --- Decoradors d'accés ---
def login_required(f):
    """Només deixa passar usuaris que han iniciat sessió; la resta van al login."""
    @wraps(f)
    def embolcall(*args, **kwargs):
        if g.usuari is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return embolcall


def admin_required(f):
    """Només deixa passar administradors (si no ho són: error 403)."""
    @wraps(f)
    def embolcall(*args, **kwargs):
        if g.usuari is None:
            return redirect(url_for("login"))
        if not g.usuari["es_admin"]:
            abort(403)
        return f(*args, **kwargs)
    return embolcall


# =============================================================================
# 4. AJUDANTS DE VALIDACIÓ
# =============================================================================
def camp(nom):
    """Valor d'un camp del formulari, sense espais als extrems ('' si no hi és)."""
    return (request.form.get(nom) or "").strip()


def llegir_hores(valor, maxim):
    """Converteix el text a hores amb 2 decimals; None si no és un número entre 0.01 i 'maxim'."""
    try:
        h = round(float(valor), 2)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(h) or h < 0.01 or h > maxim:
        return None
    return h


def a_enter(valor):
    """Converteix a enter; None si no es pot."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def mostrar_errors(errors):
    """Mostra cada error de la llista com a missatge vermell (flash 'danger')."""
    for e in errors:
        flash(e, "danger")


# =============================================================================
# 5. ZONA PÚBLICA I ACCÉS
# =============================================================================
@app.route("/")
def inici():
    """Pàgina d'inici."""
    return render_template("index.html")


@app.route("/normes")
def normes():
    """Normes d'ús de la comunitat."""
    return render_template("normes.html")


@app.route("/registre", methods=["GET", "POST"])
def registre():
    """Registre d'usuaris nous (màxim 10 intents per hora i per IP)."""
    if g.usuari:
        return redirect(url_for("mercat"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if massa_intents(f"reg:{ip}", 10, 3600):
            flash("Massa registres des d'aquesta connexió. Torna-ho a provar més tard.", "danger")
            return render_template("registre.html", form=request.form), 429
        registrar_intent(f"reg:{ip}")

        nom = camp("nom")
        correu = camp("correu").lower()
        ciutat = camp("ciutat")
        contrasenya = request.form.get("contrasenya") or ""
        errors = []

        if not 2 <= len(nom) <= 60:
            errors.append("El nom ha de tenir entre 2 i 60 caràcters.")
        if not EMAIL_RE.match(correu) or len(correu) > 120:
            errors.append("El correu electrònic no és vàlid.")
        if ciutat not in CIUTATS:
            errors.append("Selecciona una ciutat de la llista.")
        if not 8 <= len(contrasenya) <= 128:
            errors.append("La contrasenya ha de tenir entre 8 i 128 caràcters.")
        if request.form.get("normes") != "on":
            errors.append("Has d'acceptar les Normes d'Ús per registrar-te.")

        if errors:
            mostrar_errors(errors)
            return render_template("registre.html", form=request.form), 400

        try:
            get_db().execute(
                "INSERT INTO usuaris (nom, correu, contrasenya, ciutat) VALUES (?, ?, ?, ?)",
                (nom, correu, generate_password_hash(contrasenya), ciutat))
        except sqlite3.IntegrityError:
            flash("Aquest correu ja està registrat.", "danger")
            return render_template("registre.html", form=request.form), 409
        flash("Compte creat! Ja pots iniciar sessió.", "success")
        return redirect(url_for("login"))
    return render_template("registre.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    """Inici de sessió (bloqueig temporal: 5 intents fallits per compte o 30 per IP en 5 minuts)."""
    if g.usuari:
        return redirect(url_for("mercat"))
    correu = ""
    if request.method == "POST":
        correu = camp("correu").lower()
        contrasenya = request.form.get("contrasenya") or ""
        ip = request.remote_addr or "?"
        clau_compte, clau_ip = f"login:{ip}:{correu}", f"login-ip:{ip}"

        if massa_intents(clau_compte, 5, 300) or massa_intents(clau_ip, 30, 300):
            flash("Massa intents fallits. Espera uns minuts i torna-ho a provar.", "danger")
            return render_template("login.html", correu=correu), 429

        fila = get_db().execute(
            "SELECT id, contrasenya FROM usuaris WHERE correu = ?", (correu,)).fetchone()

        if fila and check_password_hash(fila["contrasenya"], contrasenya):
            session.clear()
            session["id_usuari"] = fila["id"]
            _intents.pop(clau_compte, None)
            return redirect(url_for("mercat"))

        registrar_intent(clau_compte)
        registrar_intent(clau_ip)
        flash("Correu o contrasenya incorrectes.", "danger")
        return render_template("login.html", correu=correu), 401
    return render_template("login.html", correu=correu)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    """Tanca la sessió i torna a l'inici."""
    session.clear()
    return redirect(url_for("inici"))


# =============================================================================
# 6. MERCAT I OFERTES
# =============================================================================
@app.route("/mercat")
@login_required
def mercat():
    """Llistat de totes les ofertes, de la més nova a la més antiga."""
    ofertes = get_db().execute('''
        SELECT o.id, o.titol, o.descripcio, o.hores, o.categoria,
               COALESCE(u.nom, 'Usuari eliminat') AS nom_autor, u.ciutat
        FROM ofertes o LEFT JOIN usuaris u ON u.id = o.id_usuari
        ORDER BY o.id DESC''').fetchall()
    return render_template("mercat.html", ofertes=ofertes)


@app.route("/crear_oferta", methods=["GET", "POST"])
@login_required
def crear_oferta():
    """Formulari per publicar una oferta nova."""
    if request.method == "POST":
        titol, descripcio, categoria = camp("titol"), camp("descripcio"), camp("categoria")
        hores = llegir_hores(request.form.get("hores"), MAX_HORES_OFERTA)
        errors = []
        if not 3 <= len(titol) <= 100:
            errors.append("El títol ha de tenir entre 3 i 100 caràcters.")
        if not 5 <= len(descripcio) <= 1000:
            errors.append("La descripció ha de tenir entre 5 i 1000 caràcters.")
        if categoria not in CATEGORIES_VALIDES:
            errors.append("Selecciona una categoria de la llista.")
        if hores is None:
            errors.append(f"Les hores han de ser un número entre 0.01 i {MAX_HORES_OFERTA}.")

        if errors:
            mostrar_errors(errors)
            return render_template("crear_oferta.html", form=request.form), 400

        get_db().execute(
            "INSERT INTO ofertes (id_usuari, titol, descripcio, categoria, hores) VALUES (?, ?, ?, ?, ?)",
            (g.usuari["id"], titol, descripcio, categoria, hores))
        flash("Oferta publicada!", "success")
        return redirect(url_for("mercat"))
    return render_template("crear_oferta.html", form={})


@app.route("/oferta/<int:id_oferta>")
@login_required
def detall_oferta(id_oferta):
    """Detall d'una oferta (el propietari veu el botó d'eliminar; els altres, contactar i pagar)."""
    oferta = get_db().execute('''
        SELECT o.id, o.titol, o.descripcio, o.id_usuari, o.hores, o.categoria,
               COALESCE(u.nom, 'Usuari eliminat') AS nom_autor,
               COALESCE(u.ciutat, 'Desconeguda') AS ciutat
        FROM ofertes o LEFT JOIN usuaris u ON u.id = o.id_usuari
        WHERE o.id = ?''', (id_oferta,)).fetchone()
    if oferta is None:
        abort(404)
    return render_template("detall_oferta.html", oferta=oferta,
                           es_propietari=(oferta["id_usuari"] == g.usuari["id"]))


# Pàgines a les quals es pot tornar després d'eliminar una oferta (camp 'desti' del formulari)
DESTINS = {"admin": "admin", "historial": "historial", "mercat": "mercat"}


@app.route("/eliminar_oferta/<int:id_oferta>", methods=["POST"])
@login_required
def eliminar_oferta(id_oferta):
    """Elimina una oferta i els seus xats (només el propietari o un administrador)."""
    db = get_db()
    oferta = db.execute("SELECT id_usuari FROM ofertes WHERE id = ?", (id_oferta,)).fetchone()
    if oferta is None:
        flash("Aquesta oferta ja no existeix.", "warning")
    elif oferta["id_usuari"] == g.usuari["id"] or g.usuari["es_admin"]:
        with transaccio(db):
            db.execute("DELETE FROM missatges WHERE id_oferta = ?", (id_oferta,))
            db.execute("DELETE FROM ofertes WHERE id = ?", (id_oferta,))
        flash("Oferta eliminada.", "success")
    else:
        abort(403)
    return redirect(url_for(DESTINS.get(request.form.get("desti"), "mercat")))


# =============================================================================
# 7. ZONA PERSONAL: PERFIL, HISTORIAL I PAGAMENTS
# =============================================================================
@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    """Veure i editar el perfil (nom, ciutat i descripció)."""
    db, yo = get_db(), g.usuari["id"]
    if request.method == "POST":
        nom, ciutat, descripcio = camp("nom"), camp("ciutat"), camp("descripcio")
        errors = []
        if not 2 <= len(nom) <= 60:
            errors.append("El nom ha de tenir entre 2 i 60 caràcters.")
        if ciutat not in CIUTATS:
            errors.append("Selecciona una ciutat de la llista.")
        if len(descripcio) > 500:
            errors.append("La descripció pot tenir com a màxim 500 caràcters.")

        if errors:
            mostrar_errors(errors)
        else:
            db.execute("UPDATE usuaris SET nom = ?, ciutat = ?, descripcio = ? WHERE id = ?",
                       (nom, ciutat, descripcio, yo))
            flash("Perfil actualitzat.", "success")
            return redirect(url_for("perfil"))

    usuari = db.execute("SELECT nom, correu, ciutat, descripcio FROM usuaris WHERE id = ?", (yo,)).fetchone()
    if request.method == "POST":  # només s'hi arriba amb errors: es conserva el que s'ha escrit
        usuari = (nom, usuari["correu"], ciutat, descripcio)
    return render_template("perfil.html", usuari=usuari)


@app.route("/historial")
@login_required
def historial():
    """Les meves ofertes publicades i els meus moviments d'hores (l'hora es mostra en hora local)."""
    db, yo = get_db(), g.usuari["id"]
    ofertes = db.execute(
        "SELECT id, titol, descripcio, hores FROM ofertes WHERE id_usuari = ? ORDER BY id DESC", (yo,)).fetchall()
    moviments = db.execute('''
        SELECT t.hores, datetime(t.data, 'localtime') AS data, t.concepte, t.id_pagador,
               COALESCE(p.nom, 'Usuari eliminat') AS nom_pagador,
               COALESCE(c.nom, 'Usuari eliminat') AS nom_cobrador
        FROM transaccions t
        LEFT JOIN usuaris p ON t.id_pagador = p.id
        LEFT JOIN usuaris c ON t.id_cobrador = c.id
        WHERE t.id_pagador = ? OR t.id_cobrador = ?
        ORDER BY t.id DESC''', (yo, yo)).fetchall()
    return render_template("historial.html", ofertes=ofertes, moviments=moviments)


@app.route("/transferencia", methods=["GET", "POST"])
@login_required
def transferencia():
    """Pagar hores a l'autor d'una oferta (?oferta=ID) o a un altre usuari pel seu correu."""
    db, yo = get_db(), g.usuari["id"]
    id_oferta = a_enter(request.form.get("id_oferta") if request.method == "POST"
                        else request.args.get("oferta"))
    oferta = None
    if id_oferta:
        oferta = db.execute('''SELECT o.id, o.titol, o.hores, o.id_usuari, u.nom AS nom_venedor
                               FROM ofertes o JOIN usuaris u ON u.id = o.id_usuari
                               WHERE o.id = ?''', (id_oferta,)).fetchone()
        if oferta is None:
            flash("Aquesta oferta ja no existeix.", "warning")
            return redirect(url_for("transferencia"))
        if oferta["id_usuari"] == yo and request.method == "GET":
            flash("No et pots pagar a tu mateix.", "warning")
            return redirect(url_for("transferencia"))

    if request.method == "POST":
        hores = llegir_hores(request.form.get("hores"), MAX_HORES_TRANSFERENCIA)
        concepte = camp("concepte")
        errors = []
        if hores is None:
            errors.append(f"Les hores han de ser un número entre 0.01 i {MAX_HORES_TRANSFERENCIA}.")
        if not 1 <= len(concepte) <= 120:
            errors.append("El concepte ha de tenir entre 1 i 120 caràcters.")

        # Destinatari: l'autor de l'oferta o l'usuari amb el correu indicat
        id_cobrador = None
        if oferta:
            id_cobrador = oferta["id_usuari"]
        else:
            correu = camp("correu_destinatari").lower()
            fila = db.execute("SELECT id FROM usuaris WHERE correu = ?", (correu,)).fetchone()
            if fila is None:
                errors.append("No existeix cap usuari amb aquest correu.")
            else:
                id_cobrador = fila["id"]

        if id_cobrador == yo:
            errors.append("No et pots pagar a tu mateix.")

        if not errors:
            try:
                with transaccio(db):
                    # Doble clic: si fa menys de 10 s que s'ha fet exactament el mateix pagament, no es repeteix
                    repetit = db.execute(
                        "SELECT 1 FROM transaccions WHERE id_pagador = ? AND id_cobrador = ? AND hores = ? "
                        "AND concepte = ? AND data >= datetime('now', '-10 seconds')",
                        (yo, id_cobrador, hores, concepte)).fetchone()
                    if not repetit:
                        descomptat = db.execute(
                            "UPDATE usuaris SET saldo = ROUND(saldo - ?, 2) WHERE id = ? AND saldo >= ?",
                            (hores, yo, hores)).rowcount
                        if descomptat != 1:
                            raise ValueError("saldo")
                        ingressat = db.execute(
                            "UPDATE usuaris SET saldo = ROUND(saldo + ?, 2) WHERE id = ?",
                            (hores, id_cobrador)).rowcount
                        if ingressat != 1:
                            raise ValueError("destinatari")
                        db.execute(
                            "INSERT INTO transaccions (id_pagador, id_cobrador, hores, concepte) VALUES (?, ?, ?, ?)",
                            (yo, id_cobrador, hores, concepte))
            except ValueError as e:
                errors.append("No tens prou saldo per fer aquest pagament." if str(e) == "saldo"
                              else "El destinatari ja no existeix.")
            else:
                flash(f"Pagament de {hores}h realitzat correctament.", "success")
                return redirect(url_for("historial"))
        mostrar_errors(errors)
        return render_template("transferencia.html", form=request.form, oferta=oferta), 400

    # GET: si ve d'una oferta, el formulari surt omplert amb les seves hores i el seu títol
    form = {}
    if oferta:
        form = {"hores": oferta["hores"], "concepte": f"{oferta['titol']}"[:120]}
    return render_template("transferencia.html", form=form, oferta=oferta)


# =============================================================================
# 8. XAT
# =============================================================================
# Converses de l'usuari: una per cada parella (oferta, client). Per al propietari
# de l'oferta, el títol inclou el nom del client.
CONSULTA_MEUS_XATS = """
    SELECT m.id_oferta,
           CASE WHEN o.id_usuari = ? THEN o.titol || ' - ' || COALESCE(u.nom, 'Usuari eliminat') ELSE o.titol END,
           m.id_client
    FROM missatges m
    JOIN ofertes o ON o.id = m.id_oferta
    LEFT JOIN usuaris u ON u.id = m.id_client
    WHERE m.id_client = ? OR o.id_usuari = ?
    GROUP BY m.id_oferta, m.id_client
    ORDER BY MAX(m.id) DESC
"""


@app.route("/xat")
@login_required
def xat():
    """Llista de converses (sense cap xat obert)."""
    yo = g.usuari["id"]
    chats = get_db().execute(CONSULTA_MEUS_XATS, (yo, yo, yo)).fetchall()
    return render_template("xat.html", chats=chats, missatges=None, id_oferta=None,
                           id_client=None, titol=None, interlocutor=None, el_meu_id=yo)


@app.route("/xat/<int:id_oferta>", methods=["GET", "POST"], defaults={"id_client": None})
@app.route("/xat/<int:id_oferta>/<int:id_client>", methods=["GET", "POST"])
@login_required
def xat_concret(id_oferta, id_client):
    """Una conversa concreta: veure-la i enviar-hi missatges.

    El client entra per /xat/<oferta>; el propietari, per /xat/<oferta>/<client>
    (només si aquest client ja li ha escrit)."""
    db, yo = get_db(), g.usuari["id"]
    oferta = db.execute("SELECT titol, id_usuari FROM ofertes WHERE id = ?", (id_oferta,)).fetchone()
    if oferta is None:
        flash("Aquesta oferta ja no existeix.", "warning")
        return redirect(url_for("xat"))

    titol, id_propietari = oferta["titol"], oferta["id_usuari"]

    if yo == id_propietari:
        existeix = id_client is not None and db.execute(
            "SELECT 1 FROM missatges WHERE id_oferta = ? AND id_client = ? LIMIT 1",
            (id_oferta, id_client)).fetchone()
        if not existeix:
            return redirect(url_for("xat"))
        id_interlocutor = id_client
    else:
        if id_client not in (None, yo):  # ningú pot llegir converses alienes
            return redirect(url_for("xat"))
        id_client = yo
        id_interlocutor = id_propietari

    if request.method == "POST":
        text = camp("missatge")
        if not text:
            flash("No pots enviar un missatge buit.", "warning")
        elif len(text) > 1000:
            flash("El missatge és massa llarg (màxim 1000 caràcters).", "danger")
        else:
            db.execute("INSERT INTO missatges (id_oferta, id_remitent, id_client, missatge) VALUES (?, ?, ?, ?)",
                       (id_oferta, yo, id_client, text))
        if yo == id_propietari:
            return redirect(url_for("xat_concret", id_oferta=id_oferta, id_client=id_client))
        return redirect(url_for("xat_concret", id_oferta=id_oferta))

    chats = db.execute(CONSULTA_MEUS_XATS, (yo, yo, yo)).fetchall()
    missatges = db.execute('''
        SELECT COALESCE(u.nom, 'Usuari eliminat'), m.missatge, m.id_remitent
        FROM missatges m LEFT JOIN usuaris u ON m.id_remitent = u.id
        WHERE m.id_oferta = ? AND m.id_client = ?
        ORDER BY m.id ASC''', (id_oferta, id_client)).fetchall()

    interlocutor = db.execute("SELECT nom FROM usuaris WHERE id = ?", (id_interlocutor,)).fetchone()
    return render_template("xat.html", chats=chats, missatges=missatges, id_oferta=id_oferta,
                           id_client=id_client, titol=titol, el_meu_id=yo,
                           interlocutor=interlocutor["nom"] if interlocutor else "Usuari eliminat")


@app.route("/eliminar_xat/<int:id_oferta>/<int:id_client>", methods=["POST"])
@login_required
def eliminar_xat(id_oferta, id_client):
    """Elimina una conversa (el client, el propietari de l'oferta o un administrador)."""
    db = get_db()
    oferta = db.execute("SELECT id_usuari FROM ofertes WHERE id = ?", (id_oferta,)).fetchone()
    permes = (g.usuari["es_admin"] or g.usuari["id"] == id_client
              or (oferta is not None and oferta["id_usuari"] == g.usuari["id"]))
    if not permes:
        abort(403)
    db.execute("DELETE FROM missatges WHERE id_oferta = ? AND id_client = ?", (id_oferta, id_client))
    flash("Conversa eliminada.", "success")
    return redirect(url_for("xat"))


# =============================================================================
# 9. ADMINISTRACIÓ
# =============================================================================
@app.route("/admin")
@admin_required
def admin():
    """Panell d'administració: tots els usuaris i totes les ofertes."""
    db = get_db()
    usuaris = db.execute("SELECT id, nom, correu, ciutat, saldo, es_admin FROM usuaris ORDER BY id").fetchall()
    ofertes = db.execute('''SELECT o.id, o.titol, o.id_usuari, COALESCE(u.nom, 'Usuari eliminat') AS nom_autor
                            FROM ofertes o LEFT JOIN usuaris u ON u.id = o.id_usuari
                            ORDER BY o.id DESC''').fetchall()
    return render_template("admin.html", usuaris=usuaris, ofertes=ofertes)


@app.route("/eliminar_usuari/<int:id_usuari_a_esborrar>", methods=["POST"])
@admin_required
def eliminar_usuari(id_usuari_a_esborrar):
    """Expulsa un usuari: n'esborra els missatges, les ofertes i el compte."""
    if id_usuari_a_esborrar == g.usuari["id"]:
        flash("No et pots auto-eliminar.", "danger")
        return redirect(url_for("admin"))
    db = get_db()
    with transaccio(db):
        db.execute("""DELETE FROM missatges WHERE id_remitent = ? OR id_client = ?
                      OR id_oferta IN (SELECT id FROM ofertes WHERE id_usuari = ?)""",
                   (id_usuari_a_esborrar,) * 3)
        db.execute("DELETE FROM ofertes WHERE id_usuari = ?", (id_usuari_a_esborrar,))
        esborrats = db.execute("DELETE FROM usuaris WHERE id = ?", (id_usuari_a_esborrar,)).rowcount
    if esborrats:
        flash("Usuari expulsat.", "success")
    else:
        flash("Aquest usuari ja no existeix.", "warning")
    return redirect(url_for("admin"))


# =============================================================================
# 10. GESTIÓ D'ERRORS
# =============================================================================
def pagina_error(codi, missatge):
    """Mostra la pàgina d'error (templates/error.html) amb el codi HTTP indicat."""
    return render_template("error.html", codi=codi, missatge=missatge), codi


@app.errorhandler(400)
def error_400(_e):
    """400: petició no vàlida."""
    return pagina_error(400, "Petició no vàlida. Torna enrere, recarrega la pàgina i torna-ho a provar.")


@app.errorhandler(403)
def error_403(_e):
    """403: sense permís."""
    return pagina_error(403, "No tens permís per fer aquesta acció.")


@app.errorhandler(404)
def error_404(_e):
    """404: pàgina inexistent."""
    return pagina_error(404, "Aquesta pàgina no existeix.")


@app.errorhandler(405)
def error_405(_e):
    """405: mètode no permès (p. ex. obrir amb el navegador una ruta que només accepta POST)."""
    return pagina_error(405, "Aquesta acció no es pot fer d'aquesta manera.")


@app.errorhandler(413)
def error_413(_e):
    """413: formulari massa gran."""
    return pagina_error(413, "Les dades enviades són massa grans.")


@app.errorhandler(500)
def error_500(_e):
    """500: error intern."""
    return pagina_error(500, "S'ha produït un error intern. Torna-ho a provar més tard.")


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
