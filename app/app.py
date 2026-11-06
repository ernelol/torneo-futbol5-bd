"""Aplicación web del Torneo Interfacultades de Fútbol 5.

Aquí están las pantallas y acciones. Los campos se validan en validacion.py
y las reglas de negocio de la letra están en reglas.py."""
import os
from datetime import date
from functools import wraps

import pymysql
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import db
import reglas
import validacion as v
from opciones import (COLORES_TARJETA, DEPARTAMENTOS, ESTADO_JUGADO, ESTADOS_PARTIDO, ESTADOS_TORNEO, ETIQUETAS,
                      MOTIVOS_SANCION, ROL_ADMIN, ROL_PLANILLERO, SUPERFICIES, TIPOS_JUGADOR)
from reportes import REPORTES

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave-de-desarrollo")
app.teardown_appcontext(db.cerrar)


@app.template_filter("etiqueta")
def etiqueta(valor):
    return ETIQUETAS.get(valor, valor)


@app.context_processor
def opciones_para_plantillas():
    return dict(TIPOS_JUGADOR=TIPOS_JUGADOR, ESTADOS_TORNEO=ESTADOS_TORNEO, ESTADOS_PARTIDO=ESTADOS_PARTIDO,
                SUPERFICIES=SUPERFICIES, COLORES_TARJETA=COLORES_TARJETA, MOTIVOS_SANCION=MOTIVOS_SANCION,
                DEPARTAMENTOS=DEPARTAMENTOS, ROL_ADMIN=ROL_ADMIN, hoy=date.today())


# ---------------------------------------------------------------- utilidades

def requiere(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if session.get("rol") not in roles:
                return redirect(url_for("login"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def realizar(accion, mensaje_exito: str) -> None:
    """Ejecuta la acción en una transacción y muestra el resultado al usuario."""
    try:
        accion()
        db.conexion().commit()
        flash(mensaje_exito, "ok")
    except ValueError as error:
        db.conexion().rollback()
        flash(str(error), "error")
    except pymysql.MySQLError as error:
        db.conexion().rollback()
        flash(db.mensaje_error(error), "error")


def volver():
    return redirect(request.referrer or url_for("inicio"))


def torneos_y_elegido() -> tuple[list[dict], dict | None]:
    """Lista de torneos y el elegido en ?torneo=; por defecto, el que está en curso."""
    torneos = db.consultar("SELECT * FROM torneo ORDER BY estado = 'en_curso' DESC, anio DESC, semestre DESC")
    for torneo in torneos:
        if str(torneo["id_torneo"]) == request.args.get("torneo"):
            return torneos, torneo
    return torneos, torneos[0] if torneos else None


def ids(filas: list[dict], columna: str) -> set[str]:
    return {str(fila[columna]) for fila in filas}


# ---------------------------------------------------------------- sesión

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        try:
            correo = v.email(request.form, "correo")
            contrasena = v.texto(request.form, "contrasena", 255)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("login.html")
        usuario = db.consultar_uno("SELECT contrasena, rol FROM login WHERE correo = %s", (correo,))
        if usuario and check_password_hash(usuario["contrasena"], contrasena):
            session["correo"] = correo
            session["rol"] = usuario["rol"]
            return redirect(url_for("inicio"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def inicio():
    return redirect(url_for("partidos"))


# ---------------------------------------------------------------- torneos

@app.route("/torneos")
@requiere(ROL_ADMIN)
def torneos():
    editando = db.consultar_uno("SELECT * FROM torneo WHERE id_torneo = %s", (request.args.get("editar"),))
    return render_template("torneos.html", torneos=db.consultar("SELECT * FROM torneo ORDER BY anio DESC, semestre DESC"),
                           editando=editando)


@app.post("/torneos/guardar")
@requiere(ROL_ADMIN)
def guardar_torneo():
    def accion():
        f = request.form
        nombre, anio, semestre = v.texto(f, "nombre", 100), v.entero(f, "anio", 2000, 2100), v.entero(f, "semestre", 1, 2)
        inicio, fin, estado = v.fecha(f, "fecha_inicio"), v.fecha(f, "fecha_fin"), v.opcion(f, "estado", ESTADOS_TORNEO)
        if fin < inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio.")
        if f.get("id_torneo"):
            reglas.verificar_cambio_de_estado(f["id_torneo"], estado)
            db.ejecutar("""UPDATE torneo SET nombre = %s, anio = %s, semestre = %s, fecha_inicio = %s,
                           fecha_fin = %s, estado = %s WHERE id_torneo = %s""",
                        (nombre, anio, semestre, inicio, fin, estado, f["id_torneo"]))
        else:
            db.ejecutar("""INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado)
                           VALUES (%s, %s, %s, %s, %s, %s)""", (nombre, anio, semestre, inicio, fin, estado))
    realizar(accion, "Torneo guardado.")
    return redirect(url_for("torneos"))


@app.post("/torneos/<int:id_torneo>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_torneo(id_torneo):
    def accion():
        db.ejecutar("DELETE FROM torneo WHERE id_torneo = %s", (id_torneo,))
    realizar(accion, "Torneo eliminado.")
    return redirect(url_for("torneos"))


# ---------------------------------------------------------------- jugadores

@app.route("/jugadores")
@requiere(ROL_ADMIN)
def jugadores():
    lista = db.consultar("""SELECT j.*, f.nombre AS facultad FROM jugador j
                            JOIN facultad f ON f.id_facultad = j.id_facultad ORDER BY j.apellido, j.nombre""")
    editando = db.consultar_uno("SELECT * FROM jugador WHERE ci = %s", (request.args.get("editar"),))
    return render_template("jugadores.html", jugadores=lista, editando=editando,
                           facultades=db.consultar("SELECT * FROM facultad ORDER BY nombre"))


@app.post("/jugadores/guardar")
@requiere(ROL_ADMIN)
def guardar_jugador():
    def accion():
        f = request.form
        facultades = ids(db.consultar("SELECT id_facultad FROM facultad"), "id_facultad")
        nombre, apellido, email = v.texto(f, "nombre", 50), v.texto(f, "apellido", 50), v.email(f)
        nacimiento = v.fecha_pasada(f, "fecha_nacimiento")
        facultad, tipo = v.opcion(f, "id_facultad", facultades), v.opcion(f, "tipo", TIPOS_JUGADOR)
        if f.get("original"):
            reglas.verificar_cambio_de_jugador(f["original"], facultad, tipo)
            db.ejecutar("""UPDATE jugador SET nombre = %s, apellido = %s, email = %s, fecha_nacimiento = %s,
                           id_facultad = %s, tipo = %s WHERE ci = %s""",
                        (nombre, apellido, email, nacimiento, facultad, tipo, f["original"]))
        else:
            db.ejecutar("""INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (v.ci(f), nombre, apellido, email, nacimiento, facultad, tipo))
    realizar(accion, "Jugador guardado.")
    return redirect(url_for("jugadores"))


@app.post("/jugadores/<ci>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_jugador(ci):
    def accion():
        db.ejecutar("DELETE FROM jugador WHERE ci = %s", (ci,))
    realizar(accion, "Jugador eliminado.")
    return redirect(url_for("jugadores"))


# ---------------------------------------------------------------- equipos y planteles

@app.route("/equipos")
@requiere(ROL_ADMIN)
def equipos():
    torneos, torneo = torneos_y_elegido()
    lista = db.consultar("""SELECT e.*, f.nombre AS facultad, CONCAT(j.nombre, ' ', j.apellido) AS capitan,
                                   (SELECT COUNT(*) FROM equipo_jugador_torneo ejt WHERE ejt.id_equipo = e.id_equipo) AS jugadores
                            FROM equipo e JOIN facultad f ON f.id_facultad = e.id_facultad
                            LEFT JOIN jugador j ON j.ci = e.ci_capitan
                            WHERE e.id_torneo = %s ORDER BY e.nombre""", (torneo["id_torneo"] if torneo else None,))
    editando = db.consultar_uno("SELECT * FROM equipo WHERE id_equipo = %s", (request.args.get("editar"),))
    plantel = plantel_de(editando["id_equipo"]) if editando else []
    return render_template("equipos.html", torneos=torneos, torneo=torneo, equipos=lista, editando=editando,
                           plantel=plantel, facultades=db.consultar("SELECT * FROM facultad ORDER BY nombre"))


def plantel_de(id_equipo: int) -> list[dict]:
    return db.consultar("""SELECT ejt.*, j.nombre, j.apellido, j.tipo FROM equipo_jugador_torneo ejt
                           JOIN jugador j ON j.ci = ejt.ci_jugador
                           WHERE ejt.id_equipo = %s ORDER BY ejt.numero_camiseta""", (id_equipo,))


@app.post("/equipos/guardar")
@requiere(ROL_ADMIN)
def guardar_equipo():
    def accion():
        f = request.form
        facultades = ids(db.consultar("SELECT id_facultad FROM facultad"), "id_facultad")
        nombre, facultad = v.texto(f, "nombre", 60), v.opcion(f, "id_facultad", facultades)
        if f.get("id_equipo"):
            reglas.verificar_cambio_de_facultad(f["id_equipo"], facultad)
            capitan = f.get("ci_capitan") or None  # la FK garantiza que sea del plantel
            db.ejecutar("UPDATE equipo SET nombre = %s, id_facultad = %s, ci_capitan = %s WHERE id_equipo = %s",
                        (nombre, facultad, capitan, f["id_equipo"]))
        else:
            reglas.verificar_inscripcion(f["id_torneo"])
            db.ejecutar("INSERT INTO equipo (nombre, id_facultad, id_torneo) VALUES (%s, %s, %s)",
                        (nombre, facultad, f["id_torneo"]))
    realizar(accion, "Equipo guardado.")
    return volver()


@app.post("/equipos/<int:id_equipo>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_equipo(id_equipo):
    def accion():
        equipo = db.consultar_uno("SELECT id_torneo FROM equipo WHERE id_equipo = %s", (id_equipo,))
        reglas.verificar_inscripcion(equipo["id_torneo"])
        # el capitán referencia al plantel: se quita antes de borrar el equipo (y su plantel en cascada)
        db.ejecutar("UPDATE equipo SET ci_capitan = NULL WHERE id_equipo = %s", (id_equipo,))
        db.ejecutar("DELETE FROM equipo WHERE id_equipo = %s", (id_equipo,))
    realizar(accion, "Equipo eliminado.")
    return volver()


@app.route("/equipos/<int:id_equipo>/plantel")
@requiere(ROL_ADMIN)
def plantel(id_equipo):
    equipo = db.consultar_uno("""SELECT e.*, f.nombre AS facultad, t.nombre AS torneo, t.estado AS estado_torneo
                                 FROM equipo e JOIN facultad f ON f.id_facultad = e.id_facultad
                                 JOIN torneo t ON t.id_torneo = e.id_torneo WHERE e.id_equipo = %s""", (id_equipo,))
    # jugadores de la facultad del equipo que no están en ningún equipo de esta edición
    disponibles = db.consultar("""SELECT j.* FROM jugador j
                                  WHERE j.id_facultad = %s AND NOT EXISTS (
                                      SELECT 1 FROM equipo_jugador_torneo ejt
                                      WHERE ejt.ci_jugador = j.ci AND ejt.id_torneo = %s)
                                  ORDER BY j.apellido""", (equipo["id_facultad"], equipo["id_torneo"]))
    return render_template("plantel.html", equipo=equipo, plantel=plantel_de(id_equipo), disponibles=disponibles)


@app.post("/equipos/<int:id_equipo>/plantel/agregar")
@requiere(ROL_ADMIN)
def agregar_al_plantel(id_equipo):
    def accion():
        f = request.form
        ci, camiseta = v.ci(f, "ci_jugador"), v.entero(f, "numero_camiseta", 1, 99)
        # FOR UPDATE: dos altas a la vez en el mismo equipo no pasan juntas el control de 10 jugadores
        equipo = db.consultar_uno("SELECT * FROM equipo WHERE id_equipo = %s FOR UPDATE", (id_equipo,))
        reglas.verificar_alta_en_plantel(equipo, ci)
        db.ejecutar("""INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta)
                       VALUES (%s, %s, %s, %s)""", (id_equipo, ci, equipo["id_torneo"], camiseta))
    realizar(accion, "Jugador agregado al plantel.")
    return volver()


@app.post("/equipos/<int:id_equipo>/plantel/<ci>/quitar")
@requiere(ROL_ADMIN)
def quitar_del_plantel(id_equipo, ci):
    def accion():
        equipo = db.consultar_uno("SELECT id_torneo, ci_capitan FROM equipo WHERE id_equipo = %s", (id_equipo,))
        reglas.verificar_inscripcion(equipo["id_torneo"])
        if equipo["ci_capitan"] == ci:
            raise ValueError("Es el capitán del equipo: elija otro capitán antes de quitarlo.")
        db.ejecutar("DELETE FROM equipo_jugador_torneo WHERE id_equipo = %s AND ci_jugador = %s", (id_equipo, ci))
    realizar(accion, "Jugador quitado del plantel.")
    return volver()


# ---------------------------------------------------------------- complejos y canchas

@app.route("/complejos")
@requiere(ROL_ADMIN)
def complejos():
    editando = db.consultar_uno("SELECT * FROM complejo WHERE id_complejo = %s", (request.args.get("editar"),))
    canchas = db.consultar("""SELECT c.*, co.nombre AS complejo FROM cancha c
                              JOIN complejo co ON co.id_complejo = c.id_complejo ORDER BY co.nombre, c.nombre_cancha""")
    return render_template("complejos.html", complejos=db.consultar("SELECT * FROM complejo ORDER BY nombre"),
                           canchas=canchas, editando=editando)


@app.post("/complejos/guardar")
@requiere(ROL_ADMIN)
def guardar_complejo():
    def accion():
        f = request.form
        nombre, direccion = v.texto(f, "nombre", 80), v.texto(f, "direccion", 120)
        departamento = v.opcion(f, "departamento", DEPARTAMENTOS)
        if f.get("id_complejo"):
            db.ejecutar("UPDATE complejo SET nombre = %s, direccion = %s, departamento = %s WHERE id_complejo = %s",
                        (nombre, direccion, departamento, f["id_complejo"]))
        else:
            db.ejecutar("INSERT INTO complejo (nombre, direccion, departamento) VALUES (%s, %s, %s)",
                        (nombre, direccion, departamento))
    realizar(accion, "Complejo guardado.")
    return redirect(url_for("complejos"))


@app.post("/complejos/<int:id_complejo>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_complejo(id_complejo):
    def accion():
        db.ejecutar("DELETE FROM complejo WHERE id_complejo = %s", (id_complejo,))
    realizar(accion, "Complejo eliminado.")
    return redirect(url_for("complejos"))


@app.post("/canchas/guardar")
@requiere(ROL_ADMIN)
def guardar_cancha():
    """Si la cancha ya existe en ese complejo, se modifican su superficie y si es techada."""
    def accion():
        f = request.form
        complejos_validos = ids(db.consultar("SELECT id_complejo FROM complejo"), "id_complejo")
        nombre, complejo = v.texto(f, "nombre_cancha", 40), v.opcion(f, "id_complejo", complejos_validos)
        superficie, techada = v.opcion(f, "superficie", SUPERFICIES), v.casilla(f, "techada")
        if db.consultar("SELECT 1 FROM cancha WHERE nombre_cancha = %s AND id_complejo = %s", (nombre, complejo)):
            db.ejecutar("UPDATE cancha SET superficie = %s, techada = %s WHERE nombre_cancha = %s AND id_complejo = %s",
                        (superficie, techada, nombre, complejo))
        else:
            db.ejecutar("INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES (%s, %s, %s, %s)",
                        (nombre, complejo, superficie, techada))
    realizar(accion, "Cancha guardada.")
    return redirect(url_for("complejos"))


@app.post("/canchas/eliminar")
@requiere(ROL_ADMIN)
def eliminar_cancha():
    def accion():
        db.ejecutar("DELETE FROM cancha WHERE nombre_cancha = %s AND id_complejo = %s",
                    (request.form["nombre_cancha"], request.form["id_complejo"]))
    realizar(accion, "Cancha eliminada.")
    return redirect(url_for("complejos"))


# ---------------------------------------------------------------- partidos

@app.route("/partidos")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def partidos():
    torneos, torneo = torneos_y_elegido()
    id_torneo = torneo["id_torneo"] if torneo else None
    lista = db.consultar("""SELECT p.*, el.nombre AS local, ev.nombre AS visitante, co.nombre AS complejo,
                                   t.hora_inicio AS hora, r.goles_local, r.goles_visitante
                            FROM partido p
                            JOIN equipo el ON el.id_equipo = p.id_equipo_local
                            JOIN equipo ev ON ev.id_equipo = p.id_equipo_visitante
                            JOIN turno t ON t.id_turno = p.id_turno
                            JOIN complejo co ON co.id_complejo = p.id_complejo
                            JOIN resultado_partido r ON r.id_partido = p.id_partido
                            WHERE p.id_torneo = %s ORDER BY p.numero_fecha, p.dia, t.hora_inicio""", (id_torneo,))
    opciones, editando = None, None
    if session["rol"] == ROL_ADMIN:  # el formulario es solo para el administrador
        opciones = opciones_de_partido(id_torneo)
        editando = db.consultar_uno("SELECT * FROM partido WHERE id_partido = %s", (request.args.get("editar"),))
    return render_template("partidos.html", torneos=torneos, torneo=torneo, partidos=lista,
                           opciones=opciones, editando=editando)


def opciones_de_partido(id_torneo) -> dict:
    return dict(
        equipos=db.consultar("SELECT id_equipo, nombre FROM equipo WHERE id_torneo = %s ORDER BY nombre", (id_torneo,)),
        turnos=db.consultar("SELECT id_turno, CONCAT(hora_inicio, ' a ', hora_fin) AS horario FROM turno ORDER BY hora_inicio"),
        canchas=db.consultar("""SELECT c.nombre_cancha, c.id_complejo, co.nombre AS complejo FROM cancha c
                                JOIN complejo co ON co.id_complejo = c.id_complejo ORDER BY co.nombre, c.nombre_cancha"""),
    )


@app.post("/partidos/guardar")
@requiere(ROL_ADMIN)
def guardar_partido():
    def accion():
        f = request.form
        reglas.reservar_torneo(f["id_torneo"])
        opciones = opciones_de_partido(f.get("id_torneo"))
        equipos_validos = ids(opciones["equipos"], "id_equipo")
        canchas_validas = {f"{c['id_complejo']}|{c['nombre_cancha']}" for c in opciones["canchas"]}
        id_complejo, nombre_cancha = v.opcion(f, "cancha", canchas_validas).split("|", 1)
        partido = {
            "id_partido": f.get("id_partido"),
            "id_torneo": f["id_torneo"],
            "numero_fecha": v.entero(f, "numero_fecha", 1, 50),
            "id_equipo_local": v.opcion(f, "id_equipo_local", equipos_validos),
            "id_equipo_visitante": v.opcion(f, "id_equipo_visitante", equipos_validos),
            "dia": v.fecha(f, "dia"),
            "id_turno": v.opcion(f, "id_turno", ids(opciones["turnos"], "id_turno")),
            "nombre_cancha": nombre_cancha,
            "id_complejo": id_complejo,
            "estado": v.opcion(f, "estado", ESTADOS_PARTIDO),
        }
        if partido["id_equipo_local"] == partido["id_equipo_visitante"]:
            raise ValueError("Un equipo no puede enfrentarse a sí mismo.")
        if partido["id_partido"]:
            reglas.verificar_partido_no_jugado(partido["id_partido"])
        reglas.verificar_partido(partido)
        # %(columna)s toma cada valor del diccionario partido
        if partido["id_partido"]:
            db.ejecutar("""UPDATE partido SET numero_fecha = %(numero_fecha)s, id_equipo_local = %(id_equipo_local)s,
                           id_equipo_visitante = %(id_equipo_visitante)s, dia = %(dia)s, id_turno = %(id_turno)s,
                           nombre_cancha = %(nombre_cancha)s, id_complejo = %(id_complejo)s, estado = %(estado)s
                           WHERE id_partido = %(id_partido)s""", partido)
        else:
            db.ejecutar("""INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia,
                           id_turno, nombre_cancha, id_complejo, estado)
                           VALUES (%(id_torneo)s, %(numero_fecha)s, %(id_equipo_local)s, %(id_equipo_visitante)s,
                                   %(dia)s, %(id_turno)s, %(nombre_cancha)s, %(id_complejo)s, %(estado)s)""", partido)
    realizar(accion, "Partido guardado.")
    return volver()


@app.post("/partidos/<int:id_partido>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_partido(id_partido):
    def accion():
        reglas.verificar_partido_no_jugado(id_partido)
        db.ejecutar("DELETE FROM partido WHERE id_partido = %s", (id_partido,))
    realizar(accion, "Partido eliminado.")
    return volver()


# ---------------------------------------------------------------- planilla, goles y tarjetas

@app.route("/partidos/<int:id_partido>/planilla")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def planilla(id_partido):
    partido = db.consultar_uno("""SELECT p.*, el.nombre AS local, ev.nombre AS visitante, r.goles_local,
                                         r.goles_visitante, t.hora_inicio AS hora
                                  FROM partido p
                                  JOIN equipo el ON el.id_equipo = p.id_equipo_local
                                  JOIN equipo ev ON ev.id_equipo = p.id_equipo_visitante
                                  JOIN turno t ON t.id_turno = p.id_turno
                                  JOIN resultado_partido r ON r.id_partido = p.id_partido
                                  WHERE p.id_partido = %s""", (id_partido,))
    en_planilla = db.consultar("""SELECT pp.ci_jugador, j.nombre, j.apellido, e.nombre AS equipo
                                  FROM planilla_partido pp JOIN jugador j ON j.ci = pp.ci_jugador
                                  JOIN equipo e ON e.id_equipo = pp.id_equipo
                                  WHERE pp.id_partido = %s ORDER BY e.nombre, j.apellido""", (id_partido,))
    disponibles = db.consultar("""SELECT ejt.ci_jugador, j.nombre, j.apellido, e.nombre AS equipo
                                  FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador
                                  JOIN equipo e ON e.id_equipo = ejt.id_equipo
                                  WHERE ejt.id_equipo IN (%s, %s) AND NOT EXISTS (
                                      SELECT 1 FROM planilla_partido pp
                                      WHERE pp.id_partido = %s AND pp.ci_jugador = ejt.ci_jugador)
                                  ORDER BY e.nombre, j.apellido""",
                               (partido["id_equipo_local"], partido["id_equipo_visitante"], id_partido))
    goles = db.consultar("""SELECT g.*, j.nombre, j.apellido FROM gol g JOIN jugador j ON j.ci = g.ci_jugador
                            WHERE g.id_partido = %s ORDER BY g.minuto""", (id_partido,))
    tarjetas = db.consultar("""SELECT t.*, j.nombre, j.apellido FROM tarjeta t JOIN jugador j ON j.ci = t.ci_jugador
                               WHERE t.id_partido = %s ORDER BY t.minuto""", (id_partido,))
    return render_template("planilla.html", partido=partido, en_planilla=en_planilla, disponibles=disponibles,
                           goles=goles, tarjetas=tarjetas)


@app.post("/partidos/<int:id_partido>/planilla/agregar")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def agregar_a_planilla(id_partido):
    def accion():
        ci = v.ci(request.form, "ci_jugador")
        reglas.verificar_planilla_editable(id_partido)
        id_equipo = reglas.equipo_para_planilla(id_partido, ci)
        db.ejecutar("INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, %s)",
                    (id_partido, ci, id_equipo))
    realizar(accion, "Jugador agregado a la planilla.")
    return volver()


@app.post("/partidos/<int:id_partido>/planilla/<ci>/quitar")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def quitar_de_planilla(id_partido, ci):
    def accion():
        reglas.verificar_planilla_editable(id_partido)
        db.ejecutar("DELETE FROM planilla_partido WHERE id_partido = %s AND ci_jugador = %s", (id_partido, ci))
    realizar(accion, "Jugador quitado de la planilla (y sus goles y tarjetas).")
    return volver()


@app.post("/partidos/<int:id_partido>/goles")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def agregar_gol(id_partido):
    def accion():
        f = request.form
        datos = (id_partido, v.ci(f, "ci_jugador"), v.entero(f, "minuto", 0, 60), v.casilla(f, "autogol"))
        reglas.verificar_planilla_editable(id_partido)
        db.ejecutar("INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (%s, %s, %s, %s)", datos)
    realizar(accion, "Gol registrado.")
    return volver()


@app.post("/goles/<int:id_gol>/eliminar")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def eliminar_gol(id_gol):
    def accion():
        gol = db.consultar_uno("SELECT id_partido FROM gol WHERE id_gol = %s", (id_gol,))
        reglas.verificar_planilla_editable(gol["id_partido"])
        db.ejecutar("DELETE FROM gol WHERE id_gol = %s", (id_gol,))
    realizar(accion, "Gol eliminado.")
    return volver()


@app.post("/partidos/<int:id_partido>/tarjetas")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def agregar_tarjeta(id_partido):
    def accion():
        f = request.form
        ci, minuto, color = v.ci(f, "ci_jugador"), v.entero(f, "minuto", 0, 60), v.opcion(f, "color", COLORES_TARJETA)
        reglas.verificar_planilla_editable(id_partido)
        id_tarjeta = db.insertar("INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s, %s, %s, %s)",
                                 (id_partido, ci, minuto, color))
        reglas.sancionar_por_tarjeta(id_tarjeta, id_partido, ci, color)  # misma transacción: se guardan las dos o ninguna
    realizar(accion, "Tarjeta registrada.")
    return volver()


@app.post("/tarjetas/<int:id_tarjeta>/eliminar")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def eliminar_tarjeta(id_tarjeta):
    def accion():
        tarjeta = db.consultar_uno("SELECT id_partido FROM tarjeta WHERE id_tarjeta = %s", (id_tarjeta,))
        reglas.verificar_planilla_editable(tarjeta["id_partido"])
        db.ejecutar("DELETE FROM tarjeta WHERE id_tarjeta = %s", (id_tarjeta,))
    realizar(accion, "Tarjeta eliminada (y la sanción que hubiera generado).")
    return volver()


@app.post("/partidos/<int:id_partido>/jugado")
@requiere(ROL_ADMIN, ROL_PLANILLERO)
def marcar_jugado(id_partido):
    def accion():
        partido = db.consultar_uno("SELECT * FROM partido WHERE id_partido = %s", (id_partido,))
        reglas.verificar_partido_no_jugado(id_partido)
        partido["estado"] = ESTADO_JUGADO
        reglas.verificar_partido(partido)
        db.ejecutar("UPDATE partido SET estado = %s WHERE id_partido = %s", (ESTADO_JUGADO, id_partido))
    realizar(accion, "Partido marcado como jugado.")
    return volver()


# ---------------------------------------------------------------- sanciones

@app.route("/sanciones")
@requiere(ROL_ADMIN)
def sanciones():
    torneos, torneo = torneos_y_elegido()
    id_torneo = torneo["id_torneo"] if torneo else None
    lista = db.consultar("""SELECT s.*, j.nombre, j.apellido, e.nombre AS equipo FROM sancion_jugador s
                            JOIN jugador j ON j.ci = s.ci_jugador
                            JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
                            JOIN equipo e ON e.id_equipo = ejt.id_equipo
                            WHERE s.id_torneo = %s ORDER BY s.numero_fecha_inicio, j.apellido""", (id_torneo,))
    editando = db.consultar_uno("SELECT * FROM sancion_jugador WHERE id_sancion = %s", (request.args.get("editar"),))
    return render_template("sanciones.html", torneos=torneos, torneo=torneo, sanciones=lista, editando=editando,
                           jugadores=jugadores_del_torneo(id_torneo))


def jugadores_del_torneo(id_torneo) -> list[dict]:
    return db.consultar("""SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo FROM equipo_jugador_torneo ejt
                           JOIN jugador j ON j.ci = ejt.ci_jugador JOIN equipo e ON e.id_equipo = ejt.id_equipo
                           WHERE ejt.id_torneo = %s ORDER BY e.nombre, j.apellido""", (id_torneo,))


@app.post("/sanciones/guardar")
@requiere(ROL_ADMIN)
def guardar_sancion():
    def accion():
        f = request.form
        ci = v.opcion(f, "ci_jugador", ids(jugadores_del_torneo(f.get("id_torneo")), "ci"))
        motivo = v.opcion(f, "motivo", MOTIVOS_SANCION)
        inicio, cantidad = v.entero(f, "numero_fecha_inicio", 1, 50), v.entero(f, "cantidad_fechas", 1, 20)
        if f.get("id_sancion"):
            db.ejecutar("""UPDATE sancion_jugador SET ci_jugador = %s, motivo = %s, numero_fecha_inicio = %s,
                           cantidad_fechas = %s WHERE id_sancion = %s""", (ci, motivo, inicio, cantidad, f["id_sancion"]))
        else:
            db.ejecutar("""INSERT INTO sancion_jugador (ci_jugador, motivo, numero_fecha_inicio, cantidad_fechas, id_torneo)
                           VALUES (%s, %s, %s, %s, %s)""", (ci, motivo, inicio, cantidad, f["id_torneo"]))
    realizar(accion, "Sanción guardada.")
    return volver()


@app.post("/sanciones/<int:id_sancion>/eliminar")
@requiere(ROL_ADMIN)
def eliminar_sancion(id_sancion):
    def accion():
        db.ejecutar("DELETE FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
    realizar(accion, "Sanción eliminada.")
    return volver()


# ---------------------------------------------------------------- reportes

@app.route("/reportes")
@requiere(ROL_ADMIN)
def reportes():
    torneos, torneo = torneos_y_elegido()
    parametros = {"torneo": torneo["id_torneo"] if torneo else None}
    resultados = [(reporte.titulo, db.consultar(reporte.sql, parametros)) for reporte in REPORTES]
    return render_template("reportes.html", torneos=torneos, torneo=torneo, resultados=resultados)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
