import json
from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Administrador, Usuario
from apps.audit.models import AuditLog
from apps.biometrics.models import Biometria
from apps.biometrics.tests.test_biometric_service import enrolled_student
from apps.institution.models import Campus, Room
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD
from apps.teacher_panel.models import Aluno, Turma

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    user = Usuario.objects.create_user(email="dpo@umc.br", password="SenhaForte123")
    Administrador.objects.create(usuario=user, cargo="Encarregado de Dados")
    return user


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


def request_of(user, tipo, days_ago=0):
    request = SolicitacaoLGPD.objects.create(usuario=user, tipo=tipo, justificativa="Quero exercer meu direito")
    if days_ago:
        SolicitacaoLGPD.objects.filter(pk=request.pk).update(
            data_solicitacao=timezone.now() - timedelta(days=days_ago)
        )
        request.refresh_from_db()
    return request


def decide(client, request, decisao, resposta=""):
    return client.post(
        reverse("privacy:decidir_solicitacao", args=[request.id]),
        {"decisao": decisao, "resposta": resposta},
        follow=True,
    )


def with_enrollment(student):
    campus = Campus.objects.create(
        instituicao=student.instituicao, nome="Sede", latitude="-23.5", longitude="-46.1", raio_metros=300,
    )
    turma = Turma.objects.create(
        sala=Room.objects.create(campus=campus, codigo="A-30", nome="Lab"),
        codigo="2324", nome="ES", curso="ES", semestre_inicio=date(2026, 8, 1),
    )
    return Aluno.objects.create(usuario=student, turma=turma, matricula="11221100123")


def test_only_admins_see_the_requests_screen(client):
    student = enrolled_student()
    client.force_login(student)

    assert client.get(reverse("privacy:solicitacoes_admin")).status_code == 302


def test_screen_lists_open_requests_oldest_first_and_flags_late_ones(admin_client):
    student = enrolled_student()
    late = request_of(student, SolicitacaoLGPD.TIPO_EXPORTAR_DADOS, days_ago=20)
    recent = request_of(student, SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA, days_ago=2)
    closed = request_of(student, SolicitacaoLGPD.TIPO_CORRIGIR_DADOS)
    SolicitacaoLGPD.objects.filter(pk=closed.pk).update(status=SolicitacaoLGPD.STATUS_ATENDIDA)

    html = admin_client.get(reverse("privacy:solicitacoes_admin")).content.decode()

    assert html.index(f"#{late.id} ·") < html.index(f"#{recent.id} ·")
    assert f"#{closed.id} ·" not in html
    assert "fora do prazo" in html
    assert "há 20 dias" in html


def test_attending_a_revocation_deletes_the_biometric_and_is_audited(admin_client, admin_user):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA)

    decide(admin_client, request, "atender")

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert not Biometria.objects.filter(usuario=student).exists()
    assert AuditLog.objects.filter(
        acao="SOLICITACAO_LGPD_STATUS", autor_id=admin_user.id, linha_tabela_id=request.id
    ).exists()


def test_attending_an_account_deletion_removes_every_identifier(admin_client):
    student = enrolled_student()
    aluno = with_enrollment(student)
    AceiteTermo.objects.filter(usuario=student).update(evidencia={"ip": "10.0.0.1", "user_agent": "Firefox", "contexto": "login"})
    request = request_of(student, SolicitacaoLGPD.TIPO_EXCLUIR_CONTA)

    decide(admin_client, request, "atender")

    student.refresh_from_db()
    aluno.refresh_from_db()
    assert student.email.endswith("@anonimizado.adsum")
    assert student.first_name == "Anonimizado"
    assert student.is_active is False
    assert aluno.matricula.startswith("anon-")
    assert not Biometria.objects.filter(usuario=student).exists()
    for aceite in AceiteTermo.objects.filter(usuario=student):
        assert "ip" not in aceite.evidencia
        assert "user_agent" not in aceite.evidencia
        assert aceite.evidencia.get("contexto") == "login"


def test_an_admin_cannot_anonymize_their_own_account(admin_client, admin_user):
    request = request_of(admin_user, SolicitacaoLGPD.TIPO_EXCLUIR_CONTA)

    resp = decide(admin_client, request, "atender")

    admin_user.refresh_from_db()
    assert admin_user.is_active is True
    assert "Outro administrador" in resp.content.decode()


def test_refusing_requires_an_explanation_that_the_holder_sees(admin_client):
    client = Client()
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA)

    decide(admin_client, request, "recusar", "curta")
    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_PENDENTE

    decide(admin_client, request, "recusar", "A matrícula informada não confere com a conta.")
    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_RECUSADA
    assert Biometria.objects.filter(usuario=student).exists()

    client.force_login(student)
    html = client.get(reverse("privacy:minhas_solicitacoes")).content.decode()
    assert "A matrícula informada não confere" in html


def test_a_correction_is_closed_only_with_a_description_of_what_changed(admin_client):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_CORRIGIR_DADOS)

    decide(admin_client, request, "atender")
    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_PENDENTE

    decide(admin_client, request, "atender", "Nome corrigido para Maria Souza.")
    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert request.resposta_dpo == "Nome corrigido para Maria Souza."


def test_a_closed_request_cannot_be_decided_again(admin_client):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)
    decide(admin_client, request, "atender")

    resp = decide(admin_client, request, "recusar", "Mudei de ideia sobre este pedido.")

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert "já foi atendida" in resp.content.decode()


def test_the_holder_downloads_their_data_only_after_the_export_is_attended(admin_client):
    client = Client()
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)
    client.force_login(student)

    assert client.get(reverse("privacy:baixar_meus_dados")).status_code == 404

    decide(admin_client, request, "atender")
    assert "Baixar meus dados" in client.get(reverse("privacy:minhas_solicitacoes")).content.decode()
    resp = client.get(reverse("privacy:baixar_meus_dados"))

    assert resp.status_code == 200
    assert "attachment" in resp["Content-Disposition"]
    data = json.loads(resp.content)
    assert data["conta"]["email"] == student.email
    assert "embedding" not in json.dumps(data).lower()


def test_the_back_link_never_redirects_to_another_site(admin_client):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)

    resp = admin_client.post(
        reverse("privacy:decidir_solicitacao", args=[request.id]),
        {"decisao": "analisar", "voltar": "https://site-malicioso.com/"},
    )

    assert resp["Location"] == reverse("privacy:solicitacoes_admin")


def test_login_events_no_longer_copy_the_email_into_the_audit_log(client):
    user = Usuario.objects.create_user(email="prof@umc.br", password="SenhaForte123")
    client.force_login(user)

    client.post(reverse("accounts:logout"))

    log = AuditLog.objects.get(acao="LOGOUT", autor_id=user.id)
    assert "prof@umc.br" not in json.dumps(log.payload)


def test_a_user_without_biometrics_cannot_ask_to_revoke_them(client):
    professor = Usuario.objects.create_user(email="prof.sem.rosto@umc.br", password="SenhaForte123")
    client.force_login(professor)

    page = client.get(reverse("privacy:solicitar_direito")).content.decode()
    resp = client.post(reverse("privacy:solicitar_direito"), {
        "tipo": SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA, "justificativa": "Teste", "confirmo_impacto": "on",
    })

    assert 'value="revogar_biometria"' not in page
    assert resp.status_code == 200
    assert not SolicitacaoLGPD.objects.filter(usuario=professor).exists()


def test_a_student_with_biometrics_can_ask_to_revoke_them_once_at_a_time(client):
    student = enrolled_student()
    client.force_login(student)
    data = {"tipo": SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA, "justificativa": "", "confirmo_impacto": "on"}

    assert 'value="revogar_biometria"' in client.get(reverse("privacy:solicitar_direito")).content.decode()
    client.post(reverse("privacy:solicitar_direito"), data)
    resp = client.post(reverse("privacy:solicitar_direito"), data)

    assert SolicitacaoLGPD.objects.filter(usuario=student).count() == 1
    assert "já tem uma solicitação deste tipo" in resp.content.decode()
