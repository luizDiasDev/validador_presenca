# Adsum

**Verificação de Presença Acadêmica em Múltiplos Fatores**

Sistema de registro de presença com validação por múltiplos fatores independentes (QR Code rotativo + token manual + reconhecimento facial com prova de vida), em conformidade com a LGPD.

Projeto Final de Curso do Bacharelado em Engenharia de Software da Universidade de Mogi das Cruzes (UMC), turma 8ºB - semestre 2026/2.

---

## Sumário

- Tech stack
- Estrutura
- Setup local
- Rodar
- Testes
- Infraestrutura
- Documentação
- Time

---

## Tech stack

| Camada             | Tecnologia                                        |
|--------------------|---------------------------------------------------|
| Backend            | Python 3.13, Django 6.1, Django REST Framework    |
| Banco relacional   | PostgreSQL 16 (Neon)                              |
| Cache / QR         | Redis 7 (Upstash)                                 |
| Front-end web      | Django Templates + Tailwind CSS v4 + Alpine.js + HTMX |
| Executável cliente | Python 3.13 + PySide6 + PyInstaller               |
| Facial             | InsightFace                                       |
| 2FA                | pyotp                                             |
| Testes             | pytest-django, factory-boy, fakeredis, Locust     |
| Deploy             | Railway (backend) + Neon (DB) + Upstash (cache)   |

---

## Estrutura

```
validador_presenca/                          # raiz do repo
├── docs/                                    # Ficha, Monografia, DER
├── requirements.txt                         # dependências Python
└── validador_presenca/                      # projeto Django
    ├── manage.py                            # CLI do Django (runserver, migrate)
    ├── pytest.ini                           # config do pytest (aponta pro settings)
    ├── validador_presenca/                  # config raiz (settings, urls)
    ├── apps/                                # apps do projeto
    │   ├── checkin/                         # QR, sessões, máquinas
    │   │   ├── domain/                      # regra de negócio (DDD light)
    │   │   │   ├── services/qr_service.py   # QrTokenService (gera + consome no Redis)
    │   │   │   └── values/qr_token.py       # QrToken (dataclass frozen)
    │   │   ├── migrations/                  # schema do banco
    │   │   ├── models.py                    # Machine, ChamadaSession
    │   │   ├── views.py                     # qr_demo
    │   │   └── tests/test_qr_service.py     # testes do service com fakeredis
    │   └── validator/                       # motor de confiança
    │       ├── domain/                      # regra de negócio (DDD light)
    │       │   ├── engine.py                # calcula veredito final
    │       │   ├── case.py                  # try_checkin (orquestra validators)
    │       │   ├── factory.py               # monta a lista de validadores
    │       │   ├── validation_engines/      # 4 validadores (QR, manual, facial, liveness)
    │       │   └── values/                  # Verdict, FactorResult
    │       ├── migrations/                  # schema do banco
    │       ├── models.py                    # PresencaRecord
    │       └── tests/                       # testes de domain e persistência
    ├── templates/                           # HTML por app
    │   ├── checkin/qr_demo.html             # tela da demo do QR
    │   └── validator/painel.html            # painel do professor
    └── static/images/                       # imagens (logo, divisão)
```

Cada app usa DDD light: a pasta `domain/` guarda regra de negócio (services, value objects) separada de models/views. Referência: `apps/validator/domain/`.

---

## Setup local

### Pré-requisitos

- Python 3.13
- Git
- Credenciais do Neon (Postgres) e Upstash (Redis)

### Passos

Clone o repositório:

```bash
git clone https://github.com/luizDiasDev/validador_presenca.git
cd validador_presenca
```

Cria e ativa o venv.

Windows (PowerShell):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
py -3.13 -m venv .venv
source .venv/bin/activate
```

Instala as dependências:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Cria um `.env` na raiz do repositório:

```
DATABASE_URL=postgresql://usuario:senha@host.neon.tech/neondb?sslmode=require
REDIS_URL=rediss://default:senha@host.upstash.io:6379
```

Aplica as migrations:

```bash
cd validador_presenca
python manage.py migrate
```

---

## Rodar

Servidor de desenvolvimento:

```bash
python manage.py runserver
```

Acesse `http://localhost:8000/`.

Rotas:

- `/checkin/` -> demo do QR Code rotativo
- `/validator/` -> painel do professor
- `/admin/` -> Django Admin

---

## Testes

Rodar tudo:

```bash
pytest
```

Só o check-in:

```bash
pytest apps/checkin/tests/ -v
```

Só o validator:

```bash
pytest apps/validator/tests/ -v
```

Configuração do pytest fica em `pytest.ini`. Os testes usam `fakeredis`, então não precisam do Redis do Upstash rodando local.

---

## Infraestrutura

| Serviço        | Provedor  | Uso                                                          |
|----------------|-----------|--------------------------------------------------------------|
| Backend Django | Railway   | Deploy automático via `git push` em main (ainda não ativo)   |
| PostgreSQL     | Neon      | Banco relacional                                             |
| Redis          | Upstash   | Cache + QR rotativo                                          |

---

## Documentação

Ver `docs/`:

- `Ficha_PFC_UMC_ABNT_ADSUM (ANEXO_I).docx` - escopo do projeto
- `Monografia - Adsum.docx` - texto acadêmico
- `DER_Adsum_OFC_V4.drawio.png` - modelo físico do banco

---

## Time

- **Luiz Eduardo Dias** ([@luizDiasDev](https://github.com/luizDiasDev))
- **Fabricio Rocha de Souza** ([@Fabriciors9](https://github.com/Fabriciors9))
- **Prof. Alessandro Aparecido da Silva Horas** - orientador
