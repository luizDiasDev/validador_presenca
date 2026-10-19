from django.conf import settings

DEFAULT_SETTINGS = {
    
    "ALGORITHM": "insightface-buffalo_l",
    
    "EMBEDDING_SIZE": 512,
    
    "MIN_COSINE": 0.25,
    "MAX_COSINE": 0.65,
    
    "FACIAL_SAFEGUARD": 0.40,
    
    "LIVENESS_APPROVAL": 0.80,
}


def get_setting(setting_name: str):
    
    overrides = getattr(settings, "BIOMETRICS", {})
    return overrides.get(setting_name, DEFAULT_SETTINGS[setting_name])