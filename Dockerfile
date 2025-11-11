# Usa una imagen oficial de Python
FROM python:3.12

# Define el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los requerimientos e instálalos
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código del proyecto
COPY . /app/

# Expone el puerto donde corre Gunicorn
EXPOSE 8000

# Comando de arranque: aplica migraciones y lanza el servidor
CMD python manage.py migrate --fake-initial && gunicorn gestion_creditos.wsgi
