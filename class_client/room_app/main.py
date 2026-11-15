import io
import sys

import cv2
import qrcode
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QInputDialog, QLabel, QMessageBox, QVBoxLayout, QWidget

from biometrics.camera import CameraUnavailableError, open_camera
from biometrics.face_engine import FaceEngine

from .api import ApiError, MachineNotPairedError, RoomApi
from .capture_session import MODE_ENROLLMENT, run_face_capture
from .config import RoomConfig, load_config, save_config
from .polling import AUTHORIZATION_POLL_MS, PollingSchedule

RESULT_SCREEN_MS = 4000
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
    finished_with = Signal(str, str)   # status, mensagem

    def __init__(self, api: RoomApi, engine, config: RoomConfig, authorization: dict, camera_factory=open_camera):
        super().__init__()
        self.api = api
        self.engine = engine
        self.config = config
        self.authorization = authorization
        self.camera_factory = camera_factory

    def run(self):
        try:
            camera = self.camera_factory(self.config.camera_index, self.config.camera_backend)
        except CameraUnavailableError as error:
            # sem câmera o check-in não é perdido: fica pendente para o professor
            self.finished_with.emit("PENDING", f"Câmera indisponível: {error}")
            return

        def read_frame():
            ok, frame = camera.read()
            if not ok:
                return None
            self.frame_ready.emit(frame)
            return frame

        try:
            outcome = run_face_capture(
                read_frame, self.engine.analyze, self.authorization["modo"], on_instruction=self.instruction.emit
            )
        finally:
            camera.release()

        if not outcome.success:
            self.finished_with.emit("PENDING", outcome.capture.reason)
            return
        try:
            answer = self.api.send_face(self.authorization["presenca_id"], outcome.payload)
        except ApiError as error:
            self.finished_with.emit("PENDING", str(error))
            return
        self.finished_with.emit(answer.get("status", "PENDING"), answer.get("mensagem", ""))


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

        self.setStyleSheet("background:#0F1B2E; color:#F7F3EA;")
        self.title = self._label(28, bold=True)
        self.picture = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.picture.setMinimumSize(480, 480)
        self.message = self._label(20)
        self.footer = self._label(12)
        self._show_machine_name()

        layout = QVBoxLayout(self)
        for widget in (self.title, self.picture, self.message, self.footer):
            layout.addWidget(widget)

        self.title.setText("ADSUM")
        self.message.setText("Carregando o reconhecimento facial...")
        self.loader = EngineLoader(engine_factory)
        self.loader.loaded.connect(self._engine_ready)
        self.loader.failed.connect(lambda error: self.message.setText(f"Falha ao carregar o reconhecimento facial: {error}"))
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
            self.picture.clear()
            self.message.setText(str(error))

    def _pair_again(self):
        self.timer.stop()
        self.title.setText("ADSUM")
        self.picture.clear()
        self.message.setText("Este computador foi desconectado pelo administrador. Faça o pareamento de novo.")
        self.config.machine_token = ""
        self.config = self.pair_function(self.config, self)
        self.api = RoomApi(self.config.server_url, self.config.machine_token)
        self._show_machine_name()
        self.schedule = PollingSchedule()
        self.timer.start(AUTHORIZATION_POLL_MS)

    def _show_machine_name(self):
        self.setWindowTitle(f"ADSUM | {self.config.machine_name or 'Sala'}")
        self.footer.setText(f"{self.config.machine_name} · Sala {self.config.room_code}")

    def _show_qr(self, data: dict):
        self.schedule.qr_received(data)
        if not data.get("ativa"):
            self.title.setText("ADSUM")
            self.picture.clear()
            self.message.setText(data.get("mensagem", "Nenhuma chamada aberta nesta sala."))
            return
        self.title.setText(data["disciplina"])
        self.picture.setPixmap(_qr_pixmap(data["link"], size=460))
        self.message.setText(f"Aponte a câmera do celular para o QR Code · chamada até {data['fecha_em']}")

    def _start_capture(self, authorization: dict):
        self.title.setText("Cadastro do rosto" if authorization["modo"] == MODE_ENROLLMENT else "Verificação facial")
        self.message.setText("Olhe para a câmera.")
        self.capture_worker = CaptureWorker(self.api, self.engine, self.config, authorization, self.camera_factory)
        self.capture_worker.frame_ready.connect(self._show_frame)
        self.capture_worker.instruction.connect(self.message.setText)
        self.capture_worker.finished_with.connect(self._show_result)
        self.capture_worker.start()

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        self.picture.setPixmap(QPixmap.fromImage(image).scaled(
            640, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _show_result(self, status: str, detail: str):
        self.title.setText(RESULT_TEXT.get(status, "Check-in registrado"))
        self.picture.clear()
        self.message.setText(detail)
        QTimer.singleShot(RESULT_SCREEN_MS, self._back_to_qr)

    def _back_to_qr(self):
        self.capture_worker = None
        self.schedule.refresh_now()
        self._tick()


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
    app = QApplication(sys.argv)
    config = pair_if_needed(load_config())
    window = RoomWindow(RoomApi(config.server_url, config.machine_token), config)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
