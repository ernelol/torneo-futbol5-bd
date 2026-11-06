# Parte de una imagen que ya trae Python.
FROM python:3.12-slim
WORKDIR /app
# Instala las librerías y copia el código de la aplicación.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
# Lo que se ejecuta al arrancar el contenedor.
CMD ["python", "app.py"]
