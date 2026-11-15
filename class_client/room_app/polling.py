import time

AUTHORIZATION_POLL_MS = 3000
QR_REFRESH_SECONDS = 10
IDLE_QR_SECONDS = 15


class PollingSchedule:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.call_is_open = False
        self._next_qr_at = 0.0

    def should_check_authorization(self) -> bool:
        return self.call_is_open

    def should_refresh_qr(self) -> bool:
        return self.clock() >= self._next_qr_at

    def qr_received(self, data: dict) -> None:
        self.call_is_open = bool(data.get("ativa"))
        wait = data.get("atualizar_em_s", QR_REFRESH_SECONDS) if self.call_is_open else IDLE_QR_SECONDS
        self._next_qr_at = self.clock() + wait

    def refresh_now(self) -> None:
        self._next_qr_at = 0.0
