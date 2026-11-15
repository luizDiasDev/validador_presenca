## 1. Descrição, finalidade e limitações do serviço

O que é o Adsum: sistema acadêmico de verificação de presença em múltiplos fatores. Combina QR Code rotativo, reconhecimento facial, prova de vida e geolocalização. É voltado a aulas em laboratórios com computadores.

Finalidade: registrar a presença de alunos em aulas presenciais, gerar relatórios de frequência para o professor e a coordenação e produzir trilha de auditoria para revisão institucional. O sistema não substitui outros processos acadêmicos, como avaliação, matrícula ou controle disciplinar.

Limitações:

- O reconhecimento facial pode produzir falsos positivos e falsos negativos. Resultados intermediários ficam pendentes para a revisão humana do professor, e recusas podem ser contestadas junto ao professor ou ao encarregado.
- A geolocalização depende da precisão do GPS do dispositivo do aluno. Se o sinal estiver fraco, o fator geo fica bloqueado e o check-in é recusado.
- Não há garantia de disponibilidade contínua. Em caso de indisponibilidade, a frequência é registrada pelos meios institucionais habituais.

## 2. Quem pode utilizar

O Adsum é destinado a três perfis:

- Administradores institucionais (TI): cadastram campus, salas, máquinas, turmas e usuários e instalam o programa dos computadores das salas.
- Professores: cadastram disciplinas e horários, abrem chamadas, revisam pendências e acompanham o painel de frequência.
- Alunos: realizam check-in, consultam o próprio histórico e exercem os direitos LGPD descritos na Política de Privacidade.

Para usar o sistema é necessário:

- ter conta institucional válida na instituição de ensino que adotou o Adsum
- ser maior de idade (18 anos completos)
- aceitar este Termo de Uso e a Política de Privacidade na tela de aceite exibida no primeiro acesso

Sobre a idade: o Adsum não é destinado a menores de 18 anos. O sistema é projetado para o contexto universitário e não prevê mecanismo de consentimento por responsável.

Sobre a representação: o aluno usa o sistema pessoalmente. Não é permitido registrar presença por outro aluno nem operar em nome de terceiro. A conta é individual e intransferível.

## 3. Criação e proteção da conta, papéis e permissões

Criação: a instituição de ensino é responsável pela criação e desativação das contas. O aluno não pode se autocadastrar.

Proteção: você é responsável por manter em sigilo sua senha e o segundo fator, não compartilhar credenciais, notificar o encarregado (DPO) em caso de acesso indevido e manter os dados cadastrais atualizados.

Segundo fator (TOTP) obrigatório para administradores, professores e alunos: todas as contas configuram autenticação em dois fatores no primeiro acesso.

Sessão única: cada conta tem uma única sessão ativa. Entrar em outro aparelho encerra a sessão anterior.

Controle de acesso por perfil: o sistema verifica a autorização no backend a cada operação, usando decorators de perfil. Não é possível acessar dados de outros usuários apenas alterando URLs. As ações administrativas ficam registradas na trilha de auditoria.

Alterações de frequência e presença: qualquer alteração feita pelo professor (aprovação, rejeição, revisão manual) fica registrada no log de auditoria com identificação do responsável, data e justificativa.

## 4. Responsabilidades do usuário e condutas proibidas

Suas responsabilidades:

- usar o sistema pessoalmente, sem delegar
- fornecer dados corretos no cadastro
- comunicar imediatamente falhas de segurança ou acessos indevidos

É proibido:

- tentar acessar dados ou funcionalidades de outros usuários por manipulação de URL, injeção de comandos, engenharia reversa ou qualquer outro meio
- compartilhar conta, senha ou token com terceiros
- usar biometria de outra pessoa (foto, vídeo, deepfake, modelo 3D) para simular presença
- registrar presença em nome de outro aluno
- automatizar acessos com scripts ou bots sem autorização expressa
- realizar testes de segurança (pentest e outros) sem autorização escrita
- reproduzir, distribuir ou publicar dados de outros usuários obtidos pelo sistema
- utilizar o sistema para fins ilícitos, discriminatórios, difamatórios ou que violem direitos de terceiros
- contornar o motor de confiança por qualquer meio técnico

Detectada qualquer conduta proibida, a instituição pode suspender ou encerrar a conta e anular registros de presença obtidos por fraude, sem prejuízo das medidas legais cabíveis.

## 5. Conteúdo enviado pelo usuário e propriedade intelectual

Conteúdo enviado durante o uso:

- coordenada de geolocalização (convertida em decisão booleana e não registrada como coordenada bruta)
- imagens do rosto captadas pela câmera do computador da sala, que são convertidas ali mesmo em um vetor numérico; só o vetor é enviado ao servidor (ver seção 3.3 da Política de Privacidade)

Uso desse conteúdo pelo sistema: apenas o necessário para a verificação de presença descrita na seção 1. Nada é reutilizado para outra finalidade. Nada é enviado a serviços de inteligência artificial generativa. Nada é usado para treinar modelos.

Sua propriedade sobre a imagem: você mantém todos os direitos sobre a sua imagem. O Adsum recebe autorização apenas para o uso descrito na Política de Privacidade, e apenas enquanto o consentimento estiver vigente. Ao revogar, o embedding é excluído.

Propriedade intelectual do software: o código-fonte, a documentação, os modelos de dados e os fluxos do Adsum são de autoria de Luiz Eduardo Dias e Fabrício Rocha de Souza, com orientação institucional da UMC.

Nomes de tecnologias terceirizadas (Django, PostgreSQL, Redis) pertencem aos respectivos detentores dos direitos.

## 6. Indisponibilidade, manutenção, suporte e encerramento

Indisponibilidade: o Adsum pode ficar indisponível temporariamente por manutenção, falha técnica ou motivo de força maior. Em caso de indisponibilidade que impeça o check-in, a frequência é registrada pelos meios institucionais habituais.

Manutenção: paradas programadas serão comunicadas com antecedência sempre que possível.

Suporte: o suporte é prestado pelo encarregado (DPO) pelo e-mail 11231102907@alunos.umc.br.

Encerramento da conta. Sua conta pode ser encerrada por:

- sua solicitação, via encarregado
- fim do vínculo institucional (formatura, transferência, desligamento)
- descumprimento das regras deste termo
- determinação judicial ou regulatória

Ao encerrar a conta:

- os dados pessoais são anonimizados conforme a Política de Privacidade
- os registros de presença são preservados de forma anonimizada, atendendo à obrigação legal de arquivamento
- a biometria (quando estiver cadastrada) é excluída imediatamente
- os aceites de termo ficam preservados como evidência do consentimento no momento em que foi dado
- o log de auditoria é preservado com a cadeia de hashes íntegra

Você pode solicitar uma cópia dos seus dados em JSON antes da anonimização.

## 7. Consequências do uso indevido, legislação aplicável, data e versão

Consequências do uso indevido, dependendo da gravidade:

- suspensão temporária da conta
- encerramento permanente da conta
- anulação de registros de presença obtidos por fraude
- comunicação à coordenação do curso e à instituição
- comunicação à autoridade competente em caso de crime cibernético (art. 154-A e seguintes do Código Penal)

Legislação aplicável. Este termo é regido pela legislação brasileira, com destaque para:

- Lei nº 13.709/2018 (LGPD)
- Marco Civil da Internet (Lei nº 12.965/2014)
- Regulamentações do Ministério da Educação para o ensino superior

Data e versão: o número da versão e a data de publicação aparecem no cabeçalho desta página. Novas versões são publicadas conforme o sistema evolua. Mudanças relevantes serão comunicadas pelo canal institucional e o sistema exigirá novo aceite no próximo login.

## 8. Contato

Encarregado (DPO): Fabrício Rocha de Souza, 11231102907@alunos.umc.br.

## 9. Aceite

O aceite deste termo e da Política de Privacidade ocorre na tela de aceite exibida no primeiro acesso e sempre que uma nova versão for publicada.

Ao marcar a opção de aceite e continuar, você declara que:

- leu e compreendeu este Termo de Uso
- leu e compreendeu a Política de Privacidade do Adsum
- concorda em cumprir as regras aqui estabelecidas
- tem capacidade legal para assumir essas obrigações
- consente com o tratamento dos seus dados pessoais nas hipóteses descritas na Política de Privacidade, ressalvado o direito de revogação a qualquer tempo para as bases que admitem consentimento

O sistema registra o aceite automaticamente, com evidência composta por endereço IP, user-agent, data e hora, e anota o aceite na trilha de auditoria. Esse registro fica preservado como prova documental do consentimento.

