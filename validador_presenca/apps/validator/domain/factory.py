from .engine import Engine
from .validation_engines.qrcode_validator import QrCodeValidator
from .validation_engines.facial_validator import FacialValidator
from .validation_engines.liveness_validator import LivenessValidator
from .validation_engines.geo_validator import GeoValidator

def buid_engine():

    return Engine(validators_list=[
        QrCodeValidator(),
        FacialValidator(),
        LivenessValidator(),
        GeoValidator(),
    ])