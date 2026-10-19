import numpy as np
import pytest

from apps.biometrics.domain import embedding as emb

DIM = 512


def test_validar_normaliza_o_vetor():
    vetor = np.full(DIM, 3.0)

    resultado = emb.validar(vetor, DIM)

    assert resultado.dtype == np.float32
    assert np.linalg.norm(resultado) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize("vetor", [
    np.ones(DIM - 1),          # tamanho errado
    np.ones((2, DIM)),         # dimensão errada
    np.zeros(DIM),             # vetor nulo
    np.full(DIM, np.nan),      # NaN
    np.full(DIM, np.inf),      # infinito
    ["a"] * DIM,               # não numérico
    None,                      # ausente
])
def test_validar_recusa_vetores_invalidos(vetor):
    with pytest.raises(emb.EmbeddingInvalido):
        emb.validar(vetor, DIM)


def test_media_normalizada_devolve_vetor_unitario_proximo_das_amostras():
    base = np.random.default_rng(1).normal(size=DIM)
    amostras = [base + 0.05 * np.random.default_rng(i).normal(size=DIM) for i in range(5)]

    media = emb.media_normalizada(amostras, DIM)

    assert np.linalg.norm(media) == pytest.approx(1.0, abs=1e-5)
    assert emb.similaridade_cosseno(media, emb.validar(base, DIM)) > 0.95


def test_media_normalizada_recusa_lista_vazia():
    with pytest.raises(emb.EmbeddingInvalido):
        emb.media_normalizada([], DIM)


def test_similaridade_cosseno_de_vetores_iguais_e_opostos():
    v = emb.validar(np.random.default_rng(2).normal(size=DIM), DIM)

    assert emb.similaridade_cosseno(v, v) == pytest.approx(1.0, abs=1e-5)
    assert emb.similaridade_cosseno(v, -v) == pytest.approx(-1.0, abs=1e-5)


def test_bytes_ida_e_volta_preserva_o_vetor():
    v = emb.validar(np.random.default_rng(3).normal(size=DIM), DIM)

    de_volta = emb.de_bytes(emb.para_bytes(v), DIM)

    assert np.allclose(v, de_volta)


def test_de_bytes_recusa_tamanho_inesperado():
    with pytest.raises(emb.EmbeddingInvalido):
        emb.de_bytes(b"\x00" * 16, DIM)
