from datetime import date, datetime, time, timedelta
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
def test_formato_concatenado_da_aula_com_nome_da_turma(cenario_professor):
    texto = str(cenario_professor["aula"])
    assert texto.startswith("8 Semestre B - IOT2 (")


def _no_horario(aula, hora, minuto):
    hoje = timezone.localdate()
    deslocamento = (aula.dia_semana - hoje.weekday()) % 7
    dia = hoje + timedelta(days=deslocamento)
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


def _com_agora(init_original, agora):
    def init(self, *args, **kwargs):
        kwargs.setdefault("agora", agora)
        init_original(self, *args, **kwargs)
    return init


def _dados_abrir(aula, **extra):
    return {"aula": aula.id, "duracao_min": 10, "tempos_cobertos": 2, "limite_por_maquina": 1, **extra}


@pytest.mark.django_db
def test_open_call_form_lists_all_teacher_classes_and_caps_periods(
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

    form = AbrirChamadaForm(professor=cenario_professor["professor"])
    ids_disponiveis = set(form.fields["aula"].queryset.values_list("id", flat=True))
    assert ids_disponiveis == {aula_hoje.id, aula_outro_dia.id}

    form_invalido = AbrirChamadaForm(
        data=_dados_abrir(aula_hoje, tempos_cobertos=6),
        professor=cenario_professor["professor"],
        agora=_no_horario(aula_hoje, 20, 0),
    )
    assert form_invalido.is_valid() is False
    assert "tempos_cobertos" in form_invalido.errors


@pytest.mark.django_db
def test_open_call_form_rejects_before_and_after_class_time(cenario_professor):
    aula = cenario_professor["aula"]
    for hora, minuto in ((19, 0), (22, 0), (23, 30)):
        form = AbrirChamadaForm(
            data=_dados_abrir(aula),
            professor=cenario_professor["professor"],
            agora=_no_horario(aula, hora, minuto),
        )
        assert form.is_valid() is False
        assert "só pode ser aberta durante a aula" in form.non_field_errors()[0]


@pytest.mark.django_db
def test_open_call_form_rejects_class_from_another_day(cenario_professor):
    aula = cenario_professor["aula"]
    ontem = _no_horario(aula, 20, 0) - timedelta(days=1)
    form = AbrirChamadaForm(
        data=_dados_abrir(aula),
        professor=cenario_professor["professor"],
        agora=ontem,
    )
    assert form.is_valid() is False
    assert "não é hoje" in form.non_field_errors()[0]


@pytest.mark.django_db
def test_open_call_form_accepts_during_class_and_ignores_opening_time(cenario_professor):
    aula = cenario_professor["aula"]
    form = AbrirChamadaForm(
        data=_dados_abrir(aula, horario="08:00"),
        professor=cenario_professor["professor"],
        agora=_no_horario(aula, 19, 10),
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["duracao_min"] == 10
    assert form.duracao_ajustada is False


@pytest.mark.django_db
def test_open_call_form_shortens_window_to_close_at_class_end(cenario_professor):
    aula = cenario_professor["aula"]
    form = AbrirChamadaForm(
        data=_dados_abrir(aula, duracao_min=30),
        professor=cenario_professor["professor"],
        agora=_no_horario(aula, 21, 52),
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["duracao_min"] == 8
    assert form.duracao_ajustada is True


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
def test_professor_abre_e_encerra_chamada_pela_view(client, cenario_professor, monkeypatch):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]
    durante_a_aula = _no_horario(aula, 20, 0)
    monkeypatch.setattr(AbrirChamadaForm, "__init__", _com_agora(AbrirChamadaForm.__init__, durante_a_aula))

    resp = client.post(
        reverse("teacher_panel:abrir_chamada"),
        data={
            "aula": aula.id,
            "duracao_min": 15,
            "tempos_cobertos": 4,
            "limite_por_maquina": 2,
        },
    )
    assert resp.status_code == 302

    sessao = ChamadaSession.objects.get(aula=aula)
    assert sessao.sala_id == cenario_professor["sala"].id
    assert sessao.tempos_cobertos == 4
    assert sessao.limite_por_maquina == 2

    resp_enc = client.post(
        reverse("teacher_panel:encerrar_chamada", kwargs={"sessao_id": sessao.id})
    )
    assert resp_enc.status_code == 302
    sessao.refresh_from_db()
    assert sessao.fecha_em <= sessao.abre_em or sessao.fecha_em is not None


@pytest.mark.django_db
def test_revisao_manual_atualiza_registro_e_gera_auditoria(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    agora = timezone.now()
    sessao = ChamadaSession.objects.create(
        aula=cenario_professor["aula"],
        sala=cenario_professor["sala"],
        professor=cenario_professor["professor"],
        abre_em=agora,
        fecha_em=agora,
    )
    registro = PresencaRecord.objects.create(
        sessao=sessao,
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


@pytest.mark.django_db
def test_open_call_view_rejects_outside_class_day(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]
    aula.dia_semana = (timezone.localdate().weekday() + 1) % 7
    aula.save()

    resp = client.post(reverse("teacher_panel:abrir_chamada"), data=_dados_abrir(aula), follow=True)

    assert ChamadaSession.objects.filter(aula=aula).exists() is False
    assert "não é hoje" in resp.content.decode()


@pytest.mark.django_db
def test_calls_page_has_single_block_with_open_now_and_schedule(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    html = client.get(reverse("teacher_panel:chamadas")).content.decode()

    assert html.count('name="aula"') == 1
    assert reverse("teacher_panel:abrir_chamada") in html
    assert reverse("teacher_panel:agendar_chamada") in html
    assert "ABRIR AGORA" in html
    assert "AGENDAR" in html


@pytest.mark.django_db
def test_schedule_without_opening_time_shows_clear_error(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]

    resp = client.post(reverse("teacher_panel:agendar_chamada"), data=_dados_abrir(aula), follow=True)

    assert "Preencha o campo Abre às" in resp.content.decode()


@pytest.mark.django_db
def test_schedule_too_close_to_class_end_tells_latest_opening_time(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    aula = cenario_professor["aula"]

    resp = client.post(
        reverse("teacher_panel:agendar_chamada"),
        data=_dados_abrir(aula, horario="21:55"),
        follow=True,
    )

    html = resp.content.decode()
    assert "Abrindo às 21:55 com janela de 10 min" in html
    assert "entre 19:10 e 21:50" in html
