from django.db import models
from django.conf import settings


class Biometria(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="biometria",
    )
    embedding_cifrado = models.BinaryField()
    algoritmo_usado = models.CharField(max_length=50)
    dimensao = models.PositiveSmallIntegerField()
    qtd_amostras = models.PositiveSmallIntegerField(default=1)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "biometria"
        verbose_name = "Biometria"
        verbose_name_plural = "Biometrias"

