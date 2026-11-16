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
from apps.teacher_panel.models import Aluno
from apps.validator.models import PresencaRecord

DOMINIO_ANONIMO = "anonimizado.adsum"
TIPOS_ATENDIDOS_AUTOMATICAMENTE = (
    SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA,
    SolicitacaoLGPD.TIPO_EXCLUIR_CONTA,
    SolicitacaoLGPD.TIPO_EXPORTAR_DADOS,
)
STATUS_ENCERRADOS = (SolicitacaoLGPD.STATUS_ATENDIDA, SolicitacaoLGPD.STATUS_RECUSADA)
CAMPOS_DE_EVIDENCIA_PESSOAIS = ("ip", "user_agent")
PRAZO_DIAS = 15


class SolicitacaoNaoAutomatizavelError(Exception):
    pass


class SolicitacaoEncerradaError(Exception):
    pass


class AutoAtendimentoError(Exception):
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

    Aluno.objects.filter(usuario=usuario).update(matricula=f"anon-{apelido}")
    for aceite in AceiteTermo.objects.filter(usuario=usuario):
        evidencia = {
            chave: valor for chave, valor in (aceite.evidencia or {}).items()
            if chave not in CAMPOS_DE_EVIDENCIA_PESSOAIS
        }
        if evidencia != aceite.evidencia:
            aceite.evidencia = evidencia
            aceite.save(update_fields=["evidencia"])

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


def dias_em_aberto(solicitacao: SolicitacaoLGPD, agora=None) -> int:
    fim = solicitacao.data_resposta or agora or timezone.now()
    return (fim - solicitacao.data_solicitacao).days


def _garantir_aberta(solicitacao: SolicitacaoLGPD) -> None:
    if solicitacao.status in STATUS_ENCERRADOS:
        raise SolicitacaoEncerradaError(
            f"A solicitação #{solicitacao.id} já foi {solicitacao.get_status_display().lower()}."
        )


def _auditar_status(autor_id: int, solicitacao: SolicitacaoLGPD) -> None:
    LogRegister().register(
        {
            "autor_id": autor_id,
            "origem": "privacy",
            "acao": "SOLICITACAO_LGPD_STATUS",
            "tabela": "solicitacao_lgpd",
            "linha_tabela_id": solicitacao.id,
            "payload": {"tipo": solicitacao.tipo, "status": solicitacao.status, "titular_id": solicitacao.usuario_id},
        }
    )


@transaction.atomic
def atender_solicitacao(solicitacao: SolicitacaoLGPD, autor_id: int, resposta: str = "") -> SolicitacaoLGPD:
    _garantir_aberta(solicitacao)
    resposta = resposta.strip()

    if solicitacao.tipo == SolicitacaoLGPD.TIPO_CORRIGIR_DADOS:
        if not resposta:
            raise SolicitacaoNaoAutomatizavelError(
                "Correção de dados é feita pela Gestão de Usuários. Depois, descreva o que foi corrigido na resposta."
            )
    elif solicitacao.tipo not in TIPOS_ATENDIDOS_AUTOMATICAMENTE:
        raise SolicitacaoNaoAutomatizavelError("Tipo de solicitação desconhecido.")

    if solicitacao.tipo == SolicitacaoLGPD.TIPO_EXCLUIR_CONTA and solicitacao.usuario_id == autor_id:
        raise AutoAtendimentoError("Outro administrador precisa atender a exclusão da sua própria conta.")

    if solicitacao.tipo == SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA:
        solicitacao.resposta_dpo = resposta or solicitacao.resposta_dpo
        BiometricService().fulfill_revocation_request(solicitacao)
    else:
        if solicitacao.tipo == SolicitacaoLGPD.TIPO_EXCLUIR_CONTA:
            anonimizar_conta(solicitacao.usuario, autor_id)
            padrao = "Conta anonimizada. Registros de presença preservados sem identificação."
        elif solicitacao.tipo == SolicitacaoLGPD.TIPO_EXPORTAR_DADOS:
            padrao = "Seus dados estão prontos: use o botão Baixar meus dados nesta página."
        else:
            padrao = ""
        solicitacao.status = SolicitacaoLGPD.STATUS_ATENDIDA
        solicitacao.data_resposta = solicitacao.data_resposta or timezone.now()
        solicitacao.resposta_dpo = resposta or solicitacao.resposta_dpo or padrao
        solicitacao.save()

    _auditar_status(autor_id, solicitacao)
    return solicitacao


@transaction.atomic
def recusar_solicitacao(solicitacao: SolicitacaoLGPD, autor_id: int, resposta: str) -> SolicitacaoLGPD:
    _garantir_aberta(solicitacao)
    resposta = resposta.strip()
    if len(resposta) < 10:
        raise ValueError("Explique ao titular por que a solicitação foi recusada (mínimo de 10 caracteres).")
    solicitacao.status = SolicitacaoLGPD.STATUS_RECUSADA
    solicitacao.resposta_dpo = resposta
    solicitacao.data_resposta = timezone.now()
    solicitacao.save()
    _auditar_status(autor_id, solicitacao)
    return solicitacao


def colocar_em_analise(solicitacao: SolicitacaoLGPD, autor_id: int) -> SolicitacaoLGPD:
    _garantir_aberta(solicitacao)
    solicitacao.status = SolicitacaoLGPD.STATUS_EM_ANALISE
    solicitacao.save(update_fields=["status"])
    _auditar_status(autor_id, solicitacao)
    return solicitacao
