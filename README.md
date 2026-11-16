# Adsum

**Verificação de Presença Acadêmica em Múltiplos Fatores**

Sistema de registro de presença com validação por múltiplos fatores independentes: QR Code rotativo exibido no computador da sala, localização do celular do aluno e reconhecimento facial com prova de vida feito no próprio computador da sala. Atende à LGPD (termos versionados, consentimento biométrico, central de privacidade e trilha de auditoria encadeada por hash).

Projeto Final de Curso do Bacharelado em Engenharia de Software da Universidade de Mogi das Cruzes (UMC), turma 8ºB - semestre 2026/2.

---

## Sumário

- Tech stack
- Estrutura
- Setup local
- Rodar
- Comandos de gerenciamento
- Testes
- Executável da sala
- Infraestrutura
- Documentação
- Time

---

## Tech stack

| Camada             | Tecnologia                                              |
|--------------------|---------------------------------------------------------|
| Backend            | Python 3.13, Django 6.1 (views com HTML e JSON)         |
| Banco relacional   | PostgreSQL 16 (Neon)                                    |
| Cache / QR         | Redis 7 (Upstash)                                       |
| Front-end web      | Django Templates + Tailwind CSS v4 + Lucide + Chart.js (PWA) |
| Executável da sala | Python 3.13 + PySide6 + PyInstaller                     |
| Facial             | InsightFace (buffalo_l) + onnxruntime, no executável    |
| 2FA                | pyotp                                                   |
| Testes             | pytest-django, fakeredis, Locust                        |
| Deploy             | Railway (backend) + Neon (DB) + Upstash (cache)         |

---

## Estrutura

```
validador_presenca/                    # raiz do repo
├── .github/workflows/executavel.yml   # gera o executável da sala a cada push
├── class_client/                      # executável da sala (PySide6)
│   ├── room_app/                      # janela, comunicação com o servidor, captura
│   └── biometrics/                    # InsightFace, qualidade, desafio de cabeça
├── loadtest/                          # teste de carga (Locust)
├── requirements.txt                   # dependências do servidor
├── requirements-dev.txt               # dependências do servidor + testes
└── validador_presenca/                # projeto Django
    ├── manage.py
    ├── validador_presenca/            # settings, urls
    ├── templates/                     # HTML por app
    ├── static/                        # imagens, ícones e manifest do PWA
    └── apps/
        ├── accounts/                  # usuário, perfis, TOTP, sessão única
        ├── audit/                     # trilha de auditoria encadeada por hash
        ├── institution/               # instituição, campus, sala, máquina, pareamento, geolocalização
        ├── privacy/                   # termos, aceites, solicitações LGPD
        ├── validator/                 # motor de confiança e registro de presença
        ├── checkin/                   # chamadas, agendamentos, faltas, QR e telas do aluno
        ├── teacher_panel/             # turmas, disciplinas, aulas, alunos, dashboard, pendências
        ├── biometrics/                # biometria no servidor (cifrada) e comparação
        └── class_client/              # API usada pelo executável da sala
```

Cada app separa a regra de negócio em `domain/` (services, value objects) de models e views.

---

## Setup local

### Pré-requisitos

- Python 3.13
- Git
- Postgres e Redis (Neon e Upstash, ou locais)

### Passos

```bash
git clone https://github.com/luizDiasDev/validador_presenca.git
cd validador_presenca
py -3.13 -m venv .venv
```

Ative o venv (`.\.venv\Scripts\Activate.ps1` no Windows ou `source .venv/bin/activate` no Linux/macOS) e instale:

```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

Crie um `.env` na raiz do repositório:

```
DJANGO_SECRET_KEY=uma-chave-longa-e-aleatoria
DEBUG=true
DATABASE_URL=postgresql://usuario:senha@host.neon.tech/neondb?sslmode=require
REDIS_URL=rediss://default:senha@host.upstash.io:6379
TOTP_ENCRYPTION_KEY=chave-fernet
BIOMETRIC_ENCRYPTION_KEY=chave-fernet
```

As chaves Fernet são geradas com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. A `BIOMETRIC_ENCRYPTION_KEY` precisa ser a mesma em todos os ambientes que leem o mesmo banco. Variáveis opcionais: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `GEOCODING_ENABLED` (padrão `true`) e `EXECUTAVEL_DOWNLOAD_URL`.

Aplique as migrações:

```bash
cd validador_presenca
python manage.py migrate
python manage.py createsuperuser
```

---

## Rodar

```bash
python manage.py runserver
```

Rotas principais:

- `/accounts/login/` -> login (senha, termos e TOTP)
- `/checkin/` -> check-in do aluno (aberto pelo link do QR Code)
- `/dashboard/`, `/chamadas/`, `/pendencias/` -> painel do professor
- `/validator/` -> histórico de presença do professor
- `/gestao-turmas/`, `/alunos/`, `/professores/`, `/infraestrutura/` -> gestão do administrador
- `/auditoria/` -> registro de atividades
- `/privacidade/` -> central de privacidade; `/privacidade/solicitacoes/` -> solicitações LGPD (administrador)
- `/api/v1/maquinas/` -> API do executável da sala
- `/admin/` -> Django Admin

---

## Comandos de gerenciamento

| Comando | Para que serve |
|---------|----------------|
| `publicar_termo` | Publica uma nova versão de termo; todos aceitam de novo no próximo login |
| `lgpd_exportar` | Exporta os dados de um titular em JSON |
| `lgpd_atender` | Atende uma solicitação LGPD pela linha de comando |
| `verify_audit_chain` | Confere a cadeia de hashes da auditoria e aponta o primeiro registro adulterado |
| `seed_demo` | Cria uma turma de demonstração com chamadas passadas para o dashboard |
| `medir_checkin` | Mede o tempo médio do check-in a partir dos registros |
| `preparar_carga` | Prepara dados para o teste de carga (só em banco local) |

---

## Testes

```bash
cd validador_presenca
pytest
```

A configuração fica em `pytest.ini` (settings de teste com SQLite e cache em memória). Os testes do executável ficam em `class_client/` e rodam com `pytest` dentro dessa pasta. O teste de carga está descrito em `loadtest/README.md`.

---

## Executável da sala

O GitHub Actions gera o `ADSUM-Sala.zip` a cada push e publica no Release `executavel`. O administrador baixa pelo painel, extrai no computador da sala e pareia com o código de 4 dígitos mostrado em Infraestrutura. Detalhes em `class_client/README.md`.

---

## Infraestrutura

| Serviço        | Provedor  | Uso                                              |
|----------------|-----------|--------------------------------------------------|
| Backend Django | Railway   | Deploy automático a cada push na `main`          |
| PostgreSQL     | Neon      | Banco relacional                                 |
| Redis          | Upstash   | Cache, QR rotativo e autorizações de captura     |
| Executável     | GitHub    | Build no Actions e download pelo Release         |

---

## Documentação

Ver `docs/` (ficha do projeto, monografia e DER).

---

## Time

- **Luiz Eduardo Dias** ([@luizDiasDev](https://github.com/luizDiasDev))
- **Fabricio Rocha de Souza** ([@Fabriciors9](https://github.com/Fabriciors9))
- **Prof. Alessandro Aparecido da Silva Horas** - orientador
