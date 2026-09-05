from django.test import TestCase

# Create your tests here.

import fakeredis

from apps.validator.domain.validation_engines.qrcode_validator import QrCodeValidator


def test_valid_qrcode():
    fake_cache = fakeredis.FakeStrictRedis()
    fake_cache.set("token1234", "machine1")
    fake_cache.set("token4321", "machine2")

    validator = QrCodeValidator(cache_qrtokens=fake_cache)
    result = validator.validate("token4321")

    assert result.passed is True

def test_invalid_qrcode():
    fake_cache = fakeredis.FakeStrictRedis()

    validator = QrCodeValidator(cache_qrtokens=fake_cache)
    result = validator.validate("token4321")

    assert result.passed is False


