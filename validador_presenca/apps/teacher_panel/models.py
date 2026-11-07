from django.conf import settings
from django.db import models

# Create your models here.


class Turma(models.Model):
    sala = models.ForeignKey(
        "institution.Room",
        on_delete=models.PROTECT,
        db_column="sala_id",
        related_name="turmas",
    )
    codigo = models.CharField(max_length=10)
    nome = models.CharField(max_length=100)
    curso = models.CharField(max_length=100)
    semestre_inicio = models.DateField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "turma"
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self):
        return f"{self.codigo} - {self.nome} ({self.curso})"


class Aluno(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="aluno",
    )
    turma = models.ForeignKey(
        Turma,
        on_delete=models.PROTECT,
        db_column="turma_id",
        related_name="alunos",
    )
    matricula = models.CharField(max_length=30, unique=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aluno"
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.email} ({self.matricula})"


class Disciplina(models.Model):
    professor = models.ForeignKey(
        "accounts.Professor",
        on_delete=models.PROTECT,
        db_column="professor_id",
        related_name="disciplinas",
    )
    turma = models.ForeignKey(
        Turma,
        on_delete=models.PROTECT,
        db_column="turma_id",
        related_name="disciplinas",
    )
    nome = models.CharField(max_length=200)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "disciplina"
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"

    def __str__(self):
        return f"{self.nome} - {self.turma.codigo}"


class Aula(models.Model):
    DIAS_SEMANA = [
        (0, "Segunda-feira"),
        (1, "Terça-feira"),
        (2, "Quarta-feira"),
        (3, "Quinta-feira"),
        (4, "Sexta-feira"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.PROTECT,
        db_column="disciplina_id",
        related_name="aulas",
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aula"
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"
        ordering = ["dia_semana", "hora_inicio"]

    def __str__(self):
        dia_nome = dict(self.DIAS_SEMANA).get(self.dia_semana, "")
        return f"{self.disciplina.nome} ({dia_nome} {self.hora_inicio:%H:%M}-{self.hora_fim:%H:%M})"