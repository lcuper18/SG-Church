"""
Production settings.
"""

from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]

# Security settings
# Production always sits behind a reverse proxy (Traefik/nginx) that
# terminates TLS and forwards plain HTTP internally. Without this, Django
# never sees the request as secure and SECURE_SSL_REDIRECT redirects every
# request again even when the client already used HTTPS — an infinite
# redirect loop for every visitor.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS
# "".split(",") is ['' ], a list containing one empty string — django-cors-
# headers rejects that (E013: missing scheme/netloc) and fails every system
# check, so the app never boots. Filter blanks instead.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]

# Static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Several workers serve the site, so the login-attempt counters must live in a cache they
# all share (the default is per-process memory, which would multiply every limit by the
# number of workers). Redis database 1; the Celery broker uses 0. If your proxy is not
# Traefik/nginx in front of a single hop, set TRUSTED_PROXY_COUNT.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("CACHE_URL")
        or os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0").rsplit("/", 1)[0] + "/1",
    }
}
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

# Database connection pooling
DATABASES["default"]["CONN_MAX_AGE"] = 60

# Email (production). SMTP when EMAIL_HOST is set; otherwise messages are only
# written to the log (console backend) so a deploy without mail credentials
# still works. EMAIL_BACKEND can override either choice.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# Logging - send errors to Sentry
if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

    LOGGING["handlers"]["sentry"] = {
        "level": "ERROR",
        "class": "sentry_sdk.django.SentryHandler",
    }
    LOGGING["loggers"]["django"]["handlers"].append("sentry")
