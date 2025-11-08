# Gestión de Créditos

Aplicación web desarrollada con Django para administrar clientes, créditos, pagos mensuales y abonos parciales. Incluye panel de control, alertas visuales para cuotas vencidas y generación de recibos imprimibles.

## Características principales

- Registro y edición de clientes con búsqueda rápida.
- Creación automática del plan de pagos (amortización francesa) para cada crédito.
- Control de cuotas pendientes, parciales y pagadas, con resaltado de atrasos.
- Registro de pagos y abonos anticipados con validación de saldos.
- Historial completo por crédito, incluyendo recibo imprimible.
- Panel general con métricas: créditos activos, dinero por cobrar, pagos del día/mes y clientes en mora.

## Requisitos

- Python 3.10+
- PostgreSQL (producción) o SQLite (desarrollo)
- Dependencias listadas en `requirements.txt`

## Instalación y uso

### Desarrollo local

```bash
# 1. Clonar el repositorio
git clone https://github.com/kkrakker83/gunther.git
cd gunther

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (opcional para desarrollo)
# Copiar .env.example a .env y ajustar según sea necesario
# Por defecto usa SQLite en desarrollo

# 5. Ejecutar migraciones
export DEBUG=True  # En Windows: set DEBUG=True
python manage.py migrate

# 6. Crear superusuario (opcional)
python manage.py createsuperuser

# 7. Recolectar archivos estáticos
python manage.py collectstatic --noinput

# 8. Ejecutar servidor de desarrollo
python manage.py runserver
```

La aplicación estará disponible en [http://localhost:8000](http://localhost:8000). Desde el panel principal se pueden registrar clientes, crear créditos y administrar los pagos.

### Producción

Para despliegue en producción (Railway, Heroku, etc.):

1. Configurar las siguientes variables de entorno:
   - `SECRET_KEY`: Clave secreta de Django (generada aleatoriamente)
   - `DEBUG`: Establecer en `False`
   - `DATABASE_URL`: URL de conexión a PostgreSQL
   - `ALLOWED_HOSTS`: Dominios permitidos separados por comas
   - `CSRF_TRUSTED_ORIGINS`: Orígenes CSRF de confianza separados por comas

2. El Procfile ya está configurado para usar Gunicorn

3. Los archivos estáticos se sirven mediante WhiteNoise

## Administración

El panel de administración de Django permite gestionar todos los registros desde `/admin/`.

## Tests

Ejecutar la suite de pruebas:

```bash
python manage.py test creditos
```

## Seguridad

- ✅ SECRET_KEY configurado mediante variable de entorno
- ✅ DEBUG desactivado en producción mediante variable de entorno
- ✅ ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS configurables
- ✅ Sin vulnerabilidades conocidas (verificado con CodeQL)
- ✅ Dependencias actualizadas

## Tecnologías

- Django 5.2.8
- PostgreSQL / SQLite
- Bootstrap 5.3.3
- WhiteNoise (archivos estáticos)
- Gunicorn (servidor WSGI)