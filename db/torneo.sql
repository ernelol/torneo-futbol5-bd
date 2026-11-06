-- =====================================================================
-- Torneo Interfacultades de Fútbol 5 - UCU
-- Script completo: tablas, usuarios de base de datos y datos de prueba
-- =====================================================================

SET NAMES utf8mb4;  -- para que los acentos se carguen bien con cualquier cliente

DROP DATABASE IF EXISTS torneo_futbol5;
CREATE DATABASE torneo_futbol5 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE torneo_futbol5;

-- ---------------------------------------------------------------------
-- 1. TABLAS
-- ---------------------------------------------------------------------

CREATE TABLE login (
    correo     VARCHAR(100) PRIMARY KEY,
    contrasena VARCHAR(255) NOT NULL,  -- hash, nunca texto plano
    rol        ENUM('administrador', 'planillero') NOT NULL,
    CHECK (correo LIKE '%_@_%._%')
);

CREATE TABLE facultad (
    id_facultad INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE jugador (
    ci               VARCHAR(8) PRIMARY KEY,
    nombre           VARCHAR(50) NOT NULL,
    apellido         VARCHAR(50) NOT NULL,
    email            VARCHAR(100) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    id_facultad      INT NOT NULL,
    tipo             ENUM('grado', 'posgrado', 'docente', 'funcionario') NOT NULL,
    FOREIGN KEY (id_facultad) REFERENCES facultad (id_facultad),
    CHECK (ci LIKE '_______' OR ci LIKE '________'),  -- 7 u 8 caracteres
    CHECK (email LIKE '%_@_%._%'),
    CHECK (fecha_nacimiento >= '1920-01-01')
);

CREATE TABLE torneo (
    id_torneo    INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    anio         SMALLINT NOT NULL,
    semestre     TINYINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin    DATE NOT NULL,
    estado       ENUM('inscripcion', 'en_curso', 'finalizado') NOT NULL DEFAULT 'inscripcion',
    UNIQUE (anio, semestre),
    CHECK (semestre IN (1, 2)),
    CHECK (anio BETWEEN 2000 AND 2100),
    CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE equipo (
    id_equipo   INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(60) NOT NULL,
    id_torneo   INT NOT NULL,
    id_facultad INT NOT NULL,
    ci_capitan  VARCHAR(8) NULL,  -- NULL hasta que el equipo tenga jugadores
    UNIQUE (id_torneo, nombre),
    UNIQUE (id_equipo, id_torneo),
    FOREIGN KEY (id_torneo) REFERENCES torneo (id_torneo),
    FOREIGN KEY (id_facultad) REFERENCES facultad (id_facultad)
);

CREATE TABLE equipo_jugador_torneo (
    id_equipo       INT NOT NULL,
    ci_jugador      VARCHAR(8) NOT NULL,
    id_torneo       INT NOT NULL,
    numero_camiseta TINYINT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    UNIQUE (ci_jugador, id_torneo),       -- un jugador, un solo equipo por edición
    UNIQUE (id_equipo, ci_jugador),
    UNIQUE (id_equipo, numero_camiseta),
    FOREIGN KEY (id_equipo, id_torneo) REFERENCES equipo (id_equipo, id_torneo) ON DELETE CASCADE,
    FOREIGN KEY (ci_jugador) REFERENCES jugador (ci),
    CHECK (numero_camiseta BETWEEN 1 AND 99)
);

-- el capitán debe ser uno de los jugadores del plantel del equipo
ALTER TABLE equipo ADD FOREIGN KEY (id_equipo, ci_capitan)
    REFERENCES equipo_jugador_torneo (id_equipo, ci_jugador);

CREATE TABLE complejo (
    id_complejo  INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(80) NOT NULL UNIQUE,
    direccion    VARCHAR(120) NOT NULL,
    departamento ENUM('Artigas', 'Canelones', 'Cerro Largo', 'Colonia', 'Durazno', 'Flores', 'Florida',
                      'Lavalleja', 'Maldonado', 'Montevideo', 'Paysandú', 'Río Negro', 'Rivera', 'Rocha',
                      'Salto', 'San José', 'Soriano', 'Tacuarembó', 'Treinta y Tres') NOT NULL
);

CREATE TABLE cancha (
    nombre_cancha VARCHAR(40) NOT NULL,
    id_complejo   INT NOT NULL,
    superficie    ENUM('sintetico', 'parquet') NOT NULL,
    techada       BOOLEAN NOT NULL,
    PRIMARY KEY (nombre_cancha, id_complejo),
    FOREIGN KEY (id_complejo) REFERENCES complejo (id_complejo)
);

CREATE TABLE turno (
    id_turno    TINYINT PRIMARY KEY,
    hora_inicio TIME NOT NULL UNIQUE,
    hora_fin    TIME NOT NULL,
    CHECK (hora_inicio >= '18:00:00' AND hora_fin <= '23:00:00'),
    CHECK (hora_fin = ADDTIME(hora_inicio, '01:00:00'))
);

CREATE TABLE partido (
    id_partido          INT AUTO_INCREMENT,
    id_torneo           INT NOT NULL,
    numero_fecha        TINYINT NOT NULL,
    id_equipo_local     INT NOT NULL,
    id_equipo_visitante INT NOT NULL,
    dia                 DATE NOT NULL,
    id_turno            TINYINT NOT NULL,
    nombre_cancha       VARCHAR(40) NOT NULL,
    id_complejo         INT NOT NULL,
    estado              ENUM('programado', 'jugado', 'postergado', 'cancelado') NOT NULL DEFAULT 'programado',
    PRIMARY KEY (id_partido, id_torneo),
    UNIQUE (id_partido),  -- planilla_partido referencia solo a id_partido
    -- las FK compuestas garantizan que ambos equipos sean de la misma edición del partido
    FOREIGN KEY (id_equipo_local, id_torneo) REFERENCES equipo (id_equipo, id_torneo),
    FOREIGN KEY (id_equipo_visitante, id_torneo) REFERENCES equipo (id_equipo, id_torneo),
    FOREIGN KEY (id_turno) REFERENCES turno (id_turno),
    FOREIGN KEY (nombre_cancha, id_complejo) REFERENCES cancha (nombre_cancha, id_complejo),
    CHECK (id_equipo_local <> id_equipo_visitante),
    CHECK (numero_fecha >= 1)
);

CREATE TABLE planilla_partido (
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(8) NOT NULL,
    id_equipo  INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    FOREIGN KEY (id_partido) REFERENCES partido (id_partido) ON DELETE CASCADE,
    -- solo jugadores del plantel del equipo
    FOREIGN KEY (id_equipo, ci_jugador) REFERENCES equipo_jugador_torneo (id_equipo, ci_jugador)
);

-- goles y tarjetas apuntan a la planilla: solo puede convertir o ser amonestado quien figura en ella
CREATE TABLE gol (
    id_gol     INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(8) NOT NULL,
    minuto     TINYINT NOT NULL,
    autogol    BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido (id_partido, ci_jugador) ON DELETE CASCADE,
    CHECK (minuto BETWEEN 0 AND 60)
);

CREATE TABLE tarjeta (
    id_tarjeta INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(8) NOT NULL,
    minuto     TINYINT NOT NULL,
    color      ENUM('amarilla', 'roja') NOT NULL,
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido (id_partido, ci_jugador) ON DELETE CASCADE,
    CHECK (minuto BETWEEN 0 AND 60)
);

CREATE TABLE sancion_jugador (
    id_sancion          INT AUTO_INCREMENT PRIMARY KEY,
    ci_jugador          VARCHAR(8) NOT NULL,
    id_torneo           INT NOT NULL,
    motivo              ENUM('roja', 'acumulacion_amarillas', 'disciplinaria') NOT NULL,
    numero_fecha_inicio TINYINT NOT NULL,
    cantidad_fechas     TINYINT NOT NULL DEFAULT 1,
    -- tarjeta que originó la sanción automática (NULL en las disciplinarias)
    id_tarjeta          INT NULL UNIQUE,
    FOREIGN KEY (ci_jugador, id_torneo) REFERENCES equipo_jugador_torneo (ci_jugador, id_torneo),
    FOREIGN KEY (id_tarjeta) REFERENCES tarjeta (id_tarjeta) ON DELETE CASCADE,
    CHECK (numero_fecha_inicio >= 1),
    CHECK (cantidad_fechas BETWEEN 1 AND 20)
);

-- El resultado no se guarda: se calcula a partir de los goles. Un autogol suma para el rival.
CREATE VIEW resultado_partido AS
SELECT p.id_partido,
       (SELECT COUNT(*)
        FROM gol g JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        WHERE g.id_partido = p.id_partido
          AND ((pp.id_equipo = p.id_equipo_local AND NOT g.autogol)
               OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol))) AS goles_local,
       (SELECT COUNT(*)
        FROM gol g JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        WHERE g.id_partido = p.id_partido
          AND ((pp.id_equipo = p.id_equipo_visitante AND NOT g.autogol)
               OR (pp.id_equipo = p.id_equipo_local AND g.autogol))) AS goles_visitante
FROM partido p;

-- Cada partido jugado visto desde cada uno de sus dos equipos: goles a favor (gf) y en contra (gc).
CREATE VIEW resultado_equipo AS
SELECT p.id_equipo_local AS id_equipo, r.goles_local AS gf, r.goles_visitante AS gc
FROM partido p JOIN resultado_partido r ON r.id_partido = p.id_partido
WHERE p.estado = 'jugado'
UNION ALL
SELECT p.id_equipo_visitante, r.goles_visitante, r.goles_local
FROM partido p JOIN resultado_partido r ON r.id_partido = p.id_partido
WHERE p.estado = 'jugado';

-- ---------------------------------------------------------------------
-- 2. USUARIOS DE BASE DE DATOS (permisos diferenciados)
-- ---------------------------------------------------------------------

DROP USER IF EXISTS 'torneo_login'@'%', 'torneo_admin'@'%', 'torneo_planillero'@'%';
CREATE USER 'torneo_login'@'%' IDENTIFIED BY 'login_2026';
CREATE USER 'torneo_admin'@'%' IDENTIFIED BY 'admin_2026';
CREATE USER 'torneo_planillero'@'%' IDENTIFIED BY 'planillero_2026';

-- solo para verificar credenciales al iniciar sesión
GRANT SELECT ON torneo_futbol5.login TO 'torneo_login'@'%';

-- el administrador gestiona todo (excepto la tabla de usuarios de la aplicación)
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.facultad TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.jugador TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.torneo TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.equipo TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.equipo_jugador_torneo TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.complejo TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.cancha TO 'torneo_admin'@'%';
GRANT SELECT ON torneo_futbol5.turno TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.partido TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.planilla_partido TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.gol TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.tarjeta TO 'torneo_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_futbol5.sancion_jugador TO 'torneo_admin'@'%';
GRANT SELECT ON torneo_futbol5.resultado_partido TO 'torneo_admin'@'%';
GRANT SELECT ON torneo_futbol5.resultado_equipo TO 'torneo_admin'@'%';

-- el planillero solo lee lo necesario y registra planillas, goles y tarjetas
GRANT SELECT ON torneo_futbol5.torneo TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.equipo TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.jugador TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.equipo_jugador_torneo TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.turno TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.complejo TO 'torneo_planillero'@'%';
GRANT SELECT, INSERT ON torneo_futbol5.sancion_jugador TO 'torneo_planillero'@'%';  -- sanciones automáticas por tarjeta
GRANT SELECT ON torneo_futbol5.partido TO 'torneo_planillero'@'%';
GRANT SELECT ON torneo_futbol5.resultado_partido TO 'torneo_planillero'@'%';
GRANT UPDATE (estado) ON torneo_futbol5.partido TO 'torneo_planillero'@'%';  -- marcar como jugado
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.planilla_partido TO 'torneo_planillero'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.gol TO 'torneo_planillero'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.tarjeta TO 'torneo_planillero'@'%';

-- ---------------------------------------------------------------------
-- 3. DATOS DE PRUEBA
-- ---------------------------------------------------------------------

-- contraseñas: admin123 / planillero123
INSERT INTO login VALUES
('admin@ucu.edu.uy', 'scrypt:32768:8:1$MaTP8vdaT7el8Lj6$860f59ecf66a0d3cf8151bc882d0b3aeaeefe78eaca9cfc1a1337db09639166204d2f6322ae9d92463fe5a5d84eeec7ef8ac8995c5db02a7453b14540990649c', 'administrador'),
('planillero@ucu.edu.uy', 'scrypt:32768:8:1$yjUyiVZJM5bxtRKq$4261aea9dd820127c092f792a19c7c9abc84ffc0927f0f47c1eb24c9452d540010ac8c4fe571bdc282e01deda118cfa8b14152d38246f0a40b5276bcc45bc8e3', 'planillero');

INSERT INTO facultad (nombre) VALUES
('Ingeniería y Tecnologías'), ('Ciencias Empresariales'), ('Derecho'),
('Psicología'), ('Ciencias de la Salud'), ('Ciencias Humanas'), ('Enfermería');

INSERT INTO turno VALUES
(1, '18:00', '19:00'), (2, '19:00', '20:00'), (3, '20:00', '21:00'),
(4, '21:00', '22:00'), (5, '22:00', '23:00');

INSERT INTO complejo (nombre, direccion, departamento) VALUES
('Complejo Tres Cruces', 'Av. 8 de Octubre 2738', 'Montevideo'),
('Complejo Carrasco', 'Av. Italia 6201', 'Montevideo');

INSERT INTO cancha VALUES
('Cancha 1', 1, 'sintetico', FALSE),
('Cancha 2', 1, 'parquet', TRUE),
('Cancha A', 2, 'sintetico', TRUE);

-- CI de los jugadores de prueba: '4' + facultad + '00000' + número de camiseta
INSERT INTO jugador VALUES
('41000001', 'Martín', 'Pereira', 'martin.pereira@correo.ucu.edu.uy', '2003-04-12', 1, 'grado'),
('41000002', 'Lucas', 'Rodríguez', 'lucas.rodriguez@correo.ucu.edu.uy', '2002-08-30', 1, 'grado'),
('41000003', 'Santiago', 'González', 'santiago.gonzalez@correo.ucu.edu.uy', '2004-01-05', 1, 'grado'),
('41000004', 'Nicolás', 'Fernández', 'nicolas.fernandez@correo.ucu.edu.uy', '2003-11-21', 1, 'grado'),
('41000005', 'Diego', 'López', 'diego.lopez@correo.ucu.edu.uy', '1998-06-17', 1, 'posgrado'),
('41000006', 'Pablo', 'Martínez', 'pablo.martinez@ucu.edu.uy', '1985-02-09', 1, 'docente'),
('41000007', 'Andrés', 'Silva', 'andres.silva@ucu.edu.uy', '1990-10-03', 1, 'funcionario'),
('42000001', 'Federico', 'Sosa', 'federico.sosa@correo.ucu.edu.uy', '2002-03-14', 2, 'grado'),
('42000002', 'Joaquín', 'Ramírez', 'joaquin.ramirez@correo.ucu.edu.uy', '2003-07-22', 2, 'grado'),
('42000003', 'Matías', 'Díaz', 'matias.diaz@correo.ucu.edu.uy', '2001-12-01', 2, 'grado'),
('42000004', 'Agustín', 'Álvarez', 'agustin.alvarez@correo.ucu.edu.uy', '2004-05-19', 2, 'grado'),
('42000005', 'Bruno', 'Castro', 'bruno.castro@correo.ucu.edu.uy', '1997-09-08', 2, 'posgrado'),
('42000006', 'Gonzalo', 'Núñez', 'gonzalo.nunez@correo.ucu.edu.uy', '2002-02-27', 2, 'grado'),
('42000007', 'Rodrigo', 'Méndez', 'rodrigo.mendez@ucu.edu.uy', '1988-04-15', 2, 'funcionario'),
('43000001', 'Facundo', 'Romero', 'facundo.romero@correo.ucu.edu.uy', '2003-09-10', 3, 'grado'),
('43000002', 'Emiliano', 'Suárez', 'emiliano.suarez@correo.ucu.edu.uy', '2002-11-11', 3, 'grado'),
('43000003', 'Tomás', 'Acosta', 'tomas.acosta@correo.ucu.edu.uy', '2004-03-03', 3, 'grado'),
('43000004', 'Ignacio', 'Benítez', 'ignacio.benitez@correo.ucu.edu.uy', '2001-06-25', 3, 'grado'),
('43000005', 'Sebastián', 'Medina', 'sebastian.medina@correo.ucu.edu.uy', '1996-01-30', 3, 'posgrado'),
('43000006', 'Alejandro', 'Herrera', 'alejandro.herrera@ucu.edu.uy', '1979-08-18', 3, 'docente'),
('43000007', 'Maximiliano', 'Torres', 'maximiliano.torres@correo.ucu.edu.uy', '2003-10-07', 3, 'grado'),
('44000001', 'Valentín', 'Rojas', 'valentin.rojas@correo.ucu.edu.uy', '2002-05-05', 4, 'grado'),
('44000002', 'Franco', 'Molina', 'franco.molina@correo.ucu.edu.uy', '2003-12-12', 4, 'grado'),
('44000003', 'Bautista', 'Ortiz', 'bautista.ortiz@correo.ucu.edu.uy', '2004-08-08', 4, 'grado'),
('44000004', 'Thiago', 'Silvera', 'thiago.silvera@correo.ucu.edu.uy', '2002-01-20', 4, 'grado'),
('44000005', 'Felipe', 'Cabrera', 'felipe.cabrera@correo.ucu.edu.uy', '1995-04-04', 4, 'posgrado'),
('44000006', 'Juan', 'Morales', 'juan.morales@correo.ucu.edu.uy', '2003-06-16', 4, 'grado'),
('44000007', 'Mauricio', 'Vázquez', 'mauricio.vazquez@ucu.edu.uy', '1983-07-27', 4, 'docente'),
('45000001', 'Lautaro', 'Giménez', 'lautaro.gimenez@correo.ucu.edu.uy', '2003-02-02', 5, 'grado'),
('45000002', 'Benjamín', 'Ruiz', 'benjamin.ruiz@correo.ucu.edu.uy', '2002-09-09', 5, 'grado'),
('45000003', 'Ramiro', 'Ferreira', 'ramiro.ferreira@correo.ucu.edu.uy', '2004-04-24', 5, 'grado'),
('45000004', 'Germán', 'Olivera', 'german.olivera@correo.ucu.edu.uy', '2001-10-10', 5, 'grado'),
('45000005', 'Hernán', 'Da Silva', 'hernan.dasilva@correo.ucu.edu.uy', '1994-12-28', 5, 'posgrado'),
('45000006', 'Leandro', 'Cardozo', 'leandro.cardozo@correo.ucu.edu.uy', '2003-03-13', 5, 'grado'),
('45000007', 'Ricardo', 'Piñeyro', 'ricardo.pineyro@ucu.edu.uy', '1975-05-21', 5, 'docente'),
('46000001', 'Gastón', 'Techera', 'gaston.techera@correo.ucu.edu.uy', '2002-07-07', 6, 'grado'),
('46000002', 'Marcos', 'Viera', 'marcos.viera@correo.ucu.edu.uy', '2003-01-17', 6, 'grado'),
('46000003', 'Esteban', 'Rivero', 'esteban.rivero@correo.ucu.edu.uy', '2004-06-06', 6, 'grado'),
('46000004', 'Bruno', 'Pintos', 'bruno.pintos@correo.ucu.edu.uy', '2001-11-29', 6, 'grado'),
('46000005', 'Damián', 'Correa', 'damian.correa@correo.ucu.edu.uy', '1993-08-14', 6, 'posgrado'),
('46000006', 'Cristian', 'Bentancur', 'cristian.bentancur@correo.ucu.edu.uy', '2003-05-25', 6, 'grado'),
('46000007', 'Óscar', 'Larrosa', 'oscar.larrosa@ucu.edu.uy', '1987-03-19', 6, 'funcionario'),
('47000001', 'Lucía', 'Fagúndez', 'lucia.fagundez@correo.ucu.edu.uy', '2003-09-01', 7, 'grado'),
('47000002', 'Camila', 'Rocha', 'camila.rocha@ucu.edu.uy', '1986-02-11', 7, 'funcionario');

-- Edición actual
INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado) VALUES
('Torneo Interfacultades 2026 - 2.º semestre', 2026, 2, '2026-09-01', '2026-11-30', 'en_curso');

INSERT INTO equipo (nombre, id_torneo, id_facultad) VALUES
('Los Ingenieros', 1, 1), ('Empresariales FC', 1, 2), ('Derecho FC', 1, 3),
('Psico Team', 1, 4), ('Salud United', 1, 5), ('Humanas FC', 1, 6);

-- cada equipo i recibe los 7 jugadores de la facultad i; la camiseta es el último dígito de la cédula
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta)
SELECT id_facultad, ci, 1, ci % 10 FROM jugador WHERE id_facultad <= 6;

UPDATE equipo SET ci_capitan = CONCAT('4', id_equipo, '000001') WHERE id_torneo = 1;

-- Fixture (todos contra todos en 5 fechas). Fechas 1-3 jugadas, 4-5 futuras.
INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
(1, 1, 1, 2, '2026-09-15', 1, 'Cancha 1', 1, 'jugado'),      -- 1
(1, 1, 3, 4, '2026-09-15', 2, 'Cancha 1', 1, 'jugado'),      -- 2
(1, 1, 5, 6, '2026-09-15', 1, 'Cancha 2', 1, 'jugado'),      -- 3
(1, 2, 1, 3, '2026-09-22', 1, 'Cancha 1', 1, 'cancelado'),   -- 4 (se cancela por lluvia)
(1, 2, 2, 5, '2026-09-22', 2, 'Cancha 1', 1, 'jugado'),      -- 5
(1, 2, 4, 6, '2026-09-22', 1, 'Cancha A', 2, 'jugado'),      -- 6
(1, 2, 1, 3, '2026-09-24', 3, 'Cancha 2', 1, 'jugado'),      -- 7 (reprogramación del 4)
(1, 3, 1, 4, '2026-09-29', 1, 'Cancha 1', 1, 'jugado'),      -- 8
(1, 3, 2, 6, '2026-09-29', 2, 'Cancha 2', 1, 'jugado'),      -- 9
(1, 3, 3, 5, '2026-09-29', 3, 'Cancha A', 2, 'jugado'),      -- 10
(1, 4, 1, 5, '2026-11-10', 1, 'Cancha 1', 1, 'postergado'),  -- 11
(1, 4, 2, 4, '2026-11-10', 2, 'Cancha 1', 1, 'programado'),  -- 12
(1, 4, 3, 6, '2026-11-10', 1, 'Cancha A', 2, 'programado'),  -- 13
(1, 5, 1, 6, '2026-11-17', 1, 'Cancha 1', 1, 'programado'),  -- 14
(1, 5, 2, 3, '2026-11-17', 2, 'Cancha 1', 1, 'programado'),  -- 15
(1, 5, 4, 5, '2026-11-17', 1, 'Cancha A', 2, 'programado');  -- 16

-- Planillas: en cada partido jugado juegan las camisetas 1 a 6 (la 7 nunca juega),
-- salvo 41000002, suspendido en la fecha 2 por la roja de la fecha 1.
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo)
SELECT p.id_partido, ejt.ci_jugador, ejt.id_equipo
FROM partido p
JOIN equipo_jugador_torneo ejt ON ejt.id_equipo IN (p.id_equipo_local, p.id_equipo_visitante)
WHERE p.estado = 'jugado' AND ejt.numero_camiseta <= 6
  AND NOT (p.numero_fecha = 2 AND ejt.ci_jugador = '41000002');

INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES
(1, '41000001', 12, FALSE), (1, '41000003', 30, FALSE), (1, '42000004', 41, FALSE),
(2, '43000002', 5, FALSE), (2, '44000001', 22, FALSE), (2, '44000001', 47, FALSE), (2, '43000005', 55, FALSE),
(3, '46000003', 18, FALSE), (3, '45000002', 33, TRUE),
(5, '42000001', 8, FALSE), (5, '42000002', 27, FALSE), (5, '42000001', 49, FALSE), (5, '45000004', 51, FALSE),
(6, '46000001', 35, FALSE),
(7, '41000001', 20, FALSE), (7, '43000003', 44, FALSE),
(8, '41000004', 10, FALSE), (8, '41000001', 39, FALSE), (8, '44000002', 15, FALSE),
(8, '44000005', 50, FALSE), (8, '44000001', 58, FALSE),
(10, '43000001', 3, FALSE), (10, '45000003', 29, FALSE), (10, '43000006', 40, FALSE);

INSERT INTO tarjeta (id_tarjeta, id_partido, ci_jugador, minuto, color) VALUES
(1, 1, '41000002', 25, 'roja'),
(2, 1, '42000003', 40, 'amarilla'),
(3, 2, '44000001', 15, 'amarilla'),
(4, 5, '42000003', 31, 'amarilla'),
(5, 6, '46000004', 52, 'amarilla'),
(6, 9, '42000003', 12, 'amarilla'),  -- 3.ª amarilla de 42000003
(7, 10, '45000001', 47, 'roja'),
(8, 8, '44000001', 33, 'amarilla');

INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta) VALUES
('41000002', 1, 'roja', 2, 1, 1),
('42000003', 1, 'acumulacion_amarillas', 4, 1, 6),
('45000001', 1, 'roja', 4, 1, 7),
('43000004', 1, 'disciplinaria', 4, 2, NULL);

-- Próxima edición, todavía en inscripción (para probar el ABM de planteles)
INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin) VALUES
('Torneo Interfacultades 2027 - 1.er semestre', 2027, 1, '2027-03-15', '2027-06-30');
INSERT INTO equipo (nombre, id_torneo, id_facultad) VALUES ('Los Ingenieros', 2, 1);
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(7, '41000001', 2, 10), (7, '41000003', 2, 7), (7, '41000006', 2, 1);
