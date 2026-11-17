# Relatório de acompanhamento: entrega de 16/11/2026

**Projeto:** Adsum: Verificação de Presença Acadêmica em Múltiplos Fatores
**Equipe:** Luiz Eduardo Dias e Fabrício Rocha de Souza
**Orientador:** Prof. Alessandro Aparecido da Silva Horas

## 1. Versão apresentada

- **Repositório:** https://github.com/luizDiasDev/validador_presenca (público)
- **Branch:** `main`
- **Commit:** `acbeff55333563d16831c47e2caf33b96af93ee0`
- **Sistema em produção:** https://adsum.up.railway.app
- **Executável da sala:** Release `executavel` do repositório, gerado automaticamente pelo GitHub Actions
- **Instruções e evidências de execução:** `docs/EXECUCAO.md`

## 2. O que foi desenvolvido desde a última entrega

**Chamadas e presença**
- Agendamento semanal de chamadas, que abrem sozinhas no horário marcado.
- Abertura manual só durante o horário da aula, com a janela ajustada para fechar no fim da aula; abrir e agendar no mesmo formulário.
- Falta automática para quem não fez check-in quando a chamada fecha.
- Uma presença por aluno por chamada e limite de alunos por computador definido pelo professor (o QR some quando o computador lota).
- Verificação de que o aluno pertence à turma da chamada.

**Painéis**
- Dashboard ponderado pelos tempos de aula cobertos, com filtros de turma e período.
- Paginação em todas as listas; colunas de situação dos termos e do cadastro facial.
- Padronização visual dos filtros e dos status (Aprovado, Pendente, Recusado e Falta).

**Administração e LGPD**
- Gestão de turmas pelo administrador.
- Aceite dos termos no primeiro login (antes do TOTP) e sessão única por usuário.
- Tela de Solicitações LGPD para o administrador atender, recusar ou colocar em análise; download dos próprios dados pelo titular.

**Executável da sala**
- Funciona em segundo plano, com ícone na bandeja, e mostra uma janela pequena no canto apenas durante a chamada.
- Captura sem travar a tela, desafio de virar a cabeça corrigido e log de diagnóstico.
- Pareamento protegido (código de uso único e bloqueio após 10 tentativas por IP) e repareamento automático quando a máquina é desconectada.
- Geração automática do executável a cada push (GitHub Actions) com download pelo painel.


## 3. Apontamentos corrigidos

| Apontamento | Situação |
|---|---|
| Termo de aceite no primeiro login | Corrigido |
| CRUD de turma pelo administrador | Corrigido |
| Scripts de atendimento LGPD | Corrigido (comandos + tela de solicitações) |
| Atualização dos termos | Corrigido (versão 2) |
| Dashboard considerando os tempos de aula | Corrigido |
| Visualização da situação dos termos assinados | Corrigido (colunas em alunos e professores) |
| Teste de carga e tempo médio de check-in | Corrigido (`loadtest/RESULTADOS.md` e comando `medir_checkin`) |
| Verificar se o aluno é da turma no check-in | Corrigido |
| Diagramas de classe desatualizados | Corrigido |

## 4. O que permanece pendente

- **Entrega de 23/11:** resumo expandido, manual do sistema e revisão final da documentação.
- **Melhorias conhecidas, fora do escopo atual:** limite de tentativas no login (mitigado pelo TOTP obrigatório), troca de senha pelo próprio usuário e padronização dos nomes do código em um único idioma, terceiro metodo de prova de vida.
