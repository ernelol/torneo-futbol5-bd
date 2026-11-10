"""Validación de campos del lado del servidor. Cada función devuelve el valor ya convertido
o lanza ValueError con un mensaje para el usuario."""
# Esta es la validación del backend. Las otras dos capas son el formulario HTML y la base de datos.
# En cada función, form son los datos del formulario y campo es el nombre del dato a revisar.
import re
from datetime import date

# Expresiones regulares, o sea el formato que tiene que tener el texto.
# La cédula: de 7 a 8 dígitos. El correo: algo, arroba, algo, punto y algo.
PATRON_CI = re.compile(r"^\d{7,8}$")
PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Para los mensajes: "fecha_inicio" se muestra como "fecha inicio".
def _nombre(campo: str) -> str:
    return campo.replace("_", " ")


# Texto obligatorio. strip() le saca los espacios de los costados, y no puede quedar vacío ni pasarse del largo.
def texto(form, campo: str, largo_maximo: int) -> str:
    valor = form.get(campo, "").strip()
    if not valor or len(valor) > largo_maximo:
        raise ValueError(f"El campo {_nombre(campo)} es obligatorio (máximo {largo_maximo} caracteres).")
    return valor


# Número entero dentro de un rango. Si no se puede convertir, int() da error y lo cambiamos por un mensaje claro.
def entero(form, campo: str, minimo: int, maximo: int) -> int:
    try:
        valor = int(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser un número entero.") from None
    if not minimo <= valor <= maximo:
        raise ValueError(f"El campo {_nombre(campo)} debe estar entre {minimo} y {maximo}.")
    return valor


# Fecha válida. Los formularios la mandan como 2026-11-06, que es lo que entiende fromisoformat.
def fecha(form, campo: str) -> date:
    try:
        return date.fromisoformat(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser una fecha válida.") from None


# Fecha que no sea futura, para la fecha de nacimiento. En la base no se puede, porque un CHECK no puede usar la fecha de hoy.
def fecha_pasada(form, campo: str) -> date:
    valor = fecha(form, campo)
    if valor > date.today():
        raise ValueError(f"El campo {_nombre(campo)} no puede ser una fecha futura.")
    return valor


# El valor tiene que estar entre las opciones permitidas, aunque alguien haya tocado la lista del formulario.
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


# Primero se revisa como texto (obligatorio, hasta 100 caracteres) y después el formato.
def email(form, campo: str = "email") -> str:
    valor = texto(form, campo, 100)
    if not PATRON_EMAIL.match(valor):
        raise ValueError("El correo electrónico no es válido.")
    return valor


# Una casilla solo llega en el formulario si está marcada, así que alcanza con ver si vino.
def casilla(form, campo: str) -> bool:
    return campo in form
