import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.institution.models import Institution
from apps.privacy.models import SolicitacaoLGPD, Termo


@pytest.fixture
def instituicao(db):
    return Institution.objects.create(nome="Universidade de Mogi das Cruzes", cnpj="54303514000185")


@pytest.fixture
def aluno(db):
    return Usuario.objects.create_user(email="aluno.lgpd@umc.br", password="SenhaForte123")


def test_politica_de_privacidade_retorna_200_com_o_termo_ativo(instituicao):
    # Arrange
    Termo.objects.create(
        instituicao=instituicao,
        tipo=Termo.TIPO_POLITICA,
        versao="1.0",
        titulo="Política de Privacidade do ADSUM",
        conteudo="Texto da política",
        documento_hash="a" * 64,
        ativo=True,
    )

    # Act
    response = Client().get(reverse("privacy:politica_privacidade"))

    # Assert
    assert response.status_code == 200
    assert "Política de Privacidade do ADSUM" in response.content.decode()


def test_politica_de_privacidade_retorna_404_quando_nao_ha_termo_ativo(instituicao):
    # Act
    response = Client().get(reverse("privacy:politica_privacidade"))

    # Assert
    assert response.status_code == 404
    assert "Not Found" in response.content.decode()


def test_solicitacao_lgpd_salva_e_recupera_com_status_pendente(aluno):
    # Act
    criada = SolicitacaoLGPD.objects.create(usuario=aluno, tipo=SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)

    # Assert
    recuperada = SolicitacaoLGPD.objects.get(pk=criada.pk)
    assert recuperada.usuario == aluno
    assert recuperada.status == SolicitacaoLGPD.STATUS_PENDENTE


def test_aluno_cria_solicitacao_e_ela_aparece_em_minhas_solicitacoes(aluno):
    # Arrange
    client = Client()
    client.force_login(aluno)

    # Act
    response = client.post(reverse("privacy:solicitar_direito"), {
        "tipo": SolicitacaoLGPD.TIPO_EXCLUIR_CONTA,
        "justificativa": "Concluí o curso",
        "confirmo_impacto": "on",
    })
    listagem = client.get(reverse("privacy:minhas_solicitacoes"))

    # Assert
    solicitacao = SolicitacaoLGPD.objects.get()
    assert response.status_code == 302
    assert solicitacao.usuario == aluno
    assert listagem.status_code == 200
    assert f"#{solicitacao.pk} - Excluir minha conta" in listagem.content.decode()
