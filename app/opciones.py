"""Valores válidos de los ENUM de la base y su texto para mostrar."""

ROL_ADMIN = "administrador"
ROL_PLANILLERO = "planillero"

ESTADO_INSCRIPCION = "inscripcion"
ESTADO_EN_CURSO = "en_curso"
ESTADO_FINALIZADO = "finalizado"

ESTADO_PROGRAMADO = "programado"
ESTADO_JUGADO = "jugado"
ESTADO_POSTERGADO = "postergado"
ESTADO_CANCELADO = "cancelado"

TARJETA_ROJA = "roja"
MOTIVO_ROJA = "roja"
MOTIVO_AMARILLAS = "acumulacion_amarillas"
TIPOS_LIMITADOS = ("docente", "funcionario")  # máximo 2 por plantel

TIPOS_JUGADOR = {"grado": "Grado", "posgrado": "Posgrado", "docente": "Docente", "funcionario": "Funcionario"}
ESTADOS_TORNEO = {"inscripcion": "Inscripción", "en_curso": "En curso", "finalizado": "Finalizado"}
ESTADOS_PARTIDO = {"programado": "Programado", "jugado": "Jugado", "postergado": "Postergado", "cancelado": "Cancelado"}
SUPERFICIES = {"sintetico": "Sintético", "parquet": "Parquet"}
COLORES_TARJETA = {"amarilla": "Amarilla", "roja": "Roja"}
MOTIVOS_SANCION = {"roja": "Roja", "acumulacion_amarillas": "Acumulación de amarillas", "disciplinaria": "Disciplinaria"}
DEPARTAMENTOS = {nombre: nombre for nombre in [
    "Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida", "Lavalleja", "Maldonado",
    "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha", "Salto", "San José", "Soriano", "Tacuarembó",
    "Treinta y Tres",
]}

ETIQUETAS = TIPOS_JUGADOR | ESTADOS_TORNEO | ESTADOS_PARTIDO | SUPERFICIES | COLORES_TARJETA | MOTIVOS_SANCION
