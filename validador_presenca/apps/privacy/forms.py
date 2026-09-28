from django import forms
from django.contrib.auth.forms import AuthenticationForm
from apps.privacy.models import SolicitacaoLGPD

class LoginComAceiteForm(AuthenticationForm):
    aceite_termos = forms.BooleanField(
        required=True,
        error_messages={
            "required": "Você precisa aceitar a Política de Privacidade e os Termos de Uso para continuar."
        },
        label="",
    )

class SolicitacaoLGPDForm(forms.ModelForm):
    confirmo_impacto = forms.BooleanField(
        required=True,
        label="Li e compreendi os impactos desta solicitação.",
        error_messages={
            "required": "Você precisa confirmar que leu os impactos antes de enviar.",
        },
    )

    class Meta:
        model = SolicitacaoLGPD
        fields = ["tipo", "justificativa"]
        widgets = {
            "justificativa": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Descreva sua solicitação",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        justificativa = cleaned.get("justificativa", "").strip()

        obrigatorios = [
            SolicitacaoLGPD.TIPO_EXCLUIR_CONTA,
            SolicitacaoLGPD.TIPO_CORRIGIR_DADOS,
        ]

        if tipo in obrigatorios and not justificativa:
            self.add_error(
                "justificativa",
                "Justificativa é obrigatória para este tipo de solicitação.",
            )

        return cleaned