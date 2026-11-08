from django import forms
from django.utils import timezone
from apps.teacher_panel.models import Turma, Disciplina, Aula


class TurmaForm(forms.ModelForm):
    class Meta:
        model = Turma
        fields = ["sala", "codigo", "nome", "curso", "semestre_inicio"]
        widgets = {
            "semestre_inicio": forms.DateInput(attrs={"type": "date"}),
        }


class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ["turma", "nome"]


class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        fields = ["disciplina", "dia_semana", "hora_inicio", "hora_fim", "tempos_aula"]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, professor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if professor is not None:
            self.fields["disciplina"].queryset = Disciplina.objects.filter(
                professor=professor
            ).select_related("turma")

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("hora_inicio")
        fim = cleaned.get("hora_fim")
        tempos = cleaned.get("tempos_aula")

        if inicio and fim and fim <= inicio:
            self.add_error(
                "hora_fim",
                "O horario de termino deve ser posterior ao horario de inicio.",
            )

        if tempos is not None and (tempos < 1 or tempos > 8):
            self.add_error(
                "tempos_aula",
                "A quantidade de tempos de aula deve ficar entre 1 e 8.",
            )

        return cleaned


class AbrirChamadaForm(forms.Form):
    aula = forms.ModelChoiceField(
        queryset=Aula.objects.none(),
        label="Aula",
    )
    duracao_min = forms.IntegerField(
        min_value=1,
        max_value=180,
        initial=10,
        label="Janela da chamada (minutos)",
    )
    tempos_cobertos = forms.IntegerField(
        min_value=1,
        max_value=8,
        initial=4,
        label="Tempos de aula cobertos",
    )

    def __init__(self, *args, professor=None, dia_semana=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dia_semana is None:
            dia_semana = timezone.localdate().weekday()
        if professor is not None:
            self.fields["aula"].queryset = (
                Aula.objects.filter(
                    disciplina__professor=professor,
                    dia_semana=dia_semana,
                )
                .select_related("disciplina__turma__sala")
                .order_by("hora_inicio")
            )

    def clean(self):
        cleaned = super().clean()
        aula = cleaned.get("aula")
        tempos = cleaned.get("tempos_cobertos")

        if aula is not None and tempos is not None:
            if tempos < 1 or tempos > aula.tempos_aula:
                self.add_error(
                    "tempos_cobertos",
                    f"Esta aula permite cobrir entre 1 e {aula.tempos_aula} tempo(s) configurado(s) na grade.",
                )

        return cleaned


class RevisaoPresencaForm(forms.Form):
    DECISAO_CHOICES = [
        ("APPROVED", "Aprovar presenca"),
        ("REJECTED", "Rejeitar (manter falta)"),
    ]

    status = forms.ChoiceField(choices=DECISAO_CHOICES, label="Decisao")
    motivo = forms.CharField(
        max_length=500,
        required=True,
        label="Justificativa da revisao",
    )

    def clean_motivo(self):
        motivo = self.cleaned_data.get("motivo", "").strip()
        if len(motivo) < 5:
            raise forms.ValidationError(
                "Informe uma justificativa com pelo menos 5 caracteres."
            )
        return motivo
