import os

os.environ.setdefault("DJANGO_SECRET_KEY", "chave-so-para-os-testes")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", "gF3Yc1tq8v0n6Z7Qm0j6Q2k1oW8m7xT9yH3bV5sR4aE=")
os.environ.setdefault("BIOMETRIC_ENCRYPTION_KEY", "s64fCicGMooNDwgQ17HSKUS0jbOL_Gw4KhnOvquFeFs=")

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]