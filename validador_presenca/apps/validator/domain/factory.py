from django_redis import get_redis_connection

from .engine import Engine
from .validation_engines.qrcode_validator import QrCodeValidator
from .validation_engines.manual_token_validator import ManualTokenValidator
from .validation_engines.facial_validator import FacialValidator
from .validation_engines.liveness_validator import LivenessValidator

def buid_engine():
    redis_connection = get_redis_connection("default")

    return Engine(validators_list=[
        QrCodeValidator(cache_qrtokens=redis_connection),
        ManualTokenValidator(),
        FacialValidator(),
        LivenessValidator(),
    ])