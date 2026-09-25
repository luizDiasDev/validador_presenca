from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser
from apps.institution.models import Institution

class Usuario(AbstractUser):
    instituicao = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        db_column="instituicao_id",
        related_name="usuarios",
    )
    totp_cifrado = models.BinaryField(null=True, blank=True)

    class Meta:
        db_table = "usuario"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"


class Administrador(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        db_column="id_usuario",
        related_name="administrador",
    )
    cargo = models.CharField(max_length=100)

    class Meta:
        db_table = "administrador"
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"


class Professor(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        db_column="id_usuario",
        related_name="professor",
    )
    area_atuacao = models.CharField(max_length=100)

    class Meta:
        db_table = "professor"
        verbose_name = "Professor"
        verbose_name_plural = "Professores"