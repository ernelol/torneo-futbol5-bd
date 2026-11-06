"""Consultas de reportes. Los alias de columna son los encabezados que se muestran en pantalla.
Todas reciben el parámetro %(torneo)s (las que no lo usan lo ignoran)."""
from dataclasses import dataclass


@dataclass
class Reporte:
    titulo: str
    sql: str


REPORTES = [
    # LEFT JOIN: aparecen también los equipos que todavía no jugaron (COALESCE cambia su NULL por 0).
    # En MySQL una comparación vale 1 o 0, así que SUM(r.gf > r.gc) cuenta los partidos ganados.
    Reporte("Tabla de posiciones", """
        SELECT e.nombre AS Equipo,
               COUNT(r.id_equipo) AS PJ,
               COALESCE(SUM(r.gf > r.gc), 0) AS PG,
               COALESCE(SUM(r.gf = r.gc), 0) AS PE,
               COALESCE(SUM(r.gf < r.gc), 0) AS PP,
               COALESCE(SUM(r.gf), 0) AS GF,
               COALESCE(SUM(r.gc), 0) AS GC,
               COALESCE(SUM(r.gf - r.gc), 0) AS DG,
               COALESCE(3 * SUM(r.gf > r.gc) + SUM(r.gf = r.gc), 0) AS Puntos
        FROM equipo e LEFT JOIN resultado_equipo r ON r.id_equipo = e.id_equipo
        WHERE e.id_torneo = %(torneo)s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY Puntos DESC, DG DESC, GF DESC"""),

    Reporte("Goleadores (top 10)", """
        SELECT CONCAT(j.nombre, ' ', j.apellido) AS Jugador, e.nombre AS Equipo, COUNT(*) AS Goles
        FROM gol g
        JOIN partido p ON p.id_partido = g.id_partido
        JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        JOIN jugador j ON j.ci = pp.ci_jugador
        JOIN equipo e ON e.id_equipo = pp.id_equipo
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado' AND NOT g.autogol
        GROUP BY j.ci, j.nombre, j.apellido, e.nombre
        ORDER BY Goles DESC, Jugador
        LIMIT 10"""),

    Reporte("Fair play por equipo (amarilla = 1, roja = 3; gana el menor puntaje)", """
        SELECT e.nombre AS Equipo,
               COALESCE(SUM(t.color = 'amarilla'), 0) AS Amarillas,
               COALESCE(SUM(t.color = 'roja'), 0) AS Rojas,
               COALESCE(SUM(t.color = 'amarilla') + 3 * SUM(t.color = 'roja'), 0) AS Puntaje
        FROM equipo e
        LEFT JOIN planilla_partido pp ON pp.id_equipo = e.id_equipo
        LEFT JOIN tarjeta t ON t.id_partido = pp.id_partido AND t.ci_jugador = pp.ci_jugador
        WHERE e.id_torneo = %(torneo)s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY Puntaje, Equipo"""),

    Reporte("Promedio de goles por partido en cada fecha", """
        SELECT p.numero_fecha AS Fecha, COUNT(*) AS Partidos,
               SUM(r.goles_local + r.goles_visitante) AS Goles,
               ROUND(AVG(r.goles_local + r.goles_visitante), 2) AS Promedio
        FROM partido p JOIN resultado_partido r ON r.id_partido = p.id_partido
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado'
        GROUP BY p.numero_fecha
        ORDER BY p.numero_fecha"""),

    Reporte("Promedio de goles por partido en toda la edición", """
        SELECT COUNT(*) AS Partidos,
               SUM(r.goles_local + r.goles_visitante) AS Goles,
               ROUND(AVG(r.goles_local + r.goles_visitante), 2) AS Promedio
        FROM partido p JOIN resultado_partido r ON r.id_partido = p.id_partido
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado'"""),

    Reporte("Canchas más utilizadas", """
        SELECT CONCAT(c.nombre, ' - ', p.nombre_cancha) AS Cancha, COUNT(*) AS Partidos
        FROM partido p JOIN complejo c ON c.id_complejo = p.id_complejo
        WHERE p.id_torneo = %(torneo)s AND p.estado <> 'cancelado'
        GROUP BY p.id_complejo, p.nombre_cancha, c.nombre
        ORDER BY Partidos DESC, Cancha"""),

    Reporte("Turnos más utilizados", """
        SELECT CONCAT(t.hora_inicio, ' a ', t.hora_fin) AS Turno, COUNT(*) AS Partidos
        FROM partido p JOIN turno t ON t.id_turno = p.id_turno
        WHERE p.id_torneo = %(torneo)s AND p.estado <> 'cancelado'
        GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
        ORDER BY Partidos DESC, Turno"""),

    Reporte("Jugadores por facultad y tipo (todos los registrados)", """
        SELECT f.nombre AS Facultad,
               SUM(j.tipo = 'grado') AS Grado, SUM(j.tipo = 'posgrado') AS Posgrado,
               SUM(j.tipo = 'docente') AS Docente, SUM(j.tipo = 'funcionario') AS Funcionario,
               COUNT(*) AS Total
        FROM jugador j JOIN facultad f ON f.id_facultad = j.id_facultad
        GROUP BY f.id_facultad, f.nombre
        ORDER BY Total DESC, Facultad"""),

    Reporte("Jugadores inscriptos que nunca figuraron en una planilla", """
        SELECT CONCAT(j.nombre, ' ', j.apellido) AS Jugador, e.nombre AS Equipo
        FROM equipo_jugador_torneo ejt
        JOIN jugador j ON j.ci = ejt.ci_jugador
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        WHERE ejt.id_torneo = %(torneo)s
          AND NOT EXISTS (SELECT 1 FROM planilla_partido pp
                          WHERE pp.ci_jugador = ejt.ci_jugador AND pp.id_equipo = ejt.id_equipo)
        ORDER BY Equipo, Jugador"""),

    Reporte("Sanciones por equipo y motivo", """
        SELECT e.nombre AS Equipo, s.motivo AS Motivo, COUNT(*) AS Sanciones
        FROM sancion_jugador s
        JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        WHERE s.id_torneo = %(torneo)s
        GROUP BY e.nombre, s.motivo
        ORDER BY Equipo, Motivo"""),

    Reporte("Porcentaje de partidos jugados, postergados y cancelados", """
        SELECT estado AS Estado, COUNT(*) AS Partidos,
               ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM partido WHERE id_torneo = %(torneo)s AND estado <> 'programado'), 1) AS Porcentaje
        FROM partido
        WHERE id_torneo = %(torneo)s AND estado <> 'programado'
        GROUP BY estado
        ORDER BY Partidos DESC"""),

    # --- Consultas propuestas (la letra pide agregar tres) ---

    Reporte("Propuesta 1: jugadores al borde de la suspensión (una amarilla más y se suspenden)", """
        SELECT CONCAT(j.nombre, ' ', j.apellido) AS Jugador, e.nombre AS Equipo, COUNT(*) AS Amarillas
        FROM tarjeta t
        JOIN partido p ON p.id_partido = t.id_partido
        JOIN planilla_partido pp ON pp.id_partido = t.id_partido AND pp.ci_jugador = t.ci_jugador
        JOIN jugador j ON j.ci = pp.ci_jugador
        JOIN equipo e ON e.id_equipo = pp.id_equipo
        WHERE p.id_torneo = %(torneo)s AND t.color = 'amarilla'
        GROUP BY j.ci, j.nombre, j.apellido, e.nombre
        HAVING COUNT(*) %% 3 = 2
        ORDER BY Equipo, Jugador"""),

    Reporte("Propuesta 2: jugadores con más partidos disputados (top 10)", """
        SELECT CONCAT(j.nombre, ' ', j.apellido) AS Jugador, e.nombre AS Equipo, COUNT(*) AS Partidos
        FROM planilla_partido pp
        JOIN partido p ON p.id_partido = pp.id_partido
        JOIN jugador j ON j.ci = pp.ci_jugador
        JOIN equipo e ON e.id_equipo = pp.id_equipo
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado'
        GROUP BY j.ci, j.nombre, j.apellido, e.nombre
        ORDER BY Partidos DESC, Jugador
        LIMIT 10"""),

    Reporte("Propuesta 3: próximos partidos programados", """
        SELECT p.numero_fecha AS Fecha, p.dia AS Dia, t.hora_inicio AS Hora,
               l.nombre AS Local, v.nombre AS Visitante, p.nombre_cancha AS Cancha
        FROM partido p
        JOIN turno t ON t.id_turno = p.id_turno
        JOIN equipo l ON l.id_equipo = p.id_equipo_local
        JOIN equipo v ON v.id_equipo = p.id_equipo_visitante
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'programado'
        ORDER BY p.dia, t.hora_inicio"""),
]
