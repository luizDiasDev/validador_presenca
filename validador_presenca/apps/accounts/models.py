from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser, UserManager
from apps.institution.models import Institution

class UsuarioManager(UserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        return super().create_user(
            username = email,
            email = email,
            password = password,
            **extra_fields
        )

    def create_superuser(self, email=None, password=None, **extra_fields):
        return super().create_superuser(
            username = email,
            email = email,
            password = password,
            **extra_fields
        )

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    instituicao = models.ForeignKey(
        Institution,
        on_delete = models.PROTECT,
        db_column = "instituicao_id",
        related_name =  "usuarios",
        null = True,
        blank =True,
    )
    totp_cifrado = models.BinaryField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD =  "email"
    REQUIRED_FIELDS = []

    def save(self, *args,  **kwargs):
        if not self.username:
            self.username = self.email
        #super é para executar o save da classe pai
        super().save(*args, **kwargs)

    class Meta:
        db_table = "usuario"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"


class Administrador(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete = models.CASCADE,
        db_column  = "id_usuario",
        related_name = "administrador",
    )
    cargo = models.CharField(max_length=100)

    class Meta:
        db_table = "administrador"
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"


class Professor(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete = models.CASCADE,
        db_column = "id_usuario",
        related_name = "professor",
    )
    area_atuacao = models.CharField(max_length=100)

    class Meta:
        db_table = "professor"
        verbose_name = "Professor"
        verbose_name_plural = "Professores"