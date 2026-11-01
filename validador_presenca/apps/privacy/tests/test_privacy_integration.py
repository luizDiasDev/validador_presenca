import uuid

import pytest
from django.test import Client

from apps.accounts.models import Usuario
from apps.institution.models import Institution
from apps.privacy.models import SolicitacaoLGPD, Termo

CENTRAL = "/privacidade/"
POLITICA = "/privacidade/politica/"
TERMOS = "/privacidade/termos/"
SOLICITAR = "/privacidade/solicitar/"
MINHAS = "/privacidade/minhas-solicitacoes/"

pytestmark = pytest.mark.django_db


# ---------- Helpers ----------

def create_student():
    return Usuario.objects.create_user(email=f"aluno.{uuid.uuid4().hex}@umc.br", password="SenhaForte123")


def logged_client(user=None):
    client = Client()
    client.force_login(user or create_student())
    return client


def create_term(term_type, title):
    suffix = uuid.uuid4().hex[:8]
    institution = Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))
    return Termo.objects.create(
        instituicao=institution, tipo=term_type, versao="1.0", titulo=title,
        conteudo="Conteúdo do documento", documento_hash="a" * 64, ativo=True,
    )


def build_lgpd_request(request_type=SolicitacaoLGPD.TIPO_EXPORTAR_DADOS, justification=""):
    return {"tipo": request_type, "justificativa": justification, "confirmo_impacto": "on"}


def create_lgpd_request(client, justification):
    """Creates the request through the real endpoint and returns the saved record."""
    client.post(SOLICITAR, build_lgpd_request(justification=justification))
    return SolicitacaoLGPD.objects.get(justificativa=justification)


# ---------- GET /privacidade/ ----------


def test_central_logado_deveRetornar200ComAtalhosLgpd():
    response = logged_client().get(CENTRAL)

    assert response.status_code == 200
    html = response.content.decode()
    assert SOLICITAR in html
    assert MINHAS in html


# ---------- GET /privacidade/politica/ e /privacidade/termos/ ----------

def test_politica_comTermoAtivo_deveRetornar200ComTituloDoTermo():
    termo = create_term(Termo.TIPO_POLITICA, "Política de Privacidade ADSUM")

    response = Client().get(POLITICA)

    assert response.status_code == 200
    assert response.context["termo"] == termo
    assert "Política de Privacidade ADSUM" in response.content.decode()


def test_politica_semTermoAtivo_deveRetornar404():
    create_term(Termo.TIPO_TERMO, "Só existe termo de uso")

    response = Client().get(POLITICA)

    assert response.status_code == 404
    assert "Not Found" in response.content.decode()


def test_termoUso_comTermoAtivo_deveRetornar200ComTituloDoTermo():
    termo = create_term(Termo.TIPO_TERMO, "Termo de Uso ADSUM")

    response = Client().get(TERMOS)

    assert response.status_code == 200
    assert response.context["termo"] == termo
    assert "Termo de Uso ADSUM" in response.content.decode()


def test_termoUso_semTermoAtivo_deveRetornar404():
    response = Client().get(TERMOS)

    assert response.status_code == 404
    assert "Not Found" in response.content.decode()


# ---------- GET/POST /privacidade/solicitar/ ----------

def test_solicitar_get_deveRetornar200ComFormularioEPrazo():
    response = logged_client().get(SOLICITAR)

    assert response.status_code == 200
    assert "form" in response.context
    assert "prazo" in response.context
    assert "Enviar solicitação" in response.content.decode()


def test_solicitar_comDadosValidos_deveRedirecionarParaMinhasSolicitacoesEGravar():
    user = create_student()
    justificativa = f"Concluí o curso {uuid.uuid4().hex}"

    response = logged_client(user).post(
        SOLICITAR, build_lgpd_request(SolicitacaoLGPD.TIPO_EXCLUIR_CONTA, justificativa)
    )

    assert response.status_code == 302
    assert response["Location"] == MINHAS
    # Efeito persistido
    gravada = SolicitacaoLGPD.objects.get(justificativa=justificativa)
    assert gravada.usuario == user
    assert gravada.tipo == SolicitacaoLGPD.TIPO_EXCLUIR_CONTA
    assert gravada.status == SolicitacaoLGPD.STATUS_PENDENTE


# ---------- GET /privacidade/minhas-solicitacoes/ ----------

def test_minhasSolicitacoes_semLogin_deveRedirecionar302ParaLogin():
    response = Client().get(MINHAS)

    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


def test_minhasSolicitacoes_doDono_deveRetornar200ComASolicitacao():
    client = logged_client()
    solicitacao = create_lgpd_request(client, f"minha {uuid.uuid4().hex}")

    response = client.get(MINHAS)

    assert response.status_code == 200
    assert list(response.context["solicitacoes"]) == [solicitacao]
    assert f"#{solicitacao.pk} - Exportar meus dados" in response.content.decode()


def test_minhasSolicitacoes_deOutroUsuario_naoDeveExibirSolicitacaoAlheia():
    solicitacao_alheia = create_lgpd_request(logged_client(), f"alheia {uuid.uuid4().hex}")

    response = logged_client().get(MINHAS)

    assert response.status_code == 200
    assert list(response.context["solicitacoes"]) == []
    assert f"#{solicitacao_alheia.pk} -" not in response.content.decode()