import argparse
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from biometrics.camera import CAMERA_BACKENDS, CameraUnavailableError, open_camera, open_video
from biometrics.face_engine import FaceEngine 

GREEN, YELLOW, BLACK = (0, 200, 0), (0, 220, 220), (0, 0, 0)


class BackgroundAnalyzer:

    def __init__(self, engine: FaceEngine):
        self._engine = engine
        
        self._lock = threading.Lock()
        self._pending_frame = None
        self._latest_readings = []
        self._last_analysis_ms = 0.0
        self._running = True
        
        self._thread = threading.Thread(target=self._analyze_forever, daemon=True)
        self._thread.start()

    def submit(self, frame):
        
        with self._lock:
            self._pending_frame = frame

    def latest(self):
        
        with self._lock:
            return self._latest_readings, self._last_analysis_ms

    def stop(self):
        self._running = False
        self._thread.join(timeout=2)

    def _analyze_forever(self):
        while self._running:
            with self._lock:
                frame, self._pending_frame = self._pending_frame, None
            if frame is None:
                time.sleep(0.005)
                continue

            started_at = time.perf_counter()
            readings = self._engine.analyze(frame)
            elapsed_ms = (time.perf_counter() - started_at) * 1000

            with self._lock:
                self._latest_readings, self._last_analysis_ms = readings, elapsed_ms


def describe_reading(reading, reference_embedding, analysis_ms) -> list[str]:
    
    live = "-" if reading.live_score is None else f"{reading.live_score:.2f}"
    yaw = "-" if reading.yaw is None else f"{reading.yaw:+.0f}"
    pitch = "-" if reading.pitch is None else f"{reading.pitch:+.0f}"
    lines = [
        f"deteccao={reading.detection_score:.2f}  largura={reading.face_width():.0f}px",
        f"yaw={yaw}  pitch={pitch}  live={live} ({reading.live_status})",
    ]
    if reference_embedding is None:
        lines.append("ESPACO = guardar este rosto como referencia")
    else:
        
        cosine = float(np.dot(reference_embedding, reading.embedding))
        lines.append(f"cosseno com a referencia = {cosine:.3f}")
    lines.append(f"analise = {analysis_ms:.0f} ms")
    return lines


def draw_text(frame, lines, color):
    for line_number, text in enumerate(lines):
        position = (10, 30 + 28 * line_number)
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.65, BLACK, 4)
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index", type=int, default=0, help="número da câmera")
    parser.add_argument("--backend", choices=list(CAMERA_BACKENDS), default="auto")
    parser.add_argument("--video", help="arquivo de vídeo no lugar da câmera")
    parser.add_argument("--detection-size", type=int, default=640,
                        help="tamanho do detector (640 padrão; 320 é mais rápido)")
    args = parser.parse_args()

    print("Carregando modelos do InsightFace (na primeira vez baixa ~280 MB)...")
    detection_size = (args.detection_size, args.detection_size)
    engine = FaceEngine(detection_size=detection_size).load()

    try:
        capture = open_video(args.video) if args.video else open_camera(args.index, args.backend)
    except CameraUnavailableError as error:
        sys.exit(str(error))

    analyzer = BackgroundAnalyzer(engine)
    reference_embedding = None
    print("Clique na janela da câmera. ESPAÇO = referência, Q = sair.")

    while True:
        frame_read, frame = capture.read()
        if not frame_read:
            if args.video:
                break
            continue

        analyzer.submit(frame.copy())
        readings, analysis_ms = analyzer.latest()

        for reading in readings:
            x1, y1, x2, y2 = (int(value) for value in reading.bounding_box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), GREEN, 2)

        if len(readings) == 1:
            draw_text(frame, describe_reading(readings[0], reference_embedding, analysis_ms), GREEN)
        else:
            draw_text(frame, [f"{len(readings)} rostos (preciso de exatamente 1)"], YELLOW)

        cv2.imshow("FaceEngine", frame)
        pressed_key = cv2.waitKey(1) & 0xFF
        if pressed_key in (ord("q"), ord("Q")):
            break
        if pressed_key == 32 and len(readings) == 1:   # 32 = ESPAÇO
            reference_embedding = readings[0].embedding
            print("Referência guardada.")

    analyzer.stop()
    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()