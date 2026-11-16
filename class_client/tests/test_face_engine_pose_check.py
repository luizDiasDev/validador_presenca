import pickle
import sys
import types

import pytest

from biometrics.face_engine import FaceEngine


def fake_insightface(monkeypatch, tmp_path, with_file):
    pose_model = types.SimpleNamespace(require_pose=True, mean_lmk=None)

    class FakeAnalysis:
        def __init__(self, **options):
            self.models = {"landmark_3d_68": pose_model}

        def prepare(self, ctx_id, det_size):
            pass

    package_dir = tmp_path / "insightface"
    objects = package_dir / "data" / "objects"
    objects.mkdir(parents=True)
    if with_file:
        (objects / "meanshape_68.pkl").write_bytes(pickle.dumps([[1.0, 2.0, 3.0]]))

    app = types.ModuleType("insightface.app")
    app.FaceAnalysis = FakeAnalysis
    package = types.ModuleType("insightface")
    package.__file__ = str(package_dir / "__init__.py")
    package.app = app
    monkeypatch.setitem(sys.modules, "insightface", package)
    monkeypatch.setitem(sys.modules, "insightface.app", app)
    return pose_model


def test_engine_fills_in_the_pose_data_the_frozen_library_could_not_find(monkeypatch, tmp_path):
    pose_model = fake_insightface(monkeypatch, tmp_path, with_file=True)

    FaceEngine().load()

    assert pose_model.mean_lmk == [[1.0, 2.0, 3.0]]


def test_loading_fails_clearly_when_the_pose_file_is_nowhere(monkeypatch, tmp_path):
    fake_insightface(monkeypatch, tmp_path, with_file=False)

    with pytest.raises(RuntimeError, match="meanshape_68.pkl"):
        FaceEngine().load()
