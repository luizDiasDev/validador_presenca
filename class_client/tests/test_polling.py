from room_app.polling import IDLE_QR_SECONDS, PollingSchedule


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_without_an_open_call_the_machine_only_checks_the_qr_every_idle_interval():
    clock = FakeClock()
    schedule = PollingSchedule(clock=clock)

    schedule.qr_received({"ativa": False})

    assert schedule.should_check_authorization() is False
    clock.now += IDLE_QR_SECONDS - 1
    assert schedule.should_refresh_qr() is False
    clock.now += 1
    assert schedule.should_refresh_qr() is True


def test_with_an_open_call_the_machine_checks_authorizations_and_follows_the_server_refresh():
    clock = FakeClock()
    schedule = PollingSchedule(clock=clock)

    schedule.qr_received({"ativa": True, "atualizar_em_s": 10})

    assert schedule.should_check_authorization() is True
    clock.now += 9
    assert schedule.should_refresh_qr() is False
    clock.now += 1
    assert schedule.should_refresh_qr() is True


def test_refresh_now_brings_the_qr_back_right_after_a_capture():
    clock = FakeClock()
    schedule = PollingSchedule(clock=clock)
    schedule.qr_received({"ativa": True, "atualizar_em_s": 10})

    schedule.refresh_now()

    assert schedule.should_refresh_qr() is True


def test_a_new_machine_asks_for_the_qr_before_anything_else():
    schedule = PollingSchedule(clock=FakeClock())

    assert schedule.should_refresh_qr() is True
    assert schedule.should_check_authorization() is False
