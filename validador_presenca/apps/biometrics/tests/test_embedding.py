import numpy as np
import pytest

from apps.biometrics.domain.embedding import (
    InvalidEmbeddingError,
    average_embedding,
    bytes_to_embedding,
    cosine_similarity,
    embedding_to_bytes,
    validate_and_normalize,
)

EMBEDDING_SIZE = 512


def random_vector(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(size=EMBEDDING_SIZE)


# ---------- validate_and_normalize ----------

def test_returns_vector_with_length_one_pointing_the_same_way():
    vector = np.full(EMBEDDING_SIZE, 3.0)

    normalized = validate_and_normalize(vector, EMBEDDING_SIZE)

    assert np.linalg.norm(normalized) == pytest.approx(1.0, abs=1e-6)
    
    assert np.allclose(normalized, normalized[0])


def test_accepts_plain_python_list_like_the_json_sends():
    normalized = validate_and_normalize([1.0] * EMBEDDING_SIZE, EMBEDDING_SIZE)

    assert normalized.dtype == np.float32
    assert normalized.shape == (EMBEDDING_SIZE,)


@pytest.mark.parametrize("invalid_vector", [
    np.ones(EMBEDDING_SIZE - 1),          # tamanho errado
    np.ones((2, EMBEDDING_SIZE)),         # lista de listas
    np.zeros(EMBEDDING_SIZE),             # vetor zerado (sem direção)
    np.full(EMBEDDING_SIZE, np.nan),      # NaN
    np.full(EMBEDDING_SIZE, np.inf),      # infinito
    ["a"] * EMBEDDING_SIZE,               # não numérico
    None,                                 # nada enviado
], ids=["wrong_size", "nested_list", "all_zeros", "nan", "infinite", "text", "none"])
def test_rejects_invalid_vectors(invalid_vector):
    with pytest.raises(InvalidEmbeddingError):
        validate_and_normalize(invalid_vector, EMBEDDING_SIZE)


# ---------- average_embedding ----------

def test_average_has_length_one_and_stays_close_to_the_samples():
    base_face = random_vector(1)
    
    samples = [base_face + 0.05 * random_vector(seed) for seed in range(10, 15)]

    template = average_embedding(samples, EMBEDDING_SIZE)

    assert np.linalg.norm(template) == pytest.approx(1.0, abs=1e-6)
    for sample in samples:
        assert cosine_similarity(template, validate_and_normalize(sample, EMBEDDING_SIZE)) > 0.99


def test_average_rejects_empty_list():
    with pytest.raises(InvalidEmbeddingError):
        average_embedding([], EMBEDDING_SIZE)


def test_average_rejects_when_any_sample_is_broken():
    samples = [random_vector(1), np.full(EMBEDDING_SIZE, np.nan)]

    with pytest.raises(InvalidEmbeddingError):
        average_embedding(samples, EMBEDDING_SIZE)


# ---------- cosine_similarity ----------

def test_cosine_is_one_for_same_vector_and_minus_one_for_opposite():
    vector = validate_and_normalize(random_vector(2), EMBEDDING_SIZE)

    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-6)
    assert cosine_similarity(vector, -vector) == pytest.approx(-1.0, abs=1e-6)


def test_cosine_is_close_to_zero_for_unrelated_vectors():
    first = validate_and_normalize(random_vector(3), EMBEDDING_SIZE)
    second = validate_and_normalize(random_vector(4), EMBEDDING_SIZE)

    assert abs(cosine_similarity(first, second)) < 0.2


# ---------- embedding_to_bytes / bytes_to_embedding ----------

def test_bytes_round_trip_keeps_the_vector():
    vector = validate_and_normalize(random_vector(5), EMBEDDING_SIZE)

    raw_bytes = embedding_to_bytes(vector)
    restored = bytes_to_embedding(raw_bytes, EMBEDDING_SIZE)

    assert len(raw_bytes) == EMBEDDING_SIZE * 4 
    assert np.array_equal(restored, vector)


def test_restored_vector_can_be_modified():
    restored = bytes_to_embedding(embedding_to_bytes(np.ones(EMBEDDING_SIZE)), EMBEDDING_SIZE)

    restored[0] = 2.0 

    assert restored[0] == 2.0


def test_bytes_with_unexpected_size_are_rejected():
    with pytest.raises(InvalidEmbeddingError):
        bytes_to_embedding(b"\x00" * 100, EMBEDDING_SIZE)