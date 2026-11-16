import sys
import types

import pytest

from biometrics.face_engine import FaceEngine


def fake_insightface(monkeypatch, mean_lmk):
    class FakeAnalysis:
        def __init__(self, **options):
            self.models = {"landmark_3d_68": types.SimpleNamespace(require_pose=True, mean_lmk=mean_lmk)}

        def prepare(self, ctx_id, det_size):
            pass

    app = types.ModuleType("insightface.app")
    app.FaceAnalysis = FakeAnalysis
    package = types.ModuleType("insightface")
    package.app = app
    monkeypatch.setitem(sys.modules, "insightface", package)
    monkeypatch.setitem(sys.modules, "insightface.app", app)


def test_loading_fails_clearly_when_the_pose_file_is_missing(monkeypatch):
    fake_insightface(monkeypatch, mean_lmk=None)

    with pytest.raises(RuntimeError, match="meanshape_68.pkl"):
        FaceEngine().load()


def test_loading_works_when_the_pose_file_is_present(monkeypatch):
    fake_insightface(monkeypatch, mean_lmk=[[0.0, 0.0, 0.0]])

    assert FaceEngine().load().is_loaded()
