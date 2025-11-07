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
- Dependencias listadas en `requirements.txt`

## Instalación y uso

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # Opcional, para acceder al panel de administración
python manage.py runserver
```

La aplicación estará disponible en [http://localhost:8000](http://localhost:8000). Desde el panel principal se pueden registrar clientes, crear créditos y administrar los pagos.

## Administración

El panel de administración de Django permite gestionar todos los registros desde `/admin/`.