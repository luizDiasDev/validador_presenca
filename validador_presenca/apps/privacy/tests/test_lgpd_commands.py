import json

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import Usuario
from apps.audit.models import AuditLog
from apps.biometrics.models import Biometria
from apps.biometrics.tests.test_biometric_service import enrolled_student
from apps.privacy.models import SolicitacaoLGPD, Termo
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def request_of(student, tipo):
    return SolicitacaoLGPD.objects.create(usuario=student, tipo=tipo)


def test_export_writes_the_user_data_without_the_face_vector(tmp_path):
    student = enrolled_student()

    call_command("lgpd_exportar", student.email, pasta=str(tmp_path))

    data = json.loads((tmp_path / f"dados_usuario_{student.id}.json").read_text(encoding="utf-8"))
    assert data["conta"]["email"] == student.email
    assert data["biometria"]["cadastrada"] is True
    assert "embedding" not in json.dumps(data)
    assert any(aceite["documento"] == "Termo de Consentimento Biométrico" for aceite in data["aceites_de_termos"])


def test_export_of_an_unknown_email_fails(tmp_path):
    with pytest.raises(CommandError):
        call_command("lgpd_exportar", "ninguem@umc.br", pasta=str(tmp_path))


def test_attending_an_export_request_writes_the_file_and_closes_it(tmp_path):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)

    call_command("lgpd_atender", request.id, pasta=str(tmp_path))

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert (tmp_path / f"dados_usuario_{student.id}.json").exists()


def test_attending_an_account_deletion_anonymizes_and_keeps_the_presence_history(tmp_path):
    student = enrolled_student()
    original_email = student.email
    PresencaRecord.objects.create(
        usuario=student, qr_token_hash="hash", geo_valida=True, score_facial=0, score_vida=0,
        score_final=0, aprovado=False, status="REJECTED", origem="qr",
    )
    request = request_of(student, SolicitacaoLGPD.TIPO_EXCLUIR_CONTA)

    call_command("lgpd_atender", request.id, pasta=str(tmp_path))

    student = Usuario.objects.get(pk=student.pk)
    assert student.email != original_email
    assert student.email.endswith("@anonimizado.adsum")
    assert student.is_active is False
    assert student.has_usable_password() is False
    assert not Biometria.objects.filter(usuario=student).exists()
    assert PresencaRecord.objects.filter(usuario=student).count() == 1
    assert AuditLog.objects.filter(acao="CONTA_ANONIMIZADA", linha_tabela_id=student.id).exists()


def test_attending_a_revocation_deletes_the_biometric(tmp_path):
    student = enrolled_student()
    request = request_of(student, SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA)

    call_command("lgpd_atender", request.id, pasta=str(tmp_path))

    assert not Biometria.objects.filter(usuario=student).exists()


def test_correction_requests_are_not_automated_and_a_request_is_never_attended_twice(tmp_path):
    student = enrolled_student()
    correction = request_of(student, SolicitacaoLGPD.TIPO_CORRIGIR_DADOS)
    with pytest.raises(CommandError, match="Gestão de Usuários"):
        call_command("lgpd_atender", correction.id, pasta=str(tmp_path))

    revocation = request_of(student, SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA)
    call_command("lgpd_atender", revocation.id, pasta=str(tmp_path))
    with pytest.raises(CommandError, match="já foi atendida"):
        call_command("lgpd_atender", revocation.id, pasta=str(tmp_path))


def test_publishing_a_new_version_replaces_the_active_one(tmp_path):
    student = enrolled_student()
    old = Termo.objects.create(
        instituicao=student.instituicao, tipo=Termo.TIPO_POLITICA, versao="1.0", titulo="Política",
        conteudo="Texto antigo", documento_hash="a" * 64, ativo=True,
    )
    document = tmp_path / "politica.md"
    document.write_text("Texto novo", encoding="utf-8")

    call_command("publicar_termo", Termo.TIPO_POLITICA, "2.0", str(document))

    old.refresh_from_db()
    new = Termo.objects.get(tipo=Termo.TIPO_POLITICA, ativo=True)
    assert old.ativo is False
    assert new.versao == "2.0"
    assert new.titulo == "Política"
    assert new.conteudo == "Texto novo"
    with pytest.raises(CommandError, match="já foi publicada"):
        call_command("publicar_termo", Termo.TIPO_POLITICA, "2.0", str(document))


@pytest.mark.parametrize("tipo, arquivo", [
    (Termo.TIPO_POLITICA, "apps/privacy/termos/politica_privacidade_v2.md"),
    (Termo.TIPO_TERMO, "apps/privacy/termos/termo_uso_v2.md"),
])
def test_revised_documents_publish_over_the_initial_ones(tipo, arquivo):
    call_command("loaddata", "initial_data", "termos_iniciais", verbosity=0)

    call_command("publicar_termo", tipo, "2.0", arquivo)

    new = Termo.objects.get(tipo=tipo, ativo=True)
    assert new.versao == "2.0"
    assert "laboratórios com computadores" in new.conteudo
    assert "checkbox" not in new.conteudo
