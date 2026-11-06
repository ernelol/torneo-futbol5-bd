"""Validación de campos del lado del servidor. Cada función devuelve el valor ya convertido
o lanza ValueError con un mensaje para el usuario."""
import re
from datetime import date

PATRON_CI = re.compile(r"^\d{7,8}$")
PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _nombre(campo: str) -> str:
    return campo.replace("_", " ")


def texto(form, campo: str, largo_maximo: int) -> str:
    valor = form.get(campo, "").strip()
    if not valor or len(valor) > largo_maximo:
        raise ValueError(f"El campo {_nombre(campo)} es obligatorio (máximo {largo_maximo} caracteres).")
    return valor


def entero(form, campo: str, minimo: int, maximo: int) -> int:
    try:
        valor = int(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser un número entero.") from None
    if not minimo <= valor <= maximo:
        raise ValueError(f"El campo {_nombre(campo)} debe estar entre {minimo} y {maximo}.")
    return valor


def fecha(form, campo: str) -> date:
    try:
        return date.fromisoformat(form.get(campo, ""))
    except ValueError:
        raise ValueError(f"El campo {_nombre(campo)} debe ser una fecha válida.") from None


def fecha_pasada(form, campo: str) -> date:
    valor = fecha(form, campo)
    if valor > date.today():
        raise ValueError(f"El campo {_nombre(campo)} no puede ser una fecha futura.")
    return valor


def opcion(form, campo: str, opciones) -> str:
    valor = form.get(campo, "")
    if valor not in opciones:
        raise ValueError(f"Seleccione un valor válido para {_nombre(campo)}.")
    return valor


def ci(form, campo: str = "ci") -> str:
    valor = form.get(campo, "").strip()
    if not PATRON_CI.match(valor):
        raise ValueError("La cédula debe tener 7 u 8 dígitos, sin puntos ni guion.")
    return valor


def email(form, campo: str = "email") -> str:
    valor = texto(form, campo, 100)
    if not PATRON_EMAIL.match(valor):
        raise ValueError("El correo electrónico no es válido.")
    return valor


def casilla(form, campo: str) -> bool:
    return campo in form
