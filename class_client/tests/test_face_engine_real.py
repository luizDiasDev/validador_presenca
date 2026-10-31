import os

import numpy as np
import pytest

pytestmark = [
    pytest.mark.real_models,
    pytest.mark.skipif(os.environ.get("ADSUM_REAL_MODELS") != "1",
                       reason="defina ADSUM_REAL_MODELS=1 para usar os modelos reais"),
]


@pytest.fixture(scope="module")
def engine():
    from biometrics.face_engine import FaceEngine
    return FaceEngine().load()


@pytest.fixture(scope="module")
def image_with_face():
    sample_images = pytest.importorskip("skimage.data")
    return np.ascontiguousarray(sample_images.astronaut()[:, :, ::-1])   # RGB -> BGR (padrão do OpenCV)


def test_reads_one_face_with_every_field(engine, image_with_face):
    readings = engine.analyze(image_with_face)

    assert len(readings) == 1
    reading = readings[0]
    assert reading.embedding.shape == (512,)
    assert np.linalg.norm(reading.embedding) == pytest.approx(1.0, abs=1e-4)
    assert reading.detection_score > 0.6
    assert reading.live_status == "ok"
    assert 0.0 <= reading.live_score <= 1.0
    assert reading.yaw is not None
    print(f"\nyaw={reading.yaw:.1f} pitch={reading.pitch:.1f} live={reading.live_score:.2f} "
          f"largura={reading.face_width():.0f}px")


def test_same_image_twice_gives_cosine_close_to_one(engine, image_with_face):
    first = engine.analyze(image_with_face)[0].embedding
    second = engine.analyze(image_with_face)[0].embedding

    assert float(np.dot(first, second)) > 0.999


def test_image_without_face_gives_empty_list(engine):
    assert engine.analyze(np.zeros((480, 640, 3), dtype=np.uint8)) == []
