import sqlite3

# 1. Connectem amb la base de dades (si l'arxiu no existeix, el crea automàticament)
connexio = sqlite3.connect("banc_temps.db")
cursor = connexio.cursor()

# 2. Creem la taula d'Usuaris
# Motiu: Necessitem saber qui és a la plataforma i quantes hores té.
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuaris (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    correu TEXT UNIQUE NOT NULL,
    contrasenya TEXT NOT NULL,
    saldo REAL DEFAULT 5.0
)
''')

# 3. Creem la taula de Feines (Ofertes)
# Motiu: Cada anunci ha d'estar lligat a l'usuari que l'ha creat.
cursor.execute('''
CREATE TABLE IF NOT EXISTS ofertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuari INTEGER NOT NULL,
    titol TEXT NOT NULL,
    descripcio TEXT,
    FOREIGN KEY (id_usuari) REFERENCES usuaris (id)
)
''')

# 4. Creem la taula de Transaccions (El llibre de registre)
# Motiu: Guardem qui paga, qui cobra i quantes hores s'han passat.
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

# 5. Guardem els canvis i tanquem la connexió
connexio.commit()
connexio.close()

print("Base de dades creada amb èxit!")