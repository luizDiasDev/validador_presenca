from unittest.mock import MagicMock

import pytest

from apps.validator.domain.engine import Engine
from apps.validator.domain.values.factor_result import FactorResult
from apps.validator.domain.values.verdict import Verdict


def validador_mock(nome, score=1.0, weight=1.0):
    validador = MagicMock()
    validador.validate.return_value = FactorResult(
        name=nome, passed=True, block=True, score=score, weight=weight, reason="",
    )
    return validador


def test_deve_aprovar_quando_todos_os_fatores_passam():
    # Arrange
    qr = validador_mock("qr_code", weight=0.3)
    facial = validador_mock("facial", weight=0.3)
    pacote = {"qr_code": True, "geo_valida": True}

    # Act
    veredito, _, score_final, motivo = Engine(validators_list=[qr, facial]).calculate(pacote)

    # Assert
    assert veredito == Verdict.APPROVED
    assert score_final == pytest.approx(1.0)
    assert motivo == ""
    qr.validate.assert_called_once_with(pacote)
    facial.validate.assert_called_once_with(pacote)


def test_deve_propagar_erro_de_um_validador_e_nao_chamar_os_seguintes():
    # Arrange
    facial = MagicMock()
    facial.validate.side_effect = RuntimeError("Falha ao carregar o modelo facial")
    geo = validador_mock("geo")

    # Act / Assert
    with pytest.raises(RuntimeError, match="Falha ao carregar o modelo facial"):
        Engine(validators_list=[facial, geo]).calculate({})

    geo.validate.assert_not_called()


@pytest.mark.parametrize(
    "score, veredito_esperado",
    [
        (0.75, Verdict.APPROVED),
        (0.7499, Verdict.PENDING),
        (0.55, Verdict.PENDING),
        (0.5499, Verdict.REJECTED),
    ],
)
def test_deve_classificar_o_veredito_na_fronteira_dos_limites(score, veredito_esperado):
    # Arrange: com um único fator de peso 1, o score final é o score do fator
    engine = Engine(validators_list=[validador_mock("facial", score=score)])

    # Act
    veredito, _, _, _ = engine.calculate({})

    # Assert
    assert veredito == veredito_esperado
