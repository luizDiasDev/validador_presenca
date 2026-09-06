import pytest
from apps.validator.models import PresencaRecord

@pytest.mark.django_db
def test_create_data():
    PresencaRecord.objects.create(
        score_facial = 1.0,
        score_vida = 1.0,
        geo_valida = True,
        score_final =  1.0,
        aprovado =  True,
        status = "APPROVED",
        origem = "Maquina X",
        revisado_por = 37,
        motivo = "Motivo X",
    )

    result = PresencaRecord.objects.filter(revisado_por=37)

    assert result.count() == 1
    assert result.first().origem == "Maquina X"