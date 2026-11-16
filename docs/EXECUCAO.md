# Instruções e evidências de execução do Adsum

Este documento permite verificar as funcionalidades e integrações do Adsum. Nenhuma senha, token ou dado pessoal real aparece aqui: use os dados fictícios indicados.

## 1. Ambientes

| Ambiente | Endereço | Uso |
|---|---|---|
| Produção | https://adsum.up.railway.app | Demonstração (Railway + Neon + Upstash) |
| Local | http://127.0.0.1:8000 | Desenvolvimento e testes |

Código: repositório `luizDiasDev/validador_presenca`, branch `main`. O commit verificado é o informado no relatório de acompanhamento.

## 2. Executar localmente

Pré-requisitos: Python 3.13, Git, um Postgres e um Redis (locais ou gerenciados).

```bash
git clone https://github.com/luizDiasDev/validador_presenca.git
cd validador_presenca
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
```

Crie um `.env` na raiz com valores **seus** (os abaixo são apenas o formato):

```
DJANGO_SECRET_KEY=<texto-longo-aleatorio>
DEBUG=true
DATABASE_URL=postgresql://<usuario>:<senha>@<host>/<banco>
REDIS_URL=redis://<host>:6379/0
TOTP_ENCRYPTION_KEY=<chave-fernet>
BIOMETRIC_ENCRYPTION_KEY=<chave-fernet>
```

Gere cada chave Fernet com:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Prepare o banco e o primeiro administrador:

```bash
cd validador_presenca
python manage.py migrate
python manage.py createsuperuser          # e-mail fictício, ex.: admin@exemplo.edu
python manage.py runserver
```

Em `/admin/` (Django Admin), com o superusuário:

1. Cadastre a **Instituição** (nome e CNPJ fictícios).
2. Edite o usuário criado e associe a instituição.
3. Crie um **Administrador** ligado a esse usuário.

Depois disso, entre pelo site em `/accounts/login/`: o sistema pede o aceite dos termos e a configuração do TOTP (use um app autenticador no celular).

Dados de demonstração para o dashboard (turma, 24 alunos fictícios e 10 semanas de chamadas):

```bash
python manage.py seed_demo --professor professor@exemplo.edu
python manage.py seed_demo --limpar        # remove tudo que foi criado
```

## 3. Executável da sala

1. Logado como administrador, em **Infraestrutura**, cadastre campus (latitude, longitude e raio), sala e máquina. Anote o código de 4 dígitos.
2. Baixe o executável pelo link da tela (Release `executavel` do GitHub, gerado pelo GitHub Actions a cada push).
3. Extraia o zip num computador Windows com webcam e rode `ADSUM-Sala.exe`.
4. Informe o endereço do servidor e o código. O programa fica em segundo plano (ícone na bandeja) e mostra o QR Code no canto da tela quando há chamada aberta.

Configuração local da máquina: `%USERPROFILE%\.adsum\sala.json`. Log: `%USERPROFILE%\.adsum\sala.log`.

## 4. Roteiro de verificação funcional

| Requisito | Como verificar | Resultado esperado |
|---|---|---|
| RF01 Login com 2 fatores e sessão única | Entrar com senha e TOTP; entrar de novo em outro navegador | A primeira sessão é encerrada |
| RF02 Acesso por perfil | Logado como aluno, abrir `/dashboard/` | Acesso negado |
| RF03 Auditoria encadeada | Executar ações e rodar `python manage.py verify_audit_chain` | "Cadeia íntegra" |
| RF04 QR rotativo de uso único | Abrir chamada; ler o mesmo QR duas vezes | Segunda leitura recusada |
| RF05 Localização | Negar a localização no celular | Check-in recusado com motivo |
| RF07/RF08 Motor de confiança e facial | Check-in completo de aluno cadastrado | Presença confirmada |
| RF09 Termos | Primeiro login de uma conta | Tela de aceite antes do TOTP |
| RF10 Direitos do titular | Aluno pede exportação; admin atende em Solicitações LGPD | Botão "Baixar meus dados" libera o JSON |
| RF13 Revisão de pendências | Primeiro check-in (com cadastro facial) | Fica em revisão; professor aprova com justificativa |
| RF14 Chamada | Abrir fora do horário da aula; abrir durante; agendar | Fora recusa; durante abre; agendada abre sozinha |
| RF15 Cadastros | Cadastrar professor com senha fraca | Recusado com a regra de senha |
| RF17 Dashboard | Filtrar por turma e período | Frequência ponderada pelos tempos de aula |
| RF19 Executável | Sem chamada / com chamada | Só ícone / janela no canto com QR |

## 5. Testes automatizados

```bash
cd validador_presenca
pytest --cov=apps --cov-report=term       # servidor
cd ../class_client
pytest --cov=room_app --cov=biometrics    # executável
```

Resultados na versão entregue (16/11/2026):

| Parte | Testes | Cobertura |
|---|---|---|
| Servidor (Django) | 347 aprovados | 94% |
| Executável (PySide6) | 89 aprovados, 3 ignorados* | 85% |

\* Os 3 ignorados usam os modelos reais do InsightFace e só rodam com `ADSUM_REAL_MODELS=1`.

A meta do plano de ensino é 50% de cobertura nas classes principais. Os testes usam SQLite e Redis simulado (fakeredis), sem dados reais. A mesma suíte também foi executada contra PostgreSQL 16.

## 6. Teste de carga

Descrito em `loadtest/README.md`, com resultados em `loadtest/RESULTADOS.md`. Cenário: 780 computadores de sala e 780 alunos no pico das 19h, servidor com 3 workers.

| Métrica | Resultado |
|---|---|
| Erros HTTP | 0 em 80.120 requisições |
| Tempo de resposta (mediana) | 17 ms |
| Tempo de resposta (95%) | até 400 ms |
| Check-in completo no sistema (mediana) | 2,4 s |
| Check-ins aprovados | 778 de 780 |

## 7. Evidências anexadas

- Saída do `pytest` com cobertura (servidor e executável).
- `loadtest/RESULTADOS.md`.
- Capturas de tela: login com TOTP, chamadas (abrir e agendar), QR no executável, check-in no celular, pendências, histórico, dashboard, registro de atividades, solicitações LGPD.
- Saída do `verify_audit_chain` em produção.
