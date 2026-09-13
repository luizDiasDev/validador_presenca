from django_redis import get_redis_connection
from django.core.cache import cache
from apps.checkin.domain.services.qr_service import QrTokenService

from .engine import Engine
from .validation_engines.qrcode_validator import QrCodeValidator
from .validation_engines.manual_token_validator import ManualTokenValidator
from .validation_engines.facial_validator import FacialValidator
from .validation_engines.liveness_validator import LivenessValidator

def buid_engine():
    qr_token_service = QrTokenService(cache=cache)

    return Engine(validators_list=[
        QrCodeValidator(cache_qrtokens=qr_token_service),
        ManualTokenValidator(),
        FacialValidator(),
        LivenessValidator(),
    ])