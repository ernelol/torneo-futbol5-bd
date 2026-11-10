"""Valores válidos de los ENUM de la base y su texto para mostrar."""

# Los roles de la tabla login.
ROL_ADMIN = "administrador"
ROL_PLANILLERO = "planillero"

# Las etapas del torneo.
ESTADO_INSCRIPCION = "inscripcion"
ESTADO_EN_CURSO = "en_curso"
ESTADO_FINALIZADO = "finalizado"

# Los estados de un partido.
ESTADO_PROGRAMADO = "programado"
ESTADO_JUGADO = "jugado"
ESTADO_POSTERGADO = "postergado"
ESTADO_CANCELADO = "cancelado"

# Valores que usan las reglas de sanciones y el límite de docentes o funcionarios.
TARJETA_ROJA = "roja"
MOTIVO_ROJA = "roja"
MOTIVO_AMARILLAS = "acumulacion_amarillas"
TIPOS_LIMITADOS = ("docente", "funcionario")  # máximo 2 por plantel

# Cada diccionario relaciona el valor de la base con el texto que se muestra. Tienen que coincidir con los ENUM de torneo.sql.
# Sirven para armar las listas de los formularios y para validar lo que llega.
TIPOS_JUGADOR = {"grado": "Grado", "posgrado": "Posgrado", "docente": "Docente", "funcionario": "Funcionario"}
ESTADOS_TORNEO = {"inscripcion": "Inscripción", "en_curso": "En curso", "finalizado": "Finalizado"}
ESTADOS_PARTIDO = {"programado": "Programado", "jugado": "Jugado", "postergado": "Postergado", "cancelado": "Cancelado"}
SUPERFICIES = {"sintetico": "Sintético", "parquet": "Parquet"}
COLORES_TARJETA = {"amarilla": "Amarilla", "roja": "Roja"}
MOTIVOS_SANCION = {"roja": "Roja", "acumulacion_amarillas": "Acumulación de amarillas", "disciplinaria": "Disciplinaria"}
# Acá el valor y el texto son iguales, por eso armamos el diccionario desde la lista.
DEPARTAMENTOS = {nombre: nombre for nombre in [
    "Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida", "Lavalleja", "Maldonado",
    "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha", "Salto", "San José", "Soriano", "Tacuarembó",
    "Treinta y Tres",
]}

# Junta todos los diccionarios en uno, para traducir cualquier valor en las pantallas.
ETIQUETAS = TIPOS_JUGADOR | ESTADOS_TORNEO | ESTADOS_PARTIDO | SUPERFICIES | COLORES_TARJETA | MOTIVOS_SANCION
