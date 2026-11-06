# Torneo Interfacultades de Fútbol 5 — UCU

Sistema para gestionar el torneo: jugadores, equipos y planteles, complejos y canchas, fixture,
planillas (goles y tarjetas), sanciones y reportes.

- **Backend:** Python 3 + Flask, consultas SQL escritas a mano con PyMySQL (sin ORM).
- **Frontend:** páginas HTML generadas por Flask (plantillas Jinja).
- **Base de datos:** MySQL 8 (todo en `db/torneo.sql`).

## Usuarios de prueba

| Correo                  | Contraseña      | Rol           |
|-------------------------|-----------------|---------------|
| `admin@ucu.edu.uy`      | `admin123`      | Administrador |
| `planillero@ucu.edu.uy` | `planillero123` | Planillero    |

## Opción A: con Docker

```bash
docker compose up --build
```

Abrir <http://localhost:5000>. La primera vez MySQL ejecuta `db/torneo.sql`, lo que tarda unos segundos.
Para volver a cargar la base desde cero: `docker compose down -v` y luego `docker compose up --build`.

## Opción B: sin Docker

Requisitos: Python 3.10 o superior y MySQL 8 corriendo en el puerto 3306.

1. Crear la base, los usuarios y los datos de prueba:
   ```bash
   mysql -u root -p < db/torneo.sql
   ```
2. Instalar las dependencias:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # en Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Iniciar la aplicación:
   ```bash
   cd app
   python app.py
   ```
4. Abrir <http://localhost:5000>.

Si MySQL no está en `127.0.0.1:3306`, configurar las variables `DB_HOST` y `DB_PORT` antes del paso 3.

> **Si usás MariaDB** y aparece "Access denied for user 'torneo_…'": MariaDB trae un usuario anónimo que
> tapa a los usuarios creados con host `%`. Se soluciona ejecutando como root `DROP USER ''@'localhost';`.

## Estructura

```
db/torneo.sql        tablas, usuarios de BD con permisos y datos de prueba
app/app.py           rutas (pantallas y acciones)
app/db.py            conexión a MySQL según el rol y traducción de errores
app/validacion.py    validación de campos en el servidor
app/reglas.py        reglas de negocio de la letra
app/reportes.py      consultas SQL de los reportes
app/opciones.py      valores de los ENUM y su texto para mostrar
app/templates/       pantallas HTML
INFORME.md           informe del trabajo
```
