from django import forms
from apps.institution.models import Campus, Room, Machine


class CampusForm(forms.ModelForm):
    class Meta:
        model = Campus
        fields = ["nome", "latitude", "longitude", "raio_metros"]

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get("latitude")
        lon = cleaned.get("longitude")
        raio = cleaned.get("raio_metros")

        # Valida faixa geografica da latitude (-90 a 90 graus)
        if lat is not None and (lat < -90 or lat > 90):
            self.add_error("latitude", "A latitude deve estar entre -90 e 90 graus.")

        # Valida faixa geografica da longitude (-180 a 180 graus)
        if lon is not None and (lon < -180 or lon > 180):
            self.add_error(
                "longitude", "A longitude deve estar entre -180 e 180 graus."
            )

        # Raio de validacao em metros deve ser sempre positivo
        if raio is not None and raio <= 0:
            self.add_error("raio_metros", "O raio em metros deve ser maior que zero.")

        return cleaned


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["campus", "codigo", "nome"]


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        # O codigo_pareamento de 4 digitos e gerado automaticamente no service
        fields = ["sala", "apelido"]
