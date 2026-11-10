"""Reglas de negocio de la letra. Cada función consulta la base y lanza ValueError si la regla no se cumple.
Se ejecutan dentro de la transacción de la acción (ver realizar en app.py)."""
import db
from opciones import (ESTADO_CANCELADO, ESTADO_EN_CURSO, ESTADO_FINALIZADO, ESTADO_INSCRIPCION, ESTADO_JUGADO,
                      ESTADO_POSTERGADO, ESTADO_PROGRAMADO, ESTADOS_TORNEO, MOTIVO_AMARILLAS, MOTIVO_ROJA, TARJETA_ROJA,
                      TIPOS_LIMITADOS)

# Los números que pide la letra, con nombre para no tenerlos sueltos en el código.
MINIMO_PLANTEL = 5
MAXIMO_PLANTEL = 10
MAXIMO_DOCENTES_FUNCIONARIOS = 2
AMARILLAS_PARA_SUSPENSION = 3


# Cuántos jugadores tiene un equipo. Con ["n"] sacamos el valor del alias AS n.
def cantidad_en_plantel(id_equipo) -> int:
    return db.consultar_uno("SELECT COUNT(*) AS n FROM equipo_jugador_torneo WHERE id_equipo = %s", (id_equipo,))["n"]


# ---------------------------------------------------------------- torneo

# Según la letra, los planteles solo se pueden tocar mientras el torneo está en inscripción.
def verificar_inscripcion(id_torneo) -> None:
    torneo = db.consultar_uno("SELECT estado FROM torneo WHERE id_torneo = %s", (id_torneo,))
    if torneo["estado"] != ESTADO_INSCRIPCION:
        raise ValueError("Equipos y planteles solo pueden modificarse durante la inscripción.")


# Las etapas solo avanzan: inscripción, en curso, finalizado.
# Comparamos la posición de cada estado en la lista: si el nuevo está antes que el actual, es volver para atrás.
def verificar_cambio_de_estado(id_torneo, estado_nuevo: str) -> None:
    estado_actual = db.consultar_uno("SELECT estado FROM torneo WHERE id_torneo = %s", (id_torneo,))["estado"]
    etapas = list(ESTADOS_TORNEO)
    if etapas.index(estado_nuevo) < etapas.index(estado_actual):
        raise ValueError("El estado del torneo no puede volver a una etapa anterior.")
    # Cuando se cierra la inscripción los planteles ya no se pueden cambiar,
    # así que antes revisamos que cada equipo tenga capitán y al menos 5 jugadores.
    if estado_actual == ESTADO_INSCRIPCION and estado_nuevo != ESTADO_INSCRIPCION:
        for equipo in db.consultar("SELECT id_equipo, ci_capitan FROM equipo WHERE id_torneo = %s", (id_torneo,)):
            if equipo["ci_capitan"] is None or cantidad_en_plantel(equipo["id_equipo"]) < MINIMO_PLANTEL:
                raise ValueError("Para cerrar la inscripción todos los equipos deben tener capitán "
                                 f"y al menos {MINIMO_PLANTEL} jugadores.")


# ---------------------------------------------------------------- jugadores, equipos y planteles

# Si el jugador ya está en un plantel, no le dejamos cambiar la facultad ni el tipo,
# porque se romperían los controles que se hicieron al agregarlo.
# Usamos str() porque del formulario llega texto y de la base llega un número.
def verificar_cambio_de_jugador(ci, id_facultad, tipo) -> None:
    actual = db.consultar_uno("SELECT id_facultad, tipo FROM jugador WHERE ci = %s", (ci,))
    cambia = str(actual["id_facultad"]) != str(id_facultad) or actual["tipo"] != tipo
    if cambia and db.consultar("SELECT 1 FROM equipo_jugador_torneo WHERE ci_jugador = %s", (ci,)):
        raise ValueError("No se puede cambiar facultad o tipo de un jugador que integra un plantel.")


# Todos los jugadores son de la facultad del equipo, así que con jugadores adentro no se puede cambiar.
def verificar_cambio_de_facultad(id_equipo, id_facultad) -> None:
    actual = db.consultar_uno("SELECT id_facultad FROM equipo WHERE id_equipo = %s", (id_equipo,))
    if str(actual["id_facultad"]) != str(id_facultad) and cantidad_en_plantel(id_equipo) > 0:
        raise ValueError("No se puede cambiar la facultad de un equipo que ya tiene jugadores.")


# El capitán tiene que ser uno de sus jugadores. La FK de ci_capitan solo asegura que el jugador exista.
# Si ci viene vacío, el equipo queda sin capitán y no hay nada que revisar.
def verificar_capitan(id_equipo, ci) -> None:
    if ci and not db.consultar("SELECT 1 FROM equipo_jugador_torneo WHERE id_equipo = %s AND ci_jugador = %s",
                               (id_equipo, ci)):
        raise ValueError("El capitán debe ser un jugador del plantel.")


# Lo que pide la letra para sumar un jugador: que siga la inscripción, que sea de la misma facultad,
# que el plantel no tenga ya 10 y que no se pase de 2 docentes o funcionarios.
# Que no esté en otro equipo de la edición y que la camiseta no se repita ya lo controla la base con UNIQUE.
def verificar_alta_en_plantel(equipo: dict, ci) -> None:
    verificar_inscripcion(equipo["id_torneo"])
    jugador = db.consultar_uno("SELECT id_facultad, tipo FROM jugador WHERE ci = %s", (ci,))
    if jugador is None:
        raise ValueError("El jugador no existe.")
    if jugador["id_facultad"] != equipo["id_facultad"]:
        raise ValueError("El jugador debe pertenecer a la facultad del equipo.")
    if cantidad_en_plantel(equipo["id_equipo"]) >= MAXIMO_PLANTEL:
        raise ValueError(f"El plantel ya tiene {MAXIMO_PLANTEL} jugadores.")
    # Solo si entra un docente o un funcionario contamos cuántos hay. PyMySQL convierte la tupla en la lista del IN.
    if jugador["tipo"] in TIPOS_LIMITADOS:
        limitados = db.consultar_uno("""SELECT COUNT(*) AS n FROM equipo_jugador_torneo ejt
                                        JOIN jugador j ON j.ci = ejt.ci_jugador
                                        WHERE ejt.id_equipo = %s AND j.tipo IN %s""",
                                     (equipo["id_equipo"], TIPOS_LIMITADOS))["n"]
        if limitados >= MAXIMO_DOCENTES_FUNCIONARIOS:
            raise ValueError(f"El plantel ya tiene {MAXIMO_DOCENTES_FUNCIONARIOS} docentes/funcionarios.")


# ---------------------------------------------------------------- partidos

def reservar_torneo(id_torneo) -> None:
    """FOR UPDATE: «leo y me reservo la fila». Si dos administradores programan a la vez, el segundo espera al
    COMMIT del primero. Tiene que ser la primera consulta de la transacción, para que las siguientes vean
    lo que el otro ya confirmó."""
    db.consultar("SELECT id_torneo FROM torneo WHERE id_torneo = %s FOR UPDATE", (id_torneo,))


# La letra dice que un partido jugado no se elimina. Tampoco dejamos modificarlo: lo que se corrige es la planilla.
def verificar_partido_no_jugado(id_partido) -> None:
    partido = db.consultar_uno("SELECT estado FROM partido WHERE id_partido = %s", (id_partido,))
    if partido["estado"] == ESTADO_JUGADO:
        raise ValueError("Un partido jugado no puede modificarse ni eliminarse.")


def verificar_partido(p: dict) -> None:
    """Controles de la letra al programar o modificar un partido. p tiene las columnas de la tabla partido."""
    # Al modificar un partido buscamos choques con otros partidos, no con él mismo: por eso id_partido <> otro.
    # Si es un alta todavía no tiene id, y usamos 0, que no coincide con ninguno.
    otro = p.get("id_partido") or 0  # para no compararlo consigo mismo al modificar
    if db.consultar_uno("SELECT estado FROM torneo WHERE id_torneo = %s", (p["id_torneo"],))["estado"] == ESTADO_FINALIZADO:
        raise ValueError("El torneo ya finalizó.")
    # Los dos equipos tienen que tener al menos 5 jugadores.
    if (cantidad_en_plantel(p["id_equipo_local"]) < MINIMO_PLANTEL
            or cantidad_en_plantel(p["id_equipo_visitante"]) < MINIMO_PLANTEL):
        raise ValueError(f"Ambos equipos deben tener al menos {MINIMO_PLANTEL} jugadores.")

    # Los partidos cancelados no cuentan para estos dos controles (la letra lo permite).
    # Primero, que estos dos equipos no tengan ya un partido entre ellos: los dos tienen que estar en el mismo partido.
    if p["estado"] != ESTADO_CANCELADO:
        # Si la consulta devuelve alguna fila, hay un choque (una lista vacía cuenta como falso).
        if db.consultar("""SELECT 1 FROM partido
                           WHERE id_torneo = %s AND id_partido <> %s AND estado <> %s
                             AND %s IN (id_equipo_local, id_equipo_visitante)
                             AND %s IN (id_equipo_local, id_equipo_visitante)""",
                        (p["id_torneo"], otro, ESTADO_CANCELADO, p["id_equipo_local"], p["id_equipo_visitante"])):
            raise ValueError("Estos equipos ya tienen un partido en esta edición.")
        # Después, que ninguno de los dos juegue otro partido en la misma fecha. Alcanza con que aparezca uno, por eso va OR.
        if db.consultar("""SELECT 1 FROM partido
                           WHERE id_torneo = %s AND id_partido <> %s AND estado <> %s AND numero_fecha = %s
                             AND (%s IN (id_equipo_local, id_equipo_visitante)
                                  OR %s IN (id_equipo_local, id_equipo_visitante))""",
                        (p["id_torneo"], otro, ESTADO_CANCELADO, p["numero_fecha"],
                         p["id_equipo_local"], p["id_equipo_visitante"])):
            raise ValueError("Uno de los equipos ya juega en esa fecha del torneo.")

    # Una cancha no puede tener dos partidos el mismo día y turno. Los postergados y cancelados no la ocupan.
    if p["estado"] in (ESTADO_PROGRAMADO, ESTADO_JUGADO):
        if db.consultar("""SELECT 1 FROM partido
                           WHERE id_partido <> %s AND estado IN (%s, %s) AND dia = %s AND id_turno = %s
                             AND nombre_cancha = %s AND id_complejo = %s""",
                        (otro, ESTADO_PROGRAMADO, ESTADO_JUGADO, p["dia"], p["id_turno"],
                         p["nombre_cancha"], p["id_complejo"])):
            raise ValueError("La cancha ya tiene un partido en ese día y turno.")

    # Solo se puede marcar como jugado si el turno ya terminó. TIMESTAMP junta el día y la hora en un solo valor.
    if p["estado"] == ESTADO_JUGADO:
        # NOW() de la base: una sola hora de referencia, sin importar dónde corra la aplicación
        turno = db.consultar_uno("SELECT TIMESTAMP(%s, hora_fin) > NOW() AS falta FROM turno WHERE id_turno = %s",
                                 (p["dia"], p["id_turno"]))
        if turno["falta"]:
            raise ValueError("Un partido solo puede marcarse como jugado cuando su día y turno ya pasaron.")


# ---------------------------------------------------------------- planilla y sanciones

# La llamamos antes de cualquier cambio en la planilla, los goles o las tarjetas.
# La base calcula si el partido todavía no empezó (no_empezo) y si ya pasaron 48 horas desde que terminó (vencido).
# Cada comparación da 1 si es verdad y 0 si no.
def verificar_planilla_editable(id_partido) -> None:
    """Solo con el partido ya empezado y, si ya está jugado, dentro de las 48 horas posteriores."""
    partido = db.consultar_uno("""SELECT p.estado, tor.estado AS estado_torneo,
                                         TIMESTAMP(p.dia, t.hora_inicio) > NOW() AS no_empezo,
                                         NOW() > TIMESTAMP(p.dia, t.hora_fin) + INTERVAL 48 HOUR AS vencido
                                  FROM partido p
                                  JOIN turno t ON t.id_turno = p.id_turno
                                  JOIN torneo tor ON tor.id_torneo = p.id_torneo
                                  WHERE p.id_partido = %s""", (id_partido,))
    if partido["estado_torneo"] != ESTADO_EN_CURSO:
        raise ValueError("Las planillas solo se registran con el torneo en curso.")
    if partido["estado"] in (ESTADO_POSTERGADO, ESTADO_CANCELADO):
        raise ValueError("El partido está postergado o cancelado.")
    if partido["no_empezo"]:
        raise ValueError("El partido todavía no comenzó.")
    if partido["estado"] == ESTADO_JUGADO and partido["vencido"]:
        raise ValueError("Pasaron más de 48 horas desde el partido: ya no puede corregirse.")


# Buscamos al jugador en los planteles de los dos equipos. Si no está, no puede figurar.
# Después vemos si tiene una sanción que abarque esta fecha: va desde numero_fecha_inicio hasta inicio + cantidad - 1.
# Por ejemplo, si empieza en la fecha 4 y dura 2, abarca la 4 y la 5.
def equipo_para_planilla(id_partido, ci) -> int:
    """Devuelve el equipo del jugador en este partido, si está en el plantel y no está suspendido."""
    partido = db.consultar_uno("""SELECT id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante
                                  FROM partido WHERE id_partido = %s""", (id_partido,))
    plantel = db.consultar_uno("""SELECT id_equipo FROM equipo_jugador_torneo
                                  WHERE ci_jugador = %s AND id_equipo IN (%s, %s)""",
                               (ci, partido["id_equipo_local"], partido["id_equipo_visitante"]))
    if plantel is None:
        raise ValueError("El jugador no pertenece a ninguno de los dos equipos.")
    if db.consultar("""SELECT 1 FROM sancion_jugador
                       WHERE ci_jugador = %s AND id_torneo = %s
                         AND %s BETWEEN numero_fecha_inicio AND numero_fecha_inicio + cantidad_fechas - 1""",
                    (ci, partido["id_torneo"], partido["numero_fecha"])):
        raise ValueError("El jugador está suspendido para esta fecha.")
    return plantel["id_equipo"]


# Se ejecuta en la misma transacción que la tarjeta, así que se guardan las dos o ninguna.
# Las amarillas se cuentan en toda la edición, incluida la que se acaba de cargar.
# Con % vemos el resto de dividir entre 3: si da 0 (3, 6, 9...) toca sanción, y si no, con return termina acá.
# La sanción es para la fecha siguiente. No indicamos cantidad_fechas porque en la tabla vale 1 por defecto.
def sancionar_por_tarjeta(id_tarjeta: int, id_partido, ci, color: str) -> None:
    """Roja, o cada 3 amarillas en la edición: una fecha de suspensión, la siguiente."""
    partido = db.consultar_uno("SELECT id_torneo, numero_fecha FROM partido WHERE id_partido = %s", (id_partido,))
    if color == TARJETA_ROJA:
        motivo = MOTIVO_ROJA
    else:
        amarillas = db.consultar_uno("""SELECT COUNT(*) AS n FROM tarjeta t
                                        JOIN partido p ON p.id_partido = t.id_partido
                                        WHERE t.ci_jugador = %s AND p.id_torneo = %s AND t.color <> %s""",
                                     (ci, partido["id_torneo"], TARJETA_ROJA))["n"]
        if amarillas % AMARILLAS_PARA_SUSPENSION != 0:
            return
        motivo = MOTIVO_AMARILLAS
    db.ejecutar("""INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, id_tarjeta)
                   VALUES (%s, %s, %s, %s, %s)""",
                (ci, partido["id_torneo"], motivo, partido["numero_fecha"] + 1, id_tarjeta))
