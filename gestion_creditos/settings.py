from pathlib import Path
import os
import dj_database_url

# === Rutas base ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === Seguridad ===
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-26*bxygl4h(lnf+@d4n$e=gt11@h1+4w7(h73w5%96&kbsk86k"
)

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# 👇 AÑADIMOS EL DOMINIO DE RAILWAY
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,.railway.app"
).split(",")

# 👇 También confiamos en Railway para CSRF
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1,https://*.railway.app"
).split(",")

# === Aplicaciones instaladas ===
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "creditos.apps.CreditosConfig",
]

# === Middleware ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Manejo de archivos estáticos en producción
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gestion_creditos.urls"

# === Plantillas (Templates) ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gestion_creditos.wsgi.application"

# === Base de datos ===
if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# === Validación de contraseñas ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === Internacionalización ===
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# === Archivos estáticos ===
STATIC_URL = "/static/"
# ⚠️ IMPORTANTE: no incluyas STATICFILES_DIRS si no tienes una carpeta "static" local con archivos
# Si la tienes, puedes dejarlo, pero asegúrate que exista
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# === Campos automáticos por defecto ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Redirecciones post login/logout ===
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
