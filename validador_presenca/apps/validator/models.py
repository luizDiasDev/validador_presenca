from django.db import models

# Create your models here.

class PresencaRecord(models.Model):
    qr_token_hash = models.CharField(max_length=64)
    #localizacao = ""
    score_facial = models.DecimalField(max_digits=4, decimal_places=3)
    score_vida = models.DecimalField(max_digits=4, decimal_places=3)
    geo_valida = models.BooleanField()
    score_final =  models.DecimalField(max_digits=4, decimal_places=3)
    aprovado =  models.BooleanField()
    status = models.CharField(max_length=20)
    origem = models.CharField(max_length=50)
    revisado_por = models.IntegerField()
    motivo = models.TextField()
    data_revisao = models.DateTimeField(null=True, blank=True)
    data_decisao = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "registro_presenca"
        verbose_name = "Registro de Presença"
        verbose_name_plural = "Registros de Presença"