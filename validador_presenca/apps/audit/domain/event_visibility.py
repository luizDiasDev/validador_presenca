from django.db.models import Q

from apps.audit.models import AuditLog
from apps.checkin.models import ChamadaSession
from apps.privacy.models import SolicitacaoLGPD
from apps.validator.models import PresencaRecord

ROTULOS_DE_ACAO = {
    "LOGIN_SUCESSO": "Entrou no sistema",
    "LOGIN_FALHA": "Tentativa de login com senha errada",
    "LOGOUT": "Saiu do sistema",
    "TOTP_CONFIGURADO": "Configurou o segundo fator",
    "TOTP_FALHA": "Código do segundo fator incorreto",
    "TOTP_CONFIG_FALHA": "Falha ao configurar o segundo fator",
    "TERMOS_ACEITOS": "Aceitou os termos",
    "CONSENTIMENTO_BIOMETRICO": "Consentiu com a biometria",
    "BIOMETRIA_CADASTRADA": "Rosto cadastrado",
    "BIOMETRIA_REVOGADA": "Biometria revogada",
    "APPROVED": "Check-in aprovado",
    "PENDING": "Check-in pendente",
    "REJECTED": "Check-in recusado",
    "REAVALIADO_COM_ROSTO_APPROVED": "Rosto conferido: aprovado",
    "REAVALIADO_COM_ROSTO_PENDING": "Rosto conferido: pendente",
    "REAVALIADO_COM_ROSTO_REJECTED": "Rosto conferido: recusado",
    "REVISAO_MANUAL_PRESENCA": "Presença revisada pelo professor",
    "SESSAO_ABERTA": "Chamada aberta",
    "SESSAO_ENCERRADA": "Chamada encerrada",
    "FALTAS_REGISTRADAS": "Faltas registradas ao fim da chamada",
    "CHAMADA_AGENDADA": "Chamada agendada",
    "AGENDAMENTO_EXCLUIDO": "Agendamento de chamada removido",
    "SOLICITACAO_LGPD_CRIADA": "Solicitação LGPD enviada",
    "SOLICITACAO_LGPD_STATUS": "Solicitação LGPD atualizada pelo DPO",
    "CONTA_ANONIMIZADA": "Conta anonimizada",
    "MAQUINA_CRIADA": "Computador de sala criado",
    "MAQUINA_ATUALIZADA": "Computador de sala editado",
    "MAQUINA_EXCLUIDA": "Computador de sala excluído",
    "MAQUINA_PAREADA": "Computador de sala pareado",
    "MAQUINA_DESPAREADA": "Computador de sala desconectado",
    "CODIGO_PAREAMENTO_REGENERADO": "Novo código de pareamento",
    "CAMPUS_CRIADO": "Campus criado",
    "CAMPUS_ATUALIZADO": "Campus editado",
    "CAMPUS_EXCLUIDO": "Campus excluído",
    "SALA_CRIADA": "Sala criada",
    "SALA_ATUALIZADA": "Sala editada",
    "SALA_EXCLUIDA": "Sala excluída",
    "TURMA_CRIADA": "Turma criada",
    "TURMA_ATUALIZADA": "Turma editada",
    "TURMA_EXCLUIDA": "Turma excluída",
    "DISCIPLINA_CRIADA": "Disciplina criada",
    "DISCIPLINA_ATUALIZADA": "Disciplina editada",
    "DISCIPLINA_EXCLUIDA": "Disciplina excluída",
    "AULA_CRIADA": "Horário de aula criado",
    "AULA_ATUALIZADA": "Horário de aula editado",
    "AULA_EXCLUIDA": "Horário de aula excluído",
    "ALUNO_CADASTRADO": "Aluno cadastrado",
    "ALUNO_ATUALIZADO": "Aluno editado",
    "ALUNO_EXCLUIDO": "Aluno excluído",
    "PROFESSOR_CADASTRADO": "Professor cadastrado",
    "PROFESSOR_ATUALIZADO": "Professor editado",
    "PROFESSOR_EXCLUIDO": "Professor excluído",
}


def rotulo_da_acao(acao: str) -> str:
    return ROTULOS_DE_ACAO.get(acao, acao.replace("_", " ").capitalize())


def eventos_visiveis(usuario):
    if hasattr(usuario, "administrador"):
        return AuditLog.objects.all()

    filtro = Q(autor_id=usuario.id)

    if hasattr(usuario, "professor"):
        sessoes = ChamadaSession.objects.filter(professor=usuario.professor).values("id")
        registros = PresencaRecord.objects.filter(sessao__professor=usuario.professor).values("id")
        filtro |= Q(tabela="sessao_chamada", linha_tabela_id__in=sessoes)
        filtro |= Q(tabela="registro_presenca", linha_tabela_id__in=registros)
    else:
        registros = PresencaRecord.objects.filter(usuario=usuario).values("id")
        solicitacoes = SolicitacaoLGPD.objects.filter(usuario=usuario).values("id")
        filtro |= Q(tabela="registro_presenca", linha_tabela_id__in=registros)
        filtro |= Q(tabela="solicitacao_lgpd", linha_tabela_id__in=solicitacoes)

    return AuditLog.objects.filter(filtro)
