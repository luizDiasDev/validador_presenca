import time
import fakeredis
import pytest
from apps.checkin.domain.services.qr_service import QrTokenService

@pytest.fixture
def svc():
    fake_cache = fakeredis.FakeStrictRedis(decode_responses=True)
    return QrTokenService(cache=fake_cache)

def test_gerar_retorna_qr_token_valido(svc):
    qr = svc.gerar(sessao_id=1, maquina_id=4)

    assert qr.sessao_id == 1
    assert qr.maquina_id == 4
    assert qr.ttl_s == 5

def test_consumir_token_valido_retorna_dados(svc):
    qr = svc.gerar(sessao_id=1, maquina_id=4)

    resultado = svc.consumir(qr.token)

    assert resultado is not None
    assert resultado.sessao_id == 1
    assert resultado.maquina_id == 4

def test_consumir_uso_unico(svc):
    qr = svc.gerar(sessao_id=1, maquina_id=4)
    svc.consumir(qr.token)

    assert svc.consumir(qr.token) is None

def test_consumir_token_ficticio_retorna_none(svc):
    assert svc.consumir("token-ficticio") is None

def test_consumir_token_expirado_retorna_none(svc):
    qr = svc.gerar(sessao_id=1, maquina_id=4, ttl_s=2)
    time.sleep(3)

    assert svc.consumir(qr.token) is None