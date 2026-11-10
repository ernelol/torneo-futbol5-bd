"""Acceso a MySQL sin ORM: una conexión por pedido, con el usuario de BD que corresponde al rol."""
# g es un lugar de Flask que dura un solo pedido: ahí guardamos la conexión.
# En session están los datos del usuario que inició sesión. Acá lo que nos importa es su rol.
import os

import pymysql
from flask import g, session

from opciones import ROL_ADMIN, ROL_PLANILLERO

# Antes de iniciar sesión todavía no hay rol, así que usamos este perfil, que solo puede leer la tabla login.
PERFIL_LOGIN = "login"

# Cada rol de la aplicación usa un usuario de base de datos con permisos distintos.
# La aplicación nunca entra con root. Cada rol usa su propio usuario de MySQL, creado con GRANT en torneo.sql.
# Así, aunque fallara un control de la app, MySQL igual rechaza lo que ese rol no tiene permitido.
# os.getenv lee la contraseña de una variable de entorno, y si no existe usa la del script.
CREDENCIALES = {
    PERFIL_LOGIN: ("torneo_login", os.getenv("DB_PASS_LOGIN", "login_2026")),
    ROL_ADMIN: ("torneo_admin", os.getenv("DB_PASS_ADMIN", "admin_2026")),
    ROL_PLANILLERO: ("torneo_planillero", os.getenv("DB_PASS_PLANILLERO", "planillero_2026")),
}

# Cada error de MySQL viene con un número. Estos son los que esperamos:
# 1062 clave repetida, 1451 y 1452 problemas con una FK, 3819 y 4025 un CHECK, y 1142 y 1143 falta de permiso.
MENSAJES_ERROR = {
    1062: "Ya existe un registro con esos datos.",
    1451: "No se puede eliminar: hay otros datos que dependen de este registro.",
    1452: "Alguno de los datos seleccionados no existe.",
    3819: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MySQL
    4025: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MariaDB
    1142: "No tiene permisos para esta operación.",
    1143: "No tiene permisos para esta operación.",
}


# Abrimos la conexión la primera vez que se necesita en el pedido y después usamos siempre la misma.
# Por eso todas las consultas de una acción quedan dentro de la misma transacción.
# El usuario de MySQL depende del rol de la sesión.
# Con DictCursor cada fila llega como diccionario: fila["nombre"] en vez de fila[0].
# PyMySQL arranca con el autocommit apagado, así que nada se guarda hasta que hacemos commit.
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


# Para los SELECT. Devuelve todas las filas.
# execute reemplaza cada %s por el valor de forma segura, así se evita la inyección SQL.
def consultar(sql: str, parametros=()) -> list[dict]:
    with conexion().cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


# Para cuando esperamos una sola fila. Si no hay ninguna, devuelve None.
def consultar_uno(sql: str, parametros=()) -> dict | None:
    filas = consultar(sql, parametros)
    return filas[0] if filas else None


# Para INSERT, UPDATE y DELETE. No hace commit: eso lo hace realizar() en app.py cuando termina toda la acción.
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


# Cierra la conexión al final del pedido. Lo que haya quedado sin commit se descarta.
def cerrar(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Pasa el error de MySQL a un mensaje que se entienda. Si el número no está en la lista, muestra el texto que vino.
def mensaje_error(error: pymysql.MySQLError) -> str:
    codigo, texto = error.args[0], error.args[1]
    return MENSAJES_ERROR.get(codigo, f"Error de base de datos: {texto}")
