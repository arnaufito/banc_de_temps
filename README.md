# Banc de Temps

Web per intercanviar serveis entre veïns pagant amb **hores** en lloc de diners (1 hora = 1 hora).
Feta amb **Python + Flask + SQLite**. No fa servir JavaScript.

## Índex

1. [Estructura del projecte](#estructura-del-projecte)
2. [Posada en marxa (Windows)](#posada-en-marxa-windows)
3. [Variables d'entorn](#variables-dentorn)
4. [Crear l'administrador](#crear-ladministrador)
5. [Desplegament en un servidor](#desplegament-en-un-servidor)
6. [Base de dades](#base-de-dades)
7. [Rutes de l'aplicació](#rutes-de-laplicació)
8. [Scripts auxiliars](#scripts-auxiliars)
9. [Limitacions conegudes](#limitacions-conegudes)

## Estructura del projecte

```
banc_de_temps/
├── app.py                 Tot el servidor (rutes, BD, validacions). Té el seu propi índex a dalt de tot.
├── requirements.txt       Dependències (Flask i Gunicorn)
├── README.md              Aquest fitxer
├── .gitignore             Fitxers que no es pugen a git (BD, clau secreta, etc.)
├── fer_admin.py           Script: converteix un usuari en administrador
├── verificar_bd.py        Script: mostra els usuaris de la BD
├── netejar_bd.py          Script: esborra TOTES les dades (demana confirmació)
├── static/
│   └── style.css          Tots els estils (té índex a dalt de tot)
└── templates/
    ├── _navbar.html       Barra de navegació (inclosa a les pàgines internes)
    ├── _flash.html        Missatges d'èxit / error (inclòs a les pàgines)
    ├── index.html         Inici
    ├── normes.html        Normes d'ús
    ├── registre.html      Registre
    ├── login.html         Inici de sessió
    ├── mercat.html        Llistat d'ofertes
    ├── crear_oferta.html  Publicar una oferta
    ├── detall_oferta.html Detall d'una oferta
    ├── perfil.html        El meu perfil
    ├── historial.html     Les meves ofertes i els meus moviments d'hores
    ├── transferencia.html Pagar hores
    ├── xat.html           Converses
    ├── admin.html         Panell d'administració
    └── error.html         Pàgina d'error (400, 403, 404, 405, 413, 500)
```

Els fitxers generats en executar l'app (`banc_temps.db` i `.secret_key`) no formen part del repositori.

## Posada en marxa (Windows)

```bash
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

Obre <http://127.0.0.1:5000>. La primera vegada es creen sols `banc_temps.db` i `.secret_key`.
Per veure els errors detallats mentre desenvolupes: `set FLASK_DEBUG=1` abans de `py app.py`.

## Variables d'entorn

Totes són opcionals.

| Variable | Per a què serveix |
|---|---|
| `SECRET_KEY` | Clau que signa les sessions. Si no hi és, es genera i es desa a `.secret_key`. **Al servidor, defineix-la sempre.** |
| `DATABASE` | Ruta de la base de dades. Per defecte, `banc_temps.db` al costat d'`app.py`. |
| `ADMIN_CORREU` i `ADMIN_CONTRASENYA` | Si les dues hi són (contrasenya de 8 caràcters o més), en arrencar es crea l'administrador. |
| `PROXY=1` | Posa-ho si l'app va darrere d'un proxy (Render, Railway…). Sense això, tots els usuaris compten com la mateixa IP i el límit d'intents els afecta a tots alhora. |
| `COOKIES_SEGURES=1` | Posa-ho quan la web es serveixi per HTTPS. |
| `FLASK_DEBUG=1` | Mode de depuració (només en desenvolupament). |
| `TZ` | Fus horari del servidor (p. ex. `Europe/Madrid`): l'historial mostra l'hora local del servidor. |

## Crear l'administrador

Opció A (recomanada al servidor): defineix `ADMIN_CORREU` i `ADMIN_CONTRASENYA` i arrenca l'app.

Opció B: registra't a la web, escriu el teu correu a `fer_admin.py` i executa `py fer_admin.py`.
No facis servir l'adreça pública de contacte de `normes.html`: qualsevol podria registrar-la abans que tu.

## Desplegament en un servidor

```bash
gunicorn -w 1 --threads 4 app:app
```

- **Un sol worker (`-w 1`)**: el límit d'intents de login i registre es guarda en memòria, per procés.
- **Base de dades persistent**: apunta `DATABASE` a un disc que sobrevisqui als desplegaments (en molts hostings el disc normal s'esborra a cada desplegament i es perdrien tots els usuaris).
- **`SECRET_KEY` com a variable d'entorn**, `PROXY=1` si hi ha proxy i `COOKIES_SEGURES=1` si hi ha HTTPS.

## Base de dades

SQLite, creada i migrada automàticament en arrencar (`inicialitzar_bd()` a `app.py`).

| Taula | Contingut |
|---|---|
| `usuaris` | Nom, correu (únic), contrasenya (hash), ciutat, saldo (5 h inicials), `es_admin`, descripció |
| `ofertes` | Autor, títol, descripció, hores, categoria |
| `transaccions` | Pagador, cobrador, hores, concepte, data (en UTC) |
| `missatges` | Oferta, remitent, client de la conversa, text |

## Rutes de l'aplicació

| Ruta | Mètode | Accés | Què fa |
|---|---|---|---|
| `/` | GET | Públic | Inici |
| `/normes` | GET | Públic | Normes d'ús |
| `/registre` | GET, POST | Públic | Crear compte |
| `/login` | GET, POST | Públic | Iniciar sessió |
| `/logout` | GET, POST | Tothom | Tancar sessió |
| `/mercat` | GET | Usuari | Totes les ofertes |
| `/crear_oferta` | GET, POST | Usuari | Publicar una oferta |
| `/oferta/<id>` | GET | Usuari | Detall d'una oferta |
| `/eliminar_oferta/<id>` | POST | Propietari o admin | Eliminar una oferta (i els seus xats) |
| `/perfil` | GET, POST | Usuari | Editar el perfil |
| `/historial` | GET | Usuari | Les meves ofertes i moviments |
| `/transferencia` | GET, POST | Usuari | Pagar hores |
| `/xat`, `/xat/<oferta>`, `/xat/<oferta>/<client>` | GET, POST | Usuari | Converses |
| `/eliminar_xat/<oferta>/<client>` | POST | Client, propietari o admin | Eliminar una conversa |
| `/admin` | GET | Admin | Panell d'administració |
| `/eliminar_usuari/<id>` | POST | Admin | Expulsar un usuari |

## Scripts auxiliars

| Script | Ús |
|---|---|
| `py fer_admin.py` | Fa administrador l'usuari que tingui el correu escrit dins de l'script |
| `py verificar_bd.py` | Llista els usuaris (sense contrasenyes) |
| `py netejar_bd.py` | Esborra **totes** les dades (cal escriure `SI`). Atura l'app abans. |

## Limitacions conegudes

Són decisions de disseny o funcionalitats que encara no hi són, no errors de codi:

- No hi ha protecció CSRF als formularis, i `/logout` accepta GET.
- El correu no es verifica: es poden crear comptes falsos que reben 5 h cadascun.
- Qui coneix un correu pot comprovar si està registrat (registre i pagament per correu).
- Expulsar un usuari fa desaparèixer el seu saldo, i un administrador pot expulsar-ne un altre.
- Els missatges del xat no tenen data, i qualsevol dels dos participants pot esborrar la conversa per als dos.
- No es pot canviar la contrasenya ni el correu, ni esborrar el compte.
- Si es pugen a git dades sensibles (com una clau secreta), continuen visibles a l'historial encara que s'esborrin després: cal canviar-les.

## Notes de seguretat

- Els pagaments es fan dins d'una transacció atòmica: o es fa tot o no es fa res.
- Un mateix pagament (mateix destinatari, hores i concepte) no es repeteix si es torna a enviar en menys de 10 segons (protecció davant del doble clic).
- La política de seguretat del navegador (CSP) només accepta recursos del mateix lloc i no permet JavaScript.
