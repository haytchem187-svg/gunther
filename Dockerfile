# Imagen base oficial de Python
FROM python:3.12-slim

# Establece el directorio de trabajo
WORKDIR /app

# Evita que Python genere archivos .pyc y usa salida sin buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copia los archivos del proyecto al contenedor
COPY . /app/

# Instala dependencias
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expone el puerto que Railway usa
EXPOSE 8000

# Comando para iniciar la app
CMD gunicorn gestion_creditos.wsgi:application --bind 0.0.0.0:${PORT:-8000} --timeout 120 --log-file -
