from .capture import CaptureResult


def build_checkin_payload(capture_result: CaptureResult, challenge_passed: bool | None) -> dict:
    
    _ensure_capture_is_usable(capture_result)
    return {
        "embedding": _to_plain_list(capture_result.mean_embedding),
        **_liveness_fields(capture_result, challenge_passed),
    }


def build_enrollment_payload(capture_result: CaptureResult, challenge_passed: bool | None) -> dict:
    
    _ensure_capture_is_usable(capture_result)
    return {
        "samples": [_to_plain_list(embedding) for embedding in capture_result.sample_embeddings],
        **_liveness_fields(capture_result, challenge_passed),
    }


def _ensure_capture_is_usable(capture_result: CaptureResult) -> None:
    if not capture_result.success or capture_result.mean_embedding is None:
        raise ValueError("A captura não deu certo; não há rosto para enviar.")


def _liveness_fields(capture_result: CaptureResult, challenge_passed: bool | None) -> dict:
    
    live_score = capture_result.live_score
    return {
        "liveness_score": None if live_score is None else float(live_score),
        "liveness_status": capture_result.live_status,
        "challenge_passed": challenge_passed,
    }


def _to_plain_list(embedding) -> list[float]:
    
    return [float(value) for value in embedding]