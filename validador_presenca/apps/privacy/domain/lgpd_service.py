import hashlib
import json
from pathlib import Path

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import LogRegister
from apps.audit.models import AuditLog
from apps.biometrics.domain.services.biometric_service import BiometricService
from apps.biometrics.models import Biometria
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD
from apps.validator.models import PresencaRecord

DOMINIO_ANONIMO = "anonimizado.adsum"
TIPOS_ATENDIDOS_AUTOMATICAMENTE = (
    SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA,
    SolicitacaoLGPD.TIPO_EXCLUIR_CONTA,
    SolicitacaoLGPD.TIPO_EXPORTAR_DADOS,
)


class SolicitacaoNaoAutomatizavelError(Exception):
    pass


def exportar_dados(usuario) -> dict:
    aluno = getattr(usuario, "aluno", None)
    professor = getattr(usuario, "professor", None)
    administrador = getattr(usuario, "administrador", None)
    biometria = Biometria.objects.filter(usuario=usuario).first()

    return {
        "gerado_em": timezone.now(),
        "conta": {
            "id": usuario.id,
            "nome": usuario.get_full_name(),
            "email": usuario.email,
            "instituicao": str(usuario.instituicao) if usuario.instituicao_id else None,
            "data_cadastro": usuario.date_joined,
            "ultimo_acesso": usuario.last_login,
            "segundo_fator_ativo": usuario.totp_ativo,
        },
        "perfis": {
            "aluno": {"matricula": aluno.matricula, "turma": aluno.turma.codigo} if aluno else None,
            "professor": {"area_atuacao": professor.area_atuacao} if professor else None,
            "administrador": {"cargo": administrador.cargo} if administrador else None,
        },
        "biometria": {
            "cadastrada": biometria is not None,
            "data_cadastro": biometria.data_criacao if biometria else None,
            "observacao": "O vetor facial é cifrado e não é exportado.",
        },
        "aceites_de_termos": [
            {
                "documento": aceite.termo.get_tipo_display(),
                "versao": aceite.termo.versao,
                "concedido": aceite.concedido,
                "data_concedido": aceite.data_concedido,
                "data_revogada": aceite.data_revogada,
                "evidencia": aceite.evidencia,
            }
            for aceite in AceiteTermo.objects.filter(usuario=usuario).select_related("termo")
        ],
        "presencas": [
            {
                "data": registro.data_criacao,
                "disciplina": registro.sessao.aula.disciplina.nome
                if registro.sessao_id and registro.sessao.aula_id
                else None,
                "status": registro.status,
                "origem": registro.origem,
                "localizacao_valida": registro.geo_valida,
                "score_final": registro.score_final,
                "motivo": registro.motivo,
            }
            for registro in PresencaRecord.objects.filter(usuario=usuario)
            .select_related("sessao__aula__disciplina")
            .order_by("data_criacao")
        ],
        "solicitacoes_lgpd": [
            {
                "tipo": solicitacao.get_tipo_display(),
                "status": solicitacao.get_status_display(),
                "data_solicitacao": solicitacao.data_solicitacao,
                "data_resposta": solicitacao.data_resposta,
            }
            for solicitacao in SolicitacaoLGPD.objects.filter(usuario=usuario)
        ],
        "eventos_de_auditoria": [
            {"acao": evento.acao, "origem": evento.origem, "ocorrido_em": evento.ocorrido_em}
            for evento in AuditLog.objects.filter(autor_id=usuario.id).order_by("ocorrido_em")
        ],
    }


def gravar_exportacao(usuario, pasta: str) -> Path:
    destino = Path(pasta)
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / f"dados_usuario_{usuario.id}.json"
    arquivo.write_text(
        json.dumps(exportar_dados(usuario), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return arquivo


@transaction.atomic
def anonimizar_conta(usuario, autor_id: int) -> None:
    BiometricService().revoke(usuario, origin="exclusao_de_conta")

    apelido = hashlib.sha256(usuario.email.encode()).hexdigest()[:16]
    usuario.email = f"{apelido}@{DOMINIO_ANONIMO}"
    usuario.username = usuario.email
    usuario.first_name = "Anonimizado"
    usuario.last_name = apelido
    usuario.is_active = False
    usuario.totp_cifrado = None
    usuario.totp_ativo = False
    usuario.chave_sessao_ativa = ""
    usuario.set_unusable_password()
    usuario.save()

    LogRegister().register(
        {
            "autor_id": autor_id,
            "origem": "privacy",
            "acao": "CONTA_ANONIMIZADA",
            "tabela": "usuario",
            "linha_tabela_id": usuario.id,
            "payload": {"apelido": apelido},
        }
    )


def atender_solicitacao(solicitacao: SolicitacaoLGPD, autor_id: int) -> SolicitacaoLGPD:
    if solicitacao.tipo not in TIPOS_ATENDIDOS_AUTOMATICAMENTE:
        raise SolicitacaoNaoAutomatizavelError(
            "Correção de dados é feita pela Gestão de Usuários. Depois, marque a solicitação como atendida no admin."
        )

    if solicitacao.tipo == SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA:
        return BiometricService().fulfill_revocation_request(solicitacao)

    if solicitacao.tipo == SolicitacaoLGPD.TIPO_EXCLUIR_CONTA:
        anonimizar_conta(solicitacao.usuario, autor_id)
        resposta = "Conta anonimizada. Registros de presença preservados sem identificação."
    else:
        resposta = "Dados exportados em JSON e enviados ao titular."

    solicitacao.status = SolicitacaoLGPD.STATUS_ATENDIDA
    solicitacao.data_resposta = solicitacao.data_resposta or timezone.now()
    solicitacao.resposta_dpo = solicitacao.resposta_dpo or resposta
    solicitacao.save()
    return solicitacao
