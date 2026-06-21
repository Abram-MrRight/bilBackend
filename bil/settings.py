from pathlib import Path
from datetime import timedelta
import os
import boto3
from botocore.client import Config
import environ
from decouple import config
import dj_database_url

# Initialize environ
env = environ.Env()

# Build paths first (before using BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file with proper path
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

CERTS_DIR = "/etc/bil/keys"

PRIVATE_KEY_PATH = os.path.join(CERTS_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(CERTS_DIR, "public_key.pem")

# SECURITY WARNING: keep the secret key used in production secret!
# Use environment variable for secret key in production
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-3x%pek=)69b)*e5vvq4x8hp_@!4+8(=8#_+v9zrg6lndze*&7v')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

# ALLOWED_HOSTS - Use environment variable or default
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", default="").split(",") if host.strip()]

# Extra security for production (only if DEBUG=False)
if not DEBUG:
    # Session security
    SESSION_COOKIE_AGE = 60 * 30        # 30 minutes
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_SAVE_EVERY_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True 
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    LOGIN_ATTEMPTS_LIMIT = 5
else:
    # Development settings
    SESSION_COOKIE_AGE = 60 * 30
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_SAVE_EVERY_REQUEST = True
    LOGIN_ATTEMPTS_LIMIT = 5

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api.apps.ApiConfig',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    'dashboard',
    'widget_tweaks',
    'django.contrib.humanize',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bil.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bil.wsgi.application'


DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL", default="sqlite:///db.sqlite3")
    )
}
# Choose database type based on environment variable
# DATABASE_TYPE = env('DATABASE_TYPE', default='sqlite')

# if DATABASE_TYPE == 'postgresql':
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql',
#             'NAME': env('DB_NAME', default='bilbackend_db'),
#             'USER': env('DB_USER', default='bilbackend_user'),
#             'PASSWORD': env('DB_PASSWORD', default=''),
#             'HOST': env('DB_HOST', default='localhost'),
#             'PORT': env('DB_PORT', default='5432'),
#         }
#     }
# else:  # Default to SQLite
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(env('JWT_ACCESS_MINUTES', default=60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(env('JWT_REFRESH_DAYS', default=1))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

AUTH_USER_MODEL = 'api.User'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

AWS_ACCESS_KEY_ID = env('CLOUDFLARE_R2_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('CLOUDFLARE_R2_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('CLOUDFLARE_R2_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = env('CLOUDFLARE_R2_ENDPOINT_URL', default='')
CLOUDFLARE_R2_CUSTOM_DOMAIN = env('CLOUDFLARE_R2_CUSTOM_DOMAIN', default='')

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

# STATICFILES_STORAGE = 'api.storage_backends.StaticStorage'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEFAULT_FILE_STORAGE = 'api.storage_backends.MediaStorage'

MEDIA_URL = f"https://{CLOUDFLARE_R2_CUSTOM_DOMAIN}/"
# STATIC_URL = f"https://{CLOUDFLARE_R2_CUSTOM_DOMAIN}/static/"

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, "static"),
# ]

# Media files
# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Email settings with fallbacks for CI/testing
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Only use SMTP if credentials are provided, otherwise use console for development
if env('EMAIL_HOST_USER', default='') and env('EMAIL_HOST_PASSWORD', default=''):
    EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
else:
    # Use console backend for development/testing
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Frontend URL
FRONTEND_URL = env('FRONTEND_URL', default='https://bil.atong-abraham.site')

# Logging
LOG_BASE_DIR = env('LOG_BASE_DIR', default=os.path.join(BASE_DIR, 'logs'))
if not os.path.exists(LOG_BASE_DIR):
    os.makedirs(LOG_BASE_DIR, exist_ok=True)

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
#             'style': '{',
#         },
#         'simple': {
#             'format': '{levelname} {asctime} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'file': {
#             'level': 'INFO',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOG_BASE_DIR, 'app.log'),
#             'when': 'D',          # daily-based rotation
#             'interval': 7,        # rotate every 7 days
#             'backupCount': 4,     # keep last 4 log files
#             'formatter': 'verbose',
#             'encoding': 'utf-8',
#         },
#         'console': {
#             'class': 'logging.StreamHandler',
#             'formatter': 'simple',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['file', 'console'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'api': {
#             'handlers': ['file', 'console'],
#             'level': 'DEBUG' if DEBUG else 'INFO',
#             'propagate': True,
#         },
#     },
# }

# Jazzmin settings
JAZZMIN_SETTINGS = {
    "site_title": "BilSend Admin",
    "site_header": "BilSend Dashboard",
    "site_brand": "BilSend",
    "site_icon": None,
    "welcome_sign": "Welcome to BilSend Admin",
    "copyright": "BilSend",
    "search_model": ["api.User", "api.Transaction"],
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Dashboard", "url": "/dashboard/", "new_window": True},
    ],
    "hide_apps": [
        "authtoken",
        "token_blacklist",
    ],
    "hide_models": [
        "contenttypes.contenttype",
        "sessions.session",
    ],
    "order_with_respect_to": [
        "dashboard",
        "api",
        "api.Transaction",
        "api.User",
        "api.Proof",
    ],
    "icons": {
        "dashboard": "fas fa-tachometer-alt",
        "api": "fas fa-cogs",
        "api.User": "fas fa-users",
        "api.Transaction": "fas fa-exchange-alt",
        "api.Proof": "fas fa-image",
        "auth.Group": "fas fa-users",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
}

# Custom admin site configuration for the terminator admin
# This ensures only superusers can access the main admin
ADMIN_URL = 'terminator/'