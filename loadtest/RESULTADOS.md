# Resultados do teste de carga (15/11/2026)

## Cenário

- 26 laboratórios com 30 computadores cada: 780 computadores de sala e 780 alunos, um por computador.
- Todas as chamadas abertas ao mesmo tempo, simulando o pico das 19h.
- Alunos chegando em momentos aleatórios ao longo de 150 segundos.
- Cada computador busca um QR novo a cada 10 s e, com a chamada aberta, pergunta pela liberação da câmera no intervalo testado.
- 4 minutos de duração por rodada.

## Ambiente

- Servidor: gunicorn com 3 workers, PostgreSQL 16 e Redis locais.
- Máquina: 2 vCPUs e 7 GB de RAM, compartilhados com o próprio Locust (2.47.0). A máquina que gera a carga disputa CPU com o servidor, então os números são conservadores.
- Consulta de endereço (Nominatim) desligada.
- O reconhecimento facial não entra na conta do servidor: ele roda no computador da sala, e o teste envia um vetor já pronto.

## Resultados

| Métrica | Intervalo de 3 s (atual) | Intervalo de 1,5 s (anterior) |
|---|---|---|
| Requisições por segundo no servidor | 334 | 430 |
| Erros HTTP | 0 em 80.120 | 0 em 103.090 |
| Tempo de resposta, mediana | 17 ms | 560 ms |
| Tempo de resposta, 95% em até | 400 ms | 1.200 ms |
| Check-in completo no sistema, mediana | 2,4 s | 4,6 s |
| Check-in completo no sistema, 95% em até | 4,7 s | 8,3 s |
| Check-ins aprovados | 778 de 780 | 779 de 780 |

"Check-in completo no sistema" vai da abertura da página de check-in no celular até o veredito com o rosto. Inclui a espera pela consulta do computador da sala e pela consulta de status do celular (a cada 2 s). Não inclui o tempo humano de apontar a câmera para o QR nem a captura do rosto com o desafio de virar a cabeça. Esse tempo real é medido em produção pelo comando `medir_checkin`.

## Leitura

- A maior parte da carga vem dos computadores das salas consultando o servidor, e não dos alunos. Com 1,5 s, essas consultas somavam 346 das 430 requisições por segundo.
- Dobrar o intervalo para 3 s e parar de consultar a liberação quando não há chamada aberta reduziu a mediana do tempo de resposta de 560 ms para 17 ms e cortou pela metade o tempo do check-in.
- Os 3 check-ins que terminaram pendentes (2 + 1) foram exceções do próprio fluxo, não erros do servidor.
- A consulta de endereço no Nominatim é o próximo gargalo para um pico real: o serviço aceita 1 requisição por segundo e responde em até 3 s por check-in.
