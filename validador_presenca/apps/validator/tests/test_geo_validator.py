from apps.validator.domain.validation_engines.geo_validator import GeoValidator

def test_geo_valida_true_produz_factor_result_passed():
    validator = GeoValidator()
    result = validator.validate({"geo_valida": True, "geo_motivo": ""})
    assert result.passed is True
    assert result.score == 1.0
    assert result.block is True
    assert result.name == "geo"
    assert result.reason == ""

def test_geo_valida_false_produz_factor_result_bloqueado():
    validator = GeoValidator()
    result = validator.validate({
        "geo_valida": False,
        "geo_motivo": "Coordenada a 50m",
    })
    assert result.passed is False
    assert result.score == 0.0
    assert result.block is True
    assert "500m" in result.reason

def test_geo_valida_ausente_falha_por_default():
    validator = GeoValidator()
    result = validator.validate({})
    assert result.passed is False
    assert result.score == 0.0
    assert "Localização" in result.reason