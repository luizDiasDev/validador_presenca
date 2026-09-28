from django.db import models
from django.conf import settings
from apps.institution.models import Institution

# Create your models here.

class Termo(models.Model):
    instituicao = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        db_column="instituicao_id",
        related_name="termos",
    )
    TIPO_POLITICA = 'politica_privacidade'
    TIPO_TERMO = 'termo_uso'
    TIPO_CHOICES = [
        (TIPO_POLITICA, 'Política de Privacidade'),
        (TIPO_TERMO, 'Termo de Uso'),
    ]
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    versao = models.CharField(max_length=20)
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    documento_hash = models.CharField(max_length=64)
    data_publicacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "termo"
        verbose_name = "Termo"
        verbose_name_plural = "Termos"
        ordering = ["-data_publicacao"]
        constraints = [
            models.UniqueConstraint(
                fields=["instituicao", "tipo", "versao"],
                name="unique_termo_versao_por_instituicao",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} v{self.versao}"


class AceiteTermo(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="aceites_termo",
    )
    termo = models.ForeignKey(
        Termo,
        on_delete=models.PROTECT,
        db_column="termo_id",
        related_name="aceites",
    )
    concedido = models.BooleanField()
    data_concedido = models.DateTimeField(auto_now_add=True)
    data_revogada = models.DateTimeField(null=True, blank=True)
    evidencia = models.JSONField(default=dict, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aceite_termo"
        verbose_name = "Aceite de Termo"
        verbose_name_plural = "Aceites de Termo"
        ordering = ["-data_concedido"]

    def __str__(self):
        acao = "aceitou" if self.concedido else "revogou"
        return f"{self.usuario} {acao} {self.termo}"


class SolicitacaoLGPD(models.Model):
    TIPO_REVOGAR_BIOMETRIA = "revogar_biometria"
    TIPO_EXCLUIR_CONTA = "excluir_conta"
    TIPO_EXPORTAR_DADOS = "exportar_dados"
    TIPO_CORRIGIR_DADOS = "corrigir_dados"

    TIPO_CHOICES = [
        (TIPO_REVOGAR_BIOMETRIA, "Revogar consentimento biométrico"),
        (TIPO_EXCLUIR_CONTA, "Excluir minha conta"),
        (TIPO_EXPORTAR_DADOS, "Exportar meus dados"),
        (TIPO_CORRIGIR_DADOS, "Corrigir dados incorretos"),
    ]

    STATUS_PENDENTE = "pendente"
    STATUS_EM_ANALISE = "em_analise"
    STATUS_ATENDIDA = "atendida"
    STATUS_RECUSADA = "recusada"

    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_EM_ANALISE, "Em análise"),
        (STATUS_ATENDIDA, "Atendida"),
        (STATUS_RECUSADA, "Recusada"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitacoes_lgpd",
    )
    tipo = models.CharField(max_length=32, choices=TIPO_CHOICES)
    justificativa = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    resposta_dpo = models.TextField(blank=True)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "solicitacao_lgpd"
        ordering = ["-data_solicitacao"]
        verbose_name = "Solicitação LGPD"
        verbose_name_plural = "Solicitações LGPD"

    def __str__(self):
        return f"#{self.pk} - {self.get_tipo_display()} - {self.usuario.email}"