# Teste de carga do ADSUM

Simula o pico das 19h em escala de laboratórios: 26 salas com 30 computadores cada (780 máquinas) e um aluno por computador.

- Cada **computador da sala** consulta o QR Code a cada 10 s e, com a chamada aberta, pergunta a cada 3 s se algum aluno leu o QR. Quando há aluno, envia o vetor facial, como o executável faz.
- Cada **aluno** chega em um momento aleatório da janela de chegada, abre o check-in, envia o QR e a localização e acompanha o status até o veredito.
- A métrica `check-in completo (celular + rosto)` mede o tempo do aluno do início ao fim.

O reconhecimento facial não entra na conta do servidor porque roda no computador da sala; o teste envia um vetor já pronto.

> Nunca rode contra a produção. O comando `preparar_carga` se recusa a rodar fora de um banco local.

## 1. Banco e Redis locais

```bash
docker run -d --name adsum-pg -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=adsum_carga -p 5433:5432 postgres:16
docker run -d --name adsum-redis -p 6380:6379 redis:7
```

## 2. Variáveis de ambiente (chaves de teste, nunca as reais)

```bash
export DJANGO_SECRET_KEY=carga-local
export DATABASE_URL=postgres://postgres@127.0.0.1:5433/adsum_carga
export REDIS_URL=redis://127.0.0.1:6380/0
export TOTP_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export BIOMETRIC_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export ALLOWED_HOSTS=127.0.0.1,localhost
export GEOCODING_ENABLED=false
```

`GEOCODING_ENABLED=false` desliga a consulta de endereço ao Nominatim, que tem limite de 1 requisição por segundo e não pode receber carga.

## 3. Dados e servidor

```bash
cd validador_presenca
python manage.py migrate
python manage.py preparar_carga --maquinas 780 --saida ../loadtest/dados_carga.json
gunicorn validador_presenca.wsgi:application --bind 127.0.0.1:8001 --workers 3 --timeout 60
```

## 4. Locust (em outro terminal)

```bash
cd loadtest
pip install -r requirements.txt
JANELA_DE_CHEGADA_S=150 locust -f locustfile.py --headless -H http://127.0.0.1:8001 -u 1560 -r 300 -t 4m --stop-timeout 5 --csv resultado
```

`-u` é o número de máquinas mais o de alunos. Para comparar com o intervalo antigo do executável, use `INTERVALO_AUTORIZACAO_S=1.5`.

Os números da última rodada estão em `RESULTADOS.md`.

## 5. Limpeza

```bash
cd validador_presenca
python manage.py preparar_carga --limpar
```
