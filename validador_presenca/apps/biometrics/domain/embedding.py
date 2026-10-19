import numpy as np


class InvalidEmbeddingError(ValueError):
    pass

def validate_and_normalize(raw_embedding, expected_size: int) -> np.ndarray:

    try:
        
        embedding_array = np.asarray(raw_embedding, dtype=np.float32)
    except (TypeError, ValueError) as conversion_error:
        raise InvalidEmbeddingError("Embedding não numérico") from conversion_error

    
    is_flat_list = embedding_array.ndim == 1
    if not is_flat_list or embedding_array.shape[0] != expected_size:
        raise InvalidEmbeddingError(
            f"Embedding deve ter {expected_size} valores (recebido: {embedding_array.shape})"
        )

    
    if not np.all(np.isfinite(embedding_array)):
        raise InvalidEmbeddingError("Embedding contém valores inválidos (NaN ou infinito)")

    vector_length = float(np.linalg.norm(embedding_array))
    
    if vector_length < 1e-6:
        raise InvalidEmbeddingError("Embedding nulo")

    return embedding_array / vector_length


def average_embedding(samples, expected_size: int) -> np.ndarray:
    
    if not samples:
        raise InvalidEmbeddingError("Nenhuma amostra fornecida")

    normalized_samples = [validate_and_normalize(sample, expected_size) for sample in samples]

    mean_embedding = np.mean(normalized_samples, axis=0)

    return validate_and_normalize(mean_embedding, expected_size)


def cosine_similarity(first_embedding: np.ndarray, second_embedding: np.ndarray) -> float:
    
    return float(np.dot(first_embedding, second_embedding))


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    
    return np.asarray(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(raw_bytes: bytes, expected_size: int) -> np.ndarray:

    embedding_array = np.frombuffer(raw_bytes, dtype=np.float32)
    if embedding_array.shape[0] != expected_size:
        raise InvalidEmbeddingError("Template armazenado com tamanho inesperado")

    return embedding_array.copy()