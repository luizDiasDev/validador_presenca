import pytest
from django.urls import reverse
from apps.checkin.domain.services.chamada_service import ChamadaService
from .fixtures import professor, sala


@pytest.mark.django_db
def test_status_sala_sem_chamada_retorna_ativa_false(client, sala):
    url = reverse("checkin:status_sessao_sala", kwargs={"sala_id": sala.id})
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["ativa"] is False
    assert "Nenhuma chamada" in data["mensagem"]


@pytest.mark.django_db
def test_status_sala_com_chamada_aberta_retorna_dados(client, sala, professor):
    svc = ChamadaService()
    sessao = svc.abrir(sala_id=sala.id, professor=professor, duracao_min=5)

    url = reverse("checkin:status_sessao_sala", kwargs={"sala_id": sala.id})
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["ativa"] is True
    assert data["sessao_id"] == sessao.id
    assert data["sequencia"] == 1