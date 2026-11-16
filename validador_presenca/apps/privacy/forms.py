from django import forms

from apps.biometrics.models import Biometria
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD, Termo

STATUS_ABERTOS = (SolicitacaoLGPD.STATUS_PENDENTE, SolicitacaoLGPD.STATUS_EM_ANALISE)


def tem_biometria_ou_consentimento(usuario) -> bool:
    return (
        Biometria.objects.filter(usuario=usuario).exists()
        or AceiteTermo.objects.filter(
            usuario=usuario, termo__tipo=Termo.TIPO_BIOMETRICO, concedido=True, data_revogada__isnull=True,
        ).exists()
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

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario is not None and not tem_biometria_ou_consentimento(usuario):
            self.fields["tipo"].choices = [
                opcao for opcao in self.fields["tipo"].choices
                if opcao[0] != SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA
            ]

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if tipo and self.usuario is not None and SolicitacaoLGPD.objects.filter(
            usuario=self.usuario, tipo=tipo, status__in=STATUS_ABERTOS,
        ).exists():
            self.add_error("tipo", "Você já tem uma solicitação deste tipo em andamento.")
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