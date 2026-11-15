from types import SimpleNamespace

from biometrics.face_engine import FaceEngine


def test_analyze_loads_the_engine_on_first_use(monkeypatch):
    engine = FaceEngine()

    def fake_load():
        engine._face_analysis = SimpleNamespace(get=lambda frame: [])
        return engine

    monkeypatch.setattr(engine, "load", fake_load)

    assert engine.analyze(object()) == []
    assert engine.is_loaded()
