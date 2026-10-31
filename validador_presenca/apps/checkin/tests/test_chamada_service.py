from datetime import timedelta

import pytest

from apps.audit.models import AuditLog
from apps.checkin.domain.services.chamada_service import (
    ChamadaJaAbertaError,
    ChamadaJaEncerradaError,
    ChamadaSemPermissaoError,
    ChamadaService,
)
from apps.checkin.models import ChamadaSession
from apps.institution.models import Room
from .fixtures import outro_professor, professor, relogio, sala


@pytest.fixture
def svc(relogio):
    return ChamadaService(clock=relogio)


def test_abrir_cria_sessao_aberta_com_duracao(svc, sala, professor, relogio):
    sessao = svc.abrir(sala_id=sala.id, professor=professor, duracao_min=50)

    assert sessao.sala_id == sala.id
    assert sessao.professor_id == professor.id
    assert sessao.abre_em == relogio.agora
    assert sessao.fecha_em == relogio.agora + timedelta(minutes=50)
    assert svc.esta_aberta(sessao) is True


def test_abrir_com_chamada_ja_aberta_na_sala_lanca_erro(svc, sala, professor):
    svc.abrir(sala_id=sala.id, professor=professor)

    with pytest.raises(ChamadaJaAbertaError):
        svc.abrir(sala_id=sala.id, professor=professor)

    assert ChamadaSession.objects.count() == 1


def test_abrir_depois_da_anterior_expirar_incrementa_sequencia(svc, sala, professor, relogio):
    primeira = svc.abrir(sala_id=sala.id, professor=professor, duracao_min=50)
    relogio.avancar(minutes=51)

    segunda = svc.abrir(sala_id=sala.id, professor=professor)

    assert primeira.sequencia == 1
    assert segunda.sequencia == 2


def test_abrir_com_duracao_invalida_lanca_erro(svc, sala, professor):
    with pytest.raises(ValueError):
        svc.abrir(sala_id=sala.id, professor=professor, duracao_min=0)


def test_abrir_sala_inexistente_lanca_excecao(svc, professor):
    with pytest.raises(Room.DoesNotExist):
        svc.abrir(sala_id=99999, professor=professor)


def test_encerrar_grava_fecha_em_e_sessao_deixa_de_estar_aberta(svc, sala, professor, relogio):
    sessao = svc.abrir(sala_id=sala.id, professor=professor, duracao_min=50)
    relogio.avancar(minutes=10)

    encerrada = svc.encerrar(sessao_id=sessao.id, professor=professor)

    assert encerrada.fecha_em == relogio.agora
    assert svc.esta_aberta(encerrada) is False


def test_encerrar_sessao_ja_encerrada_lanca_erro(svc, sala, professor):
    sessao = svc.abrir(sala_id=sala.id, professor=professor)
    svc.encerrar(sessao_id=sessao.id, professor=professor)

    with pytest.raises(ChamadaJaEncerradaError):
        svc.encerrar(sessao_id=sessao.id, professor=professor)


def test_encerrar_por_outro_professor_lanca_erro(svc, sala, professor, outro_professor):
    sessao = svc.abrir(sala_id=sala.id, professor=professor)

    with pytest.raises(ChamadaSemPermissaoError):
        svc.encerrar(sessao_id=sessao.id, professor=outro_professor)

    sessao.refresh_from_db()
    assert svc.esta_aberta(sessao) is True


def test_esta_aberta_no_instante_do_fechamento_retorna_false(svc, sala, professor, relogio):
    sessao = svc.abrir(sala_id=sala.id, professor=professor, duracao_min=50)
    relogio.avancar(minutes=50)

    assert svc.esta_aberta(sessao) is False


def test_abrir_e_encerrar_geram_log_de_auditoria(svc, sala, professor):
    sessao = svc.abrir(sala_id=sala.id, professor=professor)
    svc.encerrar(sessao_id=sessao.id, professor=professor)

    logs = AuditLog.objects.filter(tabela="sessao_chamada", linha_tabela_id=sessao.id).order_by("id")

    assert [log.acao for log in logs] == ["SESSAO_ABERTA", "SESSAO_ENCERRADA"]
    assert all(log.autor_id == professor.usuario_id for log in logs)
    assert logs[0].payload["sala_id"] == sala.id