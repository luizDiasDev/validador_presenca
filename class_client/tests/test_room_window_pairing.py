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
