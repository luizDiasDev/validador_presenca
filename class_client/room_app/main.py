import io
import sys

import cv2
import qrcode
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QLayout, QMenu, QMessageBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from biometrics.camera import open_camera
from biometrics.face_engine import FaceEngine

from .api import ApiError, MachineNotPairedError, RoomApi
from .capture_flow import capture_and_send
from .capture_session import MODE_ENROLLMENT
from .config import RoomConfig, load_config, save_config
from .logs import configure_logging
from .polling import AUTHORIZATION_POLL_MS, PollingSchedule

RESULT_SCREEN_MS = 4000
CORNER_WIDTH = 300
CORNER_MARGIN = 16
QR_SIZE = 240
PREVIEW_SIZE = (272, 204)
RESULT_TEXT = {
    "APPROVED": "Presença confirmada",
    "PENDING": "Presença registrada: o professor vai confirmar",
    "REJECTED": "Check-in não aceito",
}


class EngineLoader(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, engine_factory):
        super().__init__()
        self.engine_factory = engine_factory

    def run(self):
        try:
            self.loaded.emit(self.engine_factory().load())
        except Exception as error:  # noqa: BLE001 - qualquer falha vira mensagem na tela
            self.failed.emit(str(error))


class CaptureWorker(QThread):
    frame_ready = Signal(object)
    instruction = Signal(str)
    finished_with = Signal(str, str)

    def __init__(self, api: RoomApi, engine, config: RoomConfig, authorization: dict, camera_factory=open_camera):
        super().__init__()
        self.api = api
        self.engine = engine
        self.config = config
        self.authorization = authorization
        self.camera_factory = camera_factory

    def run(self):
        status, message = capture_and_send(
            self.api, self.engine, self.config, self.authorization, self.camera_factory,
            on_frame=self.frame_ready.emit, on_instruction=self.instruction.emit,
        )
        self.finished_with.emit(status, message)


class RoomWindow(QWidget):
    def __init__(self, api: RoomApi, config: RoomConfig, engine_factory=FaceEngine, camera_factory=open_camera,
                 pair_function=None):
        super().__init__()
        self.api = api
        self.config = config
        self.pair_function = pair_function or pair_if_needed
        self.engine = None
        self.camera_factory = camera_factory
        self.capture_worker = None
        self.schedule = PollingSchedule()

        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("background:#0F1B2E; color:#F7F3EA;")
        self.title = self._label(13, bold=True)
        self.picture = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.message = self._label(10)
        self.footer = self._label(8)
        for label in (self.title, self.message, self.footer):
            label.setFixedWidth(CORNER_WIDTH - 24)
        self.picture.setFixedSize(PREVIEW_SIZE[0], QR_SIZE)
        self.picture.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        for widget in (self.title, self.picture, self.message, self.footer):
            layout.addWidget(widget)

        self.tray = QSystemTrayIcon(_tray_icon(), self)
        self.tray_menu = QMenu()
        toggle_action = QAction("Mostrar ou esconder a janela", self.tray_menu)
        toggle_action.triggered.connect(self._toggle_window)
        self.tray_menu.addAction(toggle_action)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_clicked)
        self.tray.show()
        self._show_machine_name()

        self.title.setText("ADSUM")
        self._set_status("Carregando o reconhecimento facial...")
        self.loader = EngineLoader(engine_factory)
        self.loader.loaded.connect(self._engine_ready)
        self.loader.failed.connect(self._engine_failed)
        self.loader.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def _label(self, size, bold=False):
        label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(size)
        font.setBold(bold)
        label.setFont(font)
        label.setWordWrap(True)
        return label

    def _set_status(self, text: str):
        self.message.setText(text)
        self.tray.setToolTip(f"ADSUM · {text}"[:120])
        if self.isVisible():
            QTimer.singleShot(0, self._anchor_to_corner)

    def _set_picture(self, pixmap: QPixmap | None):
        if pixmap is None:
            self.picture.clear()
            self.picture.hide()
        else:
            self.picture.setPixmap(pixmap)
            self.picture.show()
        if self.isVisible():
            QTimer.singleShot(0, self._anchor_to_corner)

    def _anchor_to_corner(self):
        self.adjustSize()
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        self.move(
            screen.right() - self.width() - CORNER_MARGIN,
            screen.bottom() - self.height() - CORNER_MARGIN,
        )

    def _show_in_corner(self):
        self._anchor_to_corner()
        self.show()
        self.raise_()

    def _toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self._show_in_corner()

    def _tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()

    def _go_to_background(self, status: str):
        self.title.setText("ADSUM")
        self._set_picture(None)
        self._set_status(status)
        self.hide()

    def _engine_failed(self, error: str):
        self._set_picture(None)
        self._set_status(f"Falha ao carregar o reconhecimento facial: {error}")
        self._show_in_corner()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def _engine_ready(self, engine):
        self.engine = engine
        self.timer.start(AUTHORIZATION_POLL_MS)
        self._tick()

    def _tick(self):
        if self.capture_worker is not None:
            return
        try:
            if self.schedule.should_check_authorization():
                authorization = self.api.pending_authorization()
                if authorization.get("pendente"):
                    self._start_capture(authorization)
                    return
            if self.schedule.should_refresh_qr():
                self._show_qr(self.api.current_qr())
        except MachineNotPairedError:
            self._pair_again()
        except ApiError as error:
            self.title.setText("ADSUM")
            self._set_picture(None)
            self._set_status(str(error))
            if self.schedule.call_is_open:
                self._show_in_corner()

    def _pair_again(self):
        self.timer.stop()
        self.title.setText("ADSUM")
        self._set_picture(None)
        self._set_status("Este computador foi desconectado pelo administrador. Faça o pareamento de novo.")
        self.config.machine_token = ""
        self.config = self.pair_function(self.config, self)
        self.api = RoomApi(self.config.server_url, self.config.machine_token)
        self._show_machine_name()
        self.schedule = PollingSchedule()
        self.timer.start(AUTHORIZATION_POLL_MS)

    def _show_machine_name(self):
        self.setWindowTitle(f"ADSUM | {self.config.machine_name or 'Sala'}")
        self.footer.setText(f"{self.config.machine_name} · Sala {self.config.room_code}")
        self.tray.setToolTip(f"ADSUM · {self.config.machine_name or 'Sala'}")

    def _show_qr(self, data: dict):
        self.schedule.qr_received(data)
        if not data.get("ativa"):
            self._go_to_background(data.get("mensagem", "Nenhuma chamada aberta nesta sala."))
            return
        self.title.setText(data["disciplina"])
        if data.get("lotada") or "link" not in data:
            self._set_picture(None)
            self._set_status(data.get("mensagem", "Este computador não recebe mais check-ins nesta chamada."))
            self._show_in_corner()
            return
        self._set_picture(_qr_pixmap(data["link"], size=QR_SIZE))
        self._set_status(f"Leia o QR Code com o celular · até {data['fecha_em']}")
        self._show_in_corner()

    def _start_capture(self, authorization: dict):
        if authorization["modo"] == MODE_ENROLLMENT:
            self.title.setText("Primeiro acesso: cadastro do rosto")
            self._set_status("Vamos registrar o seu rosto. Olhe para a câmera e siga as instruções.")
        else:
            self.title.setText("Verificação facial")
            self._set_status("Olhe para a câmera.")
        self._show_in_corner()
        self.capture_worker = CaptureWorker(self.api, self.engine, self.config, authorization, self.camera_factory)
        self.capture_worker.frame_ready.connect(self._show_frame)
        self.capture_worker.instruction.connect(self._set_status)
        self.capture_worker.finished_with.connect(self._show_result)
        self.capture_worker.start()

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        if self.picture.isHidden():
            self.picture.show()
        self.picture.setPixmap(QPixmap.fromImage(image).scaled(
            *PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _show_result(self, status: str, detail: str):
        self.title.setText(RESULT_TEXT.get(status, "Check-in registrado"))
        self._set_picture(None)
        self._set_status(detail)
        self._show_in_corner()
        QTimer.singleShot(RESULT_SCREEN_MS, self._back_to_qr)

    def _back_to_qr(self):
        self.capture_worker = None
        self.schedule.refresh_now()
        self._tick()


def _tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#C9962C"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QColor("#0F1B2E"))
    font = QFont()
    font.setPointSize(30)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()
    return QIcon(pixmap)


def _qr_pixmap(link: str, size: int) -> QPixmap:
    buffer = io.BytesIO()
    qrcode.make(link, border=2).save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue())
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio)


def pair_if_needed(config: RoomConfig, parent=None) -> RoomConfig:
    if config.is_paired:
        return config
    server, ok = QInputDialog.getText(parent, "ADSUM", "Endereço do servidor:", text=config.server_url)
    if not ok:
        sys.exit(0)
    code, ok = QInputDialog.getText(parent, "ADSUM", "Código de pareamento (4 dígitos):")
    if not ok:
        sys.exit(0)
    api = RoomApi(server)
    try:
        data = api.pair(code.strip())
    except ApiError as error:
        QMessageBox.critical(parent, "ADSUM", str(error))
        sys.exit(1)
    config.server_url = server
    config.machine_token = data["token"]
    config.machine_name = data.get("apelido", "")
    config.room_code = data.get("sala_codigo", "")
    save_config(config)
    return config


def main():
    configure_logging()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    config = pair_if_needed(load_config())
    window = RoomWindow(RoomApi(config.server_url, config.machine_token), config)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
