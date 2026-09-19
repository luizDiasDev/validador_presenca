from django.db import models

# Create your models here.

class AuditLog(models.Model):
    autor_id = models.IntegerField()
    ocorrido_em = models.DateField(auto_now_add=True)
    origem = models.CharField(max_length=50)
    acao = models.CharField(max_length=50)
    tabela = models.CharField(max_length=50)
    linha_tabela_id = models.BigIntegerField()

class Meta:
    db_table  = "log_auditoria"
    verbose_name = "Log de Auditoria"
    verbose_name_plural = "Logs de Auditoria"

