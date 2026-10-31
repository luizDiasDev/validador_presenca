from datetime import datetime, timedelta
from django.utils import timezone

import pytest

from apps.accounts.models import Professor, Usuario
from apps.institution.models import Campus, Institution, Room


class RelogioFalso:
    def __init__(self, inicio: datetime):
        self.agora = inicio

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, **kwargs):
        self.agora += timedelta(**kwargs)


@pytest.fixture
def relogio():
    return RelogioFalso(timezone.make_aware(datetime(2026, 10, 12, 19, 0)))


@pytest.fixture
def sala(db):
    instituicao = Institution.objects.create(
        nome="Universidade de Mogi das Cruzes",
        cnpj="54303514000185",
    )
    campus = Campus.objects.create(
        instituicao=instituicao,
        nome="Campus Sede",
        latitude="-23.5169621",
        longitude="-46.1826845",
        raio_metros=300,
    )
    return Room.objects.create(campus=campus, codigo="B-207", nome="Laboratório 7")


@pytest.fixture
def professor(db):
    usuario = Usuario.objects.create_user(email="prof@umc.br", password="senha-forte-123")
    return Professor.objects.create(usuario=usuario, area_atuacao="Engenharia de Software")


@pytest.fixture
def outro_professor(db):
    usuario = Usuario.objects.create_user(email="outro@umc.br", password="senha-forte-123")
    return Professor.objects.create(usuario=usuario, area_atuacao="Banco de Dados")