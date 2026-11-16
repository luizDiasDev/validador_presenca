"""Fluxo completo com o executável: celular lê o QR, a câmera da sala manda o rosto, o motor decide."""
import json
from datetime import timedelta

import numpy as np
import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.biometrics.models import Biometria
from apps.biometrics.domain.services.biometric_service import BiometricService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import ChamadaSession
from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.institution.models import Machine
from apps.privacy.models import Termo
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

CAMPUS_CENTER = {"lat": "-23.5169621", "lon": "-46.1826845"}
EMBEDDING_SIZE = 512
LIVE = {"liveness_score": 0.97, "liveness_status": "ok", "challenge_passed": True}


def face(seed, base=None, noise=0.02):
    random_generator = np.random.default_rng(seed)
    vector = random_generator.normal(size=EMBEDDING_SIZE) if base is None else base + noise * random_generator.normal(size=EMBEDDING_SIZE)
    return vector / np.linalg.norm(vector)


STUDENT_FACE = face(1)
OTHER_FACE = face(2)


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()


@pytest.fixture
def room(cenario_professor):
    now = timezone.now()
    session = ChamadaSession.objects.create(
        sala=cenario_professor["sala"], professor=cenario_professor["professor"], aula=cenario_professor["aula"],
        sequencia=1, limite_por_maquina=5, abre_em=now - timedelta(minutes=5), fecha_em=now + timedelta(minutes=10),
    )
    machine = Machine.objects.create(sala=cenario_professor["sala"], apelido="PC-01", codigo_pareamento="4321")
    token = MachinePairingService().emitir_token(machine)
    computer = Client(HTTP_AUTHORIZATION=f"Bearer {token}")
    Termo.objects.create(
        instituicao=cenario_professor["sala"].campus.instituicao, tipo=Termo.TIPO_BIOMETRICO, versao="1.0",
        titulo="Termo biométrico", conteudo="Conteúdo", documento_hash="a" * 64, ativo=True,
    )
    return {"session": session, "machine": machine, "computer": computer, **cenario_professor}


def make_student(room, email="aluno.sala@alunos.umc.br", enrolled=False):
    user = Usuario.objects.create_user(email=email, password="senha-forte-123",
                                       instituicao=room["sala"].campus.instituicao)
    Aluno.objects.create(usuario=user, turma=room["turma"], matricula=email[:8])
    if enrolled:
        service = BiometricService()
        service.grant_consent(user)
        service.enroll(user, [face(seed, base=STUDENT_FACE).tolist() for seed in range(10, 15)], 0.97, "ok", True)
    phone = Client()
    phone.force_login(user)
    return user, phone


def read_room_qr(room, phone):
    """O celular lê o QR que o executável está exibindo."""
    link = room["computer"].get(reverse("class_client:qr")).json()["link"]
    token = link.split("?t=")[1]
    return phone.post(reverse("checkin:student_checkin"), {"token": token, **CAMPUS_CENTER}).content.decode()


def send_face(room, payload):
    pending = room["computer"].get(reverse("class_client:autorizacao")).json()
    response = room["computer"].post(
        reverse("class_client:rosto"),
        data=json.dumps({"presenca_id": pending["presenca_id"], "payload": payload}),
        content_type="application/json",
    )
    return pending, response


# ---------- pareamento e QR ----------

def test_pairing_returns_a_token_that_authenticates_the_machine(room):
    MachinePairingService().desparear(maquina_id=room["machine"].id, autor_id=0)
    response = Client().post(reverse("institution:parear_maquina_api"),
                             data=json.dumps({"codigo_pareamento": "4321"}), content_type="application/json")
    token = response.json()["token"]

    assert MachinePairingService().autenticar(token) == room["machine"]
    room["machine"].refresh_from_db()
    assert token not in (room["machine"].token_hash or "")


def test_api_refuses_a_machine_without_token(room):
    response = Client().get(reverse("class_client:qr"))

    assert response.status_code == 401


def test_machine_shows_the_qr_of_the_open_session(room):
    data = room["computer"].get(reverse("class_client:qr")).json()

    assert data["ativa"] is True
    assert "/checkin/?t=" in data["link"]
    assert data["disciplina"] == "IOT2"


def test_machine_without_open_session_has_no_qr(room):
    room["session"].delete()

    assert room["computer"].get(reverse("class_client:qr")).json()["ativa"] is False


# ---------- check-in com rosto ----------

def test_enrolled_student_with_the_same_face_is_approved(room):
    user, phone = make_student(room, enrolled=True)

    html = read_room_qr(room, phone)
    pending, response = send_face(room, {"embedding": face(20, base=STUDENT_FACE).tolist(), **LIVE})

    assert "Olhe para a câmera da sala" in html
    assert pending["modo"] == "checkin"
    assert response.json()["status"] == "APPROVED"
    record = PresencaRecord.objects.get(usuario=user)
    assert record.status == "APPROVED"
    assert record.origem == "qr+facial"


def test_someone_else_in_front_of_the_camera_is_rejected(room):
    user, phone = make_student(room, enrolled=True)

    read_room_qr(room, phone)
    _, response = send_face(room, {"embedding": OTHER_FACE.tolist(), **LIVE})

    assert response.json()["status"] == "REJECTED"
    assert PresencaRecord.objects.get(usuario=user).motivo == "Rosto não confere com o cadastro"


def test_phone_follows_the_result_through_the_status_endpoint(room):
    user, phone = make_student(room, enrolled=True)
    read_room_qr(room, phone)
    record = PresencaRecord.objects.get(usuario=user)
    status_url = reverse("checkin:status_presenca", args=[record.id])

    waiting = phone.get(status_url).json()
    send_face(room, {"embedding": face(21, base=STUDENT_FACE).tolist(), **LIVE})
    done = phone.get(status_url).json()

    assert waiting["aguardando_rosto"] is True
    assert done == {"status": "APPROVED", "motivo": "", "aguardando_rosto": False}


def test_face_cannot_be_sent_twice_for_the_same_checkin(room):
    _, phone = make_student(room, enrolled=True)
    read_room_qr(room, phone)
    pending, _ = send_face(room, {"embedding": face(22, base=STUDENT_FACE).tolist(), **LIVE})

    again = room["computer"].post(
        reverse("class_client:rosto"),
        data=json.dumps({"presenca_id": pending["presenca_id"], "payload": {"embedding": STUDENT_FACE.tolist(), **LIVE}}),
        content_type="application/json",
    )

    assert again.status_code == 409


def test_without_face_from_the_room_the_checkin_stays_pending(room):
    user, phone = make_student(room, enrolled=True)

    read_room_qr(room, phone)

    assert PresencaRecord.objects.get(usuario=user).status == "PENDING"


# ---------- primeiro check-in: cadastro do rosto (RF20) ----------

def test_first_checkin_asks_for_the_biometric_consent(room):
    _, phone = make_student(room)

    html = read_room_qr(room, phone)

    assert "Cadastro do rosto" in html
    assert room["computer"].get(reverse("class_client:autorizacao")).json()["pendente"] is False


def test_accepting_the_term_enrolls_the_face_and_leaves_the_day_for_review(room):
    user, phone = make_student(room)
    read_room_qr(room, phone)

    html = phone.post(reverse("checkin:consentimento"), {"resposta": "aceito"}).content.decode()
    pending, response = send_face(room, {"samples": [face(s, base=STUDENT_FACE).tolist() for s in range(30, 35)], **LIVE})

    assert "Olhe para a câmera da sala" in html
    assert pending["modo"] == "cadastro"
    assert Biometria.objects.filter(usuario=user).exists()
    record = PresencaRecord.objects.get(usuario=user)
    assert record.status == "PENDING"
    assert "Primeiro check-in após o cadastro facial" in record.motivo


def test_declining_the_term_keeps_the_checkin_for_the_teacher(room):
    user, phone = make_student(room)
    read_room_qr(room, phone)

    html = phone.post(reverse("checkin:consentimento"), {"resposta": "recusado"}).content.decode()

    assert "Sem o cadastro facial" in html
    assert not Biometria.objects.filter(usuario=user).exists()
    assert room["computer"].get(reverse("class_client:autorizacao")).json()["pendente"] is False


def test_enrollment_with_two_different_people_is_refused(room):
    user, phone = make_student(room)
    read_room_qr(room, phone)
    phone.post(reverse("checkin:consentimento"), {"resposta": "aceito"})

    _, response = send_face(room, {"samples": [STUDENT_FACE.tolist(), OTHER_FACE.tolist(), STUDENT_FACE.tolist()], **LIVE})

    assert response.status_code == 422
    assert not Biometria.objects.filter(usuario=user).exists()
    assert "Cadastro facial não concluído" in PresencaRecord.objects.get(usuario=user).motivo


# ---------- histórico do aluno (RF16) ----------

def test_student_history_shows_only_their_own_checkins(room):
    user, phone = make_student(room, enrolled=True)
    other, other_phone = make_student(room, email="outro@alunos.umc.br", enrolled=True)
    read_room_qr(room, phone)
    send_face(room, {"embedding": face(23, base=STUDENT_FACE).tolist(), **LIVE})
    read_room_qr(room, other_phone)

    html = phone.get(reverse("checkin:minhas_presencas")).content.decode()

    assert "IOT2" in html
    assert html.count("Confirmada") >= 1
    assert PresencaRecord.objects.filter(usuario=user).count() == 1


def test_student_cannot_read_the_status_of_someone_elses_checkin(room):
    _, phone = make_student(room, enrolled=True)
    other, other_phone = make_student(room, email="outro2@alunos.umc.br", enrolled=True)
    read_room_qr(room, other_phone)
    other_record = PresencaRecord.objects.get(usuario=other)

    response = phone.get(reverse("checkin:status_presenca", args=[other_record.id]))

    assert response.status_code == 404
