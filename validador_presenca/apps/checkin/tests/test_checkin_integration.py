import uuid
from datetime import time

import pytest
import requests
from django.test import Client

from apps.accounts.models import Professor, Usuario
from django.core.cache import cache

from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.institution.models import Campus, Institution, Room
from apps.teacher_panel.models import Aluno, Aula, Disciplina, Turma
from apps.validator.models import PresencaRecord

QR_PATH = "/checkin/"
STATUS_PATH = "/checkin/api/v1/sessoes/sala/{sala_id}/status/"

pytestmark = pytest.mark.django_db(transaction=True)


# ---------- Helpers ----------

def create_room():
    suffix = uuid.uuid4().hex[:8]
    institution = Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))
    campus = Campus.objects.create(
        instituicao=institution,
        nome="Campus Sede",
        latitude="-23.5169621",
        longitude="-46.1826845",
        raio_metros=300,
    )
    return Room.objects.create(campus=campus, codigo=f"B-{suffix[:4]}", nome="Laboratório 7")


def create_teacher():
    user = Usuario.objects.create_user(email=f"prof.{uuid.uuid4().hex}@umc.br", password="senha-forte-123")
    return Professor.objects.create(usuario=user, area_atuacao="Engenharia de Software")


def create_lesson(room, teacher, subject_name):
    class_group = Turma.objects.create(
        sala=room, codigo="ES-8", nome="Turma 8", curso="Eng. Software", semestre_inicio="2026-08-01"
    )
    subject = Disciplina.objects.create(professor=teacher, turma=class_group, nome=subject_name)
    return Aula.objects.create(disciplina=subject, dia_semana=5, hora_inicio=time(19), hora_fim=time(22))


def logged_http_session():
    """Creates a user, logs in through the framework and returns a requests.Session with the session cookie."""
    user = Usuario.objects.create_user(email=f"aluno.{uuid.uuid4().hex}@umc.br", password="senha-forte-123")
    suffix = uuid.uuid4().hex[:6]
    class_group = Turma.objects.create(
        sala=create_room(), codigo=f"AL-{suffix}", nome="Turma do aluno", curso="Eng. Software", semestre_inicio="2026-08-01"
    )
    Aluno.objects.create(usuario=user, turma=class_group, matricula=suffix)
    django_client = Client()
    django_client.force_login(user)
    http = requests.Session()
    http.cookies.set("sessionid", django_client.cookies["sessionid"].value)
    return http, user


# ---------- GET /checkin/api/v1/sessoes/sala/{id}/status/ ----------


def test_status_comChamadaAbertaDeUmaAula_deveRetornar200ComDisciplinaDaAula(live_server):
    # Relacionamento: sala -> turma -> disciplina -> aula -> sessao de chamada
    sala = create_room()
    professor = create_teacher()
    aula = create_lesson(sala, professor, "Desenvolvimento de Software Corporativo")
    sessao = ChamadaService().abrir(sala_id=sala.id, professor=professor, aula=aula, duracao_min=5)

    response = requests.get(live_server.url + STATUS_PATH.format(sala_id=sala.id))

    assert response.status_code == 200
    body = response.json()
    assert body["ativa"] is True
    assert body["sessao_id"] == sessao.id
    assert body["sequencia"] == 1
    assert body["disciplina"] == "Desenvolvimento de Software Corporativo"
    assert body["abre_em"] == sessao.abre_em.isoformat()


def test_status_comSalaIdNaoNumerico_deveRetornar404(live_server):
    response = requests.get(live_server.url + "/checkin/api/v1/sessoes/sala/abc/status/")

    assert response.status_code == 404
    assert "Not Found" in response.text


# ---------- POST /checkin/ (qr_demo: consome o token e registra presença) ----------

def test_qrDemo_postComTokenValido_deveRegistrarPresencaNoBanco(live_server):
    http, aluno = logged_http_session()
    http.get(live_server.url + QR_PATH)  # abre a tela do aluno (recebe o cookie de CSRF)
    # o QR agora é exibido na tela da sala; aqui o token é gerado direto pelo serviço
    token = QrTokenService(cache=cache).gerar(sessao_id=1, maquina_id=1).token

    response = http.post(
        live_server.url + QR_PATH,
        data={"token": token},
        headers={"X-CSRFToken": http.cookies["csrftoken"]},
    )

    assert response.status_code == 200
    assert "Check-in não aceito" in response.text  # sessão 1 não existe, então a chamada não está aberta
    # Efeito persistido: um registro de presença foi gravado pelo try_checkin
    registro = PresencaRecord.objects.get()
    assert registro.origem == "qr"
    assert registro.geo_valida is False