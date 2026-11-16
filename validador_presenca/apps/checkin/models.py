from django.db import models

# Create your models here.

class AgendamentoChamada(models.Model):
    aula = models.ForeignKey(
        "teacher_panel.Aula",
        on_delete=models.CASCADE,
        related_name="agendamentos",
    )
    horario = models.TimeField()
    duracao_min = models.PositiveSmallIntegerField(default=10)
    tempos_cobertos = models.PositiveSmallIntegerField(default=2)
    limite_por_maquina = models.PositiveSmallIntegerField(default=1)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agendamento_chamada"
        verbose_name = "Agendamento de Chamada"
        verbose_name_plural = "Agendamentos de Chamada"
        ordering = ["aula__dia_semana", "horario"]

    def __str__(self):
        return f"{self.aula} às {self.horario:%H:%M}"


class ChamadaSession(models.Model):
    # Definindo FK
    aula = models.ForeignKey(
        "teacher_panel.Aula",
        on_delete=models.PROTECT,
        db_column="aula_id",
        related_name="sessoes_chamada",
        null=True,
        blank=True,
    )
    sala = models.ForeignKey(
        "institution.Room",
        on_delete=models.PROTECT,
        db_column="sala_id",
        related_name="sessoes_chamada",
        null=True,
        blank=True,
    )
    professor = models.ForeignKey(
        "accounts.Professor",
        on_delete=models.PROTECT,
        db_column="professor_id",
        related_name="sessoes_chamada",
        null=True,
        blank=True,
    )

    # Definindo Colunas
    sequencia = models.IntegerField(default=1)
    tempos_cobertos = models.PositiveSmallIntegerField(default=1)
    limite_por_maquina = models.PositiveSmallIntegerField(default=1)
    agendamento = models.ForeignKey(
        "AgendamentoChamada",
        on_delete=models.SET_NULL,
        related_name="sessoes",
        null=True,
        blank=True,
    )
    faltas_registradas = models.BooleanField(default=False)
    abre_em = models.DateTimeField()
    fecha_em = models.DateTimeField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Nome que vai aparecer
    class Meta:
        db_table = "sessao_chamada"
        verbose_name = "Sessão de Chamada"
        verbose_name_plural = "Sessões de Chamada"
        ordering = ["-abre_em"]

    # Como vai retornar
    def __str__(self):
        aula_nome = f" - {self.aula.disciplina.nome}" if self.aula else ""
        return f"Sessão Chamada #{self.pk} (Seq {self.sequencia}){aula_nome} [{self.abre_em:%d/%m %H:%M}]"
