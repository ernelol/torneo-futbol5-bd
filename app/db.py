"""Acceso a MySQL sin ORM: una conexión por pedido, con el usuario de BD que corresponde al rol."""
import os

import pymysql
from flask import g, session

from opciones import ROL_ADMIN, ROL_PLANILLERO

PERFIL_LOGIN = "login"

# Cada rol de la aplicación usa un usuario de base de datos con permisos distintos.
CREDENCIALES = {
    PERFIL_LOGIN: ("torneo_login", os.getenv("DB_PASS_LOGIN", "login_2026")),
    ROL_ADMIN: ("torneo_admin", os.getenv("DB_PASS_ADMIN", "admin_2026")),
    ROL_PLANILLERO: ("torneo_planillero", os.getenv("DB_PASS_PLANILLERO", "planillero_2026")),
}

MENSAJES_ERROR = {
    1062: "Ya existe un registro con esos datos.",
    1451: "No se puede eliminar: hay otros datos que dependen de este registro.",
    1452: "Alguno de los datos seleccionados no existe.",
    3819: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MySQL
    4025: "Algún valor no cumple las restricciones de la base de datos.",  # CHECK en MariaDB
    1142: "No tiene permisos para esta operación.",
    1143: "No tiene permisos para esta operación.",
}


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


def consultar(sql: str, parametros=()) -> list[dict]:
    with conexion().cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


def consultar_uno(sql: str, parametros=()) -> dict | None:
    filas = consultar(sql, parametros)
    return filas[0] if filas else None


def ejecutar(sql: str, parametros=()) -> int:
    """Ejecuta sin confirmar y devuelve la cantidad de filas afectadas."""
    with conexion().cursor() as cursor:
        return cursor.execute(sql, parametros)


def insertar(sql: str, parametros=()) -> int:
    """Ejecuta un INSERT sin confirmar y devuelve el id generado."""
    with conexion().cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.lastrowid


def cerrar(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def mensaje_error(error: pymysql.MySQLError) -> str:
    codigo, texto = error.args[0], error.args[1]
    return MENSAJES_ERROR.get(codigo, f"Error de base de datos: {texto}")
