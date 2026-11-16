import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from room_app.api import MachineNotPairedError  # noqa: E402
from room_app.config import RoomConfig  # noqa: E402
from room_app.main import RoomWindow  # noqa: E402


class DisconnectedApi:
    def current_qr(self):
        raise MachineNotPairedError("Máquina não pareada. Faça o pareamento de novo.")

    def pending_authorization(self):
        raise MachineNotPairedError("Máquina não pareada. Faça o pareamento de novo.")


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_a_disconnected_machine_asks_for_pairing_again_and_uses_the_new_token(qt_app):
    old_config = RoomConfig(server_url="https://adsum.test", machine_token="revogado", machine_name="PC-01", room_code="B-207")
    seen = {}

    def pair_again(config, parent):
        seen["token_when_asked"] = config.machine_token
        return RoomConfig(server_url=config.server_url, machine_token="novo", machine_name="PC-02", room_code="B-208")

    window = RoomWindow(DisconnectedApi(), old_config, engine_factory=lambda: object(), pair_function=pair_again)
    window.loader.wait()
    window._tick()

    assert seen["token_when_asked"] == ""
    assert window.api.machine_token == "novo"
    assert window.config.machine_name == "PC-02"
    assert "PC-02" in window.footer.text()
    window.timer.stop()


class FullMachineApi:
    def current_qr(self):
        return {"ativa": True, "lotada": True, "mensagem": "Este computador já recebeu 1 aluno(s) nesta chamada.",
                "disciplina": "IOT2", "fecha_em": "19:25", "atualizar_em_s": 10}

    def pending_authorization(self):
        return {"pendente": False}


def test_a_full_machine_hides_the_qr_but_keeps_waiting_for_the_face_step(qt_app):
    window = RoomWindow(FullMachineApi(), RoomConfig(machine_token="ok"), engine_factory=lambda: object())
    window.loader.wait()

    window._tick()

    assert window.picture.pixmap().isNull()
    assert "já recebeu 1 aluno" in window.message.text()
    assert window.schedule.should_check_authorization() is True
    window.timer.stop()


class NoCallApi:
    def current_qr(self):
        return {"ativa": False, "mensagem": "Nenhuma chamada aberta nesta sala."}

    def pending_authorization(self):
        return {"pendente": False}


class OpenCallApi:
    def current_qr(self):
        return {"ativa": True, "link": "https://adsum.test/checkin/qr/?t=abc", "disciplina": "IOT2",
                "fecha_em": "19:25", "atualizar_em_s": 10}

    def pending_authorization(self):
        return {"pendente": False}


def test_without_a_call_the_window_stays_hidden_in_the_background(qt_app):
    window = RoomWindow(NoCallApi(), RoomConfig(machine_token="ok"), engine_factory=lambda: object())
    window.loader.wait()

    window._tick()

    assert window.isVisible() is False
    assert "Nenhuma chamada" in window.tray.toolTip()
    window.timer.stop()


def test_an_open_call_shows_a_small_window_in_the_bottom_right_corner(qt_app):
    window = RoomWindow(OpenCallApi(), RoomConfig(machine_token="ok"), engine_factory=lambda: object())
    window.loader.wait()

    window._tick()

    screen = qt_app.primaryScreen().availableGeometry()
    assert window.isVisible() is True
    assert window.picture.pixmap().isNull() is False
    assert window.width() <= 320
    assert window.height() < screen.height()
    assert window.geometry().right() <= screen.right()
    assert window.geometry().bottom() <= screen.bottom()
    assert window.x() > screen.center().x()
    assert window.y() > screen.center().y() - window.height()
    window.timer.stop()
    window.hide()


def test_the_window_goes_back_to_the_background_when_the_call_closes(qt_app):
    window = RoomWindow(OpenCallApi(), RoomConfig(machine_token="ok"), engine_factory=lambda: object())
    window.loader.wait()
    window._tick()

    window.api = NoCallApi()
    window.schedule.refresh_now()
    window._tick()

    assert window.isVisible() is False
    window.timer.stop()


def test_closing_the_window_only_hides_it(qt_app):
    window = RoomWindow(OpenCallApi(), RoomConfig(machine_token="ok"), engine_factory=lambda: object())
    window.loader.wait()
    window._tick()

    window.close()

    assert window.isVisible() is False
    assert window.tray is not None
    window.timer.stop()
