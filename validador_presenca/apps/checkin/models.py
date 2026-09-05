from django.db import models

# Create your models here.

class Machine(models.Model):
    # Definindo Colunas
    apelido = models.CharField(max_length=20)
    codigo_pareamento = models.CharField(max_length=4, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    visto_em = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Nome que vai aparecer
    class Meta:
        db_table = "maquina"
        verbose_name = "Máquina"
        verbose_name_plural = "Máquinas"

    # Como vai retornar
    def __str__(self):
        return f"Máquina {self.codigo_pareamento}"

class ChamadaSession(models.Model):
    sequencia = models.IntegerField(default=1)
    abre_em = models.DateTimeField()
    fecha_em = models.DateTimeField()
    duracao_qr_s = models.PositiveSmallIntegerField(default=5)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sessao_chamada"
        verbose_name = "Sessão de Chamada"
        verbose_name_plural = "Sessões de Chamada"
        ordering = ["-abre_em"]

    def __str__(self):
        return f"Sessão Chamada #{self.pk}. Abre em: ({self.abre_em:%d/%m %H:%M}). Fecha em ({self.fecha_em:%d/%m %H:%M})"