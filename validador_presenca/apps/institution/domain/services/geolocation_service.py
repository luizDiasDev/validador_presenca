from geopy.distance import geodesic
from apps.institution.models import Campus
from apps.institution.domain.values.geo_validation_result import GeoValidationResult


class GeolocationService:

    def validate(self, lat: float, lon: float, campus_id: int) -> GeoValidationResult:
        campus = Campus.objects.get(pk=campus_id) # busca campus

        distancia = geodesic(
            (lat, lon),
            (float(campus.latitude), float(campus.longitude))
        ).meters # Calcula a distancia entre aluno e campus

        valida = distancia <= campus.raio_metros # Valida se está dentro do Raio (true) ou não

        motivo = "" if valida else (
            f"Coordenada a {distancia:.1f}m do campus, acima do raio de {campus.raio_metros}m permitido"
        ) # Retorno do motivo

        return GeoValidationResult(
            valida=valida,
            distancia_m=distancia,
            campus_id=campus.id,
            motivo=motivo,
        )