from django.test import TestCase

# Create your tests here.

from apps.validator.domain.validation_engines.qrcode_validator import QrCodeValidator


def test_valid_qrcode():
    validator = QrCodeValidator()
    result = validator.validate({"qr_code": True})

    assert result.passed is True

def test_invalid_qrcode():
    validator = QrCodeValidator()
    result = validator.validate({"qr_code": False})

    assert result.passed is False


