"""
Django settings for the Dida Motos - Gestão de Estoque project.
"""

from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-ap2cw#yyvds4ip-#_9u2q22fhtu%=rq_zsfl063c5)y+=*hs46",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps do projeto
    "core",
    "pecas",
    "movimentacoes",
    "ordens_servico",
    "fornecedores",
    "relatorios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ForcarTrocaSenhaMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.papel_usuario",
                "core.context_processors.alerta_estoque_baixo",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
#
# Configurado via variáveis de ambiente (arquivo .env na raiz do projeto,
# veja .env.example). Por padrão usa MySQL/MariaDB; para rodar rapidamente
# sem banco instalado, defina DB_ENGINE=sqlite no .env.

if config("DB_ENGINE", default="mysql") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config("DB_NAME", default="dida_motos"),
            "USER": config("DB_USER", default="root"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login/logout
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"


# E-mail (usado no fluxo "Esqueci minha senha")
# https://docs.djangoproject.com/en/5.2/topics/email/
#
# Em desenvolvimento, o backend padrão é "console": o e-mail não é enviado
# de verdade, só aparece impresso no terminal onde o `runserver` está
# rodando (útil para pegar o link de redefinição durante os testes).
# Em produção, defina EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# e as variáveis EMAIL_HOST/EMAIL_PORT/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD/
# EMAIL_USE_TLS no .env (veja .env.example).
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Dida Motos <nao-responda@didamotos.local>")

# Prazo de validade do link de redefinição de senha (em segundos). Padrão
# do Django é 3 dias; deixamos explícito aqui para facilitar ajuste.
PASSWORD_RESET_TIMEOUT = config("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 24 * 3, cast=int)


# Segurança para produção
# https://docs.djangoproject.com/en/5.2/topics/security/
#
# Essas configurações só entram em vigor quando DEBUG=False (ou seja, em
# produção — veja .env.example). Em desenvolvimento (DEBUG=True) elas ficam
# desligadas para não atrapalhar (ex.: exigir HTTPS quebraria o
# runserver em http://localhost). O deploy real precisa estar atrás de
# HTTPS (proxy/servidor com certificado) para essas opções funcionarem.
if not DEBUG:
    # Nunca aceite requisições HTTP puro; redireciona tudo para HTTPS.
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)

    # Cookies de sessão e CSRF só trafegam em conexões HTTPS.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS: instrui o navegador a sempre usar HTTPS com esse domínio pelos
    # próximos 30 dias (2592000s). Começa conservador — pode ser aumentado
    # depois que o HTTPS estiver validado em produção.
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=2592000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
    )
    SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)

    # Evita que o navegador tente "adivinhar" o tipo de um arquivo estático
    # (mitiga alguns ataques de MIME sniffing).
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Impede que o site seja carregado dentro de um <iframe> em outro
    # domínio (proteção contra clickjacking); já há um middleware para
    # isso, aqui só deixamos explícito o valor padrão mais seguro.
    X_FRAME_OPTIONS = "DENY"

    # Cookie de sessão não acessível via JavaScript (mitiga roubo de sessão
    # por XSS). CSRF_COOKIE_HTTPONLY fica de fora porque o front-end usa o
    # cookie csrftoken em alguns formulários enviados via fetch/JS.
    SESSION_COOKIE_HTTPONLY = True
