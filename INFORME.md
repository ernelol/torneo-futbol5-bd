# Informe — Sistema de gestión del Torneo Interfacultades de Fútbol 5

Base de Datos 1, Universidad Católica del Uruguay, segundo semestre de 2026.

Repositorio: https://github.com/ernelol/torneo-futbol5-bd

## 1. Decisiones de implementación

### Arquitectura
- **Flask y plantillas HTML.** El frontend se genera en el servidor con Jinja y no hay un framework de frontend aparte.
  Para un sistema de formularios y tablas alcanza, y evita mantener una API y una aplicación cliente por separado.
- **PyMySQL sin ORM.** Todas las consultas están escritas en SQL y usan parámetros (`%s`), sin concatenar datos del usuario, lo que evita la inyección SQL.
- **Una conexión por pedido** (`db.py`). Cada acción corre en una transacción: si algo falla, se hace `rollback`.

### Dónde está cada regla
Se usan temas del curso: restricciones, vistas, joins, funciones de agregación, privilegios y transacciones.
No se usan triggers ni procedimientos almacenados. Lo que la base puede garantizar con claves y `CHECK`
queda en la base; lo demás está en `reglas.py`, escrito una sola vez, como consultas SQL dentro de la transacción de cada acción.

| Regla | Dónde se controla |
|---|---|
| Ambos equipos del partido son de la misma edición | FK compuesta `(id_equipo, id_torneo)` → `equipo` |
| Un equipo no se enfrenta a sí mismo | `CHECK (id_equipo_local <> id_equipo_visitante)` y `app.py` |
| El capitán es un jugador del plantel | `verificar_capitan`, además de la FK `ci_capitan` → `jugador` |
| Un jugador integra un solo equipo por edición | `UNIQUE (ci_jugador, id_torneo)` |
| En la planilla solo hay jugadores del plantel | FK `(id_equipo, ci_jugador)` → `equipo_jugador_torneo` |
| Solo convierten o son amonestados los que están en la planilla | FK de `gol` y `tarjeta` → `planilla_partido` |
| Plantel de hasta 10 jugadores, de la facultad del equipo, como máximo 2 docentes/funcionarios | `verificar_alta_en_plantel` |
| Planteles y equipos solo se modifican durante la inscripción | `verificar_inscripcion` |
| Para cerrar la inscripción, todos los equipos tienen capitán y al menos 5 jugadores | `verificar_cambio_de_estado` |
| El torneo no vuelve a una etapa anterior | `verificar_cambio_de_estado` |
| Al menos 5 jugadores por equipo, sin rival repetido salvo cancelación, un partido por fecha, cancha libre | `verificar_partido` |
| Solo se marca como jugado si el día y el turno ya pasaron | `verificar_partido` |
| Un partido jugado no se elimina ni se modifica | `verificar_partido_no_jugado` |
| Un suspendido no figura en la planilla | `equipo_para_planilla` |
| La planilla se corrige solo dentro de las 48 horas | `verificar_planilla_editable` |
| Sanción automática por roja o por cada 3 amarillas | `sancionar_por_tarjeta` |

### Versión de MySQL
El `docker-compose` inicial del curso usa MySQL 5.7, pero acá se usa MySQL 8.4. Antes de la versión 8.0.16, MySQL acepta los `CHECK` pero
no los aplica, y la letra pide validar también en la base de datos. Del compose del curso se tomaron el juego de caracteres y el volumen `mysql_data`.

### Transacciones y ACID
| Propiedad | En este sistema |
|---|---|
| Atomicidad | Cada acción termina en `commit` o, ante un error, en `rollback` (función `realizar`). Una tarjeta y la sanción que genera se guardan juntas o no se guarda ninguna. |
| Consistencia | Claves primarias y foráneas, `UNIQUE`, `CHECK` y las reglas de `reglas.py`. |
| Aislamiento | `SELECT ... FOR UPDATE` al programar un partido y al agregar a un plantel: si dos usuarios lo hacen a la vez, el segundo espera al `COMMIT` del primero y decide con datos actualizados. |
| Durabilidad | La garantiza el motor: lo confirmado sobrevive a un corte. |

Las transacciones son cortas: empiezan y terminan dentro de un mismo pedido, nunca quedan abiertas esperando al usuario.

### Validación en las tres capas
- **Frontend:** atributos HTML (`required`, `min`, `max`, `maxlength`, `pattern`, `type="email"`, `type="date"`).
- **Backend:** `validacion.py` controla el formato, los rangos y que los valores de las listas sean válidos.
- **Base de datos:** tipos, `NOT NULL`, `ENUM`, `CHECK`, claves primarias, foráneas y únicas.

### Seguridad
- Las contraseñas se guardan con hash (scrypt, mediante `werkzeug.security`), nunca en texto plano.
- **Tres usuarios de base de datos con permisos distintos**, y la aplicación se conecta con el que corresponde al rol:
  - `torneo_login`: solo puede leer la tabla `login` (para iniciar sesión).
  - `torneo_admin`: lectura y escritura sobre las tablas del torneo, pero no sobre `login`.
  - `torneo_planillero`: lectura de lo necesario, alta y baja en `planilla_partido`, `gol` y `tarjeta`, y
    `UPDATE` **solo de la columna `estado`** de `partido` (para marcarlo como jugado).
    Sobre `sancion_jugador` solo tiene lectura y alta, para las sanciones automáticas por tarjeta.
- Las páginas también controlan el rol (decorador `requiere`).

## 2. Mejoras al modelo de datos

- **El resultado no se guarda: se calcula** con la vista `resultado_partido` a partir de los goles
  (el autogol suma para el rival). Así es imposible que el resultado y los goles no coincidan.
- **`partido` tiene además `UNIQUE (id_partido)`.** La clave primaria es `(id_partido, id_torneo)`, como pide la letra, pero `planilla_partido`
  referencia solo a `id_partido`, y una clave foránea necesita apuntar a una clave completa.
- **`sancion_jugador.id_tarjeta`** (nueva columna): vincula una sanción automática con la tarjeta que la generó.
  Si se corrige la planilla y se borra la tarjeta, la sanción se borra sola (`ON DELETE CASCADE`).
- **Claves únicas adicionales:** `torneo (anio, semestre)`, `equipo (id_torneo, nombre)`, camiseta única por equipo,
  `jugador.email` y `complejo.nombre`.
- **`complejo.departamento`** es un `ENUM` con los 19 departamentos del Uruguay.
- **`turno`** tiene un `CHECK` que exige turnos de una hora entre las 18:00 y las 23:00.
- Los valores de los `ENUM` van sin tildes ni espacios (`inscripcion`, `en_curso`, `acumulacion_amarillas`).
  La aplicación los muestra con su texto correcto.

**Consideradas y no implementadas:** validar el dígito verificador de la cédula, una tabla de árbitros/planilleros
asignados a cada partido, y que dos amarillas en un mismo partido equivalgan a una roja.

**Limitaciones conocidas (se dejaron así por simplicidad):**
- Las reglas de `reglas.py` se aplican al usar la aplicación: quien modifique la base directamente con un usuario
  con permisos puede saltearlas. Las claves, los `CHECK` y los permisos rigen siempre.
- Si se cambian los equipos de un partido que ya tiene planilla cargada, hay que quitar y volver a cargar esa planilla.
- Si se corrige una planilla borrando una amarilla anterior a la tercera, la suspensión por acumulación no se recalcula:
  el administrador la elimina desde el ABM de sanciones. Si se borra la tercera amarilla, la sanción se borra sola.
- Las contraseñas de los usuarios de base de datos están en el script y tienen valores por defecto en la aplicación.
  Sirve para un trabajo académico; en producción irían solo en variables de entorno.

## 3. Consultas propuestas
1. **Jugadores al borde de la suspensión:** los que tienen 2 amarillas acumuladas y se suspenden con la próxima.
   Le sirve a la organización y a los capitanes.
2. **Jugadores con más partidos disputados:** mide la participación y el compromiso.
3. **Próximos partidos programados:** ayuda a la organización a preparar canchas y planilleros.

## 4. Datos de prueba
`db/torneo.sql` carga 7 facultades, 44 jugadores, 2 complejos con 3 canchas y 5 turnos, y 2 ediciones:
- **2026, 2.º semestre (en curso):** 6 equipos de 7 jugadores y fixture completo de 5 fechas.
  Las fechas 1 a 3 están jugadas e incluyen un partido cancelado y reprogramado.
  Las fechas 4 y 5 están programadas e incluyen un partido postergado.
  Hay goles, un autogol, tarjetas rojas, una suspensión por 3 amarillas y una sanción disciplinaria de 2 fechas.
- **2027, 1.er semestre (en inscripción):** un equipo con 3 jugadores, para probar el ABM de planteles.

## 5. Bitácora
Todas las etapas se hicieron con asistencia de Claude Code (ver sección 6).

| Etapa | Trabajo realizado |
|---|---|
| 1. Primera versión | Modelo de datos, script SQL, usuarios de base de datos, datos de prueba, aplicación Flask y Docker Compose. Pruebas sobre MariaDB. |
| 2. Revisión contra la letra | Se exige plantel completo y capitán para cerrar la inscripción, se valida que la fecha de nacimiento no sea futura, se corrige el porcentaje de partidos, la clave de `partido` pasa a ser la de la letra y se valida el login en el backend. |
| 3. Revisión contra los materiales del curso | Las reglas pasan de triggers a consultas en Python, porque los triggers no están en los materiales. Se usan vistas para los resultados y `FOR UPDATE` para el aislamiento, se quitan funciones de SQL que no figuran en ellos y el capitán pasa a una FK simple hacia `jugador`, más un control en `reglas.py`. Pruebas de las reglas sobre MariaDB. |
| Pendiente | Prueba con `docker compose up` sobre MySQL 8.4. |

## 6. Uso de inteligencia artificial
Según lo que pide el syllabus de la materia (sección 1.5), se declara que se usó Claude Code (modelo Claude Opus 5.5, de Anthropic)
como asistente para diseñar el modelo y escribir el código, los datos de prueba, las pruebas y este informe.
El trabajo se revisó contra la letra y los materiales del curso. Los datos de prueba son inventados.

## 7. Bibliografía
- Universidad Católica del Uruguay. Base de Datos I: *Syllabus 2026-2*, presentaciones *SQL*, *JOIN en SQL*, *Seguridad*, *Transacciones y ACID* y *Ejemplo de PRIMARY KEY y FOREIGN KEY*, y `docker-compose` inicial.
- Anthropic. (2026). *Claude Code* (Claude Opus 5.5) [Asistente de inteligencia artificial]. https://claude.ai/code
- Oracle. *MySQL 8.4 Reference Manual*: "CHECK Constraints" y "GRANT Statement". https://dev.mysql.com/doc/refman/8.4/en/
- Pallets. *Flask Documentation (3.1.x)*: "Message Flashing". https://flask.palletsprojects.com/en/stable/patterns/flashing/
- *PyMySQL Documentation*: "Installation". https://pymysql.readthedocs.io/en/latest/user/installation.html
- Docker Hub. *mysql (imagen oficial)*. https://hub.docker.com/_/mysql
- W3Schools. *MySQL Functions*. https://www.w3schools.com/mysql/mysql_ref_functions.asp
