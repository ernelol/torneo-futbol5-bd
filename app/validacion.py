"""Validación de campos del lado del servidor. Cada función devuelve el valor ya convertido
o lanza ValueError con un mensaje para el usuario."""
# Esta es la capa de validación del backend. Las otras dos son el formulario HTML y la base de datos.
# form son los datos del formulario y campo es el nombre del dato que queremos validar.
import re
from datetime import date

# Expresiones regulares: describen el formato que tiene que tener un texto.
# Cédula: de 7 a 8 dígitos. Correo: algo, una arroba, algo, un punto y algo.
PATRON_CI = re.compile(r"^\d{7,8}$")
PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Para los mensajes de error: convierte "fecha_inicio" en "fecha inicio".
def _nombre(campo: str) -> str:
    return campo.replace("_", " ")


# Texto obligatorio. strip() le saca los espacios de los costados, y no puede quedar vacío ni pasarse del largo.
def texto(form, campo: str, largo_maximo: int) -> str:
    valor = form.get(campo, "").strip()
    if not valor or len(valor) > largo_maximo:
        raise ValueError(f"El campo {_nombre(campo)} es obligatorio (máximo {largo_maximo} caracteres).")
    return valor


# Número entero dentro de un rango. Si no se puede convertir, int() lanza ValueError y lo cambiamos por un mensaje claro.
def entero(form, campo: str, minimo: int, maximo: int) -> int:
    try:
        valor = int(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser un número entero.") from None
    if not minimo <= valor <= maximo:
        raise ValueError(f"El campo {_nombre(campo)} debe estar entre {minimo} y {maximo}.")
    return valor


# Fecha válida. Los formularios la mandan como 2026-11-06, que es el formato que lee fromisoformat.
def fecha(form, campo: str) -> date:
    try:
        return date.fromisoformat(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser una fecha válida.") from None


# Fecha que no sea futura. Se usa para la fecha de nacimiento: un CHECK de la base no puede usar la fecha de hoy.
def fecha_pasada(form, campo: str) -> date:
    valor = fecha(form, campo)
    if valor > date.today():
        raise ValueError(f"El campo {_nombre(campo)} no puede ser una fecha futura.")
    return valor


# El valor tiene que estar entre las opciones permitidas. Protege aunque alguien manipule la lista desplegable.
def opcion(form, campo: str, opciones) -> str:
    valor = form.get(campo, "")
    if valor not in opciones:
        raise ValueError(f"Seleccione un valor válido para {_nombre(campo)}.")
    return valor


# Cédula uruguaya: 7 u 8 dígitos, sin puntos ni guion.
def ci(form, campo: str = "ci") -> str:
    valor = form.get(campo, "").strip()
    if not PATRON_CI.match(valor):
        raise ValueError("La cédula debe tener 7 u 8 dígitos, sin puntos ni guion.")
    return valor


# Primero se valida como texto (obligatorio, hasta 100 caracteres) y después su formato.
def email(form, campo: str = "email") -> str:
    valor = texto(form, campo, 100)
    if not PATRON_EMAIL.match(valor):
        raise ValueError("El correo electrónico no es válido.")
    return valor


# Una casilla de verificación solo llega en el formulario si está marcada: por eso alcanza con ver si está.
def casilla(form, campo: str) -> bool:
    return campo in form
