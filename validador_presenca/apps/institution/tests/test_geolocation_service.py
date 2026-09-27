import pytest
from apps.institution.models import Institution, Campus
from apps.institution.domain.services.geolocation_service import GeolocationService

@pytest.fixture
def campus_umc(db):
    instituicao = Institution.objects.create(
        nome="Universidade de Mogi das Cruzes",
        cnpj="54303514000185",
    )
    return Campus.objects.create(
        instituicao=instituicao,
        nome="Campus Sede",
        latitude="-23.5169621",
        longitude="-46.1826845",
        raio_metros=300,
    )

@pytest.fixture
def svc():
    return GeolocationService()

def test_validate_dentro_do_raio_retorna_valido(svc, campus_umc):
    resultado = svc.validate(lat=-23.5170, lon=-46.1826, campus_id=campus_umc.id)
    assert resultado.valida is True
    assert resultado.distancia_m < 20
    assert resultado.motivo == ""
    assert resultado.campus_id == campus_umc.id

def test_validate_fora_do_raio_retorna_invalido(svc, campus_umc):
    resultado = svc.validate(lat=-23.5505, lon=-46.6333, campus_id=campus_umc.id)
    assert resultado.valida is False
    assert resultado.distancia_m > 40_000
    assert "acima do raio" in resultado.motivo

def test_validate_campus_inexistente_lanca_excecao(svc, db):
    with pytest.raises(Campus.DoesNotExist):
        svc.validate(lat=-23.5, lon=-46.1, campus_id=99999)