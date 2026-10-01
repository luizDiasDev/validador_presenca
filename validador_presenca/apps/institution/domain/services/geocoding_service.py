import requests

class GeocodingService:
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

    def translate_location(self, lat: float, lon: float) -> str:
        try:
            response = requests.get(
                self.NOMINATIM_URL,
                params = {
                    "format": "json",
                    "lat": lat,
                    "lon": lon
                },
                headers = {
                    "User-Agent": "adsum-pfc-umc/1.0"
                },
                timeout = 3,
            )
            
            response.raise_for_status()
            
            return response.json().get("display_name", "Não localizado")
        
        except (requests.RequestException, ValueError):
            
            return "Não Localizado"