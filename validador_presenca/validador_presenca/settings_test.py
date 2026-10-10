"""
Settings exclusivos para a suíte de testes.

Herda tudo de settings.py e troca apenas o que depende de serviço externo:
- Postgres (Neon) -> SQLite em memória, criado e descartado a cada execução
- Redis (Upstash) -> cache local em memória

Assim os testes rodam em máquina limpa, sem .env e sem rede.
Uso: pytest --ds=validador_presenca.settings_test
"""

import os

# settings.py lê essas variáveis com os.environ[...] na importação;
# setdefault garante que existam numa máquina sem .env (e não sobrescreve se já existirem)
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", "gF3Yc1tq8v0n6Z7Qm0j6Q2k1oW8m7xT9yH3bV5sR4aE=")

from .settings import *  # noqa: E402,F401,F403

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

# hasher rápido só para os testes (argon2 deixa a suíte lenta sem ganho nenhum aqui)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
