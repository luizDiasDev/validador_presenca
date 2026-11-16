from django.test import override_settings
from django.urls import reverse

from apps.checkin.tests.test_phone_checkin import (  # noqa: F401
    CAMPUS_CENTER,
    cenario_professor,
    open_session,
    room_token,
    student_phone,
)
from apps.institution.domain.services.geocoding_service import GeocodingService


def fake_address(monkeypatch, calls):
    def translate(self, lat, lon):
        calls.append((lat, lon))
        return "Av. Dr. Cândido Xavier de Almeida e Souza, Mogi das Cruzes"

    monkeypatch.setattr(GeocodingService, "translate_location", translate)


@override_settings(GEOCODING_ENABLED=True)
def test_student_sees_the_address_when_geocoding_is_enabled(student_phone, open_session, monkeypatch):
    calls = []
    fake_address(monkeypatch, calls)

    html = student_phone.post(reverse("checkin:student_checkin"), {"token": room_token(open_session), **CAMPUS_CENTER}).content.decode()

    assert calls == [(CAMPUS_CENTER["lat"], CAMPUS_CENTER["lon"])]
    assert "Mogi das Cruzes" in html


@override_settings(GEOCODING_ENABLED=False)
def test_geocoding_can_be_switched_off_for_load_tests(student_phone, open_session, monkeypatch):
    calls = []
    fake_address(monkeypatch, calls)

    student_phone.post(reverse("checkin:student_checkin"), {"token": room_token(open_session), **CAMPUS_CENTER})

    assert calls == []
