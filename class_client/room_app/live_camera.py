import threading
import time

PREVIEW_INTERVAL_SECONDS = 1 / 15
NEW_FRAME_WAIT_SECONDS = 1.0


class LiveCamera:
    def __init__(self, camera, on_frame=lambda frame: None, clock=time.monotonic):
        self._camera = camera
        self._on_frame = on_frame
        self._clock = clock
        self._condition = threading.Condition()
        self._latest = None
        self._latest_number = 0
        self._consumed_number = 0
        self._running = True
        self._thread = threading.Thread(target=self._read_forever, daemon=True)
        self._thread.start()

    def next_frame(self):
        with self._condition:
            self._condition.wait_for(
                lambda: self._latest_number > self._consumed_number or not self._running,
                timeout=NEW_FRAME_WAIT_SECONDS,
            )
            if self._latest_number == self._consumed_number:
                return None
            self._consumed_number = self._latest_number
            return self._latest.copy()

    def stop(self):
        with self._condition:
            self._running = False
            self._condition.notify_all()
        self._thread.join(timeout=2)
        self._camera.release()

    def _read_forever(self):
        last_preview = 0.0
        while self._running:
            ok, frame = self._camera.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            with self._condition:
                self._latest = frame
                self._latest_number += 1
                self._condition.notify_all()
            now = self._clock()
            if now - last_preview >= PREVIEW_INTERVAL_SECONDS:
                last_preview = now
                self._on_frame(frame)
