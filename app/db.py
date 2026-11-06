"""Acceso a MySQL sin ORM: una conexión por pedido, con el usuario de BD que corresponde al rol."""
# g: un lugar de Flask para guardar datos durante un solo pedido. Ahí dejamos la conexión.
# session: los datos del usuario que inició sesión (acá nos importa su rol).
import os

import pymysql
from flask import g, session

from opciones import ROL_ADMIN, ROL_PLANILLERO

# Antes de iniciar sesión todavía no hay rol: usamos este perfil, que solo puede leer la tabla login.
PERFIL_LOGIN = "login"

# Cada rol de la aplicación usa un usuario de base de datos con permisos distintos.
# La aplicación nunca usa root. Cada rol entra con su propio usuario, creado en torneo.sql con GRANT.
# Así, aunque falle el control de la aplicación, MySQL mismo rechaza lo que ese rol no tiene permitido.
# os.getenv lee la contraseña de una variable de entorno; si no existe, usa la del script.
CREDENCIALES = {
    PERFIL_LOGIN: ("torneo_login", os.getenv("DB_PASS_LOGIN", "login_2026")),
    ROL_ADMIN: ("torneo_admin", os.getenv("DB_PASS_ADMIN", "admin_2026")),
    ROL_PLANILLERO: ("torneo_planillero", os.getenv("DB_PASS_PLANILLERO", "planillero_2026")),
}

# Cada error de MySQL trae un número. Acá traducimos los que esperamos:
# 1062 clave repetida, 1451 y 1452 errores de FK, 3819 y 4025 CHECK, 1142 y 1143 falta de permiso.
MENSAJES_ERROR = {
    1062: "Ya existe un registro con esos datos.",
    1451: "No se puede eliminar: hay otros datos que dependen de este registro.",
    1452: "Alguno de los datos seleccionados no existe.",
    3819: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MySQL
    4025: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MariaDB
    1142: "No tiene permisos para esta operación.",
    1143: "No tiene permisos para esta operación.",
}


# Abre la conexión la primera vez que se necesita en el pedido, y después reutiliza la misma.
# Por eso todas las consultas de una acción quedan dentro de la misma transacción.
# Elige el usuario de base según el rol de la sesión.
# DictCursor hace que cada fila venga como diccionario: fila["nombre"] en lugar de fila[0].
def conexion() -> pymysql.connections.Connection:
    if "db" not in g:
        usuario, contrasena = CREDENCIALES[session.get("rol", PERFIL_LOGIN)]
        g.db = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=usuario,
            password=contrasena,
            database=os.getenv("DB_NAME", "torneo_futbol5"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    return g.db


# Para SELECT: devuelve todas las filas.
# execute(sql, parametros) reemplaza cada %s de forma segura: así se evita la inyección SQL.
def consultar(sql: str, parametros=()) -> list[dict]:
    with conexion().cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


# Para cuando esperamos una sola fila: devuelve esa fila, o None si no hay ninguna.
def consultar_uno(sql: str, parametros=()) -> dict | None:
    filas = consultar(sql, parametros)
    return filas[0] if filas else None


# Para INSERT, UPDATE y DELETE. No hace commit: de eso se encarga realizar() en app.py, al final de la acción.
def ejecutar(sql: str, parametros=()) -> int:
    """Ejecuta sin confirmar y devuelve la cantidad de filas afectadas."""
    with conexion().cursor() as cursor:
        return cursor.execute(sql, parametros)


# Igual que ejecutar, pero devuelve el id que AUTO_INCREMENT le dio a la fila nueva.
def insertar(sql: str, parametros=()) -> int:
    """Ejecuta un INSERT sin confirmar y devuelve el id generado."""
    with conexion().cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.lastrowid


# Cierra la conexión al terminar el pedido. Si quedó algo sin commit, se descarta.
def cerrar(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Convierte un error de MySQL en un mensaje entendible. Si el número no está en la lista, muestra el texto original.
def mensaje_error(error: pymysql.MySQLError) -> str:
    codigo, texto = error.args[0], error.args[1]
    return MENSAJES_ERROR.get(codigo, f"Error de base de datos: {texto}")
