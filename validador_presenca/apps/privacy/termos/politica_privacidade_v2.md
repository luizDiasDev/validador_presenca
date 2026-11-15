## 1. Sobre esta política

Esta política descreve o tratamento de dados pessoais no Adsum: quais dados são coletados, para quê, por quanto tempo, com quem são compartilhados e como você pode exercer seus direitos como titular.

O Adsum é um sistema acadêmico de verificação de presença em múltiplos fatores, que combina QR Code rotativo, reconhecimento facial, prova de vida e geolocalização. Ele é voltado a aulas em laboratórios com computadores: o QR Code e a câmera usados no check-in são os do computador da sala.

## 2. Responsáveis pelo tratamento

Controlador: Universidade de Mogi das Cruzes (UMC), instituição responsável pelas decisões sobre o tratamento dos dados dos alunos, professores e administradores.

Operadores técnicos: Luiz Eduardo Dias e Fabrício Rocha de Souza, autores do sistema, responsáveis pela implementação dos controles descritos aqui.

Encarregado (DPO): Fabrício Rocha de Souza.

Canal funcional de contato: 11231102907@alunos.umc.br. Solicitações relativas aos direitos previstos na LGPD são respondidas em até 15 dias, conforme o artigo 19 da LGPD.

## 3. Dados pessoais tratados

As categorias abaixo listam os dados pessoais tratados pelo sistema, com a finalidade, a hipótese legal e o prazo de retenção de cada um.

### 3.1. Identificação e autenticação

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Nome completo | Identificar o usuário nas telas e nos relatórios de frequência | Execução de contrato educacional | Enquanto vínculo institucional ativo |
| E-mail institucional | Login único e canal de comunicação | Execução de contrato | Enquanto vínculo ativo |
| Senha | Autenticação segura | Execução de contrato | Enquanto vínculo ativo |
| Segredo do segundo fator (TOTP) | Segundo fator obrigatório para administrador, professor e aluno | Legítimo interesse em segurança | Enquanto o 2FA estiver ativo |

Sobre a senha: o sistema aplica hash Argon2 no cadastro e valida apenas o hash no login.

Sobre o segundo fator: o segredo compartilhado com o aplicativo autenticador é cifrado antes de ser gravado.

### 3.2. Dados acadêmicos

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Matrícula (RGM) | Identificar o aluno no contexto acadêmico | Execução de contrato + obrigação legal de arquivamento educacional | Enquanto vínculo ativo + prazo legal |
| Vínculo com turma | Determinar quais chamadas o aluno participa | Execução de contrato | Enquanto vínculo ativo |
| Cargo (administrador) | Identificar o perfil administrativo | Execução de contrato | Enquanto vínculo ativo |
| Área de atuação (professor) | Identificar a especialidade docente | Execução de contrato | Enquanto vínculo ativo |

### 3.3. Dado biométrico

O reconhecimento facial faz parte do escopo declarado do sistema. Este é um dado sensível pela LGPD (art. 5º, II) e recebe tratamento diferenciado.

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Embedding facial | Comparar a face capturada ao vivo com o cadastro do próprio aluno | Consentimento específico (art. 11, I) | Até revogação ou fim do vínculo |
| Imagens do cadastro (5 leituras) | Gerar o embedding | Consentimento específico (art. 11, I) | Processadas em memória no computador da sala e descartadas em seguida |
| Imagem ao vivo no check-in | Gerar o vetor comparado com o cadastro | Consentimento específico (art. 11, I) | Processada em memória no computador da sala, nunca enviada ao servidor |
| Pontuações de semelhança e de prova de vida | Compor o veredito do motor de confiança | Consentimento específico (art. 11, I) | 5 anos, junto do registro de presença |

Sobre o embedding: nenhuma imagem sai do computador da sala. O programa da sala transforma o rosto em um vetor numérico, que não permite reconstruir o rosto original, e envia só esse vetor. O servidor cifra o vetor antes de gravar.

Alternativa menos invasiva: o aluno que não quer usar biometria escolhe "Agora não" na tela do termo biométrico. Nesse caso, nenhum vetor é gerado e o check-in, conferido pelo QR Code e pela localização, fica pendente para o professor confirmar. A decisão do professor passa pela mesma trilha de auditoria e não gera prejuízo acadêmico.

Revisão humana: o reconhecimento facial pode gerar falsos positivos e falsos negativos. Resultados intermediários ficam pendentes e só valem depois da decisão do professor. Check-ins recusados por um fator bloqueante (QR Code inválido, fora do raio do campus, turma diferente ou rosto de outra pessoa) podem ser contestados junto ao professor ou ao encarregado, conforme o artigo 20 da LGPD.

Revogação: o aluno pode revogar o consentimento biométrico a qualquer momento pela Central de Privacidade. Quando o encarregado atende a solicitação, o embedding é apagado e o consentimento é marcado como revogado. Nos check-ins seguintes, o termo biométrico é oferecido de novo; enquanto o aluno não aceitar, a presença fica pendente para o professor.

### 3.4. Localização

Durante o check-in, o sistema verifica se você está dentro do raio de tolerância do campus. Isso usa a API W3C Geolocation do seu próprio navegador, que exige permissão explícita antes de fornecer coordenadas. Para mostrar a você o endereço aproximado de onde o check-in foi feito, a coordenada também é enviada ao serviço Nominatim (OpenStreetMap); esse endereço não é gravado.

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Latitude e longitude no momento do check-in | Validar presença física no campus | Execução de contrato + legítimo interesse antifraude | A coordenada bruta não é registrada; apenas o resultado booleano (dentro ou fora do raio) fica armazenado |

O backend recebe a coordenada, calcula a distância até o centro do campus e guarda apenas a decisão. Quando o check-in é recusado por estar fora do raio, o motivo registra a distância, por exemplo, "Coordenada a 2.400 m do campus (raio permitido: 300 m)".

### 3.5. Fluxo do check-in

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Token QR temporário | Ligar a leitura do aluno à chamada e ao computador da sala | Execução de contrato | 30 segundos, uso único |
| Identificador do computador da sala | Saber em qual computador o rosto deve ser conferido e aplicar o limite de alunos por computador definido pelo professor | Execução de contrato | 5 anos, junto do registro de presença |
| Hash do token consumido | Auditoria (evidenciar qual QR foi usado) | Legítimo interesse em segurança | 5 anos |
| Status do check-in (aprovado, pendente, rejeitado) | Registrar frequência acadêmica | Obrigação legal educacional | Prazo legal de arquivamento |

### 3.6. Auditoria e segurança

| Dado | Finalidade | Hipótese legal | Retenção |
|------|------------|----------------|----------|
| Endereço IP | Rastreabilidade de acessos e resposta a incidentes | Legítimo interesse em segurança | 5 anos |
| User-agent do navegador | Rastreabilidade de dispositivos | Legítimo interesse em segurança | 5 anos |
| Log de ações | Registro de logins, tentativas com falha, aceites de termo, logout, ações administrativas | Legítimo interesse + obrigação legal | 5 anos |

O log usa hash SHA-256 encadeado, o que permite detectar qualquer alteração retroativa nos registros. Senhas e tokens ativos não são gravados no log.

## 4. Compartilhamento e serviços externos

O sistema depende de provedores de infraestrutura. Cada terceiro está listado abaixo com a finalidade e os dados que passam por ele.

- Neon (PostgreSQL gerenciado): banco de dados relacional principal. Recebe os dados descritos na seção 3, com exceção dos efêmeros. Conexão via TLS obrigatória. Servidores em US-East. Política em https://www.databricks.com/legal/privacynotice.
- Upstash (Redis gerenciado): cache e armazenamento efêmero do token QR e da liberação da câmera da sala. A liberação guarda, por até 120 segundos, o identificador do aluno e do registro de presença; nenhum dado biométrico passa por aqui. Conexão via TLS. Servidores em US-East. Política em https://upstash.com/trust/privacy.pdf.
- Railway (hospedagem do backend): provedora do ambiente de execução. Não armazena dados de negócio, apenas processa requisições em memória. Política em https://railway.com/legal/privacy.
- W3C Geolocation API: API nativa do navegador do próprio aluno. Não envolve terceiro externo, apenas expõe a coordenada com consentimento explícito. Especificação em https://www.w3.org/TR/geolocation/.
- Nominatim (OpenStreetMap Foundation): recebe a coordenada do check-in para devolver o endereço aproximado exibido ao aluno. O endereço não é gravado. Política em https://osmfoundation.org/wiki/Privacy_Policy.
- Redes de distribuição de conteúdo (jsDelivr, unpkg e Google Fonts): fornecem bibliotecas visuais e fontes das páginas. Recebem apenas o endereço IP e o navegador de quem abre a página, como em qualquer site.
- Reconhecimento facial (InsightFace): roda dentro do computador da sala. Não é um serviço externo e não recebe dados.

Nenhum dado pessoal do Adsum é enviado a serviços de inteligência artificial generativa. Nenhum dado biométrico é usado para treinar modelos.

## 5. Transferência internacional

Os provedores Neon, Upstash e Railway operam servidores localizados nos Estados Unidos (US-East), e o Nominatim opera servidores na Europa. Isso configura transferência internacional de dados nos termos do artigo 33 da LGPD.

Salvaguardas aplicadas:

- comunicação cifrada com TLS obrigatório em todos os canais
- credenciais mantidas fora do código-fonte, em variáveis de ambiente do provedor de hospedagem, com controle de acesso restrito
- adesão dos provedores a padrões internacionais de proteção de dados, conforme certificações publicadas nos respectivos trust centers

## 6. Cookies

O Adsum utiliza apenas cookies estritamente necessários. Não há cookies opcionais e por isso não há banner de escolha.

- Cookie de sessão (`sessionid`): identifica a sessão logada. Tempo de vida: 30 minutos de inatividade. Marcado como `HttpOnly` e `Secure` em ambiente de produção. Cada conta tem uma única sessão ativa: entrar em outro aparelho encerra a sessão anterior.
- Cookie CSRF (`csrftoken`): previne ataques de forjamento de requisição. Renovado a cada sessão.

Não usamos cookies de rastreamento comportamental, análise de audiência ou publicidade.

## 7. Retenção e descarte

Cada categoria de dado tem uma regra clara de retenção. O descarte é executado pelo encarregado (DPO) via canal descrito na seção 2, com prazo de 15 dias a partir da solicitação.

| Categoria | Prazo | Destino após o prazo |
|-----------|-------|----------------------|
| Conta de usuário (nome, e-mail, senha) | Enquanto vínculo institucional ativo | Anonimização: e-mail e nome viram hash irreversível |
| Embedding facial | Enquanto vínculo ativo ou até revogação | Exclusão imediata ao revogar |
| Registros de presença | 5 anos (arquivamento acadêmico) | Anonimização preservando o histórico agregado |
| Token QR efêmero | Alguns segundos (expira após o uso) | Expiração automática, nunca copiado para banco persistente |
| Segredo do segundo fator | Enquanto o 2FA estiver ativo | Exclusão ao desativar o 2FA |
| Aceites de termo | Enquanto o termo estiver em vigor + prazo legal de comprovação | Anonimização preservando o registro do consentimento |
| Log de auditoria | 5 anos, imutável | Exclusão ao fim do prazo; antes disso, nenhum registro é alterado, porque qualquer alteração quebraria a cadeia de hashes |

Como o descarte é executado: o encarregado verifica a identidade do titular e atende cada solicitação de revogação, exclusão ou exportação com as rotinas próprias do sistema, que registram o atendimento na trilha de auditoria. Na exclusão de conta, o nome e o e-mail viram um código irreversível, o acesso é bloqueado e a biometria é apagada, enquanto os registros de presença ficam preservados sem identificação. O token QR expira automaticamente por configuração técnica do Redis.

## 8. Direitos dos titulares

A LGPD garante direitos que o Adsum permite exercer:

- Confirmação e acesso: consultar quais dados o sistema tem sobre você.
- Correção: solicitar correção de dados incorretos.
- Anonimização, bloqueio ou eliminação: quando os dados forem desnecessários ou tratados em desacordo com a LGPD.
- Portabilidade: receber uma cópia dos seus dados em formato estruturado (JSON), com conta, perfis, aceites, presenças, solicitações e eventos de auditoria. O vetor facial não é exportado.
- Eliminação: remoção dos dados tratados com base em consentimento, ressalvadas obrigações legais de arquivamento.
- Revogação do consentimento: especialmente para biometria, efetivada quando o encarregado atende a solicitação, dentro do prazo de 15 dias.
- Informação sobre compartilhamentos: a lista pública está na seção 4.
- Oposição: quando o tratamento estiver baseado em legítimo interesse, você pode se opor.
- Revisão de decisões automatizadas: no fluxo do check-in, resultados intermediários já passam por revisão do professor por padrão, e recusas podem ser contestadas pelo canal abaixo.

Canal: você pode fazer a solicitação pela própria plataforma em "Fazer solicitação LGPD" dentro da ferramenta, ou por contato direto com o encarregado pelo e-mail da seção 2. O prazo de resposta é de 15 dias.

Sobre exposição comparativa: o Adsum não expõe rankings, notas comparativas ou métricas de desempenho entre alunos. Cada aluno acessa apenas o próprio histórico, e o professor acessa apenas as turmas sob sua responsabilidade.

## 9. Análise de legítimo interesse

Alguns tratamentos usam legítimo interesse como base legal (art. 7º, IX). Cada um está documentado abaixo com finalidade, necessidade, expectativa razoável, riscos, salvaguardas e possibilidade de oposição.

### 9.1. Segundo fator (TOTP)

- Finalidade: proteger contas com poder administrativo contra acesso indevido.
- Necessidade: senha isolada é insuficiente para contas que podem alterar frequência ou dados pessoais de terceiros.
- Expectativa razoável: administradores e professores esperam que o sistema aplique controles compatíveis com o poder de decisão que exercem.
- Riscos: exposição do segredo do segundo fator em caso de vazamento do banco.
- Salvaguardas: segredo cifrado com Fernet, chave de criptografia mantida fora do código-fonte, decifração apenas em memória.
- Oposição: não aplicável para administrador, professor e aluno.

### 9.2. Validação de geolocalização

- Finalidade: impedir que um aluno registre presença sem estar fisicamente no campus.
- Necessidade: a fraude por presença remota é o vetor de ataque mais provável do sistema.
- Expectativa razoável: o aluno espera que um sistema de verificação de presença acadêmica confira presença física.
- Riscos: coleta involuntária de coordenada precisa fora do campus.
- Salvaguardas: a coordenada bruta não é gravada; apenas o resultado booleano é persistido. O consentimento da API W3C ocorre no navegador antes de qualquer envio.
- Oposição: o aluno pode negar a permissão de geolocalização no navegador. Nesse caso, o fator geo fica bloqueado e o check-in é recusado; o aluno pode contestar a falta junto ao professor ou ao encarregado.

### 9.3. Log de auditoria com hash encadeado

- Finalidade: garantir integridade e rastreabilidade de ações críticas (aceites de termo, tentativas de login, alterações administrativas).
- Necessidade: sem auditoria imutável, incidentes de segurança não podem ser investigados nem prestados contas em eventual solicitação da ANPD.
- Expectativa razoável: usuários de sistemas institucionais esperam que ações administrativas sejam registradas.
- Riscos: exposição de IP e user-agent em caso de vazamento do log.
- Salvaguardas: log com hash SHA-256 encadeado (o hash de cada registro depende do hash do anterior), controle de acesso restrito ao admin do sistema, retenção limitada a 5 anos.
- Oposição: não aplicável, é registro obrigatório para segurança.

## 10. Segurança

Medidas técnicas aplicadas no sistema atual:

- senhas armazenadas apenas como hash Argon2, nunca em texto puro
- segredo do segundo fator cifrado com Fernet antes de gravar
- TLS obrigatório nas conexões com Neon e Upstash
- cookies de sessão com `HttpOnly` (padrão do Django) e `Secure` em produção
- proteção CSRF em todos os formulários
- autorização verificada no backend em cada operação, com decorators de perfil (`only_teacher`, `only_admin`, `only_student`), não apenas escondendo botões no frontend
- vetor facial cifrado com Fernet antes de gravar, com chave própria fora do código-fonte
- computador da sala autenticado por token, do qual o servidor guarda apenas o hash SHA-256
- log de auditoria com hash SHA-256 encadeado (ver seção 9.3)
- testes automatizados não usam dados reais
- uso do ORM do Django e consultas parametrizadas em toda a base
- chaves, tokens e credenciais fora do código-fonte, mantidos em variáveis de ambiente do provedor

## 11. Resposta a incidentes

Em caso de incidente de segurança que envolva risco ou dano relevante aos titulares, seguimos este procedimento:

1. Detecção e confirmação do incidente
2. Contenção do vetor comprometido e preservação de evidências
3. Identificação dos titulares e dos dados afetados
4. Avaliação do risco ou dano relevante
5. Comunicação à ANPD e aos titulares dentro do prazo regulatório
6. Correção da causa e registro das medidas no log de auditoria

## 12. Data, versão e alterações

O número da versão e a data de publicação aparecem no cabeçalho desta página.

Novas versões podem ser publicadas conforme o sistema evolua. Mudanças relevantes são comunicadas pelo canal institucional e, no próximo login, antes do segundo fator, o sistema mostra os documentos alterados e pede novo aceite.

## 13. Contato

- Encarregado (DPO): Fabrício Rocha de Souza, 11231102907@alunos.umc.br
- Autoridade Nacional de Proteção de Dados (ANPD): https://www.gov.br/anpd

Se você acredita que seus dados foram tratados de forma inadequada e não obteve resposta satisfatória do encarregado, pode reportar diretamente à ANPD.

