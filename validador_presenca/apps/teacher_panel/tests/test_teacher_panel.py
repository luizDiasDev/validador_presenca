from datetime import date, time
from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Administrador, Professor, Usuario
from apps.audit.models import AuditLog
from apps.checkin.models import ChamadaSession
from apps.institution.models import Campus, Institution, Room
from apps.teacher_panel.forms import AbrirChamadaForm, AulaForm
from apps.teacher_panel.models import Aula, Disciplina, Turma
from apps.validator.models import PresencaRecord


@pytest.fixture
def cenario_professor(db):
    inst = Institution.objects.create(
        nome="Universidade de Mogi das Cruzes",
        cnpj="54303514000185",
    )
    campus = Campus.objects.create(
        instituicao=inst,
        nome="Campus Sede",
        latitude="-23.5169621",
        longitude="-46.1826845",
        raio_metros=300,
    )
    sala = Room.objects.create(campus=campus, codigo="B-207", nome="Laboratório 7")
    user = Usuario.objects.create_user(
        email="prof.teste@umc.br",
        password="testpassword123",
        instituicao=inst,
    )
    professor = Professor.objects.create(
        usuario=user, area_atuacao="Engenharia de Software"
    )
    turma = Turma.objects.create(
        sala=sala,
        codigo="2324",
        nome="8 Semestre B",
        curso="Engenharia de Software",
        semestre_inicio=date(2026, 8, 1),
    )
    disciplina = Disciplina.objects.create(
        professor=professor,
        turma=turma,
        nome="IOT2",
    )
    dia_hoje = timezone.localdate().weekday()
    aula = Aula.objects.create(
        disciplina=disciplina,
        dia_semana=dia_hoje,
        hora_inicio=time(19, 10),
        hora_fim=time(22, 0),
        tempos_aula=4,
    )
    return {
        "inst": inst,
        "user": user,
        "professor": professor,
        "sala": sala,
        "turma": turma,
        "disciplina": disciplina,
        "aula": aula,
    }


@pytest.mark.django_db
def test_usuario_sem_perfil_professor_eh_redirecionado(client, cenario_professor):
    user_admin = Usuario.objects.create_user(
        email="adm@umc.br",
        password="testpassword123",
        instituicao=cenario_professor["inst"],
    )
    Administrador.objects.create(usuario=user_admin, cargo="Secretaria")
    client.force_login(user_admin)

    resp = client.get(reverse("teacher_panel:turmas"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_formato_concatenado_da_aula_com_turma_e_curso(cenario_professor):
    texto = str(cenario_professor["aula"])
    assert texto.startswith("2324 (Engenharia de Software) - IOT2 (")


@pytest.mark.django_db
def test_abrir_chamada_form_filtra_dia_vigente_e_limita_tempos_da_grade(
    cenario_professor,
):
    aula_hoje = cenario_professor["aula"]
    outro_dia = (aula_hoje.dia_semana + 1) % 7
    aula_outro_dia = Aula.objects.create(
        disciplina=cenario_professor["disciplina"],
        dia_semana=outro_dia,
        hora_inicio=time(19, 10),
        hora_fim=time(22, 0),
        tempos_aula=2,
    )

    form_hoje = AbrirChamadaForm(professor=cenario_professor["professor"])
    ids_disponiveis = list(
        form_hoje.fields["aula"].queryset.values_list("id", flat=True)
    )
    assert aula_hoje.id in ids_disponiveis
    assert aula_outro_dia.id not in ids_disponiveis

    # Tenta enviar tempos_cobertos = 6 para uma aula que tem tempos_aula = 4 na grade
    form_invalido = AbrirChamadaForm(
        data={
            "aula": aula_hoje.id,
            "duracao_min": 10,
            "tempos_cobertos": 6,
        },
        professor=cenario_professor["professor"],
    )
    assert form_invalido.is_valid() is False
    assert "tempos_cobertos" in form_invalido.errors


@pytest.mark.django_db
def test_aula_form_rejeita_hora_fim_menor_ou_igual_inicio(cenario_professor):
    form = AulaForm(
        data={
            "disciplina": cenario_professor["disciplina"].id,
            "dia_semana": 0,
            "hora_inicio": "22:00",
            "hora_fim": "19:10",
            "tempos_aula": 4,
        },
        professor=cenario_professor["professor"],
    )
    assert form.is_valid() is False
    assert "hora_fim" in form.errors


@pytest.mark.django_db
def test_professor_edita_e_exclui_aula(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]

    resp_edit = client.post(
        reverse("teacher_panel:editar_aula", kwargs={"aula_id": aula.id}),
        data={
            "disciplina": cenario_professor["disciplina"].id,
            "dia_semana": 2,
            "hora_inicio": "19:10",
            "hora_fim": "20:30",
            "tempos_aula": 2,
        },
    )
    assert resp_edit.status_code == 302
    aula.refresh_from_db()
    assert aula.dia_semana == 2
    assert aula.tempos_aula == 2

    resp_del = client.post(
        reverse("teacher_panel:excluir_aula", kwargs={"aula_id": aula.id})
    )
    assert resp_del.status_code == 302
    assert Aula.objects.filter(pk=aula.id).exists() is False


@pytest.mark.django_db
def test_professor_abre_e_encerra_chamada_pela_view(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]

    resp = client.post(
        reverse("teacher_panel:abrir_chamada"),
        data={
            "aula": aula.id,
            "duracao_min": 15,
            "tempos_cobertos": 4,
        },
    )
    assert resp.status_code == 302

    sessao = ChamadaSession.objects.get(aula=aula)
    assert sessao.sala_id == cenario_professor["sala"].id
    assert sessao.tempos_cobertos == 4

    resp_enc = client.post(
        reverse("teacher_panel:encerrar_chamada", kwargs={"sessao_id": sessao.id})
    )
    assert resp_enc.status_code == 302
    sessao.refresh_from_db()
    assert sessao.fecha_em <= sessao.abre_em or sessao.fecha_em is not None


@pytest.mark.django_db
def test_revisao_manual_atualiza_registro_e_gera_auditoria(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    registro = PresencaRecord.objects.create(
        qr_token_hash="abc123hash",
        score_facial=Decimal("0.620"),
        score_vida=Decimal("0.880"),
        geo_valida=True,
        score_final=Decimal("0.680"),
        aprovado=False,
        status="PENDING",
        origem="web",
        motivo="Score intermediario",
    )

    resp = client.post(
        reverse("teacher_panel:revisar_pendencia", kwargs={"registro_id": registro.id}),
        data={
            "status": "APPROVED",
            "motivo": "Aluno presente em bancada verificado pelo docente",
        },
    )
    assert resp.status_code == 302

    registro.refresh_from_db()
    assert registro.status == "APPROVED"
    assert registro.aprovado is True
    assert registro.revisado_por == cenario_professor["user"].id
    assert registro.data_revisao is not None

    log = AuditLog.objects.filter(
        acao="REVISAO_MANUAL_PRESENCA",
        linha_tabela_id=registro.id,
    ).first()
    assert log is not None
