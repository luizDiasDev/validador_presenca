import time
from dataclasses import dataclass, field

import numpy as np

from .models import LIVENESS_STATUS_OK, LIVENESS_STATUS_REJECTED, LIVENESS_STATUS_UNAVAILABLE
from .quality import QualityConfig, check_quality


@dataclass(frozen=True)
class CaptureConfig:
    # quantas leituras boas juntar antes de encerrar
    samples_needed: int = 5
    # tempo máximo tentando
    timeout_seconds: float = 20.0
    # menor cosseno aceito entre as leituras
    min_pairwise_cosine: float = 0.50
    # limites de qualidade de cada leitura
    quality: QualityConfig = field(default_factory=QualityConfig)


@dataclass(frozen=True)
class CaptureResult:
    success: bool
    reason: str = ""                          # mensagem para o aluno quando não deu certo
    sample_embeddings: tuple = ()             # o embedding de cada leitura aceita
    mean_embedding: np.ndarray | None = None  # a média delas, com comprimento 1
    live_score: float | None = None           # mediana das notas de vida das leituras
    live_status: str = LIVENESS_STATUS_UNAVAILABLE
    frames_read: int = 0                      # quantos frames foram lidos até terminar


def collect_samples(
    read_frame,
    analyze_frame,
    config: CaptureConfig = CaptureConfig(),
    require_liveness: bool = True,
    clock=time.monotonic,
    on_progress=None,
) -> CaptureResult:
    
    started_at = clock()
    good_readings = []
    frames_read = 0
    hint = ""

    while len(good_readings) < config.samples_needed:
        if clock() - started_at > config.timeout_seconds:
            return CaptureResult(
                success=False,
                reason=hint or "Tempo esgotado sem capturar o rosto.",
                frames_read=frames_read,
            )

        frame = read_frame()
        if frame is None:
            continue
        frames_read += 1

        faces = analyze_frame(frame)
        if len(faces) == 0:
            hint = "Nenhum rosto detectado."
        elif len(faces) > 1:
            hint = "Apenas uma pessoa deve aparecer na câmera."
        else:
            problem = check_quality(faces[0], config.quality, require_liveness=require_liveness)
            if problem:
                hint = problem
            else:
                good_readings.append(faces[0])
                hint = ""

        if on_progress:
            on_progress(len(good_readings), config.samples_needed, hint)

    return _combine_readings(good_readings, config, frames_read)


def _combine_readings(good_readings, config: CaptureConfig, frames_read: int) -> CaptureResult:
    
    embeddings_matrix = np.stack([reading.embedding for reading in good_readings])

    pairwise_cosines = embeddings_matrix @ embeddings_matrix.T
    
    if float(pairwise_cosines.min()) < config.min_pairwise_cosine:
        return CaptureResult(
            success=False,
            reason="As leituras não parecem ser da mesma pessoa. Tente de novo.",
            frames_read=frames_read,
        )

    mean_embedding = embeddings_matrix.mean(axis=0)
    mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

    live_scores = [
        reading.live_score for reading in good_readings
        if reading.live_status == LIVENESS_STATUS_OK and reading.live_score is not None
    ]
    if live_scores:
        
        live_score, live_status = float(np.median(live_scores)), LIVENESS_STATUS_OK
    elif any(reading.live_status == LIVENESS_STATUS_REJECTED for reading in good_readings):
        live_score, live_status = None, LIVENESS_STATUS_REJECTED
    else:
        live_score, live_status = None, LIVENESS_STATUS_UNAVAILABLE

    return CaptureResult(
        success=True,
        sample_embeddings=tuple(reading.embedding for reading in good_readings),
        mean_embedding=mean_embedding.astype(np.float32),
        live_score=live_score,
        live_status=live_status,
        frames_read=frames_read,
    )