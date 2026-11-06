"""Consultas de reportes. Los alias de columna son los encabezados que se muestran en pantalla.
Todas reciben el parámetro %(torneo)s (las que no lo usan lo ignoran)."""
from dataclasses import dataclass


# Goles de cada partido, calculados a partir de la tabla gol. Un autogol suma para el rival.
RESULTADOS = """(
    SELECT p.id_partido,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_local AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol) THEN 1 ELSE 0 END) AS goles_local,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_visitante AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_local AND g.autogol) THEN 1 ELSE 0 END) AS goles_visitante
    FROM partido p
    LEFT JOIN gol g ON g.id_partido = p.id_partido
    LEFT JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
    GROUP BY p.id_partido
)"""


@dataclass
class Reporte:
    titulo: str
    sql: str


REPORTES = [
    Reporte("Tabla de posiciones", f"""
        SELECT e.nombre AS Equipo,
               COUNT(r.id_equipo) AS PJ,
               COALESCE(SUM(r.gf > r.gc), 0) AS PG,
               COALESCE(SUM(r.gf = r.gc), 0) AS PE,
               COALESCE(SUM(r.gf < r.gc), 0) AS PP,
               COALESCE(SUM(r.gf), 0) AS GF,
               COALESCE(SUM(r.gc), 0) AS GC,
               COALESCE(SUM(r.gf - r.gc), 0) AS DG,
               COALESCE(SUM(3 * (r.gf > r.gc) + (r.gf = r.gc)), 0) AS Puntos
        FROM equipo e
        LEFT JOIN (
            SELECT p.id_equipo_local AS id_equipo, r.goles_local AS gf, r.goles_visitante AS gc
            FROM partido p JOIN {RESULTADOS} r ON r.id_partido = p.id_partido
            WHERE p.estado = 'jugado'
            UNION ALL
            SELECT p.id_equipo_visitante, r.goles_visitante, r.goles_local
            FROM partido p JOIN {RESULTADOS} r ON r.id_partido = p.id_partido
            WHERE p.estado = 'jugado'
        ) r ON r.id_equipo = e.id_equipo
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
               COUNT(CASE t.color WHEN 'amarilla' THEN 1 END) AS Amarillas,
               COUNT(CASE t.color WHEN 'roja' THEN 1 END) AS Rojas,
               COALESCE(SUM(CASE t.color WHEN 'amarilla' THEN 1 WHEN 'roja' THEN 3 END), 0) AS Puntaje
        FROM equipo e
        LEFT JOIN planilla_partido pp ON pp.id_equipo = e.id_equipo
        LEFT JOIN tarjeta t ON t.id_partido = pp.id_partido AND t.ci_jugador = pp.ci_jugador
        WHERE e.id_torneo = %(torneo)s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY Puntaje, Equipo"""),

    Reporte("Promedio de goles por partido", f"""
        SELECT CONCAT('Fecha ', p.numero_fecha) AS Fecha, COUNT(*) AS Partidos,
               SUM(r.goles_local + r.goles_visitante) AS Goles,
               ROUND(AVG(r.goles_local + r.goles_visitante), 2) AS Promedio
        FROM partido p JOIN {RESULTADOS} r ON r.id_partido = p.id_partido
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado'
        GROUP BY p.numero_fecha
        UNION ALL
        SELECT 'Toda la edición', COUNT(*), SUM(r.goles_local + r.goles_visitante),
               ROUND(AVG(r.goles_local + r.goles_visitante), 2)
        FROM partido p JOIN {RESULTADOS} r ON r.id_partido = p.id_partido
        WHERE p.id_torneo = %(torneo)s AND p.estado = 'jugado'
        HAVING COUNT(*) > 0"""),

    Reporte("Canchas más utilizadas", """
        SELECT CONCAT(c.nombre, ' - ', p.nombre_cancha) AS Cancha, COUNT(*) AS Partidos
        FROM partido p JOIN complejo c ON c.id_complejo = p.id_complejo
        WHERE p.id_torneo = %(torneo)s AND p.estado <> 'cancelado'
        GROUP BY p.id_complejo, p.nombre_cancha, c.nombre
        ORDER BY Partidos DESC, Cancha"""),

    Reporte("Turnos más utilizados", """
        SELECT CONCAT(TIME_FORMAT(t.hora_inicio, '%%H:%%i'), ' a ', TIME_FORMAT(t.hora_fin, '%%H:%%i')) AS Turno,
               COUNT(*) AS Partidos
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

    Reporte("Propuesta 3: edad promedio de cada plantel", """
        SELECT e.nombre AS Equipo, COUNT(*) AS Jugadores,
               ROUND(AVG(TIMESTAMPDIFF(YEAR, j.fecha_nacimiento, CURDATE())), 1) AS `Edad promedio`
        FROM equipo e
        JOIN equipo_jugador_torneo ejt ON ejt.id_equipo = e.id_equipo
        JOIN jugador j ON j.ci = ejt.ci_jugador
        WHERE e.id_torneo = %(torneo)s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY `Edad promedio`"""),
]
