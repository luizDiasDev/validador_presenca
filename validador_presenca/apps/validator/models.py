from django.conf import settings
from django.db import models


class PresencaRecord(models.Model):
    sessao = models.ForeignKey(
        "checkin.ChamadaSession",
        on_delete=models.SET_NULL,
        db_column="sessao_id",
        related_name="registros_presenca",
        null=True,
        blank=True,
    )
    maquina = models.ForeignKey(
        "institution.Machine",
        on_delete=models.SET_NULL,
        db_column="maquina_id",
        related_name="registros_presenca",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="usuario_id",
        related_name="registros_presenca",
        null=True,
        blank=True,
    )
    qr_token_hash = models.CharField(max_length=64)
    score_facial = models.DecimalField(max_digits=4, decimal_places=3)
    score_vida = models.DecimalField(max_digits=4, decimal_places=3)
    geo_valida = models.BooleanField()
    score_final = models.DecimalField(max_digits=4, decimal_places=3)
    aprovado = models.BooleanField()
    status = models.CharField(max_length=20)
    origem = models.CharField(max_length=50)
    revisado_por = models.IntegerField(null=True, blank=True)
    motivo = models.TextField()
    data_revisao = models.DateTimeField(null=True, blank=True)
    data_decisao = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "registro_presenca"
        verbose_name = "Registro de Presença"
        verbose_name_plural = "Registros de Presença"
