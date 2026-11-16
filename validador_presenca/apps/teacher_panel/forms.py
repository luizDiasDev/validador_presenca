from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Professor, Usuario
from apps.checkin.models import AgendamentoChamada
from apps.institution.models import Institution
from apps.teacher_panel.models import Turma, Disciplina, Aula, Aluno

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
    limite_por_maquina = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        label="Alunos por computador",
    )

    def __init__(self, *args, professor=None, agora=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.agora = agora or timezone.localtime()
        self.duracao_ajustada = False
        if professor is not None:
            self.fields["aula"].queryset = (
                Aula.objects.filter(disciplina__professor=professor)
                .select_related("disciplina__turma__sala")
                .order_by("dia_semana", "hora_inicio")
            )

    def clean(self):
        cleaned = super().clean()
        aula = cleaned.get("aula")
        tempos = cleaned.get("tempos_cobertos")
        duracao = cleaned.get("duracao_min")

        if aula is not None and tempos is not None:
            if tempos < 1 or tempos > aula.tempos_aula:
                self.add_error(
                    "tempos_cobertos",
                    f"Esta aula permite cobrir entre 1 e {aula.tempos_aula} tempo(s) configurado(s) na grade.",
                )

        if aula is None:
            return cleaned

        horario_aula = f"{aula.get_dia_semana_display()}, das {aula.hora_inicio:%H:%M} às {aula.hora_fim:%H:%M}"
        if aula.dia_semana != self.agora.weekday():
            raise forms.ValidationError(
                f"Esta aula não é hoje ({horario_aula}). Use Agendar para deixar a chamada programada."
            )
        agora_min = _minutos(self.agora)
        if not _minutos(aula.hora_inicio) <= agora_min < _minutos(aula.hora_fim):
            raise forms.ValidationError(
                f"A chamada só pode ser aberta durante a aula ({horario_aula}). Use Agendar para programar o horário."
            )

        restante = _minutos(aula.hora_fim) - agora_min
        if duracao and duracao > restante:
            cleaned["duracao_min"] = restante
            self.duracao_ajustada = True

        return cleaned


class AgendamentoChamadaForm(forms.ModelForm):
    class Meta:
        model = AgendamentoChamada
        fields = ["aula", "horario", "duracao_min", "tempos_cobertos", "limite_por_maquina"]

    def __init__(self, *args, professor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aula"].queryset = (
            Aula.objects.filter(disciplina__professor=professor)
            .select_related("disciplina__turma")
            .order_by("dia_semana", "hora_inicio")
        )
        self.fields["duracao_min"].validators.append(MinValueValidator(1))
        self.fields["duracao_min"].validators.append(MaxValueValidator(180))
        self.fields["tempos_cobertos"].validators.append(MinValueValidator(1))
        self.fields["limite_por_maquina"].validators.append(MinValueValidator(1))
        self.fields["limite_por_maquina"].validators.append(MaxValueValidator(10))
        self.fields["horario"].required = True
        self.fields["horario"].error_messages["required"] = "Preencha o campo Abre às para agendar a chamada."

    def clean(self):
        cleaned = super().clean()
        aula = cleaned.get("aula")
        horario = cleaned.get("horario")
        duracao = cleaned.get("duracao_min")
        tempos = cleaned.get("tempos_cobertos")
        if not (aula and horario and duracao):
            return cleaned

        inicio = _minutos(horario)
        fim = inicio + duracao
        if inicio < _minutos(aula.hora_inicio) or fim > _minutos(aula.hora_fim):
            ultimo_inicio = _minutos(aula.hora_fim) - duracao
            if ultimo_inicio < _minutos(aula.hora_inicio):
                raise forms.ValidationError(
                    f"A janela de {duracao} min é maior que a aula ({aula.hora_inicio:%H:%M} às {aula.hora_fim:%H:%M})."
                )
            raise forms.ValidationError(
                f"Abrindo às {horario:%H:%M} com janela de {duracao} min, a chamada fecharia fora da aula "
                f"({aula.hora_inicio:%H:%M} às {aula.hora_fim:%H:%M}). Escolha um horário entre "
                f"{aula.hora_inicio:%H:%M} e {ultimo_inicio // 60:02d}:{ultimo_inicio % 60:02d}."
            )
        if tempos and tempos > aula.tempos_aula:
            raise forms.ValidationError(f"Esta aula tem {aula.tempos_aula} tempo(s).")
        for outro in AgendamentoChamada.objects.filter(aula=aula).exclude(pk=self.instance.pk):
            outro_inicio = _minutos(outro.horario)
            if inicio < outro_inicio + outro.duracao_min and outro_inicio < fim:
                raise forms.ValidationError(
                    f"Já existe uma chamada agendada às {outro.horario:%H:%M} nesse intervalo."
                )
        return cleaned


def _minutos(horario) -> int:
    return horario.hour * 60 + horario.minute


class RevisaoPresencaForm(forms.Form):
    DECISAO_CHOICES = [
        ("APPROVED", "Aprovar presença"),
        ("REJECTED", "Recusar presença"),
    ]

    status = forms.ChoiceField(choices=DECISAO_CHOICES, label="Decisão")
    motivo = forms.CharField(
        max_length=500,
        required=True,
        label="Justificativa da revisão",
    )

    def clean_motivo(self):
        motivo = self.cleaned_data.get("motivo", "").strip()
        if len(motivo) < 5:
            raise forms.ValidationError(
                "Informe uma justificativa com pelo menos 5 caracteres."
            )
        return motivo


def _validate_new_password(senha: str, usuario=None) -> str:
    if senha:
        try:
            validate_password(senha, user=usuario)
        except ValidationError as erro:
            raise forms.ValidationError(list(erro.messages)) from erro
    return senha


class AlunoCadastroForm(forms.Form):
    turma = forms.ModelChoiceField(queryset=Turma.objects.all(), label="Turma")
    matricula = forms.CharField(max_length=30, label="Matrícula")
    nome = forms.CharField(max_length=150, label="Nome Completo")
    email = forms.EmailField(label="E-mail Institucional")
    senha = forms.CharField(
        max_length=128,
        required=False,
        label="Senha",
    )

    def __init__(self, *args, aluno_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno_instance = aluno_instance
        if not aluno_instance:
            self.fields["senha"].required = True

    def clean_matricula(self):
        matricula = self.cleaned_data["matricula"].strip()
        qs = Aluno.objects.filter(matricula=matricula)
        if self.aluno_instance:
            qs = qs.exclude(pk=self.aluno_instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Já existe um aluno cadastrado com esta matrícula."
            )
        return matricula

    def clean_senha(self):
        usuario = self.aluno_instance.usuario if self.aluno_instance else None
        return _validate_new_password(self.cleaned_data.get("senha", ""), usuario)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = Usuario.objects.filter(email=email)
        if self.aluno_instance:
            qs = qs.exclude(pk=self.aluno_instance.usuario_id)
        if qs.exists():
            raise forms.ValidationError(
                "Já existe um usuário cadastrado com este e-mail."
            )
        return email

    @transaction.atomic
    def save(self, instituicao=None) -> Aluno:
        nome_completo = self.cleaned_data["nome"].strip()
        partes_nome = nome_completo.split(" ", 1)
        first_name = partes_nome[0]
        last_name = partes_nome[1] if len(partes_nome) > 1 else ""
        email = self.cleaned_data["email"]
        senha = self.cleaned_data.get("senha")
        turma = self.cleaned_data["turma"]
        matricula = self.cleaned_data["matricula"]
        instituicao_final = instituicao or Institution.objects.first()

        if self.aluno_instance:
            usuario = self.aluno_instance.usuario
            usuario.email = email
            usuario.username = email
            usuario.first_name = first_name
            usuario.last_name = last_name
            if senha:
                usuario.set_password(senha)
            usuario.save()

            self.aluno_instance.turma = turma
            self.aluno_instance.matricula = matricula
            self.aluno_instance.save()
            return self.aluno_instance

        usuario = Usuario.objects.create_user(
            email=email,
            password=senha,
            first_name=first_name,
            last_name=last_name,
            instituicao=instituicao_final,
        )
        return Aluno.objects.create(
            usuario=usuario,
            turma=turma,
            matricula=matricula,
        )

class ProfessorCadastroForm(forms.Form):
    nome = forms.CharField(max_length=150, label="Nome Completo")
    email = forms.EmailField(label="E-mail Institucional")
    area_atuacao = forms.CharField(max_length=100, label="Área de Atuação")
    senha = forms.CharField(max_length=128, required=False, label="Senha")

    def __init__(self, *args, professor_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.professor_instance = professor_instance
        
        if not professor_instance:
            self.fields["senha"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        usuarios_com_email = Usuario.objects.filter(email=email)
        if self.professor_instance:
            usuarios_com_email = usuarios_com_email.exclude(pk=self.professor_instance.usuario_id)
        if usuarios_com_email.exists():
            raise forms.ValidationError("Já existe um usuário cadastrado com este e-mail.")
        return email

    def clean_senha(self):
        usuario = self.professor_instance.usuario if self.professor_instance else None
        return _validate_new_password(self.cleaned_data.get("senha", ""), usuario)

    def clean_area_atuacao(self):
        area_atuacao = self.cleaned_data["area_atuacao"].strip()
        if not area_atuacao:
            raise forms.ValidationError("Informe a área de atuação do professor.")
        return area_atuacao

    @transaction.atomic
    def save(self, instituicao=None) -> Professor:
        nome_completo = self.cleaned_data["nome"].strip()
        partes_nome = nome_completo.split(" ", 1)
        first_name = partes_nome[0]
        last_name = partes_nome[1] if len(partes_nome) > 1 else ""
        email = self.cleaned_data["email"]
        senha = self.cleaned_data.get("senha")
        area_atuacao = self.cleaned_data["area_atuacao"]

        if self.professor_instance:
            usuario = self.professor_instance.usuario
            usuario.email = email
            usuario.username = email
            usuario.first_name = first_name
            usuario.last_name = last_name
            if senha:
                usuario.set_password(senha)
            usuario.save()

            self.professor_instance.area_atuacao = area_atuacao
            self.professor_instance.save()
            return self.professor_instance

        usuario = Usuario.objects.create_user(
            email=email,
            password=senha,
            first_name=first_name,
            last_name=last_name,
            instituicao=instituicao or Institution.objects.first(),
        )
        return Professor.objects.create(usuario=usuario, area_atuacao=area_atuacao)
